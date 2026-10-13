"""Launch AirMorse."""

import sys


def main() -> int:
    from airmorse.ui.main_window import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
