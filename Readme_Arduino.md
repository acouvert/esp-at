./build.py install
> {"platform": "PLATFORM_ESP32", "module": "ESP32-D2WD", "description": "2MB flash, No OTA", "silence": 0}

./build.py menuconfig
> CONFIG_ESP_CONSOLE_NONE=y
> CONFIG_AT_UART_DEFAULT_FLOW_CONTROL=0

./build.py clean
./build.py build

Download build/factory/factory_ESP32-D2WD.bin

Flash  python esp-idf/components/esptool_py/esptool/esptool.py -p /dev/ttyACM0 -b 115200 --before default_reset --after hard_reset --chip esp32  write_flash -z 0 /mnt/c/Users/acouvert/Downloads/factory_ESP32-D2WD.bin