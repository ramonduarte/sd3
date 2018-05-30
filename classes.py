import multiprocessing.dummy as dummy
import logging
import socket
import sys


log = logging.getLogger(__name__)

class Process(object):
    threads = []

    def __init__(self, *args, **kwargs):
        self.pid = 0

    def create_thread(self) -> "Thread":
        pass

    def create_socket(self, process: Process) -> "socket":
        pass

    def __lt__(self, other: Process):
        return self.pid < other.pid

    def __eq__(self, other: Process):
        return self.pid == other.pid

    def __gt__(self, other: Process):
        return self.pid > other.pid


class Thread(object):
    # def __init__(self, thread: dummy.Process, sock: socket.socket, *args, **kwargs):
    def __init__(self, thread: dummy.Process, *args, **kwargs):
        self.underlying = thread
        self.start_socket()

    def run(self, *args, **kwargs):
        """ Function permanently run by this thread. """
        raise NotImplementedError

    def start_socket(self, address='', port=8002):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(address, port)


class ListenerThread(Thread):
    # TODO: implement this method as an abstract function (RM 2018-05-30 13:58:16)
    def __init__(self, parameter_list):
        # self.socket.listen(10)
        pass

    def run(self, *args, **kwargs):
        while True:
            # accept connections from outside
            (clientsocket, address) = self.socket.accept()
            ip, port = str(address[0]), str(address[1])
            # now do something with the clientsocket
            # in this case, we'll pretend this is a threaded server

            log.info("Accepting connection from {}:{}".format(ip, port))
            try:
                self.underlying(target=self.write_log, args=(clientsocket, ip, port)).start()
            except:
                print("Terrible error!")
                import traceback
                traceback.print_exc()
    
        self.socket.close()

    # TODO: lift this method to abstract class Thread (RM 2018-05-30 14:21:35)
    def write_log(self, clientsocket, ip='', port=8002, MAX_BUFFER_SIZE = 4096):
        # the input is in bytes, so decode it
        input_from_client_bytes = clientsocket.recv(MAX_BUFFER_SIZE)

        # MAX_BUFFER_SIZE is how big the message can be
        # this is test if it's sufficiently big
        siz = sys.getsizeof(input_from_client_bytes)
        if  siz >= MAX_BUFFER_SIZE:
            log.error("The length of input is probably too long: {}.".format(siz))

        # decode input and strip the end of line
        input_from_client = input_from_client_bytes.decode("utf8").rstrip()

        log.info(input_from_client)

        # likely not needed (RM 2018-05-30 14:18:25)
        vysl = input_from_client.encode("utf8")  # encode the result string
        clientsocket.sendall(vysl)  # send it to client

        # close connection
        clientsocket.close()
        log.info("Connection {}:{} ended.")


class EmitterThread(Thread):
    # TODO: implement this method as an abstract function (RM 2018-05-30 13:58:16)
    def __init__(self, parameter_list):
        # self.socket.listen(10)
        pass

    def run(self, *args, **kwargs):
        self.socket.connect(("127.0.0.1", 8002))

        self.socket.send(self.generate) # we must encode the string to bytes  

        # likely not needed (RM 2018-05-30 14:27:38)
        result_bytes = self.socket.recv(4096) # the number means how the response can be in bytes  
        result_string = result_bytes.decode("utf8") # the return will be in bytes, so decode

    def generate(self, *args, **kwargs):
        """ Generates a random UTF-8 encoded string. """
        # TODO: create some sentence here (RM 2018-05-30 14:26:05)
        return ''.encode("utf")



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
