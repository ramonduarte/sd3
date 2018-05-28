#!/usr/bin/env python3
"""
Generator of events at a fixed rate.
"""
import logging
import signal
import sys
from datetime import datetime
from random import randint, choice
from time import sleep
from manager import user_input_handler

log = logging.getLogger(__name__)


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

class EventGenerator:
    """
    Class responsible to create events at a fixed rate.
    """
    def __init__(self, *args, **kwargs):
        self.events_by_process = int(args[1]) if args[1] else 100
        self.events_per_second = int(args[2]) if args[2] else 1
        self.pid = randint(1, 10000)
        self.words = {
            "adj": ["fancy", "dirty", "wise", "stupid", "funny"],
            "noun": ["Anna", "Brandon", "Charles", "Diana", "Emma"],
            "verb": ["went away", "were found", "were okay", "arrived", "slept"],
            "adv": ["yesterday", "downhill", "outside", "like a pig", "like a boss"],
        }

    def __str__(self):
        return  # TODO: write this function (RM 2018-05-27T17:59:08.589BRT)

    def __doc__(self):
        return  # TODO: write this docstring (RM 2018-05-27T17:59:17.044BRT)
    
    def sentence(self, *args, **kwargs):
        return "{} {} and {} {} {} {}.".format(
            choice(self.words["adj"]).title(),
            choice(self.words["noun"]),
            choice(self.words["adj"]),
            choice(self.words["noun"]),
            choice(self.words["verb"]),
            choice(self.words["adv"]),
        )

    def generate(self, *args, **kwargs) -> str:
        """ Generates readable text for events."""
        event = kwargs.get("event", "")
        return " from pid {}: {} @ {}".format(self.pid, event, datetime.now())

    def run(self):
        """ Loop through input parameters."""
        for tick in range(self.events_by_process):
            log.info(self.generate(**{"event": "event #{} '{}'".format(
                tick+1, self.sentence()
            )}))
            sleep(1.0/self.events_per_second)


def main():
    log.info("Start of the run.")
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGUSR1, signal_handler)
    signal.signal(signal.SIGUSR2, signal_handler)
    event_generator = EventGenerator(*user_input_handler())
    event_generator.run()
    log.info("End of the run.")
    return 0

if __name__ == '__main__':
    from manager import user_input_handler
    main()
