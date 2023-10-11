import time
import dbus
from gi.repository import GLib as glib
import threading

from dbus.mainloop.glib import DBusGMainLoop

class DBusThread(threading.Thread):
  def __init__(self):
    super(DBusThread, self).__init__(daemon=True)
    DBusGMainLoop(set_as_default=True)

  def tryopen(self):
    try:
      print("success open")
    except Exception as e:
        print(e)

  def handle_sleep(self, mode):
    if mode:
        print("Sleep")
        self.tryopen()
    else:
        print("Resume")
        time.sleep(10)
        self.tryopen()

  def run(self):
    print("starting dbus")
    bus = dbus.SystemBus()                 # connect to system wide dbus
    bus.add_signal_receiver(               # define the signal to listen to
        self.handle_sleep,                      # callback function
        'PrepareForSleep',                 # signal name
        'org.freedesktop.login1.Manager',  # interface
        'org.freedesktop.login1'           # bus name
    )
    loop = glib.MainLoop()
    loop.run()

  def join(self):
    super().join()
    glib.idle_add(quit)
