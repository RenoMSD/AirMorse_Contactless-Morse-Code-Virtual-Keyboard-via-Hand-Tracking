"""python -m airmorse"""

import sys

from airmorse.ui.main_window import run


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
