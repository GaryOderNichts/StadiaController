import usb.core, usb.util
import struct
import time

class OEMError(Exception):
    """Generic error while in OEM mode"""

class OEM:
    device = None

    def __init__(self, device: usb.core.Device):
        self.device = device

        if not self.in_oem_mode():
            raise OEMError('Device not in OEM mode')

    def in_oem_mode(self):
        return self.device.idProduct == 0x9400 and self.device.idVendor == 0x18d1

    def get_firmware_version(self):
        # read firmware info
        fw_info = self.device.ctrl_transfer(
            usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE | usb.util.CTRL_IN,
            0x81,
            0,
            0,
            64
        )

        if not fw_info:
            return None

        # first 4 bytes contain the version
        return struct.unpack('<I', fw_info[0:4])[0]


    def get_battery_percentage(self):
        # request battery percentage
        self.device.ctrl_transfer(
            usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE | usb.util.CTRL_OUT,
            0x83
        )

        time.sleep(.1)

        # read battery percentage
        battery_level = self.device.ctrl_transfer(
            usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE | usb.util.CTRL_IN,
            0x84,
            0,
            0,
            64
        )

        if not battery_level:
            return None

        return struct.unpack('<H', battery_level)[0]
