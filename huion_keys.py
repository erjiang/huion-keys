#!/usr/bin/env python3
import os
import time
import signal
import argparse
import configparser

from _xdo_cffi import ffi, lib

CONFIG_FILE_PATH = None

TABLET_MODELS = {
    "Kamvas Pro (2019)": "256c:006e",
    "Q620M": "256c:006d",
}

BUTTON_BINDINGS = {}
BUTTON_BINDINGS_HOLD = {}
CYCLE_BUTTON = None
CYCLE_MODE = 1
CYCLE_MODES = 1
DIAL_MODES = {} 

def main():
    #Commandline arguments processing
    parser = argparse.ArgumentParser(
            description='Linux utility to create custom key bindings for the Huion Kamvas Pro (2019), Inspiroy Q620M, and potentially other tablets.')
    parser.add_argument('--rules', action='store_true', default=False,
                    help='print out the udev rules for known tablets and exit')
    parser.add_argument('-c', '--config', type=str,
                    help='location of config file, ~/.config/huion_keys.conf by default')
    args = parser.parse_args()
    if args.rules:
        make_rules()
        os._exit(0)

    global CONFIG_FILE_PATH
    if args.config is None:
        CONFIG_FILE_PATH = os.path.expanduser(os.path.join(
                os.getenv('XDG_CONFIG_HOME', default='~/.config'), 'huion_keys.conf'))
    else:
        CONFIG_FILE_PATH = os.path.expanduser(args.config)

    global CYCLE_MODES, CYCLE_MODE, CYCLE_BUTTON
    xdo = lib.xdo_new(ffi.NULL)
    if os.path.isfile(CONFIG_FILE_PATH):
        read_config(CONFIG_FILE_PATH)
    else:
        print("No config file found.")
        create_default_config(CONFIG_FILE_PATH)
        print("Created an example config file at " + CONFIG_FILE_PATH)
        return 1
    signal.signal(signal.SIGUSR1, handle_reload_signal) # Reload the config if recieved SIGUSR1
    prev_button = None
    while True:
        hidraw_path = None
        # search for a known tablet device
        for device_name, device_id in TABLET_MODELS.items():
            hidraw_path = get_tablet_hidraw(device_id)
            if hidraw_path is not None:
                print("Found %s at %s" % (device_name, hidraw_path))
                break
        if hidraw_path is None:
            print("Could not find tablet hidraw device")
            time.sleep(2)
            continue
        try:
            hidraw = open(hidraw_path, 'rb')
        except PermissionError as e:
            print(e)
            print("Trying again in 5 seconds...")
            time.sleep(5)
            continue
        while True:
            try:
                btn = get_button_press(hidraw)
            except OSError as e:
                print("Lost connection with the tablet - searching for tablet...")
                time.sleep(3)
                break
            print("Got button %s" % (btn,))
            if btn == CYCLE_BUTTON and CYCLE_BUTTON is not None:
               CYCLE_MODE = CYCLE_MODE + 1 
               if CYCLE_MODE > CYCLE_MODES:
                   CYCLE_MODE = 1
               print("Cycling to mode %s" % (CYCLE_MODE,)) 
            elif CYCLE_MODE in DIAL_MODES and btn in DIAL_MODES[CYCLE_MODE]:
                print("Sending %s from Mode %d" % (DIAL_MODES[CYCLE_MODE][btn], CYCLE_MODE),)
                lib.xdo_send_keysequence_window(
                        xdo, lib.CURRENTWINDOW, DIAL_MODES[CYCLE_MODE][btn], 1000)
            elif btn in BUTTON_BINDINGS_HOLD:
                print("Pressing %s" % (BUTTON_BINDINGS_HOLD[btn],))
                lib.xdo_send_keysequence_window_down(xdo, lib.CURRENTWINDOW, BUTTON_BINDINGS_HOLD[btn], 12000)
                get_button_release(hidraw)
                print("Releasing %s" % (BUTTON_BINDINGS_HOLD[btn],))
                lib.xdo_send_keysequence_window_up(xdo, lib.CURRENTWINDOW, BUTTON_BINDINGS_HOLD[btn], 12000)
            elif btn in BUTTON_BINDINGS:
                print("Sending %s" % (BUTTON_BINDINGS[btn],))
                lib.xdo_send_keysequence_window(
                    xdo, lib.CURRENTWINDOW, BUTTON_BINDINGS[btn], 1000)


def get_tablet_hidraw(device_id):
    """Finds the /dev/hidrawX file that belongs to the given device ID (in xxxx:xxxx format)."""
    # TODO: is this too fragile?
    hidraws = os.listdir('/sys/class/hidraw')
    for h in hidraws:
        device_path = os.readlink(os.path.join('/sys/class/hidraw', h, 'device'))
        if device_id.upper() in device_path:
            # need to confirm that there's "input" because there are two hidraw
            # files listed for the tablet, but only one of them carries the
            # mouse/keyboard input
            if os.path.exists(os.path.join('/sys/class/hidraw', h, 'device/input')):
                return os.path.join('/dev', os.path.basename(h))
    return None


def read_config(config_file):
    global CYCLE_MODES, CYCLE_MODE, CYCLE_BUTTON
    CONFIG = configparser.ConfigParser()
    CONFIG.read(config_file)
    # It is still better for performance to pre-encode these values
    for binding in CONFIG['Bindings']:
        if binding.isdigit():
        # store button configs with their 1-indexed ID
            BUTTON_BINDINGS[int(binding)] = CONFIG['Bindings'][binding].encode('utf-8')
        elif binding == 'scroll_up':
            BUTTON_BINDINGS['scroll_up'] = CONFIG['Bindings'][binding].encode('utf-8')
        elif binding == 'scroll_down':
            BUTTON_BINDINGS['scroll_down'] = CONFIG['Bindings'][binding].encode('utf-8')
        elif binding == 'dial_cw':
            BUTTON_BINDINGS['dial_cw'] = CONFIG['Bindings'][binding].encode('utf-8')
        elif binding == 'dial_ccw':
            BUTTON_BINDINGS['dial_ccw'] = CONFIG['Bindings'][binding].encode('utf-8')
        elif binding == '':
            continue # ignore empty line
        else:
            print("[WARN] unrecognized regular binding '%s'" % (binding,))
    #Same, but for buttons that should be held down
    if 'Hold' in CONFIG:
        for binding in CONFIG['Hold']:
            if binding.isdigit():
                BUTTON_BINDINGS_HOLD[int(binding)] = CONFIG['Hold'][binding].encode('utf-8')
            elif binding == '':
                continue
            else:
                print ("[WARN] unrecognized hold binding '%s'" % (binding,))
    # Assume that if cycle is assigned we have modes for now
    if 'Dial' in CONFIG:
        CYCLE_BUTTON = int(CONFIG['Dial']['cycle'])
        for key in CONFIG:
            if key.startswith("Mode"):
                # Count the modes
                mode = int(key.split(' ')[1]) 
                if mode > CYCLE_MODES:
                    CYCLE_MODES = mode
                DIAL_MODES[mode] = {}
                for binding in CONFIG[key]:
                    DIAL_MODES[mode][binding] = CONFIG[key][binding].encode('utf-8')


def handle_reload_signal(signum, frame):
    print("SIGUSR1 recieved - reloading config..")
    read_config(CONFIG_FILE_PATH)

def make_rules():
    for device_name, device_id in TABLET_MODELS.items():
        print("# %s" % (device_name, ))
        VID, PID = device_id.split(':')
        print('KERNEL=="hidraw*", ATTRS{idVendor}=="%s", ATTRS{idProduct}=="%s", MODE="0660", TAG+="uaccess"' % (VID, PID, ))

def create_default_config(config_file):
    with open(config_file, 'w') as config:
        config.write("""
# use one line for each button you want to configure
# buttons that aren't in this file will be ignored by this program
# (but may be handled by another driver)
[Bindings]
4=ctrl+s
5=ctrl+z
6=ctrl+shift+equal
7=ctrl+minus
# etc. up to the highest button number
16=Tab
scroll_up=bracketright
scroll_down=bracketleft
#Buttons that should be held instead of instantly firing
[Hold]
3=ctrl
#Q620M Dial
[Dial]
cycle = 9
[Mode 1]
dial_cw=6
dial_ccw=4
[Mode 2]
dial_cw=minus
dial_ccw=equal
""")


BUTTON_BITS = {
    0x01: 1,
    0x02: 2,
    0x04: 3,
    0x08: 4,
    0x10: 5,
    0x20: 6,
    0x40: 7,
    0x80: 8,
}

SCROLL_STATE=None

def get_button_press(hidraw):
    global SCROLL_STATE
    while True:
        sequence = hidraw.read(12)
        # 0xf7 is what my Kamvas Pro 22 reads
        # another model seems to send 0x08
        # Q620M reads as 0xf9
        if sequence[0] != 0xf7 and sequence[0] != 0x08 and sequence[0] != 0xf9:
            pass
        if sequence[1] == 0xe0: # buttons
            # doesn't seem like the tablet will let you push two buttons at once
            if sequence[4] > 0:
                return BUTTON_BITS[sequence[4]]
            elif sequence[5] > 0:
                # right-side buttons are 8-15, so add 8
                return BUTTON_BITS[sequence[5]] + 8
            else:
                # must be button release (all zeros)
                continue
        elif sequence[1] == 0xf0: # scroll strip
            scroll_pos = sequence[5]
            if scroll_pos == 0:
                # reset scroll state after lifting finger off scroll strip
                SCROLL_STATE = None
            elif SCROLL_STATE is not None:
                # scroll strip is numbered from top to bottom so a greater new
                # value means they scrolled down
                if scroll_pos > SCROLL_STATE:
                    SCROLL_STATE = scroll_pos
                    return 'scroll_down'
                elif scroll_pos < SCROLL_STATE:
                    SCROLL_STATE = scroll_pos
                    return 'scroll_up'
            else:
                SCROLL_STATE = scroll_pos
                continue
        elif sequence[1] == 0xf1: # dial on Q620M, practically 2 buttons
            if sequence[5] == 0x1:
                return 'dial_cw'
            elif sequence[5] == 0xff: 
                return 'dial_ccw'
        else:
            continue

def get_button_release(hidraw):
    while True:
        sequence = hidraw.read(12)
        if sequence[1] == 0xe0 and sequence[4] == 0 and sequence[5] == 0:
            return True


if __name__ == "__main__":
    main()
