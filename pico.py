from machine import Pin
from time import sleep_ms

from neopixel import NeoPixel

from frame import imageIndexToFrameIndex

import sys
import struct

ledCount = 1280
ledPin = Pin(22, Pin.OUT)
pixels = NeoPixel(ledPin, ledCount)
data = None

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
    
def displayFrame(frameIndex, frameStartIndex, frameSize, paletteStartIndex, paletteSize, spriteStartIndex, spriteSize):
    print(f'Display frame: {frameIndex}')
    frameByteIndex = frameStartIndex + frameIndex * frameSize
    spriteIndex = data[frameByteIndex]
    print(f'Sprite index: {spriteIndex}')
    (offsetX,) = struct.unpack_from('<H', data, spriteIndex + 1)
    (offsetY,) = struct.unpack_from('<H', data, spriteIndex + 3)
    paletteIndex = data[spriteIndex + 5]
    durationMs = data[spriteIndex + 6]
    brightness = data[spriteIndex + 7]
    horizontallyMirrored = data[spriteIndex + 8] > 0
    verticallyMirrored = data[spriteIndex + 8] > 0



print('Run')

ready = openFile('anims/sonic1frame.wl')
print(f'File opened: {ready}')

if ready== False:
    sys.exit()
    
frameStartIndex = 5
frameCount = data[frameStartIndex]
frameSize = 10  # TODO Move to config

frameByteCount = frameCount * frameSize

spriteWidth = data[frameStartIndex + frameByteCount + 1]
spriteHeight = data[frameStartIndex + frameByteCount + 2]

print(f'Sprite size: {spriteWidth}x{spriteHeight}')

paletteCount = data[frameStartIndex + frameByteCount + 3]
paletteSize = 16 * 3 # 16 colors on 3 bytes
paletteStartIndex = frameStartIndex + frameByteCount + 4

print(f'Palette count: {paletteCount}')

paletteByteCount = paletteCount * paletteSize

spriteCount = data[paletteStartIndex + paletteByteCount]
spriteSize = 32 * 40 / 2
spriteStartIndex = paletteStartIndex + paletteByteCount + 1

print(f'Sprite count: {spriteCount}')

displayFrame(0, frameStartIndex, frameSize, paletteStartIndex, paletteSize, spriteStartIndex, spriteSize)

#while True:
#    chenillard()
#chenillard()
#run2()

