import hid
import usb.core, usb.util
import struct

class SDPError(Exception):
    """Generic error while in SDP mode"""

class SDP:
    # command types
    COMMAND_READ_REGISTER   = 0x0101
    COMMAND_WRITE_REGISTER  = 0x0202
    COMMAND_WRITE_FILE      = 0x0404
    COMMAND_ERROR_STATUS    = 0x0505
    COMMAND_DCD_WRITE       = 0x0a0a
    COMMAND_JUMP_ADDRESS    = 0x0b0b

    device = None
    hid = None

    def __init__(self, device: usb.core.Device):
        self.device = device
        if device.idVendor != 0x1fc9 or device.idProduct != 0x0135:
            raise SDPError('Not in SDP mode')

        self.hid = hid.HID(device)

    def send_command(self, type, address, format, data_count, data):
        report = struct.pack(
            '>BHIBIIB',
            1, # report id
            type,
            address,
            format,
            data_count,
            data_count,
            0 # reserved
        )

        self.hid.write_report(report)

    def write_file(self, address, data):
        # send WRITE_FILE command
        self.send_command(
            SDP.COMMAND_WRITE_FILE,
            address,
            0,
            len(data),
            0
        )

        # start data stage
        # send data in 1024 byte chunks (max packet size)
        bytesSent = 0
        while (bytesSent < len(data)):
            toSend = min(bytesSent + 1024, len(data))

            report = data[bytesSent:toSend]
            report += b'\0' * (1024 - len(report))
            self.hid.write_report(b'\x02' + report)

            bytesSent = toSend

        # wait for result response
        while True:
            report = self.hid.read_report(.25)

            # hab mode
            if report[0] == 0x03:
                continue

            # result
            if report[0] == 0x04:
                return struct.unpack('>I', report[1:5])[0]

    def jump_address(self, address):
        # send command
        self.send_command(
            SDP.COMMAND_JUMP_ADDRESS,
            address,
            0,
            0,
            0
        )

        # don't read result after jump
