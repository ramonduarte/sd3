import threading
import logging

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


class Thread(threading.Thread):
    def __init__(self, process: Process, *args, **kwargs):
        threading.Thread.__init__(self)
        self.process = process


class ListenerThread(Thread):
    pass


class EmitterThread(Thread):
    pass



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
        self.lock = threading.lock()

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


class PriorityLine(object):  # TODO: find an appropriate inheritance (RM 2018-05-28T21:00:09.381BRT)
    pass
