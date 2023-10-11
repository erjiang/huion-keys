import time
import dbus
from gi.repository import GLib as glib
import threading

from dbus.mainloop.glib import DBusGMainLoop

class DBusThread(threading.Thread):
  def __init__(self, obs=None):
    # dbus.mainloop.glib.threads_init()
    DBusGMainLoop(set_as_default=True)
    super(DBusThread, self).__init__(daemon=True)
    time.sleep(1)
    
    self.obs = obs
    self.obs.trigger("events", arg1='asdf')

  def tryopen(self):
    try:
      print("success open")
    except Exception as e:
        print(e)

  def handle_sleep(self, mode):
    if mode:
        self.obs.trigger("events", arg1=dict(event='suspend'))
        # self.tryopen()
    else:
        time.sleep(10)
        self.obs.trigger("events", arg1=dict(event='resume'))
        # self.tryopen()

  def run(self):
    print("starting dbus")
    bus = dbus.SystemBus()                 # connect to system wide dbus
    bus.add_signal_receiver(               # define the signal to listen to
        self.handle_sleep,                      # callback function
        'PrepareForSleep',                 # signal name
        'org.freedesktop.login1.Manager',  # interface
        'org.freedesktop.login1'           # bus name
    )
    glib.MainLoop().run()

  def join(self):
    glib.idle_add(quit)
    super().join()
