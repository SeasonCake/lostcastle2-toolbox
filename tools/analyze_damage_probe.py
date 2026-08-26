from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from toolbox.damage_probe_analysis import summarize_probe_file


def main() -> int:
    parser = argparse.ArgumentParser(
        description="汇总 LC2DamageProbe 日志；不输出实体或账号标识"
    )
    parser.add_argument("log", type=Path)
    args = parser.parse_args()
    if not args.log.is_file():
        parser.error(f"日志不存在：{args.log}")
    print(summarize_probe_file(args.log).to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
