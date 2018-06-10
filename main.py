#!/usr/bin/env python3
"""
COS470 - Assignment 3
Ramon Melo (ramonduarte at poli.ufrj.br)
"""
import signal
from multiprocessing.dummy import Pool
from manager import user_input_handler, signal_handler, ger_or_default, log_setup
from classes import Process
from multiprocessing.dummy import Pool
from conf import LOG_DIR


def main():
    """ Centralizing all computations on a single function."""

    ## SETTING UP THE ENVIRONMENT ##
    # parse command line arguments
    user_input = user_input_handler()

    # logging
    LOG = log_setup()

    # handling signals
    signal.signal(signal.SIGTERM, signal_handler)  # user interrupted
    signal.signal(signal.SIGUSR1, signal_handler)  # halted
    signal.signal(signal.SIGUSR2, signal_handler)  # awaken


    ## LIGHT. CAMERA. ACTION.
    try:
        process = Process(
            LOG=LOG,
            target_address=ger_or_default(user_input, 1, "0.0.0.0"),
            target_port=ger_or_default(user_input, 2, 8002),
            address=ger_or_default(user_input, 3, "0.0.0.0"),
            port=ger_or_default(user_input, 4, 8003),
            # target_address=ger_or_default(user_input, 1, "192.168.0.3"),
            # target_address=ger_or_default(user_input, 1, "192.168.0.3"),
            )

        print("Setting up listener thread.")
        # process.listener_thread.run()
        pool = Pool(processes=4)

        pool.apply_async(process.listener_thread.run, ())

        print("Setting up emitter thread.")
        process.emitter_thread.run()
        # res2 = pool.apply_async(process.emitter_thread.run, ())

        signal.pause()

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
