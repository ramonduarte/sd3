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
        self.address = address if address else "0.0.0.0"
        self.port = int(port)
        self.start_socket()

    def run(self, *args, **kwargs):
        """ Function permanently run by this thread. """
        raise NotImplementedError

    def start_socket(self):
        """ Set up connection through TCP/IP socket. """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setblocking(0)

    @property
    def hostname(self):
        return socket.gethostname()


class ListenerThread(Thread):
    """ Thread responsible for handling receiving messages. """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.socket.bind((self.address, self.port))
        self.socket.listen(10)
        if __debug__:
            print("socket is listening")

    def run(self, *args, **kwargs):
        # accept connections from outside
        # (client_socket, address) = self.socket.accept()
        if __debug__:
            print("Accepting connection at {}:{}".format(self.address, self.port))
        (client_socket, address) = self.socket.accept()
        if __debug__:
            print("Connection accepted")
        self.client_ip_addr = str(address[0])
        self.client_port = str(address[1])
        
        self.process.LOG.info("Accepting connection from %s:%s",
                              self.client_ip_addr,
                              self.client_port)

        # self.process.LOG.info("client socket: %s", client_socket)
        while True:
            try:
                self.listen(client_socket)
                # res = self.listen(client_socket)
                # self.underlying(
                #     target=self.listen,
                #     args=(client_socket)).start()
                break
            except Exception as e:
                self.process.LOG.fatal(e)
                traceback.print_exc()
                print(client_socket)
                sleep(1)

                self.listen(self.socket)

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
            print(input_from_client)

            if input_from_client == "CLOSE":
                # TODO: ReceivedMessage() (RM 2018-06-06 13:01:13)
                # client_socket.close()
                self.process.LOG.info("Connection %s:%s ended.", self.client_ip_addr,
                         self.client_port)
                # return 0
                continue
            
            # TODO: fix better approach to ack checks (RM 2018-06-10 13:35:33)
            if "ACK" in input_from_client:
                # TODO: fetch sent message and log it (RM 2018-06-10 13:38:03)
                message = ReceivedMessage(
                    self.process,
                    datetime.today(),
                    self.client_ip_addr,
                    self.address,
                    input_from_client
                )
                continue

            message = ReceivedMessage(
                self.process,
                datetime.today(),
                self.client_ip_addr,
                self.address,
                input_from_client
            )

            self.process.queue.put(message)
            # FIXME: self.process.LOG.info("RECEIVED %s", message.content)

            # returning ACK message (RM 2018-06-04 20:52:41)
            self.process.clock.increment()

            try:
                ack = AckMessage(
                    process=self.process,
                    timestamp=datetime.today(),
                    source=self.address,
                    target=self.client_ip_addr,
                    receipt_of=message.emitter_id,
                    original_clock=message.emitter_clock
                )
                # FIXME: self.process.LOG.info(ack.content)
                # can_read, can_write, under_exception = select.select(
                #     [client_socket],
                #     [self.process.emitter_thread.socket],
                #     [self.process.emitter_thread.socket]
                # )
                self.process.emitter_thread.socket.send(ack.content.encode("utf8"))
                message.mark_as_done()
                print("ACK sent")
                print(ack.content)
            except AttributeError:
                print("=>", message.content)

                sleep(1)
            except BrokenPipeError:
                print("ACK was not sent")

                sleep(1)

            print("listening")
            # TODO: end this function asynchronously (RM 2018-06-03 22:34:13)
            sleep(1)


class EmitterThread(Thread):
    """ Thread responsible for sending messages. """
    def __init__(self, target_address="", target_port=8002, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_address = target_address
        self.target_port = int(target_port)

    def run(self, *args, **kwargs):
        """ Loop through input parameters."""
        able_to_read, able_to_write, under_exception = select.select(
                [self.socket],
                [self.socket],
                [self.socket]
            )
        if self.socket in able_to_write:
            try:
                self.socket.connect((self.target_address, self.target_port))
            except (ConnectionRefusedError, BlockingIOError):
                if __debug__:
                    # print(self.address, self.port)
                    print(self.target_address, self.target_port)
                    print(able_to_write)
                # self.socket.close()
                sleep(1)
        # while True:

        for tick in range(self.process.events_by_process):
            self.process.clock.increment()
            message = SentMessage(
                self.process,
                datetime.now(),
                self.address,
                self.target_address,
            )
            try:
                can_read, can_write, under_exception = select.select(
                    [],
                    [self.socket],
                    [self.socket]
                )
                while self.socket not in can_write:
                    sleep(1)
                self.socket.send(message.content.encode("utf8"))
                
                if __debug__:
                    print("sent message", tick)
                    print(message.content)
            except BrokenPipeError:
                if __debug__:
                    print(self.target_port, self.target_address)
                traceback.print_exc()
                sleep(10)

            # FIXME: self.process.LOG.info(message.content)
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


class Event(object):
    """ Ocurrence that prompts update of Lamport clock. """
    def __init__(self, process: Process, timestamp: datetime, source: str):
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
        raise NotImplementedError

    def parse_content(self):
        """ Generate structure from message content. """
        raise NotImplementedError


# TODO: replace clock with self.process.clock (RM 2018-06-10 11:56:31)
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

    def log(self):
        self.process.LOG.info(self.content)


# TODO: replace clock with self.process.clock (RM 2018-06-10 11:56:31)
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

    def log(self):
        self.process.LOG.info(self.content)

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

                    # TODO: write message if ready (RM 2018-06-10 17:23:20)
                    # write message if head clock >= emitter_clock
                    print(self.process.queue.head, ">=", self.emitter_clock)
                    if self.process.queue.empty() or self.process.queue.head >= self.emitter_clock:
                        message = self.process.queue.fetch()
                        message.log()
                        print("log written")
                else:
                    # print(self.content)
                    print(self.emitter_clock, self.emitter_id)

        except:
            traceback.print_exc()


# TODO: replace clock with self.process.clock (RM 2018-06-10 11:56:31)
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

    def log(self):
        self.process.LOG.info(self.content)


class MessageQueue(object):
    """ Data structure holding messages while they wait for confirmation. """
    def __init__(self, process: Process, underlying=dummy.Queue):
        self.process = process
        self._underlying = underlying()
        self._head = 1
        self.lock = dummy.Lock()
    
    def put(self, message):
        """ Insert message at the back of a queue. """
        # print(self._underlying.qsize())
        self._underlying.put_nowait(message)

    def fetch(self):
        """ Return message from the head of a queue. """
        print("fetching", self._underlying.qsize())

        message = self._underlying.get()
        self.head = max(message.clock, self.head) + 1
        return message

    @property
    def head(self):
        self.lock.acquire()
        try:
            return self._head
        except Exception as e:
            self.process.LOG.error(e)
            raise e
        finally:
            self.lock.release()

    @head.setter
    def head(self, value):
        self.lock.acquire()
        try:
            self._head = value
        except Exception as e:
            self.process.LOG.error(e)
            raise e
        finally:
            self.lock.release()

    def empty(self):
        return self._underlying.empty()

