#!/usr/bin/env python3
"""
COS470 - Assignment 3
Ramon Melo (ramonduarte at poli.ufrj.br)
"""
import signal
import logging
import os
from manager import user_input_handler, signal_handler
from classes import Process
from multiprocessing.dummy import Pool
from conf import LOG_DIR


logging.basicConfig(filename=os.path.join(LOG_DIR, "sd3.log"), level=logging.DEBUG)
LOG = logging.getLogger(__name__)

# Creates log directory if not available
try:
    os.mkdir(LOG_DIR)
except OSError:
    pass


def main():
    """ Centralizing all computations on a single function."""
    signal.signal(signal.SIGTERM, signal_handler)  # user interrupted
    signal.signal(signal.SIGUSR1, signal_handler)  # halted
    signal.signal(signal.SIGUSR2, signal_handler)  # awaken

    try:
        process = Process("192.168.0.3")

        print("Setting up listener thread.")
        process.listener_thread.run()
        pool = Pool(processes=4)

        pool.apply_async(process.listener_thread.run, ())

        print("Setting up emitter thread.")
        process.emitter_thread.run()
        # res2 = pool.apply_async(process.emitter_thread.run, ())

        return 0
    except:
        print("Terrible error!")
        import traceback
        traceback.print_exc()

        process.emitter_thread.socket.close()
        process.listener_thread.socket.close()
        return 1


if __name__ == '__main__':
    main()
