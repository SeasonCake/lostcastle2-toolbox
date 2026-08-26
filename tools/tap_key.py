from __future__ import annotations

import argparse
import ctypes
import time


KEYS = {"F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("key", choices=KEYS)
    args = parser.parse_args()
    vk_code = KEYS[args.key]
    user32 = ctypes.windll.user32
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.06)
    user32.keybd_event(vk_code, 0, 0x0002, 0)
    print(args.key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
