#!/usr/bin/env python3
import sys

def read32(data, offset):
    return (
        data[offset + 3] << 24 |
        data[offset + 2] << 16 | 
        data[offset + 1] << 8  |
        data[offset + 0]
    )

def read16(data, offset):
    return (
        data[offset + 1] << 8  |
        data[offset + 0]
    )

def printSeq(data, offset, count):
    for i in range(count):
        print(f'\tseqNum: {data[offset + i * 4]:02x}')
        print(f'\tseqIdx: {data[offset + i * 4 + 1]:02x}')

def printLutSeq(data, offset, count):
    for i in range(count):
        print(f'\t{i}:')
        for j in range(4):
            seq = read32(data, offset + (i * 4 * 4) + j * 4)
            print(f'\t\tFLEXSPI_LUT_SEQ({(seq & 0xfc00) >> 10:02x}, {(seq & 0x300) >> 8:02x}, {seq & 0xff:02x}, {(seq & 0xfc000000) >> 26:02x}, {(seq & 0x3000000) >> 24:02x}, {(seq & 0xff0000) >> 16:02x})')

if len(sys.argv) != 2:
    print(f'Usage:\npython3 {sys.argv[0]} <fcb.bin>')
    sys.exit(1)

block = b''
with open(sys.argv[1], 'rb') as f:
    block = f.read()

tag = read32(block, 0x000)
print(f'Tag: {tag:08x}')
if tag != 0x42464346:
    print('Invalid FlexSPI NOR Configuration Block')
    sys.exit(1)

print(f'Version: {read32(block, 0x004):08x}')
print(f'readSampleClkSrc: {block[0x00c]:02x}')
print(f'csHoldTime: {block[0x00d]:02x}')
print(f'csSetupTime: {block[0x00e]:02x}')
print(f'columnAdressWidth: {block[0x00f]:02x}')
print(f'deviceModeCfgEnable: {block[0x010]:02x}')
print(f'deviceModeType: {block[0x011]:02x}')
print(f'waitTimeCfgCommands: {read16(block, 0x012):04x}')
print('deviceModeSeq:')
printSeq(block, 0x014, 1)
print(f'deviceModeArg: {read32(block, 0x018):08x}')
print(f'configCmdEnable: {block[0x01c]:02x}')
print(f'configModeType: {block[0x01d]:02x}{block[0x01e]:02x}{block[0x01f]:02x}')
print('configCmdSeqs:')
printSeq(block, 0x020, 3)
print(f'cfgCmdArgs: {read32(block, 0x030):08x} {read32(block, 0x034):08x} {read32(block, 0x038):08x}')
print(f'controllerMiscOption: {read32(block, 0x040):08x}')
print(f'deviceType: {block[0x044]:02x}')
print(f'sflashPadType: {block[0x045]:02x}')
print(f'serialClkFreq: {block[0x046]:02x}')
print(f'lutCustomSeqEnable: {block[0x047]:02x}')
print(f'sflashA1Size: {read32(block, 0x050):08x}')
print(f'sflashA2Size: {read32(block, 0x054):08x}')
print(f'sflashB1Size: {read32(block, 0x058):08x}')
print(f'sflashB2Size: {read32(block, 0x05c):08x}')
print(f'csPadSettingOverride: {read32(block, 0x060):08x}')
print(f'sclkPadSettingOverride: {read32(block, 0x064):08x}')
print(f'dataPadSettingOverride: {read32(block, 0x068):08x}')
print(f'dqsPadSettingOverride: {read32(block, 0x06c):08x}')
print(f'timeoutInMs: {read32(block, 0x070):08x}')
print(f'commandInterval: {read32(block, 0x074):08x}')
print(f'dataValidTime: {read32(block, 0x078):08x}')
print(f'busyOffset: {read16(block, 0x07c):04x}')
print(f'busyBitPolarity: {read16(block, 0x07e):04x}')
print('lookupTable:')
printLutSeq(block, 0x080, 16)
print('lutCustomSeq:')
printSeq(block, 0x180, 12)
print(f'pageSize: {read32(block, 0x1c0):08x}')
print(f'sectorSize: {read32(block, 0x1c4):08x}')
print(f'ipCmdSerialClkFreq: {read32(block, 0x1c8):08x}')
print(f'isUniformBlockSize: {read32(block, 0x1c9):08x}')
print(f'serialNorType: {block[0x1cc]:02x}')
print(f'needExitNoCmdMode: {read32(block, 0x1cd):08x}')
print(f'halfClkForNonReadCmd: {block[0x1ce]:02x}')
print(f'needrestorNoCmdMode: {block[0x1cf]:02x}')
print(f'blockSize: {read32(block, 0x1d0):08x}')
