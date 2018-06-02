import multiprocessing.dummy as dummy
import logging
import socket
import sys
from random import choice
from datetime import datetime
from conf import *
from time import sleep


log = logging.getLogger(__name__)

class Process(object):
    threads = []

    def __init__(self,
    events_by_process=100, events_per_second=1, *args, **kwargs):
        self.events_by_process = events_by_process
        self.events_per_second = events_per_second
        self.pid = os.getpid()

    def create_threads(self) -> "Thread":
        pass

    # TODO: lift socket creation to Process level (RM 2018-06-01 22:47:12)
    def create_socket(self, process: Process) -> "socket":
        pass

    def __lt__(self, other: Process):
        return self.pid < other.pid

    def __eq__(self, other: Process):
        return self.pid == other.pid

    def __gt__(self, other: Process):
        return self.pid > other.pid


class Thread(object):
    def __init__(self, thread: dummy.Process, *args, **kwargs):
        self.underlying = thread
        self.start_socket()

    def run(self, *args, **kwargs):
        """ Function permanently run by this thread. """
        raise NotImplementedError

    def start_socket(self, address='', port=8002):
        """ Set up connection through TCP/IP socket. """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(address, port)


class ListenerThread(Thread):
    # TODO: this method as an abstract function (RM 2018-05-30 13:58:16)
    def __init__(self, parameter_list):
        self.socket.listen(10)

    def run(self, *args, **kwargs):
        while True:
            # accept connections from outside
            (client_socket, address) = self.socket.accept()
            ip, port = str(address[0]), str(address[1])
            log.info("Accepting connection from {}:{}".format(ip, port))

            try:
                self.underlying(
                    target=self.listen,
                    args=(client_socket, ip, port)).start()
            except:
                print("Terrible error!")
                import traceback
                traceback.print_exc()
    
        self.socket.close()

    # # likely not needed (RM 2018-05-30 14:27:38)
    # def listen(self):
    #     # the number means how long the response can be in bytes  
    #     result_bytes = self.socket.recv(4096) 
    #     # the return will be in bytes, so decode
    #     result_string = result_bytes.decode("utf8")


    # likely not needed (RM 2018-05-30 14:27:38)
    def listen(self, client_socket):
        # the input is in bytes, so decode it
        input_from_client_bytes = client_socket.recv(MAX_BUFFER_SIZE)
        size = sys.getsizeof(input_from_client_bytes)
        if  size >= MAX_BUFFER_SIZE:
            log.warn("The length of input is too long: {}".format(size))

        # decode input and strip the end of line
        input_from_client = input_from_client_bytes.decode("utf8").rstrip()

        log.info(input_from_client)

        vysl = input_from_client.encode("utf8")  # encode the result string
        client_socket.sendall(vysl)  # send it to client
        client_socket.close()  # close connection
        # FIXME: desconnection formatting
        log.info("Connection {}:{} ended.")


    # TODO: lift this method to abstract class Thread (RM 2018-05-30 14:21:35)
    # tbh this is no longer need (RM 2018-06-01 22:05:39)
    def write_log(self, client_socket, ip='', port=8002):
        # the input is in bytes, so decode it
        input_from_client_bytes = client_socket.recv(MAX_BUFFER_SIZE)
        size = sys.getsizeof(input_from_client_bytes)
        if  size >= MAX_BUFFER_SIZE:
            log.error("The length of input is too long: {}.".format(size))

        # decode input and strip the end of line
        input_from_client = input_from_client_bytes.decode("utf8").rstrip()

        log.info(input_from_client)

        # likely not needed (RM 2018-05-30 14:18:25)
        vysl = input_from_client.encode("utf8")  # encode the result string
        client_socket.sendall(vysl)  # send it to client

        # close connection
        client_socket.close()


class EmitterThread(Thread):
    # TODO:  this method as an abstract function (RM 2018-05-30 13:58:16)
    def __init__(self, process: Process, *args, **kwargs):
        self.process = process
        if kwargs and sorted(kwargs.keys()) == ['adj', 'adv', 'noun', 'verb']:
            self.words = kwargs
        else:
            self.words = {
                "adj": ["fancy", "dirty", "wise", "stupid", "funny"],
                "noun": ["Anna", "Brandon", "Charles", "Diana", "Emma"],
                "verb": ["went away", "were found", "were okay", "arrived", "slept"],
                "adv": ["yesterday", "downhill", "outside", "like a pig",
                "like a boss"],
            }
        self.socket.listen(10)

    def sentence(self, *args, **kwargs):
        """ Generates readable text for events."""
        return "{} {} and {} {} {} {}.".format(
            choice(self.words["adj"]).title(),
            choice(self.words["noun"]),
            choice(self.words["adj"]),
            choice(self.words["noun"]),
            choice(self.words["verb"]),
            choice(self.words["adv"]),
        )

    def run(self, *args, **kwargs):
        """ Loop through input parameters."""
        self.socket.connect(("127.0.0.1", 8002))
        for tick in range(self.process.events_by_process):
            self.socket.send(self.generate()) # must encode the string to bytes
            log.info(self.generate(**{"event": "event #{} '{}'".format(
                tick+1, self.sentence()
            )}))
            sleep(1.0/self.process.events_per_second)
        self.socket.close()

    def generate(self, *args, **kwargs):
        """ Generates a random UTF-8 encoded string. """
        event = self.sentence()
        return "from pid {}: {} @ {}".format(
            self.process.pid, event, datetime.now()).encode("utf")


class Channel(object):
    def __init__(self, sender: Process, receiver: Process, *args, **kwargs):
        self.processes = [sender, receiver]

    @property
    def sender(self):
        return min(self.processes)
    
    @property
    def receiver(self):
        return max(self.processes)
    

class LogicalClock(object):
    
    def __init__(self, process: Process, *args, **kwargs):
        self.value = 0
        self.process = process
        self.lock = dummy.Lock()

    def increment(self):
        self.lock.acquire()
        try:
            self.value += 1
        except Exception as e:
            log.error(e)
            raise e
        finally:
            self.lock.release()

    def get_value(self):
        try:
            return self.value
        except Exception as e:
            log.error(e)
            raise e
        finally:
            self.lock.release()

    def __gt__(self, other: LogicalClock):
        return self.get_value() > other.get_value()

    def __eq__(self, other: LogicalClock):
        return self.get_value() == other.get_value()

    def __lt__(self, other: LogicalClock):
        return self.get_value() < other.get_value()


class Event(object):
    pass


class Message(Event):
    pass


# TODO: find an appropriate inheritance (RM 2018-05-28T21:00:09.381BRT)
class PriorityLine(object):
    pass
