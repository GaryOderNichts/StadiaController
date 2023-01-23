# stadiatool
Tool to interact with the Stadia Controller.  

> :warning: Use at your own risk. This tool can put your controller into a non-usable state.  
> Consider reading the [blog post](https://garyodernichts.blogspot.com/2023/01/looking-into-stadia-controller.html) to understand how the flashing process works, before using any of this.

## Usage
Place `flashloader_fcb_*.bin` and other required files into a `data` directory (See [Files](../README.md#files)).

### info
Prints info which can be retrieved while in OEM mode.
```
Usage:
python3 stadiatool.py info
```

### flashloader
Loads a flashloader file while in SDP mode.
```
Usage:
python3 stadiatool.py flashloader [restricted_ivt_flashloader.bin]
```

### flash_firmware
Flashes a firmware file while in flashloader.  
> :warning: Do not try to flash incompatible firmwares.  
> When in doubt, don't flash a firmware.
```
Usage:
python3 stadiatool.py flash_firmware <firmware_signed.bin>
```

### dump
Dumps a region from flash (slow!) while in flashloader.
```
Usage:
python3 stadiatool.py dump <start> <end> <dump.bin>
```

### reset
Resets the controller while in flashloader.
```
Usage:
python3 stadiatool.py reset [slot]
```

## Disclaimer
This tool was written in a rush and has not been tested properly, use at your own risk.  
Only tested on Linux with a `Google LLC Stadia Controller rev. A`.
