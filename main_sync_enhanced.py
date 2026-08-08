"""Compatibility entry point for the retired autonomous sync launcher.

Unattended provider synchronization is not part of the supported product. This
module starts the maintained local-first application instead.
"""

from main import main


if __name__ == "__main__":
    print("Autonomous sync is retired; starting the maintained review-gated application.")
    main()
