from __future__ import annotations

import argparse
import ctypes
import time


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("start_x", type=int)
    parser.add_argument("start_y", type=int)
    parser.add_argument("end_x", type=int)
    parser.add_argument("end_y", type=int)
    args = parser.parse_args()
    user32 = ctypes.windll.user32
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        user32.SetProcessDPIAware()
    user32.SetCursorPos(args.start_x, args.start_y)
    time.sleep(0.08)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    steps = 12
    for index in range(1, steps + 1):
        x = args.start_x + (args.end_x - args.start_x) * index // steps
        y = args.start_y + (args.end_y - args.start_y) * index // steps
        user32.SetCursorPos(x, y)
        time.sleep(0.025)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    print(f"{args.start_x},{args.start_y}->{args.end_x},{args.end_y}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
