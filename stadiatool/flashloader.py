import hid
import usb.core, usb.util
import struct

class FlashloaderError(Exception):
    """Generic error while in Flashloader"""

class CommandFailedError(FlashloaderError):
    """A command has failed"""

class Flashloader:
    Command_FlashEraseAll           = 0x01
    Command_FlashEraseRegion        = 0x02
    Command_ReadMemory              = 0x03
    Command_WriteMemory             = 0x04
    Command_FillMemory              = 0x05
    Command_FlashSecurityDisable    = 0x06
    Command_GetProperty             = 0x07
    Command_Execute                 = 0x09
    Command_FlashReadResource       = 0x10
    Command_Call                    = 0x0a
    Command_Reset                   = 0x0b
    Command_SetProperty             = 0x0c
    Command_FlashEraseAllUnsecure   = 0x0d
    Command_eFuseProgram            = 0x0e
    Command_eFuseRead               = 0x0f
    Command_FlashReadResource       = 0x10
    Command_ConfigureMemory         = 0x11
    Command_ReliableUpdate          = 0x12

    Response_Generic            = 0xa0
    Response_ReadMemory         = 0xa3
    Response_GetProperty        = 0xa7
    Response_FlashReadOnce      = 0xaf
    Response_FlashReadResource  = 0xb0

    device = None
    hid = None

    def __init__(self, device: usb.core.Device):
        self.device = device
        if device.idVendor != 0x15a2 or device.idProduct != 0x0073:
            raise FlashloaderError('Not in flashloader')

        self.hid = hid.HID(device)

    def send_frame(self, report_id, data):
        cmd = struct.pack('<BBH', report_id, 0, len(data)) + data
        self.hid.write_report(cmd)

    def receive_frame(self, wait=None):
        report = self.hid.read_report(wait)
        if not report:
            return None

        _unk0, size = struct.unpack('<BH', report[1:4])
        return (report[0], report[4:4+size])

    def handle_response(self, resp) -> bool:
        tag, flags, _reserved, num_parameters = struct.unpack('<BBBB', resp[0:4])
        parameters = []
        for i in range(num_parameters):
            parameters += struct.unpack('<I', resp[4 + (i * 4):8 + (i * 4)])

        if tag == Flashloader.Response_Generic:
            if parameters[0] != 0:
                raise CommandFailedError(
                    f'Command 0x{parameters[1]:02x} failed with status 0x{parameters[0]:x}',
                    parameters[0], parameters[1]
                )
        elif tag == Flashloader.Response_ReadMemory:
            if parameters[0] != 0:
                raise CommandFailedError(
                    f'ReadMemory failed with status 0x{parameters[0]:x}',
                    parameters[0]
                )

        # lowest flags bit indicates more data follows
        return flags & 1

    def receive_response(self) -> bytes:
        """
        Receives a response.
        Returns optional data received in data stage, or raises an exepction on error.
        """

        data = b''
        while True:
            frame = self.receive_frame(1)
            #print(frame)

            # response
            if frame[0] == 0x03:
                if not self.handle_response(frame[1]):
                    return data

            # data
            elif frame[0] == 0x04:
                data += frame[1]

    def send_command(self, tag, flags, parameters):
        cmd = struct.pack('<BBBB', tag, flags, 0, len(parameters))
        for p in parameters:
            cmd += struct.pack('<I', p)
        return self.send_frame(1, cmd)

    def flash_erase_region(self, address, size):
        # erase in 16k regions
        while size > 0:
            toErase = 0x4000 if size > 0x4000 else size
            self.send_command(Flashloader.Command_FlashEraseRegion, 0, [address, toErase, 0])
            self.receive_response()

            address += toErase
            size -= toErase

    def read_memory(self, address, size):
        self.send_command(Flashloader.Command_ReadMemory, 0, [address, size, 0])
        return self.receive_response()

    def write_memory(self, address, data):
        self.send_command(Flashloader.Command_WriteMemory, 1, [address, len(data), 0])
        self.receive_response()

        # start data stage
        # send data in 512 byte chunks (max packet size)
        bytesSent = 0
        while (bytesSent < len(data)):
            toSend = min(bytesSent + 512, len(data))

            frame = data[bytesSent:toSend]
            self.send_frame(2, frame)

            bytesSent = toSend

        self.receive_response()

    def fill_memory(self, address, size, pattern):
        self.send_command(Flashloader.Command_FillMemory, 0, [address, size, pattern])
        self.receive_response()

    def reset(self):
        self.send_command(Flashloader.Command_Reset, 0, [])
        self.receive_response()

    def configure_memory(self, type, address):
        self.send_command(Flashloader.Command_ConfigureMemory, 0, [type, address])
        self.receive_response()

    def read32(self, address):
        data = self.read_memory(address, 4)
        if len(data) != 4:
            return None

        return struct.unpack('<I', data)[0]

    def set32(self, address, value):
        # Use a 4-byte fill to avoid requiring a data stage
        self.fill_memory(address, 4, value)
