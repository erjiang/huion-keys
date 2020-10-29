import time

from _xdo_cffi import ffi, lib

X = 200

xdo = lib.xdo_new(ffi.NULL)
for i in range(20):
    lib.xdo_move_mouse(xdo, X * i, 500, 0)
    time.sleep(0.1)
