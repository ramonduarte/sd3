#!/usr/bin/env python3
"""
COS470 - Assignment 3
Ramon Melo (ramonduarte at poli.ufrj.br)
"""
import signal
from manager import Sd3Instance
import event_generator
from helper import *
import logging

logging.basicConfig(filename=os.path.join(LOG_DIR, "sd3.log"), level=logging.DEBUG)
log = logging.getLogger(__name__)


def main():
    """ Centralizing all computations on a single function."""
    event_generator.main()
    return 0


if __name__ == '__main__':
    main()
