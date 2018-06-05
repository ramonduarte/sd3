"""
Classes used for this assignment.
"""

import multiprocessing.dummy as dummy
import logging
import socket
import sys
import traceback
import uuid
import os
from random import choice
from datetime import datetime
from time import sleep
from conf import MAX_BUFFER_SIZE


LOG = logging.getLogger(__name__)

class Process(object):
    """
    Process that will coordenate threads.
    """
    def __init__(self, target_address, events_by_process=100,
                 events_per_second=1):
        self.events_by_process = events_by_process
        self.events_per_second = events_per_second
        self.pid = os.getpid()
        self.create_threads(target_address)
        self.clock = LogicalClock(self)

    def create_threads(self, target_address):
        """ Set up threads for listening and sending messages. """
        self.listener_thread = ListenerThread(self)
        self.emitter_thread = EmitterThread(self, **{"address":
                                                     target_address})

    # TODO: lift socket creation to Process level (RM 2018-06-01 22:47:12)
    def create_socket(self) -> "socket":
        """ Start socket for its threads to use. """
        pass

    def __lt__(self, other: "Process"):
        return self.pid < other.pid

    def __eq__(self, other: "Process"):
        return self.pid == other.pid

    def __gt__(self, other: "Process"):
        return self.pid > other.pid


class Thread(object):
    """ Abstract class to encapsulate threading functionality. """
    def __init__(self, process: Process, thread=dummy.Process,
                 *args, **kwargs):
        self.underlying = thread
        self.process = process
        self.address = kwargs.get("address", "")
        self.port = int(kwargs.get("port", 8002))
        self.start_socket()

    def run(self, *args, **kwargs):
        """ Function permanently run by this thread. """
        raise NotImplementedError

    def start_socket(self):
        """ Set up connection through TCP/IP socket. """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


class ListenerThread(Thread):
    """ Thread responsible for handling receiving messages. """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.socket.bind((self.address, self.port))
        self.socket.listen(10)

    def run(self, *args, **kwargs):
        # accept connections from outside
        (client_socket, address) = self.socket.accept()
        self.client_ip_addr = str(address[0])
        self.client_port = str(address[1])
        LOG.info("Accepting connection from %s:%s", self.client_ip_addr,
                 self.client_port)

        # LOG.info("client socket: %s", client_socket)

        try:
            self.listen(client_socket)
            # res = self.listen(client_socket)
            # self.underlying(
            #     target=self.listen,
            #     args=(client_socket)).start()
        except Exception as e:
            LOG.fatal(e)
            traceback.print_exc()
            print(client_socket)

        self.socket.close()


    # needs to be a function to keep thread semantics (RM 2018-06-03 22:32:44)
    def listen(self, client_socket):
        """ Listen to socket until a message is received. """
        while True:
            input_from_client_bytes = client_socket.recv(MAX_BUFFER_SIZE)
            self.process.clock.increment()
            size = sys.getsizeof(input_from_client_bytes)

            if  size >= MAX_BUFFER_SIZE:
                LOG.error("The length of input is too long: %d", size)
                return 1
            if size == 33:  # empty message, remote thread failed
                LOG.info("Connection %s:%s ended.", self.client_ip_addr,
                         self.client_port)
                return 0

            # decode input and strip the end of line
            input_from_client = input_from_client_bytes.decode("utf8").rstrip()

            if input_from_client == "CLOSE":
                client_socket.close()
                LOG.info("Connection %s:%s ended.", self.client_ip_addr,
                         self.client_port)
                return 0

            LOG.info("RECEIVED %s", input_from_client)

            # returning ACK message (RM 2018-06-04 20:52:41)
            self.process.clock.increment()
            ack = AckMessage(
                self.process.clock.get_value(),
                datetime.today(),
                self.address,
                self.client_ip_addr,
                "placeholder_uuid" #FIXME(RM 2018-06-04 20:58:01)
            )
            LOG.info(ack.content)
            client_socket.send(ack.content.encode("utf8"))

            # TODO: end this function asynchronously (RM 2018-06-03 22:34:13)
            sleep(1)


class EmitterThread(Thread):
    """ Thread responsible for sending messages. """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self, *args, **kwargs):
        """ Loop through input parameters."""
        self.socket.connect((self.address, self.port))

        for tick in range(self.process.events_by_process):
            try:
                self.process.clock.increment()
                message = SentMessage(
                    self.process.clock.get_value(),
                    datetime.now(),
                    '127.0.0.1',  # FIXME: (RM 2018-06-04 19:35:10)
                    self.address,
                    )
                self.socket.send(message.content.encode("utf8"))
            except BrokenPipeError:
                traceback.print_exc()
                sleep(10)

            LOG.info("SENT %s", message.content)
            sleep(1.0/self.process.events_per_second)

        # FIXME: define protocol to end connection
        self.socket.send("CLOSE".encode("utf8"))

        self.socket.close()


class Channel(object):
    """ Communication between remote processes. """
    def __init__(self, sender: Process, receiver: Process, *args, **kwargs):
        self.processes = [sender, receiver]

    @property
    def sender(self):
        """ Process that should initiate a connection. """
        return min(self.processes)

    @property
    def receiver(self):
        """ Process that should receive a connection. """
        return max(self.processes)


class LogicalClock(object):
    """ Implementation of local Lamport clock. """
    def __init__(self, process: Process, *args, **kwargs):
        self.value = 1
        self.process = process
        self.lock = dummy.Lock()

    def increment(self):
        """ Increment logical clock counter. """
        self.lock.acquire()
        try:
            self.value += 1
        except Exception as e:
            LOG.error(e)
            raise e
        finally:
            self.lock.release()

    def get_value(self):
        """ Access value stored in the logical clock counter. """
        self.lock.acquire()
        try:
            return self.value
        except Exception as e:
            LOG.error(e)
            raise e
        finally:
            self.lock.release()

    def update(self, other: int):
        """ Update logical clock counter. """
        self.lock.acquire()
        try:
            self.value = max(self.value, other) + 1
        except Exception as e:
            LOG.error(e)
            raise e
        finally:
            self.lock.release()

    def __gt__(self, other: "LogicalClock"):
        return self.get_value() > other.get_value()

    def __eq__(self, other: "LogicalClock"):
        return self.get_value() == other.get_value()

    def __lt__(self, other: "LogicalClock"):
        return self.get_value() < other.get_value()


class Event(object):
    """ Ocurrence that prompts update of Lamport clock. """
    def __init__(self, clock: int, timestamp: datetime, source: int):
        self.clock = clock
        self.timestamp = timestamp
        self.source = source
        self.id = uuid.uuid1()


class Message(Event):
    """ Message sent or received through a TCP socket. """
    def __init__(self, clock: int, timestamp: datetime, source: int, target: str):
        super().__init__(clock, timestamp, source)
        self.content = ""
        self.target = target

    def __str__(self):
        return "Message {}: '{}'".format(
            self.id,
            self.content[:50] + (self.content[50:] and '...')
            )


class SentMessage(Message):
    """ Message sent through a TCP socket. """
    def __init__(self, clock: int, timestamp: datetime, source: int, target: str):
        super().__init__(clock, timestamp, source, target)
        self.content = self.generate()

    def sentence(self):
        """ Generates readable text for events."""
        return choice(open("sentences.txt").readlines())

    def generate(self):
        """ Generates an UTF-8 encoded string. """
        return "<{}> from process {} to {}: {} ({})".format(
            self.clock,
            self.source,
            self.target,
            self.sentence(),
            datetime.now()
            )


class ReceivedMessage(Message):
    """ Message received through a TCP socket. """
    def __init__(self,
                 clock: int,
                 timestamp: datetime,
                 source: int,
                 target: str):
        super().__init__(clock, timestamp, source, target)
        self.content = ""


class AckMessage(Message):
    """ Acknowledgement of a message received through a TCP socket. """
    def __init__(self,
                 clock: int,
                 timestamp: datetime,
                 source: int,
                 target: str,
                 receipt_of: uuid.UUID):
        super().__init__(clock, timestamp, source, target)
        self.receipt_of = receipt_of
        self.content = "<{}> ACK {} in confirmation of message {}" \
                        " from {} to {} ({}).".format(
                            self.clock,
                            self.id,
                            self.receipt_of,
                            self.target,
                            self.source,
                            self.timestamp
                        )


# TODO: find an appropriate inheritance (RM 2018-05-28T21:00:09.381BRT)
class PriorityLine(object):
    pass
