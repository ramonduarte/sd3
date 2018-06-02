#!/usr/bin/env python3
"""
Manages local threads.
"""
import logging
import signal
import sys

LOG = logging.getLogger(__name__)


def user_input_handler():
    """ Function to handle input from user and other threads."""
    class_input = [line for line in sys.argv[1:]]
    return class_input


def signal_handler(sig: signal.signal, frame) -> int:
    """ Handle extern signals in order to set up coordenation."""
    if sig == signal.SIGTERM:
        LOG.error("Terminated by user (likely by Ctrl+C).")
        sys.exit(0)
        return 1
    elif sig == signal.SIGUSR1:  # halt
        LOG.warning("Suspended by user (SIGUSR1).")
        signal.pause()
        return 0
    elif sig == signal.SIGUSR2:  # continue
        LOG.warning("Awaken by user (SIGUSR2).")
        return 0
    else:
        return 1
