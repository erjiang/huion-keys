#!/usr/bin/env python3
import time

from _xdo_cffi import ffi, lib

X = 200

# should make mouse cursor walk across screen
xdo = lib.xdo_new(ffi.NULL)
for i in range(15):
    lib.xdo_move_mouse(xdo, X * i, 500, 0)
    time.sleep(0.1)
