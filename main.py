#!/usr/bin/env python3
"""
COS470 - Assignment 3
Ramon Melo (ramonduarte at poli.ufrj.br)
"""
import signal
from manager import user_input_handler, NoNameYet
from event_generator import EventGenerator, signal_handler


def main():
    """ Centralizing all computations on a single function."""
    # print(user_input_handler())
    # print(NoNameYet(*user_input_handler()))
    signal.signal(signal.SIGINT, signal_handler)
    event_generator = EventGenerator(*user_input_handler())
    event_generator.run()
    print("End of the run")
    return 0


if __name__ == '__main__':
    main()
