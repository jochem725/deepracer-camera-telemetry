from queue import Queue
import threading


class StreamingClient(object):
    def __init__(self):
        self.streamBuffer = bytes()
        self.streamQueue = Queue()
        self.streamThread = threading.Thread(target=self.stream)
        self.streamThread.daemon = True
        self.connected = True
        self.kill = False

        super().__init__()

    def start(self):
        self.streamThread.start()

    def transmit(self, data):
        return len(data)

    def stop(self):
        pass

    def bufferStreamData(self, data):
        # use a thread-safe queue to ensure stream buffer is not modified while we're sending it
        self.streamQueue.put(data)

    def stream(self):
        while self.connected:
            # this call blocks if there's no data in the queue, avoiding the need for busy-waiting
            self.streamBuffer += self.streamQueue.get()

            # check if kill or connected state has changed after being blocked
            if self.kill or not self.connected:
                self.stop()
                return

            while len(self.streamBuffer) > 0:
                streamedTo = self.transmit(self.streamBuffer)
                if streamedTo and streamedTo >= 0:
                    self.streamBuffer = self.streamBuffer[streamedTo:]
                else:
                    self.streamBuffer = bytes()


class TCPStreamingClient(StreamingClient):
    def __init__(self, sock):
        super(TCPStreamingClient, self).__init__()
        self.sock = sock
        self.sock.settimeout(5)

    def stop(self):
        self.sock.close()

    def transmit(self, data):
        try:
            return self.sock.send(data)
        except OSError as e:
            self.connected = False
            self.sock.close()
