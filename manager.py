#!/usr/bin/env python3
"""
Helpful code wrapped up in functions for clarity.
"""
import logging
import signal
import sys
import os
from conf import LOG_DIR


def user_input_handler() -> list:
    """ Function to handle input from user and other threads."""
    input_list = [line for line in sys.argv[1:]]
    return input_list


def signal_handler(sig: signal.signal, frame) -> int:
    """ Handle extern signals in order to set up coordenation."""
    if sig in (signal.SIGTERM, signal.SIGINT):
        LOG.fatal("Terminated by user (likely by Ctrl+C).")
        try:
            process.emitter_thread.socket.close()
            process.listener_thread.socket.close()
        except:
            pass
        finally:
            sys.exit(0)
            return 1
    elif sig == signal.SIGUSR1:  # halt
        LOG.warning("Suspended by user (SIGUSR1).")
        signal.pause()
        return 0
    elif sig == signal.SIGUSR2:  # continue
        LOG.warning("Awaken by user (SIGUSR2).")""
        return 0

    elif sig == signal.SIGPIPE:
        if __debug__:
            print("SIGPIPE")
            return 0
    else:
        return 1

def ger_or_default(obj: object, index: int, default=0):
    """ Similar to dict.get() but for iterables. """
    try:
        iter(obj)
        return obj[index] if -len(obj) <= index < len(obj) else default
    except TypeError:
        return default

def log_setup() -> logging.Logger:
    """ Creates log directory if not available. """
    try:
        os.mkdir(LOG_DIR)
    except OSError:
        pass

    # prepping log
    logging.basicConfig(
        filename=os.path.join(
            LOG_DIR,
            "8-10000-1" + ger_or_default(user_input_handler(), 0, "") + ".log"
        ),
        level=logging.DEBUG
    )
    return logging.getLogger(__name__)
