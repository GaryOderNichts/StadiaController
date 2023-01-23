import usb.core, usb.util
import threading

class HIDError(Exception):
    """HID error"""

class HIDTimeoutError(HIDError):
    """Error if a timeout occurs"""

class HID:
    REPORT_QUEUE_SIZE = 30

    device = None

    thread = None

    in_endpoint = None
    out_endpoint = None

    report_ev = None
    report_queue = []

    def read_thread(self):
        while True:
            # try to read a report from the endpoint
            try:
                report = self.device.read(
                    self.in_endpoint.bEndpointAddress,
                    self.in_endpoint.wMaxPacketSize,
                    5000)
            except usb.core.USBTimeoutError:
                # no data, try again
                continue
            except usb.core.USBError:
                # stop read thread on error
                return

            # make sure we don't queue up too many reports
            if len(self.report_queue) == HID.REPORT_QUEUE_SIZE:
                self.report_queue.pop()

            # append report
            self.report_queue.append(report)
            self.report_ev.set()

    def __init__(self, device: usb.core.Device):
        self.device = device

        # set the configuration
        self.device.set_configuration()

        # find the hid interface
        interface = usb.util.find_descriptor(device.get_active_configuration(), bInterfaceClass = 3)
        if not interface:
            raise HIDError("No HID interface in device")

        # find hid endpoints
        for endpoint in interface:
            if usb.util.endpoint_type(endpoint.bmAttributes) == usb.util.ENDPOINT_TYPE_INTR:
                if usb.util.endpoint_direction(endpoint.bEndpointAddress) == usb.util.ENDPOINT_IN:
                    self.in_endpoint = endpoint
                elif usb.util.endpoint_direction(endpoint.bEndpointAddress) == usb.util.ENDPOINT_OUT:
                    self.out_endpoint = endpoint

        # need an in endpoint
        if not self.in_endpoint:
            raise HIDError("No IN endpoint")
        
        self.report_ev = threading.Event()

        thread = threading.Thread(daemon=True, target=HID.read_thread, args=(self,))
        thread.start()

    def write_report(self, report):
        if self.out_endpoint:
            return self.device.write(self.out_endpoint.bEndpointAddress, report)
        else:
            # use the ctrl endpoint if there is no interrupt out endpoint
            return self.device.ctrl_transfer(
                usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_INTERFACE | usb.util.CTRL_OUT,
                0x09, # SET_REPORT
                0x200 | report[0], # hid type + report id
                0x00,
                report
            )
    
    def read_report(self, wait=None):
        self.report_ev.clear()

        # handle empty queue
        if not self.report_queue:
            # if we don't specify a wait time return immediately
            if not wait:
                return None

            # wait for a report
            if not self.report_ev.wait(wait):
                raise HIDTimeoutError("read_report timed out, try replugging the device")

        # pop report from queue
        return self.report_queue.pop()
