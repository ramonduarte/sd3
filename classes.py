"""
Classes used for this assignment.
"""

import multiprocessing.dummy as dummy
import socket
import sys
import traceback
import uuid
import os
import re
import select
from random import choice
from datetime import datetime
from time import sleep
from conf import MAX_BUFFER_SIZE


class Process(object):
    """
    Process that will coordenate threads.
    """
    def __init__(self, LOG, target_address="", target_port=8002, address="",
                 port=8002, events_by_process=5, events_per_second=.1):
        self.events_by_process = events_by_process
        self.events_per_second = events_per_second
        self.address = address
        self.port = int(port)
        self.target_address = target_address
        self.target_port = int(target_port)
        self.create_socket()
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

    def create_socket(self) -> "socket":
        """ Start socket for its threads to use. """
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.address, self.port))

    @property
    def ready(self):
        """ Flag to join async threads. """
        return self.emitter_thread._ready and self.listener_thread._ready

    # TODO: broadcast message to all processes (RM 2018-06-12 21:42:02)
    def broadcast(self, origin):
        """ Send messages to all processes. """
        pass

    @property
    def pid(self):
        return os.getpid()

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
        self._ready = False
        self.underlying = thread
        self.process = process
        self.address = address if address else "0.0.0.0"
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
        # self.socket.bind((self.address, self.port))
        self.process.server_socket.listen(10)
        if __debug__:
            print("socket is listening")

    def run(self, *args, **kwargs):
        # accept connections from outside
        # (client_socket, address) = self.socket.accept()
        if __debug__:
            print("Accepting connection at {}:{}".format(self.address, self.port))
        (client_socket, address) = self.process.server_socket.accept()
        if __debug__:
            print("Connection accepted")
        self.client_ip_addr = str(address[0])
        self.client_port = str(address[1])

        if __debug__:
            self.process.LOG.info("Accepting connection from %s:%s",
                                  self.client_ip_addr,
                                  self.client_port)

        while True:
            try:
                self.listen(client_socket)
                break
            except Exception as exception:
                self.process.LOG.fatal(exception)
                if __debug__:
                    print(client_socket)
                    traceback.print_exc()
                sleep(1)

        self._ready = True
        return 0


    # needs to be a function to keep thread semantics (RM 2018-06-03 22:32:44)
    def listen(self, client_socket):
        """ Listen to socket until a message is received. """

        while True:
            input_from_client_bytes = client_socket.recv(MAX_BUFFER_SIZE)
            size = sys.getsizeof(input_from_client_bytes)

            if  size >= MAX_BUFFER_SIZE:
                # TODO: ReceivedMessage() (RM 2018-06-06 13:01:13)
                self.process.LOG.error("The length of input is too long: %d", size)
                continue

            # decode input and strip the end of line
            input_from_client = input_from_client_bytes.decode("utf8").rstrip()

            if size == 33 or input_from_client == "CLOSE":  # empty message, remote thread failed
                # TODO: ReceivedMessage() (RM 2018-06-06 13:01:13)
                if __debug__:
                    self.process.LOG.info("Connection %s:%s ended.",
                                          self.client_ip_addr,
                                          self.client_port)
                return 0

            message = ReceivedMessage(
                self.process,
                datetime.today(),
                self.client_ip_addr,
                self.address,
                input_from_client
            )

            if "ACK" in input_from_client:
                continue

            self.process.queue.put(message)

            while True:
                try:
                    ack = AckMessage(
                        process=self.process,
                        timestamp=datetime.today(),
                        source=self.address,
                        target=self.client_ip_addr,
                        receipt_of=message.emitter_id,
                        original_clock=message.emitter_clock
                    )
                    
                    able_to_write = select.select([], [self.process.client_socket], [])[1]
                    while self.process.client_socket not in able_to_write:
                        sleep(1)
                    self.process.client_socket.send(ack.content.encode("utf8"))

                    # FIXME: this doesn't do anything (RM 2018-06-12 12:22:26)
                    message.mark_as_done()

                    if __debug__:
                        print("ACK sent")
                        print(ack.content)

                    break
                except AttributeError:
                    if __debug__:
                        print("=>", message.content)
                    sleep(1)
                except BrokenPipeError:
                    if __debug__:
                        print("ACK was not sent")
                    sleep(1)

            if __debug__:
                print("listening")

            # TODO: end this function asynchronously (RM 2018-06-03 22:34:13)
            sleep(1)

        # return 0

class EmitterThread(Thread):
    """ Thread responsible for sending messages. """
    def __init__(self, target_address="", target_port=8002, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_address = target_address
        self.target_port = int(target_port)

    def run(self, *args, **kwargs):
        """ Loop through input parameters."""
        able_to_write = select.select([], [self.process.client_socket], [])[1]
        if self.process.client_socket in able_to_write:
            try:
                self.process.client_socket.connect((self.target_address, self.target_port))
            except (ConnectionRefusedError, BlockingIOError):
                if __debug__:
                    print(self.target_address, self.target_port)
                    print(able_to_write)
                # self.socket.close()
                sleep(1)

        for tick in range(self.process.events_by_process):
            message = SentMessage(
                self.process,
                datetime.now(),
                self.address,
                self.target_address,
            )
            sent = False
            attempt = 0

            while not sent:
                sent = self.send(message, tick)
                attempt += 1
                print("attempt =", attempt)
                if sent:
                    break
                sleep(2)

            self.process.queue.put(message)
            sleep(1.0/self.process.events_per_second)



        if __debug__:
            print("broke loop")
        # FIXME: define protocol to end connection
        self.process.client_socket.send("CLOSE".encode("utf8"))

        self._ready = True
        while True:
            sleep(100)

    # TODO: ideally this should be lifted to Process (RM 2018-06-12 22:38:03)
    def send(self, message, tick=""):
        """ Send messages using client socket. """
        if __debug__:
            print("loop running")
        try:
            able_to_write = select.select([], [self.process.client_socket], [])[1]
            while self.process.client_socket not in able_to_write:
                sleep(1)
            self.process.client_socket.sendall(message.content.encode("utf8"))
            
            if __debug__:
                print("sent message", tick)
                print(message.content)

            return True
        except BrokenPipeError:
            if __debug__:
                print(self.target_port, self.target_address)
                traceback.print_exc()
                self.process.client_socket.close()
                sleep(10)
                self.process.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.process.client_socket.connect((self.target_address, self.target_port))
                sleep(2)
                self.process.client_socket.sendall(message.content.encode("utf8"))
                print("message sent after recovering")
            return False


class Channel(object):
    """ Communication between remote processes. """
    def __init__(self, sender: Process, receiver: Process):
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
    def __init__(self, process: Process):
        self.value = 1
        self.process = process
        self.lock = dummy.Lock()

    def increment(self):
        """ Increment logical clock counter. """
        self.lock.acquire()
        try:
            self.value += 1
        except Exception as exception:
            self.process.LOG.error(exception)
            raise exception
        finally:
            self.lock.release()

    def get_value(self):
        """ Access value stored in the logical clock counter. """
        self.lock.acquire()
        try:
            return self.value
        except Exception as exception:
            self.process.LOG.error(exception)
            raise exception
        finally:
            self.lock.release()

    def update(self, other: int):
        """ Update logical clock counter. """
        self.lock.acquire()
        try:
            self.value = max(self.value, other) + 1
        except Exception as exception:
            self.process.LOG.error(exception)
            raise exception
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
    def __init__(self, process: Process, timestamp: datetime, source: str):
        self.process = process
        self._clockstamp = self.process.clock.get_value()
        self.timestamp = timestamp
        self.source = source
        self.id = uuid.uuid1()
        self.process.clock.increment()

    @property
    def clock(self):
        """ Value of recorded logical clock. """
        return self._clockstamp

    @clock.setter
    def clock(self, value):
        """ Value of recorded logical clock. """
        raise TypeError("event cannot have its clock value changed.")


class Message(Event):
    """ Message sent or received through a TCP socket. """
    def __init__(self, process: Process, timestamp: datetime, source: str,
                 target: str):
        super().__init__(process, timestamp, source)
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

    def log(self):
        """ Write message to log. """
        self.process.LOG.info(self.content)



class SentMessage(Message):
    """ Message sent through a TCP socket. """
    def __init__(self, process: Process, timestamp: datetime, source: str,
                 target: str):
        super().__init__(process, timestamp, source, target)
        self.content = self.generate()

    def sentence(self):
        """ Generates readable text for events."""
        return choice(open("sentences.txt").readlines()).rstrip()

    def generate(self):
        """ Generates an UTF-8 encoded string. """
        return "<{}> SENT message {} from {} to {}: {} ({})".format(
            self.clock,
            self.id,
            self.source,
            self.target,
            self.sentence(),
            datetime.now()
            )


class ReceivedMessage(Message):
    """ Message received through a TCP socket. """
    def __init__(self,
                 process: Process,
                 timestamp: datetime,
                 source: str,
                 target: str,
                 content=""):
        super().__init__(process, timestamp, source, target)
        self.content = content
        self.parse_content()

    def parse_content(self):
        print("received message")
        print(self.content)
        try:
            if "ACK" in self.content:
                print("ACK")
                pattern = r"<(\d*)>.*([\w-]{36}).*\s([\w-]{36}).*<(\d*)>\s" \
                r"from\s([\d.]+) to ([\d.]+)\s\(([\d\s\-.:]*)\)"
                match = re.search(pattern, self.content)
                self.emitter_clock = match.group(1)
                self.emitter_id = match.group(2)
                self.confirmation_clock = match.group(3)
                self.original_clock = int(match.group(4))
                # self.source = match.group(5)
                # self.target = match.group(6)
                self.emitter_timestamp = match.group(7)

                # TODO: write message if ready (RM 2018-06-10 17:23:20)
                # write message if all acks received
                print("original_clock = ", self.original_clock)
                message = self.process.queue.fetch()
                message.log()

                # possibly unnecessary (RM 2018-06-10 23:06:07)
                self.process.queue.head = max(self.process.queue.head,
                                              self.original_clock) + 1
            else:
                pattern = r"<(\d*)>.*([\w-]{36}).*from ([\d.]+) " \
                r"to ([\d.]+): ([\w\s',]+) \(([\d\s\-.:]*)\)"
                match = re.search(pattern, self.content)
                if match:
                    self.emitter_clock = int(match.group(1))
                    self.emitter_id = match.group(2)
                    # self.source = match.group(3)
                    # self.target = match.group(4)
                    self.emitter_content = match.group(5)
                    self.emitter_timestamp = match.group(6)
        except Exception:
            traceback.print_exc()


class AckMessage(Message):
    """ Acknowledgement of a message received through a TCP socket. """
    def __init__(self,
                 process: Process,
                 timestamp: datetime,
                 source: str,
                 target: str,
                 receipt_of: uuid.UUID,
                 original_clock: int):
        super().__init__(process, timestamp, source, target)
        self.receipt_of = receipt_of
        self.original_clock = int(original_clock)
        self.content = "<{}> ACK {} in confirmation of message {} <{}>" \
                        " from {} to {} ({})".format(
                            self.clock,
                            self.id,
                            self.receipt_of,
                            self.original_clock,
                            self.target,
                            self.source,
                            self.timestamp
                        )


class MessageQueue(object):
    """ Data structure holding messages while they wait for confirmation. """
    def __init__(self, process: Process, underlying=dummy.Queue):
        self.process = process
        self._underlying = underlying()
        self._head = 1
        self.lock = dummy.Lock()

    def put(self, message):
        """ Insert message at the back of a queue. """
        self._underlying.put_nowait(message)

    def fetch(self):
        """ Return message from the head of a queue. """
        if __debug__:
            print("after fetching:", self._underlying.qsize())

        message = self._underlying.get()
        self.head = max(message.clock, self.head) + 1
        return message

    @property
    def head(self):
        """ Value of recorded logical clock of first message in queue. """
        self.lock.acquire()
        try:
            return self._head
        except Exception as exception:
            self.process.LOG.error(exception)
            raise exception
        finally:
            self.lock.release()

    @head.setter
    def head(self, value):
        """ Value of recorded logical clock of first message in queue. """
        self.lock.acquire()
        try:
            self._head = value
        except Exception as exception:
            self.process.LOG.error(exception)
            raise exception
        finally:
            self.lock.release()

    def empty(self):
        """ Returns True if no messages on queue. """
        return self._underlying.empty()
