"""
Classes used for this assignment.
"""

import multiprocessing.dummy as dummy
import socket
import sys
import traceback
import uuid
import os
from random import choice
from datetime import datetime
from time import sleep
from conf import MAX_BUFFER_SIZE


class Process(object):
    """
    Process that will coordenate threads.
    """
    def __init__(self, LOG, target_address="", target_port=8002, address="",
                 port=8002, events_by_process=100, events_per_second=1):
        self.events_by_process = events_by_process
        self.events_per_second = events_per_second
        self.pid = os.getpid()
        self.create_threads(
            target_address=target_address,
            target_port=target_port,
            address=address,
            port=int(port),
            )
        self.clock = LogicalClock(self)
        self.queue = MessageQueue(self)
        self.LOG = LOG

    def create_threads(self, target_address, target_port, address, port):
        """ Set up threads for listening and sending messages. """
        self.listener_thread = ListenerThread(self, address=address, port=port)
        self.emitter_thread = EmitterThread(process=self,
                                            target_address=target_address,
                                            target_port=target_port,
                                           )

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
    def __init__(self, process: Process, thread=dummy.Process, address="",
                 port=8002):
        self.underlying = thread
        self.process = process
        self.address = address
        self.port = int(port)
        self.start_socket()

    def run(self, *args, **kwargs):
        """ Function permanently run by this thread. """
        raise NotImplementedError

    def start_socket(self):
        """ Set up connection through TCP/IP socket. """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    @property
    def hostname(self):
        return socket.gethostname()


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
        
        self.process.LOG.info("Accepting connection from %s:%s", self.client_ip_addr,
                 self.client_port)

        # self.process.LOG.info("client socket: %s", client_socket)

        try:
            self.listen(client_socket)
            # res = self.listen(client_socket)
            # self.underlying(
            #     target=self.listen,
            #     args=(client_socket)).start()
        except Exception as e:
            self.process.LOG.fatal(e)
            traceback.print_exc()
            print(client_socket)

        # self.socket.close()


    # needs to be a function to keep thread semantics (RM 2018-06-03 22:32:44)
    def listen(self, client_socket):
        """ Listen to socket until a message is received. """
        while True:
            input_from_client_bytes = client_socket.recv(MAX_BUFFER_SIZE)
            self.process.clock.increment()
            size = sys.getsizeof(input_from_client_bytes)
            

            if  size >= MAX_BUFFER_SIZE:
                # TODO: ReceivedMessage() (RM 2018-06-06 13:01:13)
                self.process.LOG.error("The length of input is too long: %d", size)
                continue

            if size == 33:  # empty message, remote thread failed
                # TODO: ReceivedMessage() (RM 2018-06-06 13:01:13)
                self.process.LOG.info("Connection %s:%s ended.", self.client_ip_addr,
                         self.client_port)
                return 0

            # decode input and strip the end of line
            input_from_client = input_from_client_bytes.decode("utf8").rstrip()

            if input_from_client == "CLOSE":
                # TODO: ReceivedMessage() (RM 2018-06-06 13:01:13)
                client_socket.close()
                self.process.LOG.info("Connection %s:%s ended.", self.client_ip_addr,
                         self.client_port)
                return 0
            
            # TODO: fix better approach to ack checks (RM 2018-06-10 13:35:33)
            if "ACK" in input_from_client:
                # TODO: fetch sent message and log it (RM 2018-06-10 13:38:03)
                continue

            message = ReceivedMessage(
                self.process.clock.get_value(),
                datetime.today(),
                self.client_ip_addr,
                self.address,
                input_from_client
            )

            self.process.queue.put(message)
            # FIXME: self.process.LOG.info("RECEIVED %s", message.content)

            # returning ACK message (RM 2018-06-04 20:52:41)
            self.process.clock.increment()
            ack = AckMessage(
                clock=self.process.clock.get_value(),
                timestamp=datetime.today(),
                source=self.address,
                target=self.client_ip_addr,
                receipt_of=message.emitter_id
            )
            # FIXME: self.process.LOG.info(ack.content)
            client_socket.send(ack.content.encode("utf8"))
            message.mark_as_done()

            # TODO: end this function asynchronously (RM 2018-06-03 22:34:13)
            sleep(1)


class EmitterThread(Thread):
    """ Thread responsible for sending messages. """
    def __init__(self, target_address="", target_port=8002, *args, **kwargs):
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
                    self.hostname,
                    self.address,
                    )
                self.socket.send(message.content.encode("utf8"))
            except BrokenPipeError:
                traceback.print_exc()
                sleep(10)

            # FIXME: self.process.LOG.info("SENT %s", message.content)
            self.process.queue.put(message)
            sleep(1.0/self.process.events_per_second)

        # FIXME: define protocol to end connection
        self.socket.send("CLOSE".encode("utf8"))

        # self.socket.close()


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
            self.process.LOG.error(e)
            raise e
        finally:
            self.lock.release()

    def get_value(self):
        """ Access value stored in the logical clock counter. """
        self.lock.acquire()
        try:
            return self.value
        except Exception as e:
            self.process.LOG.error(e)
            raise e
        finally:
            self.lock.release()

    def update(self, other: int):
        """ Update logical clock counter. """
        self.lock.acquire()
        try:
            self.value = max(self.value, other) + 1
        except Exception as e:
            self.process.LOG.error(e)
            raise e
        finally:
            self.lock.release()

    def __gt__(self, other: "LogicalClock"):
        return self.get_value() > other.get_value()

    def __eq__(self, other: "LogicalClock"):
        return self.get_value() == other.get_value()

    def __lt__(self, other: "LogicalClock"):
        return self.get_value() < other.get_value()


# TODO: replace clock with self.process.clock (RM 2018-06-10 11:56:31)
class Event(object):
    """ Ocurrence that prompts update of Lamport clock. """
    def __init__(self, process: Process, timestamp: datetime, source: int):
        self.process = process
        self._clockstamp = self.process.clock.get_value()
        self.timestamp = timestamp
        self.source = source
        self.id = uuid.uuid1()

    @property
    def clock(self):
        return self._clockstamp

    @clock.setter
    def clock(self, value):
        raise TypeError("event cannot have its clock value changed.")


# TODO: replace clock with self.process.clock (RM 2018-06-10 11:56:31)
class Message(Event):
    """ Message sent or received through a TCP socket. """
    def __init__(self, clock: int, timestamp: datetime, source: int,
                 target: str):
        super().__init__(clock, timestamp, source)
        self.content = ""
        self.target = target
        self.status = False

    def __str__(self):
        return "Message {}: '{}'".format(
            self.id,
            self.content[:50] + (self.content[50:] and '...')
            )

    def mark_as_done(self):
        """ Change Message status. """
        self.status = True

    def log(self, parameter_list):
        raise NotImplementedError


# TODO: replace clock with self.process.clock (RM 2018-06-10 11:56:31)
class SentMessage(Message):
    """ Message sent through a TCP socket. """
    def __init__(self, clock: int, timestamp: datetime, source: int,
                 target: str):
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

    def log(self, parameter_list):
        raise NotImplementedError


# TODO: replace clock with self.process.clock (RM 2018-06-10 11:56:31)
class ReceivedMessage(Message):
    """ Message received through a TCP socket. """
    def __init__(self,
                 clock: int,
                 timestamp: datetime,
                 source: int,
                 target: str,
                 content=""):
        super().__init__(clock, timestamp, source, target)
        self.content = content

    @property
    def emitter_id(self):
        return self.content  # TODO: apply some regex (RM 2018-06-06 13:16:53)

    def log(self, parameter_list):
        raise NotImplementedError


# TODO: replace clock with self.process.clock (RM 2018-06-10 11:56:31)
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

    def log(self, parameter_list):
        raise NotImplementedError


# TODO: find an appropriate inheritance (RM 2018-05-28T21:00:09.381BRT)
class MessageQueue(object):
    """ Data structure holding messages while they wait for confirmation. """
    def __init__(self, process: Process, underlying=dummy.Queue):
        self.process = process
        self.underlying = underlying
    
    def put(self, message):
        self.underlying.put_nowait(message)

    def fetch(self):
        return self.underlying.get()
