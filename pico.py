from machine import Pin
from time import sleep_ms, ticks_us, ticks_diff

from neopixel import NeoPixel

from frame import imageIndexToFrameIndex

import sys
import struct

from array import array

ledCount = 1280
ledPin = Pin(22, Pin.OUT)
pixels = NeoPixel(ledPin, ledCount)
data = None
paletteSize = 16 * 3 # 16 colors on 3 bytes
workPalette = bytearray(paletteSize)

ledIndexLut = array('H', (imageIndexToFrameIndex(i) for i in range(ledCount)))

def rotate():
    n = pixels.n
    rn, gn, bn = pixels[n - 1]
    for i in reversed(range(1, n)):
        pixels[i] = pixels[i - 1]
    pixels[0] = (rn, gn, bn)
    pixels.write()
    
offset = 0

def chenillard():
    global offset
    pixels.fill((0, 0, 0))
    index = imageIndexToFrameIndex(offset % ledCount)
    pixels[index] = (30, 30, 30)
    pixels.write()
    offset += 1

def run2():
    pixels[0] = (30, 0, 0)
    pixels.write()
    print('Light on first pixel')
#    offset += 1

def run():
    pixels[0] = (0, 30, 0)
    pixels.write()
    print('Light on first pixel')
    
# #    rotate(pixels)
# #    print('Rotation')
#     while True:
# #        sleep_ms(100)
#         rotate()
# #        print('Rotation')
    
def openFile(path):
    global data
    with open(path, 'rb') as f:
        data = f.read()
    print(len(data))
    print(data[0], data[1], data[2], data[3], data[4])
    if data[0] != 87 or data[1] != 76:
        print('Unknown file')
        return False
    if data[2] != 1: # TODO Move to config
        print(f'Bad file version: {data[2]}')
        return False
    if data[3] != 32: # TODO Move to config
        print(f'Bad width: {data[3]}')
        return False
    if data[4] != 40: # TODO Move to config
        print(f'Bad height: {data[4]}')
        return False
    return True

@micropython.native
def drawSprite(
    spriteIndex, spriteWidth, spriteHeight,
    frameWidth, frameHeight, offsetX, offsetY,
    isHorizontallyMirrored, isVerticallyMirrored,
):
    _data = data                # globales -> locales
    _palette = workPalette
    _buf = pixels.buf
    _lut = ledIndexLut

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
            lbase = _lut[index] * 3
            _buf[lbase]     = _palette[pbase]
            _buf[lbase + 1] = _palette[pbase + 1]
            _buf[lbase + 2] = _palette[pbase + 2]
            index += 1

    pixels.write()

    
def displayFrame(
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
    t0 = ticks_us()
    
    #print(f'Display frame: {frameIndex}')
    frameByteIndex = frameStartIndex + frameIndex * frameSize
    spriteNumber = data[frameByteIndex]
    #print(f'Sprite index: {spriteNumber}')
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
    
    drawSprite(spriteIndex, spriteWidth, spriteHeight, 32, 40, offsetX, offsetY, horizontallyMirrored, verticallyMirrored)
    
    dt = ticks_diff(ticks_us(), t0)
    print(f'Frame {frameIndex}: {dt} us ({dt / 1000:.1f} ms)')

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

    for i in range(frameCount):
        displayFrame(i, frameStartIndex, frameSize, paletteStartIndex, paletteSize, spriteStartIndex, spriteSize, spriteWidth, spriteHeight)

def clear():
    pixels.fill((0, 0, 0))
    pixels.write()

print('Run')

ready = openFile('anims/sonic.wl')
print(f'File opened: {ready}')

if ready== False:
    sys.exit()
    
try:
    playAnimation()
except KeyboardInterrupt:
    print("Arrêt demandé")
finally:
    clear()

#while True:
#    chenillard()
