#!/usr/bin/env python3
import os
import time
import argparse
import threading
import yaml

from _xdo_cffi import ffi, lib
from dbus_daemon import DBusThread
from update import Update

CONFIG_FILE_PATH = None

TABLET_MODELS = {
    "Kamvas Pro (2019)": "256c:006e",
    "Q620M": "256c:006d",
    "H320M": "256c:006d"
}

BUTTON_BINDINGS = {}
BUTTON_BINDINGS_HOLD = {}
CYCLE_BUTTON = None
CYCLE_MODES = 1
DIAL_MODES = {}

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

update = Update()

def main():
    # Commandline arguments processing
    parser = argparse.ArgumentParser(
            description='Linux utility to create custom key bindings for the Huion Kamvas Pro (2019), Inspiroy Q620M, and potentially other tablets.')
    parser.add_argument('--rules', action='store_true', default=False,
                    help='print out the udev rules for known tablets and exit')
    parser.add_argument('-c', '--config', type=str,
                    help='location of config file, ~/.config/huion_keys.conf by default')
    args = parser.parse_args()
    if args.rules:
        make_rules()
        return 0

    global CONFIG_FILE_PATH
    if args.config is None:
        CONFIG_FILE_PATH = os.path.expanduser(os.path.join(
                os.getenv('XDG_CONFIG_HOME', default='~/.config'), 'huion_keys/default.conf'))
    else:
        CONFIG_FILE_PATH = os.path.expanduser(args.config)

    if os.path.isfile(CONFIG_FILE_PATH):
        read_config(CONFIG_FILE_PATH)
    else:
        print("No config file found.", flush=True)
        create_default_config(CONFIG_FILE_PATH)
        print("Created an example config file at " + CONFIG_FILE_PATH, flush=True)
        print("Additional application specific files can be created with <app_name>.conf", flush=True)
        return 1

    hidraw_paths = []
    dbus = DBusThread(update)
    dbus.start()
    while True:
        # search for a known tablet devices
        for device_name, device_id in TABLET_MODELS.items():
            hidraw_path = get_tablet_hidraw(device_id, device_name)
            if hidraw_path is not None:
                print("Found %s at %s" % (device_name, hidraw_path), flush=True)
                hidraw_paths = hidraw_paths + hidraw_path
        if not hidraw_paths:
            print("Could not find any tablet hidraw devices", flush=True)
            time.sleep(3)
            continue
        elif hidraw_paths:
            threads = []
            for hidraw_path in hidraw_paths:
                thread = PollThread(hidraw_path, update)
                # Do not let the threads to continue if main script is terminated
                thread.daemon = True
                threads.append(thread)
                thread.start()
            # TODO: Maybe should be reworked for the edge case of having more than one tablet connected at the same time.
            for thread in threads:
                thread.join()
            hidraw_paths.clear()
            continue


class PollThread(threading.Thread):

    cycle_mode = None
    scroll_state = None
    hidraw_path = None
    xdo = None

    def __init__(self, hidraw_path, update):
        super(PollThread, self).__init__()
        self.xdo = lib.xdo_new(ffi.NULL)
        self.hidraw_path = hidraw_path
        self.cycle_mode = 1
        update.subscribe(self.events)
    def run(self):
        global BUTTON_BINDINGS, BUTTON_BINDINGS_HOLD, CYCLE_MODES, CYCLE_BUTTON, DIAL_MODES
        while True:
            try:
                hidraw = open(self.hidraw_path, 'rb')
                break
            except PermissionError as e:
                print(e, flush=True)
                print("Trying again in 5 seconds...", flush=True)
                time.sleep(5)
                continue

        while True:
            name = ffi.new("unsigned char *[100]")
            type = ffi.new("int *")
            try:
                btn = self.get_button_press(hidraw)
            except OSError as e:
                print("%s lost connection with the tablet..." % (self.name,), flush=True)
                break
            print("Got button %s" % (btn,), flush=True)
            # w = ffi.new("Window *")
            # lib.xdo_get_active_window(self.xdo, w)
            # wid = ffi.unpack(w, 1)[0]
            # print(lib.xdo_get_pid_window(self.xdo, wid), flush=True)
            # lib.xdo_get_window_name(self.xdo, wid, name, ffi.new("int *", 100), type)
            # print(ffi.string(ffi.unpack(name, 1)[0], 100), flush=True)
            # print(wid, flush=True)
            if btn == CYCLE_BUTTON and CYCLE_BUTTON is not None:
                self.cycle_mode = self.cycle_mode + 1
                if self.cycle_mode > CYCLE_MODES:
                    self.cycle_mode = 1
                print("Cycling to mode %s" % (self.cycle_mode,), flush=True)
            elif self.cycle_mode in DIAL_MODES and btn in DIAL_MODES[self.cycle_mode]:
                print("Sending %s from Mode %d" % (DIAL_MODES[self.cycle_mode][btn], self.cycle_mode), flush=True)
                lib.xdo_send_keysequence_window(
                            self.xdo, lib.CURRENTWINDOW, DIAL_MODES[self.cycle_mode][btn], 1000)
            elif btn in BUTTON_BINDINGS_HOLD:
                print("Pressing %s" % (BUTTON_BINDINGS_HOLD[btn],), flush=True)
                lib.xdo_send_keysequence_window_down(self.xdo, lib.CURRENTWINDOW, BUTTON_BINDINGS_HOLD[btn], 12000)
                self.get_button_release(hidraw)
                print("Releasing %s" % (BUTTON_BINDINGS_HOLD[btn],), flush=True)
                lib.xdo_send_keysequence_window_up(self.xdo, lib.CURRENTWINDOW, BUTTON_BINDINGS_HOLD[btn], 12000)
            elif btn in BUTTON_BINDINGS:
                print("Sending %s" % (BUTTON_BINDINGS[btn],), flush=True)
                lib.xdo_send_keysequence_window(
                    self.xdo, lib.CURRENTWINDOW, BUTTON_BINDINGS[btn], 1000)

    def get_button_press(self, hidraw):
        while True:
            sequence = hidraw.read(12)
            # 0xf7 is what my Kamvas Pro 22 reads
            # another model seems to send 0x08
            # Q620M reads as 0xf9
            if sequence[0] != 0xf7 and sequence[0] != 0x08 and sequence[0] != 0xf9:
                pass
            if sequence[1] == 0xe0:  # buttons
                # doesn't seem like the tablet will let you push two buttons at once
                if sequence[4] > 0:
                    return BUTTON_BITS[sequence[4]]
                elif sequence[5] > 0:
                    # right-side buttons are 8-15, so add 8
                    return BUTTON_BITS[sequence[5]] + 8
                else:
                    # must be button release (all zeros)
                    continue
            elif sequence[1] == 0xf0:  # scroll strip
                scroll_pos = sequence[5]
                if scroll_pos == 0:
                    # reset scroll state after lifting finger off scroll strip
                    self.scroll_state = None
                elif self.scroll_state is not None:
                    # scroll strip is numbered from top to bottom so a greater new
                    # value means they scrolled down
                    if scroll_pos > self.scroll_state:
                        self.scroll_state = scroll_pos
                        return 'scroll_down'
                    elif scroll_pos < self.scroll_state:
                        self.scroll_state = scroll_pos
                        return 'scroll_up'
                else:
                    self.scroll_state = scroll_pos
                    continue
            elif sequence[1] == 0xf1:  # dial on Q620M, practically 2 buttons
                if sequence[5] == 0x1:
                    return 'dial_cw'
                elif sequence[5] == 0xff:
                    return 'dial_ccw'
            else:
                continue

    def get_button_release(self, hidraw):
        while True:
            sequence = hidraw.read(12)
            if sequence[1] == 0xe0 and sequence[4] == 0 and sequence[5] == 0:
                return True

    def events(self, args):
        print('event received:', args)

def get_tablet_hidraw(device_id, device_name):
    """Finds the /dev/hidrawX file or files that belong to the given device ID (in xxxx:xxxx format)."""
    # TODO: is this too fragile?
    hidraws = os.listdir('/sys/class/hidraw')
    inputs = []
    for h in hidraws:
        device_path = os.readlink(os.path.join('/sys/class/hidraw', h, 'device'))
        
        if device_id.upper() in device_path:
            # need to confirm that there's "input" because there are two or more hidraw
            # files listed for the tablet, but only few of them carry the
            # mouse/keyboard input
            path = os.path.join('/sys/class/hidraw', h, 'device/input')
            if os.path.exists(path):
                entries = os.scandir(path)
                for entry in entries:
                    if device_name.lower() in open(os.path.join(entry, 'name')).read().lower() :
                        inputs.append(os.path.join('/dev', os.path.basename(h)))
                        break
    if inputs:
        return inputs
    return None


def read_config(config_file):
    global CYCLE_MODES, CYCLE_BUTTON, BUTTON_BINDINGS, BUTTON_BINDINGS_HOLD
    CONFIG = yaml.load(open(config_file, 'r'), yaml.Loader)
    # It is still better for performance to pre-encode these values
    for binding in CONFIG['Bindings']:
        if type(binding) is int:
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
            continue  # ignore empty line
        else:
            print("[WARN] unrecognized regular binding '%s'" % (binding,), flush=True)
    # Same, but for buttons that should be held down
    if 'Hold' in CONFIG:
        for binding in CONFIG['Hold']:
            if type(binding) is int:
                BUTTON_BINDINGS_HOLD[int(binding)] = CONFIG['Hold'][binding].encode('utf-8')
            elif binding == '':
                continue
            else:
                print("[WARN] unrecognized hold binding '%s'" % (binding,), flush=True)
    # Assume that if cycle is assigned we have modes for now
    if 'Cycle' in CONFIG:
        CYCLE_BUTTON = int(CONFIG['Cycle']['Switch'])
        
        for key in CONFIG['Cycle']:
            print(key, flush=True)
            if key.startswith("Mode"):
                # Count the modes
                mode = int(key.split(' ')[1])
                if mode > CYCLE_MODES:
                    CYCLE_MODES = mode
                DIAL_MODES[mode] = {}
                for binding in CONFIG['Cycle'][key]:
                    DIAL_MODES[mode][int(binding) if type(binding) is int else binding] = CONFIG['Cycle'][key][binding].encode('utf-8')

def make_rules():
    for device_name, device_id in TABLET_MODELS.items():
        print("# %s" % (device_name, ), flush=True)
        VID, PID = device_id.split(':')
        print('KERNEL=="hidraw*", ATTRS{idVendor}=="%s", ATTRS{idProduct}=="%s", MODE="0660", TAG+="uaccess"' % (VID, PID, ), flush=True)


def create_default_config(config_file):
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    with open(config_file, 'w') as config:
        config.write("""
# use one line for each button you want to configure
# buttons that aren't in this file will be ignored by this program
# (but may be handled by another driver)
Bindings:
  4: ctrl+s
  5: ctrl+z
6: ctrl+shift+equal
7: ctrl+minus
# etc. up to the highest button number
16: Tab
scroll_up: bracketright
scroll_down: bracketleft
#Buttons that should be held instead of instantly firing
Hold:
  3: ctrl
#Q620M Dial
Cycle:
  Switch: 9
  "Mode 1":
    1: ctrl+c
  "Mode 2":
    1: ctrl+v
  "Mode 3":
    1: ctrl+z
""")

if __name__ == "__main__":
    main()
