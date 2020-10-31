import threading
import time


class Broadcaster:
    """Handles relaying the source MJPEG stream to connected clients"""

    def __init__(self, source, key="/"):
        self.source = source
        self.key = key
        self.clients = []

        self.kill = False
        self.broadcastThread = threading.Thread(target=self.streamFromSource)
        self.broadcastThread.daemon = True

        self.broadcasting = False
        self.boundarySeparator = "frame"

    def start(self):
        self.broadcasting = True
        self.broadcastThread.start()

    def broadcast(self, data):
        # Serve to clients.
        for client in self.clients:
            if not client.connected:
                self.clients.remove(client)

            client.bufferStreamData(data)

    def prepare_frame(self, frame):
        data = "--{}".format(self.boundarySeparator).encode()
        data += b"\r\n"
        data += b"Content-type: image/jpeg\r\n"
        data += "Content-length: {}\r\n".format(len(frame)).encode()
        data += "X-Timestamp: {:6f}\r\n\r\n".format(time.time()).encode()
        data += frame
        data += b"\r\n"

        return data

    def streamFromSource(self):
        while True:
            self.broadcast(self.prepare_frame(self.source.placeholder()))

            try:
                for data in self.source.generate_frames():
                    if self.kill:
                        for client in self.clients:
                            client.kill = True
                        return

                    if data is None:
                        break

                    self.broadcast(self.prepare_frame(data))
            except Exception as e:
                print(e)
            finally:
                self.broadcast(self.prepare_frame(self.source.placeholder()))

                # Retry every second.
                time.sleep(1)
