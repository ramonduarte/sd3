#!/usr/bin/env python3
"""
Manages local threads.
"""

from sys import argv


def user_input_handler():
    """ Function to handle input from user and other threads."""
    class_input = [line for line in argv[1:]]
    return class_input


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

    def __doc__(self):
        return  # TODO: write this docstring (RM 2018-05-27T17:57:02.589BRT)
