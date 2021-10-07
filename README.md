# huion-keys

Linux utility to create custom key bindings for the Huion Kamvas Pro (2019),
Inspiroy Q620M, and potentially other tablets.

![Image of Huion Kamvas Pro 22 (2019) and Inspiroy Q620M](https://i.imgur.com/zdBHGvX.png)

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
5. Run `huion_keys.py`. It will create an example config file at `~/.config/huion_keys.conf`.
6. Edit the config file to set up your key bindings. See the below section for more instructions. 
7. Install the udev rules to set up permissions for the tablet. This program
   can generate the udev rules for you, so you can do something like:
   `python huion_keys.py --rules > /etc/udev/rules.d/50-huion-tablet.rules`

   Alternatively, you can run `huion_keys.py` as root or give yourself read permission for your tablet's hidraw file. For example:
   `chmod o+r /dev/hidraw3`
8. When you push your tablet's buttons or swipe the scroll strips, this program should display information about what's going on.

## Configuration

The first time you start this program, it will create an example config file at `~/.config/huion_keys.conf`. The configuration file is in INI format that has, at minimum, a `[Bindings]` section.

Each button is numbered, so assigning button 3 to be "ctrl+z" looks like this:

```
[Bindings]
3=ctrl+z
```

The keys need to be in a format understood by xdotool, so look at xdotool's
documentation for more details. There's also this [handy list of key codes](
    https://gitlab.com/cunidev/gestures/-/wikis/xdotool-list-of-key-codes
) that may be helpful.

Normal key bindings are pressed and released immediately once you push down the button. If you need the keys to be held down for as long as you hold the button down, put its binding in the `[Hold]` section instead. This is useful for modifier keys such as the Control key.

```
[Hold]
4=ctrl
```

The scroll strip and rotating dial can be configured with the following button names:

* `scroll_up` and `scroll_down`
* `dial_cw` and `dial_ccw`

You can configure alternative bindings as separate "modes". For example, you can configure the dial knob to adjust brush size in one mode and zoom in a different mode. A separate button needs to be configured to switch to the next mode. Here's an example that uses button 9 to switch modes:

```
[Mode 1]
dial_cw=bracketright
dial_ccw=bracketleft

[Mode 2]
dial_cw=ctrl+shift+equal
dial_ccw=ctrl+minus

[Dial]
cycle=9
```

## How does it work?

It works by listening on the tablet's hidraw interface for button presses and sending key events to X using xdotool.

## Does it work for other Huion tablets?

I'm not sure what other Huion tablets it works for, but you can open a Github issue if you have a Huion tablet and would like to help add support for it.

The general process for adding a new tablet is:

1. Make the code detect your tablet based on USB Vendor and Product ID (see call to `get_tablet_hidraw()`.
2. Test all of the buttons, scroll strips, dials, etc.
3. Add support for any new buttons.


## Known Issues

### On some keyboard layouts, the keys sent by this program are incorrect

For example, on a Dvorak layout, this application may report that it sent "F"
but it actually results in a "Y" keypress.

As a workaround, try running `setxkbmap` without any arguments before running
this program.
