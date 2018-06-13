#!/usr/bin/env python3
"""
COS470 - Assignment 3
Ramon Melo (ramonduarte at poli.ufrj.br)
"""
import signal
import traceback
from time import sleep
from multiprocessing.dummy import Pool
from manager import user_input_handler, signal_handler, ger_or_default, log_setup
from classes import Process
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
    signal.signal(signal.SIGPIPE, signal_handler)  # awaken

    if __debug__:
        print(user_input, ger_or_default(user_input, 2, 8002))


    ## LIGHT. CAMERA. ACTION.
    try:
        process = Process(
            LOG=LOG,
            target_address=ger_or_default(user_input, 1, "0.0.0.0"),
            target_port=ger_or_default(user_input, 2, 8002),
            address=ger_or_default(user_input, 3, "0.0.0.0"),
            port=ger_or_default(user_input, 4, 8003),
            events_by_process=ger_or_default(user_input, 5, 5),
            events_per_second=ger_or_default(user_input, 6, 1),
        )

        listener_pool = Pool(processes=1)
        sender_pool = Pool(processes=1)

        if __debug__:
            print("Setting up listener thread.")
        listener_pool.apply_async(process.listener_thread.run, ())

        sleep(5)

        if __debug__:
            print("Setting up emitter thread.")
        sender_pool.apply_async(process.emitter_thread.run, ())

        while not process.ready:
            sleep(10)

        while not process.queue.empty():
            message = process.queue.fetch()
            message.log()
            if __debug__:
                print("log written")

        return 0
    except Exception:
        traceback.print_exc()

        process.emitter_thread.socket.close()
        process.listener_thread.socket.close()
        return 1




if __name__ == '__main__':
    main()
