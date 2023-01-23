#!/usr/bin/env python3
import usb.core, usb.util
import utils, oem, sdp, flashloader
import sys
import struct

deviceFilters = [
    # flashloader
    {
        'vendorId': 0x15a2,
        'productId': 0x0073,
    },
    # OEM
    {
        'vendorId': 0x18d1,
        'productId': 0x9400
    },
    # bootloader
    {
        'vendorId': 0x18d1,
        'productId': 0x946b
    },
    # sdp
    {
        'vendorId': 0x1fc9,
        'productId': 0x0135
    }
]

mcuTypes = {
    0x6C0000: '106XA0',
    0x6C0001: '106XA1',
}

flashTypes = {
    0x17C8: 'Giga-16m',
    0x17EF: 'Winbond-16m',
}

def printInfo(dev):
    _oem = oem.OEM(dev)
    print('Controller serial number: ' + dev.serial_number)

    prefix = dev.serial_number[0:2]
    if prefix in ['91', '92', '93', '94']:
        print('Warning: Unable to flash devices with serial number prefix ' + prefix)
        sys.exit(1)

    device_type = ''
    if prefix in ['95', '96', '97'] or (prefix == '98' and int(dev.serial_number[0:4], 16) <= 0x9809):
        device_type = 'dvt'
    else:
        device_type = 'pvt'

    print('Controller is a ' + device_type + ' device')

    fw_ver = _oem.get_firmware_version()
    fw_name = 'gotham' if fw_ver < 320480 else 'bruce'
    print(f'Current firmware is {fw_name} build {fw_ver}')

    battery_level = _oem.get_battery_percentage()
    print(f'Current battery level: {battery_level}%')

def loadFlashloader(dev):
    fl = b''
    if len(sys.argv) < 3:
        fl = utils.get_data_file('restricted_ivt_flashloader.bin')
    else:
        fl = utils.get_file(sys.argv[2])

    print(f'flashloader image is {len(fl)} bytes')

    _sdp = sdp.SDP(dev)

    # write file to memory
    result = _sdp.write_file(0x20000000, fl)
    print(f'SDP load result: 0x{result:08x}')

    # jump to loaded file
    _sdp.jump_address(0x20000400)

def detectMCUType(fl):
    mcu_type = fl.read32(0x400D8260)
    if mcu_type not in mcuTypes.keys():
        print(f'Unknown MCU type for 0x{mcu_type:04x}')
        sys.exit(1)

    print(f'MCU: {mcu_type:x} ({mcuTypes[mcu_type]})')

class ReadFailedException(Exception):
    """Exception while reading"""

def writeFlashRegister(fl, reg, val, mask=False):
    if mask:
        cur = fl.read32(0x402A8000 + reg)
        if cur == None:
            raise ReadFailedException("Failed to read register for masking")

        val = cur | val
        if val == cur:
            return

    fl.set32(0x402A8000 + reg, val)

def flashRead32(fl, offset, size):
    # FLSHCR2 |= 0x80000000
    writeFlashRegister(fl, 0x80, 0x80000000, True)
    # INTR |= 0x1e
    writeFlashRegister(fl, 0x14, 0x1e, True)
    # IPCR0 = offset
    writeFlashRegister(fl, 0xA0, offset)
    # IPRXFCR = 1
    writeFlashRegister(fl, 0xB8, 1)
    # IPTXFCR = 1
    writeFlashRegister(fl, 0xBC, 1)
    # seqId 0 == read/device_id depending on configuration block
    # IPCR1 = FLEXSPI_IPCR1_ISEQID(0) | FLEXSPI_IPCR1_IDATSZ(4)
    writeFlashRegister(fl, 0xA4, size & 0xffff)
    # IPCMD = 1
    writeFlashRegister(fl, 0xB0, 1)
    # ret = RFDR[0]
    ret = fl.read32(0x402A8100)
    if ret == None:
        raise ReadFailedException("Failed to read RFDR")
    return ret

def detectFlashType(fl):
    # load the get_vendor_id configuration block
    fcb = utils.get_data_file('flashloader_fcb_get_vendor_id.bin')
    fl.write_memory(0x2000, fcb)
    fl.configure_memory(9, 0x2000)

    # read from offset 0 (Read Device ID with get_vendor_id configuration)
    flash_type = flashRead32(fl, 0, 2)
    if flash_type not in flashTypes.keys():
        print(f'Unknown flash type for 0x{flash_type:04x}')
        sys.exit(1)

    print(f'Flash: {flash_type:x} ({flashTypes[flash_type]})')
    return flashTypes[flash_type]

def setupFlash(fl, name):
    if name == 'Giga-16m':
        fl.set32(0x2000, 0xC0000206)
    elif name == 'Winbond-16m':
        fcb = utils.get_data_file('flashloader_fcb_w25q128jw.bin')
        fl.write_memory(0x2000, fcb)
    else:
        print('unknown flash type ' + name)
        sys.exit(1)

    fl.configure_memory(9, 0x2000)

class FirmwareBuildInfo:
    bootable = False
    ivt_offset = 0
    ivt_size = 0x1000
    partition_info = None
    reset_handler_address = 0

    class Partition:
        name = ''
        offset = 0
        size = 0
        slot = 0

        def __init__(self, reset_handler_address):
            if 0x60040000 <= reset_handler_address and 0x60800000 >= reset_handler_address:
                self.name = "Application A"
                self.offset = 0x60040000
                self.size = 0x7C0000
                self.slot = 1
            elif 0x60840000 <= reset_handler_address and 0x61000000 >= reset_handler_address:
                self.name = "Application B"
                self.offset = 0x60840000
                self.size = 0x7C0000
                self.slot = 2
            elif 0x60800000 <= reset_handler_address and 0x60802000 >= reset_handler_address:
                self.name = "Bootloader A"
                self.offset = 0x60800000
                self.size = 0x20000
                self.slot = 3
            elif 0x60820000 <= reset_handler_address and 0x60822000 >= reset_handler_address:
                self.name = "Bootloader B"
                self.offset = 0x60820000
                self.size = 0x20000
                self.slot = 4
            else:
                print(f'Cannot determine partition for reset handler: {reset_handler_address:08x}')
                sys.exit(1)

    def __init__(self, data):
        # check if bootloader
        self.bootable = struct.unpack('>I', data[0:4])[0] == 0xd1002041
        build_info_offset = 0x400
        if self.bootable:
            build_info_offset += 0x1000
        build_info = data[build_info_offset:build_info_offset+0x100]

        # parse build info
        header, unk0, size = struct.unpack('<III', build_info[0:12])
        footer, = struct.unpack('<I', build_info[0xFC:0x100])
        if header != 0x747315A2:
            print(f'Invalid build info. Expected header of 0x747315A2, got 0x{header:08x} instead')
            sys.exit(1)
        if footer != 0x4786CD88:
            print(f'Invalid build info. Expected footer of 0x4786CD88, got 0x{header:08x} instead')
            sys.exit(1)
        if size != 0x100:
            print('Unexpected build info size: {buildInfo.size}')

        # get reset handler address
        reset_handler_offset = 4
        if self.bootable:
            reset_handler_offset += 0x1000
        self.reset_handler_address = struct.unpack('<I', data[reset_handler_offset:reset_handler_offset+4])[0]

        # get partition info based on reset handler
        self.partition_info = FirmwareBuildInfo.Partition(self.reset_handler_address)

def flashFirmware(dev):
    if len(sys.argv) < 3:
        print('Usage:\npython3 python3 stadiatool.py flash_firmware <firmware_signed.bin>')
        sys.exit(1)

    fw = utils.get_file(sys.argv[2])
    fw_info = FirmwareBuildInfo(fw)

    fl = flashloader.Flashloader(dev)

    print('Detecting MCU type...')
    detectMCUType(fl)
    print('Detecting Flash type...')
    flash_type = detectFlashType(fl)
    print('Setting up flash')
    setupFlash(fl, flash_type)

    print('Clearing GPR flags')
    fl.set32(0x400F8030, 0) # GPR 4
    fl.set32(0x400F8034, 0) # GPR 5
    fl.set32(0x400F8038, 0) # GPR 6

    if fw_info.bootable:
        print('Extracting IVT and flashing')
        ivt = fw[fw_info.ivt_offset:fw_info.ivt_offset+fw_info.ivt_size]
        fl.flash_erase_region(0x60001000, len(ivt))
        fl.write_memory(0x60001000, ivt)

    print(f'Flashing to {fw_info.partition_info.name} at 0x{fw_info.partition_info.offset:08x}...')
    fl.flash_erase_region(fw_info.partition_info.offset, len(fw))
    fl.write_memory(fw_info.partition_info.offset, fw)

    # set GPR 6 to slot
    if fw_info.partition_info.slot == 1:
        fl.set32(0x400F8038, 1)
    elif fw_info.partition_info.slot == 2:
        fl.set32(0x400F8038, 2)

    print('Resetting device')
    fl.reset()

    print('Done!')

def dumpFlash(dev):
    if len(sys.argv) < 5:
        print('Usage:\npython3 stadiatool.py dump <start> <end> <dump.bin>')
        sys.exit(1)

    offset = int(sys.argv[2])
    end = int(sys.argv[3])

    fl = flashloader.Flashloader(dev)

    print('Detecting MCU type...')
    detectMCUType(fl)
    print('Detecting Flash type...')
    flash_type = detectFlashType(fl)
    print('Setting up flash')
    setupFlash(fl, flash_type)

    with open(sys.argv[4], 'wb') as f:
        for i in range(offset // 4, end // 4):
            while True:
                try:
                    flash_data = struct.pack('<I', flashRead32(fl, i * 4))
                except ReadFailedException as e:
                    print(f'\nFailed to read from 0x{i * 4:08x} ({e}), trying again...')
                    continue
                print(f'\rReading [0x{i * 4:08x} / 0x{end:08x}]', end='')
                f.write(flash_data)
                break
        print('')

    print('Done!')

def reset(dev):
    fl = flashloader.Flashloader(dev)
    fl.reset()

if len(sys.argv) < 2:
    print(f'Usage: {sys.argv[0]} <info/flashloader/flash_firmware/dump/reset>')
    sys.exit(1)

dev = usb.core.find(custom_match=lambda dev: any([True for f in deviceFilters if f['vendorId'] == dev.idVendor and f['productId'] == dev.idProduct]))
if not dev:
    print('Could not find stadia controller')
    sys.exit(1)

print(f'Found: {dev.idVendor:04x}:{dev.idProduct:04x} ({dev.manufacturer} {dev.product})')

# detach kernel driver if active
if dev.is_kernel_driver_active(0):
    dev.detach_kernel_driver(0)

if sys.argv[1] == 'info':
    printInfo(dev)
elif sys.argv[1] == 'flashloader':
    loadFlashloader(dev)
elif sys.argv[1] == 'flash_firmware':
    flashFirmware(dev)
elif sys.argv[1] == 'dump':
    dumpFlash(dev)
elif sys.argv[1] == 'reset':
    reset(dev)
else:
    print(f'Unknown arg "{sys.argv[1]}"')
    sys.exit(1)
