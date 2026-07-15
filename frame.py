debug = False

def imageIndexToFrameIndex(imageIndex):
    panelOffset = getOffset(imageIndex)
    if (debug):
        print(f'panelOffset = {panelOffset}')
        
#     mod8 = imageIndex % 8
#     if (debug):
#         print(f'mod8 = {mod8}')

    div32 = imageIndex // 32
    if (debug):
        print(f'div32 = {div32}')
    
    column = getColumn(imageIndex)
    if (debug):
        print(f'column = {column}')
    
    mod2 = imageIndex % 2
    if (debug):
        print(f'mod2 = {mod2}')
    if (mod2 == 1):
        line = 7 - (div32 % 8)
    else:
        line = div32 % 8
    if (debug):
        print(f'line = {line}')
    return column + line + panelOffset
    
def getOffset(imageIndex):
    if (imageIndex in range(0, 256)):
        return 1024
    elif (imageIndex in range(256, 512)):
        return 768
    elif (imageIndex in range(512, 768)):
        return 512
    elif (imageIndex in range(768, 1024)):
        return 256
    else:
        return 0
    
def getColumn(imageIndex):
    mod32 = imageIndex % 32
    if (debug):
        print(f'mod32 = {mod32}')
    
    if  (imageIndex in range(256, 512) or imageIndex in range(768, 1024)):
        return mod32 * 8
    else:
        return (31 - mod32) * 8
    
def testIndex(imageIndex, expectedIndex):
    print(f'Get frame index for {imageIndex}')
    frameIndex = imageIndexToFrameIndex(imageIndex)
    print(f'frameIndex = {frameIndex}')
    print(f'expectedIndex = {expectedIndex}')
    if (expectedIndex == frameIndex):
        print('\033[32mSuccess\033[0m')
    else:
        print('\033[31mError\033[0m')
    print()

def testKeyValues():
    imageIndex = 0
    testIndex(imageIndex, 1272)
    imageIndex = 31
    testIndex(imageIndex, 1031)
    imageIndex = 224
    testIndex(imageIndex, 1279)
    imageIndex = 255
    testIndex(imageIndex, 1024)
    imageIndex = 256
    testIndex(imageIndex, 768)
    imageIndex = 287
    testIndex(imageIndex, 1023)
    imageIndex = 480
    testIndex(imageIndex, 775)
    imageIndex = 511
    testIndex(imageIndex, 1016)
    imageIndex = 512
    testIndex(imageIndex, 760)
    imageIndex = 543
    testIndex(imageIndex, 519)
    imageIndex = 736
    testIndex(imageIndex, 767)
    imageIndex = 767
    testIndex(imageIndex, 512)
