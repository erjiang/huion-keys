import time
import dbus
from gi.repository import GLib as glib
import threading

from dbus.mainloop.glib import DBusGMainLoop

class DBusThread(threading.Thread):
  def __init__(self, update):
    super(DBusThread, self).__init__(daemon=True)
    DBusGMainLoop(set_as_default=True)
    self.update = update

  def handle_sleep(self, mode):
    if mode:
        self.update.send("Suspend")
    else:
        self.update.send('Resume')

  def run(self):
    bus = dbus.SystemBus()                 # connect to system wide dbus
    bus.add_signal_receiver(               # define the signal to listen to
        self.handle_sleep,                      # callback function
        'PrepareForSleep',                 # signal name
        'org.freedesktop.login1.Manager',  # interface
        'org.freedesktop.login1'           # bus name
    )
    glib.MainLoop().run()

  def join(self):
    super().join()  #this must be called on first to make sure join is handled before all
    glib.idle_add(quit)
