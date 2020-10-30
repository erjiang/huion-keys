import os

from _xdo_cffi import ffi, lib

CONFIG_FILE_PATH = os.path.expanduser('~/.config/huion_keys.conf')

BUTTON_BINDINGS = {}

def main():
    xdo = lib.xdo_new(ffi.NULL)
    hidraw_path = get_tablet_hidraw('256c', '006e')
    if hidraw_path is None:
        print("Could not find tablet hidraw device")
    print("Found tablet at " + hidraw_path)
    if os.path.isfile(CONFIG_FILE_PATH):
        read_config(CONFIG_FILE_PATH)
    else:
        print("No config file found.")
        create_default_config(CONFIG_FILE_PATH)
        print("Created an example config file at " + CONFIG_FILE_PATH)
        return 1
    hidraw = open(hidraw_path, 'rb')
    while True:
        btn = get_button_press(hidraw)
        print("Got button %s" % (btn,))
        if btn in BUTTON_BINDINGS:
            print("Sending %s" % (BUTTON_BINDINGS[btn],))
            lib.xdo_send_keysequence_window(
                xdo, lib.CURRENTWINDOW, BUTTON_BINDINGS[btn], 10)


def get_tablet_hidraw(vendor_id, product_id):
    """Finds the /dev/hidrawX file that belongs to the given vendor and product ID."""
    # TODO: is this too fragile?
    hidraws = os.listdir('/sys/class/hidraw')
    for h in hidraws:
        device_path = os.readlink(os.path.join('/sys/class/hidraw', h, 'device'))
        if ("%s:%s" % (vendor_id.upper(), product_id.upper())) in device_path:
            # need to confirm that there's "input" because there are two hidraw
            # files listed for the tablet, but only one of them carries the
            # mouse/keyboard input
            if os.path.exists(os.path.join('/sys/class/hidraw', h, 'device/input')):
                return os.path.join('/dev', os.path.basename(h))
    return None


def read_config(config_file):
    with open(config_file, 'r') as config:
        for line in config.readlines():
            # strip out any comment
            if line.find('#') > -1:
                line = line[:line.find('#')]
            if line.find('='):
                setting = line[:line.find('=')].strip()
                value = line[line.find('=')+1:].strip()
                if setting.isdigit():
                    # button bindings are 0-indexed so need to subtract one
                    BUTTON_BINDINGS[int(setting)-1] = value.encode('utf-8')
                elif setting == 'scroll_up':
                    BUTTON_BINDINGS['scroll_up'] = value.encode('utf-8')
                elif setting == 'scroll_down':
                    BUTTON_BINDINGS['scroll_down'] = value.encode('utf-8')
                elif setting == '':
                    continue # ignore empty line
                else:
                    print("[WARN] unrecognized setting '%s'" % (setting,))


def create_default_config(config_file):
    with open(config_file, 'w') as config:
        config.write("""
# use one line for each button you want to configure
# buttons that aren't in this file will be ignored by this program
# (but may be handled by another driver)
4=ctrl+s
5=ctrl+z
6=ctrl+shift+equal
7=ctrl+minus
# etc. up to the highest button number
16=tab
scroll_up=bracketright
scroll_down=bracketleft
""")


BUTTON_BITS = {
    0x01: 0,
    0x02: 1,
    0x04: 2,
    0x08: 3,
    0x10: 4,
    0x20: 5,
    0x40: 6,
    0x80: 7,
}

SCROLL_STATE=None

def get_button_press(hidraw):
    global SCROLL_STATE
    while True:
        sequence = hidraw.read(12)
        # don't think there's anything we care about that doesn't start with 0xf7
        if sequence[0] != 0xf7:
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


if __name__ == "__main__":
    main()
