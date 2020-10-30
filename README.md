# huion-keys

Linux utility to create custom key bindings for the Huion Kamvas Pro (2019).

![Image of Huion Kamvas Pro 22 (2019)](https://prd-huion.oss-accelerate.aliyuncs.com/5/739/kamvas-pro-22-pen-display-01.jpg)

## Requirements

* Linux
* Python 3 and development headers (python3-dev)
* libxdo and development headers (libxdo-dev)
* C compiler
* X server

## Installation

1. Install the requirements listed above.
2. Clone this repository.
3. Install the Python cffi module (either using Pipenv and the included Pipfile, through your system's package manager, or however you prefer to install Python packages).
4. Run the `xdo_build.py` script. It should create a file named `_xdo_cffi.cpython-...-linux-gnu.so`.
5. Run the `huion_keys.py`. It will create an example config file at `~/.config/huion_keys`.
6. Edit the config file to set up your key bindings. The key sequences are sent to xdotool, so look at xdotool's documentation for more details. There's also this [handy list of key codes](
    https://gitlab.com/cunidev/gestures/-/wikis/xdotool-list-of-key-codes
) that may be helpful.
7. Run `huion_keys.py` as root or give yourself read permission for your tablet's hidraw file. For example:
    `chmod o+r /dev/hidraw3`
8. When you push your tablet's buttons or swipe the scroll strips, this program should display information about what's going on.

## How does it work?

It works by listening on the tablet's hidraw interface for button presses and sending key events to X using xdotool.

## Does it work for other Huion tablets?

I'm not sure what other Huion tablets it works for, but you can open a Github issue if you have a Huion tablet and would like to help add support for it.
