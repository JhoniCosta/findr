import logging
import os
import signal
import sys


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("FINDR_LOG", "WARNING").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Let Ctrl+C stop the GTK main loop.

    from findr.app import FindrApplication

    return FindrApplication().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
