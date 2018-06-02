#!/usr/bin/env python3
"""
COS470 - Assignment 3
Ramon Melo (ramonduarte at poli.ufrj.br)
"""
import signal
import logging
from conf import *

logging.basicConfig(filename=os.path.join(LOG_DIR, "sd3.log"), level=logging.DEBUG)
LOG = logging.getLogger(__name__)


def main():
    """ Centralizing all computations on a single function."""
    return 0


if __name__ == '__main__':
    main()
