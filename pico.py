from machine import Pin
from time import sleep_ms

from neopixel import NeoPixel

from frame import imageIndexToFrameIndex

ledCount = 1280
ledPin = Pin(22, Pin.OUT)
pixels = NeoPixel(ledPin, ledCount)

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
    

print('Run')
while True:
    chenillard()
#chenillard()
#run2()

