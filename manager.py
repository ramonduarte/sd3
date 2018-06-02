#!/usr/bin/env python3
"""
Manages local threads.
"""
import logging
import signal
import sys
from datetime import datetime
from random import randint, choice
from time import sleep

log = logging.getLogger(__name__)


def user_input_handler():
    """ Function to handle input from user and other threads."""
    class_input = [line for line in sys.argv[1:]]
    return class_input


def signal_handler(sig: signal.signal, frame) -> int:
    """ Handle extern signals in order to set up coordenation."""
    if sig == signal.SIGTERM:
        log.error("Terminated by user (likely by Ctrl+C).")
        sys.exit(0)
    elif sig == signal.SIGUSR1:  # halt
        log.warning("Suspended by user (SIGUSR1).")
        signal.pause()
    elif sig == signal.SIGUSR2:  # continue
        log.warning("Awaken by user (SIGUSR2).")
        return 0
    else:
        return 1


class Sd3Instance:
    """ not sure yet of what this is supposed to be."""
    def __init__(self, *args):
        self.number_of_processes = int(args[0]) if args[0] else 1
        self.events_by_process = int(args[1]) if args[1] else 100
        self.events_per_second = int(args[2]) if args[2] else 1

    def __str__(self):
        return 'number_of_processes: {}\nevents_by_process: {}\nevents_per_second: {}'.format(
            self.number_of_processes, self.events_by_process, self.events_per_second
        )
