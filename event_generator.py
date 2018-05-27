#!/usr/bin/env python3
"""
Generator of events at a fixed rate.
"""

import signal
import sys
from datetime import datetime
from random import randint
from time import sleep


def signal_handler(sig, frame):
    """ Handle extern signals in order to set up coordenation."""
    print("ops")  # TODO: write signal handler (RM 2018-05-27T17:58:50.746BRT)
    sys.exit(0)

class EventGenerator:
    """
    Class responsible to create events at a fixed rate.
    """
    def __init__(self, *args):
        self.events_by_process = int(args[1]) if args[1] else 100
        self.events_per_second = int(args[2]) if args[2] else 1
        self.pid = randint(1, 10000)


    def __str__(self):
        return  # TODO: write this function (RM 2018-05-27T17:59:08.589BRT)

    def __doc__(self):
        return  # TODO: write this docstring (RM 2018-05-27T17:59:17.044BRT)

    def generate(self) -> str:
        """ Generates readable text for events."""
        return "pid: {} @ {}".format(self.pid, datetime.now())

    def run(self):
        """ Loop through input parameters."""
        for tick in range(self.events_by_process):
            print(self.generate())
            sleep(1.0/self.events_per_second)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    event_generator = EventGenerator(*user_input_handler())
    event_generator.run()
    print("End of the run")
    return 0

if __name__ == '__main__':
    from manager import user_input_handler
    main()
