from machine import Pin
from time import sleep_us

import rp2

from frame import imageIndexToFrameIndex

import sys
import struct

ledCount = 1280
ledPin = 22  # GPIO number; the PIO drives it via side-set
data = None
paletteSize = 16 * 3  # 16 colors on 3 bytes
workPalette = bytearray(paletteSize)

# Image-index -> physical-LED-index permutation, precomputed once.
# Replaces the per-pixel call to imageIndexToFrameIndex() in the hot loop.
from array import array
ledIndexLut = array('H', (imageIndexToFrameIndex(i) for i in range(ledCount)))


# ---------------------------------------------------------------------------
# WS2812 PIO program: 800 kHz, 24 bits/pixel, MSB first.
# 10 SM cycles per bit -> run the SM at 8 MHz.
# ---------------------------------------------------------------------------
@rp2.asm_pio(
    sideset_init=rp2.PIO.OUT_LOW,
    out_shiftdir=rp2.PIO.SHIFT_LEFT,
    autopull=True,
    pull_thresh=24,
)
def _ws2812():
    T1 = 2
    T2 = 5
    T3 = 3
    wrap_target()
    label("bitloop")
    out(x, 1)               .side(0)    [T3 - 1]
    jmp(not_x, "do_zero")   .side(1)    [T1 - 1]
    jmp("bitloop")          .side(1)    [T2 - 1]
    label("do_zero")
    nop()                   .side(0)    [T2 - 1]
    wrap()


class Ws2812Dma:
    """Asynchronous WS2812 driver.

    The PIO state machine shifts the bit stream out on its own; a DMA channel
    feeds the state machine's TX FIFO straight from a frame buffer. Once a
    transfer is kicked off the CPU is free to render the next frame while the
    current one is streamed out. Two buffers ping-pong so rendering never
    touches the buffer being transferred.
    """

    def __init__(self, pin, n, smid=0):
        self.n = n
        self.sm = rp2.StateMachine(
            smid, _ws2812, freq=8_000_000, sideset_base=Pin(pin)
        )
        self.sm.active(1)

        # One 32-bit word per LED. We store the three colour bytes in natural
        # order at offsets +0/+1/+2 (the +3 byte stays 0); the DMA's bswap
        # then reverses each word into the MSB-first, left-justified 24-bit
        # layout the PIO expects. This keeps drawSprite's indexing natural.
        self.back = bytearray(4 * n)
        self.front = bytearray(4 * n)

        # DREQ index for this SM's TX FIFO: (pio_block << 3) + sm_index.
        treq = ((smid >> 2) << 3) + (smid & 3)

        self.dma = rp2.DMA()
        self._ctrl = self.dma.pack_ctrl(
            size=2,           # 32-bit transfers: one LED per transfer
            inc_read=True,    # walk through the frame buffer
            inc_write=False,  # always the same FIFO register
            treq_sel=treq,    # pace to the SM so the FIFO never overruns
            bswap=True,       # reverse bytes -> GRB ends up MSB-first
        )

    def send(self, buf):
        """Kick off the transfer of `buf` and return immediately."""
        self.dma.config(
            read=buf, write=self.sm, count=self.n, ctrl=self._ctrl, trigger=True
        )

    def wait(self):
        """Block until the in-flight frame is fully latched on the strip."""
        while self.dma.active():      # DMA still feeding the FIFO
            pass
        while self.sm.tx_fifo():      # FIFO still draining into the shifter
            pass
        sleep_us(300)                 # last word shift-out + WS2812 reset latch

    def present(self):
        """Swap buffers and start streaming the freshly rendered one."""
        self.front, self.back = self.back, self.front
        self.send(self.front)


strip = Ws2812Dma(ledPin, ledCount)


def openFile(path):
    global data
    with open(path, 'rb') as f:
        data = f.read()
    print(len(data))
    print(data[0], data[1], data[2], data[3], data[4])
    if data[0] != 87 or data[1] != 76:
        print('Unknown file')
        return False
    if data[2] != 1:  # TODO Move to config
        print(f'Bad file version: {data[2]}')
        return False
    if data[3] != 32:  # TODO Move to config
        print(f'Bad width: {data[3]}')
        return False
    if data[4] != 40:  # TODO Move to config
        print(f'Bad height: {data[4]}')
        return False
    return True


@micropython.native
def drawSprite(
    dst,
    spriteIndex,
    spriteWidth,
    spriteHeight,
    frameWidth,
    frameHeight,
    offsetX,
    offsetY,
    isHorizontallyMirrored,
    isVerticallyMirrored,
):
    _data = data          # globals -> locals for speed
    _pal = workPalette
    _lut = ledIndexLut
    _buf = dst

    baseY = spriteHeight - frameHeight
    index = 0
    for destY in range(frameHeight):
        srcYRow = destY + baseY - offsetY
        for destX in range(frameWidth):
            srcX = destX - offsetX
            srcY = srcYRow
            if isHorizontallyMirrored:
                srcX = spriteWidth - 1 - srcX
            if isVerticallyMirrored:
                srcY = spriteHeight - 1 - srcY

            paletteIndex = 0
            if 0 <= srcX < spriteWidth and 0 <= srcY < spriteHeight:
                p = srcY * spriteWidth + srcX
                byte = _data[spriteIndex + (p >> 1)]
                paletteIndex = (byte >> 4) if (p & 1) == 0 else (byte & 0xF)

            pbase = paletteIndex * 3
            # 4 bytes per LED. Colour bytes in natural order; +3 stays 0.
            # DMA bswap turns [c0, c1, c2, 0] into the wire order c0, c1, c2.
            wbase = _lut[index] << 2
            _buf[wbase]     = _pal[pbase]
            _buf[wbase + 1] = _pal[pbase + 1]
            _buf[wbase + 2] = _pal[pbase + 2]
            index += 1


def displayFrame(
    dst,
    frameIndex,
    frameStartIndex,
    frameSize,
    paletteStartIndex,
    paletteSize,
    spriteStartIndex,
    spriteSize,
    spriteWidth,
    spriteHeight,
):
    frameByteIndex = frameStartIndex + frameIndex * frameSize
    spriteNumber = data[frameByteIndex]
    (offsetX,) = struct.unpack_from('<h', data, frameByteIndex + 1)
    (offsetY,) = struct.unpack_from('<h', data, frameByteIndex + 3)
    paletteNumber = data[frameByteIndex + 5]
    durationMs = data[frameByteIndex + 6]
    brightness = data[frameByteIndex + 7]
    horizontallyMirrored = data[frameByteIndex + 8] > 0
    verticallyMirrored = data[frameByteIndex + 9] > 0

    paletteIndex = paletteStartIndex + paletteNumber * paletteSize
    for i in range(paletteSize):
        workPalette[i] = data[paletteIndex + i] * brightness // 255

    spriteIndex = spriteStartIndex + spriteNumber * spriteSize
    drawSprite(
        dst, spriteIndex, spriteWidth, spriteHeight, 32, 40,
        offsetX, offsetY, horizontallyMirrored, verticallyMirrored,
    )
    return durationMs


def playAnimation():
    frameCount = data[5]
    print(f'Frame count: {frameCount}')

    frameStartIndex = 6
    frameSize = 10  # TODO Move to config
    frameByteCount = frameCount * frameSize

    spriteWidth = data[frameStartIndex + frameByteCount]
    spriteHeight = data[frameStartIndex + frameByteCount + 1]
    print(f'Sprite size: {spriteWidth}x{spriteHeight}')

    paletteCount = data[frameStartIndex + frameByteCount + 2]
    paletteStartIndex = frameStartIndex + frameByteCount + 3
    print(f'Palette count: {paletteCount}')

    paletteByteCount = paletteCount * paletteSize

    spriteCount = data[paletteStartIndex + paletteByteCount]
    spriteSize = spriteWidth * spriteHeight // 2
    spriteStartIndex = paletteStartIndex + paletteByteCount + 1
    print(f'Sprite count: {spriteCount}')

    # Pipeline: render frame N+1 into the back buffer while the DMA streams
    # frame N out of the front buffer. Period = max(render, transfer).
    for i in range(frameCount):  # NOTE: frameCount, not frameByteCount
        displayFrame(
            strip.back, i, frameStartIndex, frameSize, paletteStartIndex,
            paletteSize, spriteStartIndex, spriteSize, spriteWidth, spriteHeight,
        )
        strip.wait()      # let the previous frame finish latching
        strip.present()   # swap + kick DMA on the frame we just rendered
        # TODO: pace to durationMs here (subtract the time already elapsed).


def clear():
    strip.wait()
    strip.send(bytearray(4 * ledCount))  # all zero
    strip.wait()


print('Run')

ready = openFile('anims/sonic.wl')
print(f'File opened: {ready}')

if ready == False:
    sys.exit()

try:
    playAnimation()
    strip.wait()  # make sure the very last frame is displayed before exiting
except KeyboardInterrupt:
    print("Arrêt demandé")
finally:
    clear()
