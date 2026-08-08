"""Compatibility entry point for the former enhanced launcher.

The historical implementation made unverified provider-access claims and is
intentionally retired. The maintained application lives in ``main.py``.
"""

from main import main


if __name__ == "__main__":
    print("main_enhanced.py is retired; starting the maintained review-gated application.")
    main()
