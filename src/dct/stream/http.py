import socket
import threading
import logging
import re
from .streaming import TCPStreamingClient
from .broadcaster import Broadcaster
import os


class HTTPRequestHandler:
    """Handles the initial connection with HTTP clients"""

    def __init__(self, port):
        self.header = ""
        self.header += "HTTP/1.0 200 OK\r\n"
        self.header += "Connection: keep-alive\r\n"
        self.header += "Server: MJPEG-DeepRacer\r\n"
        self.header += "Cache-Control: no-store, no-cache, must-revalidate\r\n"
        self.header += "Cache-Control: pre-check=0, post-check=0, max-age=0\r\n"
        self.header += "Pragma: no-cache\r\n"
        self.header += "Expires: -1\r\n"
        self.header += (
            "Content-Type: multipart/x-mixed-replace;boundary={boundaryKey}\r\n"
        )
        self.header += "\r\n"

        self.acceptsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.acceptsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.acceptsock.bind(("0.0.0.0", port))
        self.acceptsock.listen(10)

        self.broadcasters = {}
        self.kill = False

        self.clientThread = threading.Thread(target=self.acceptClients)
        self.clientThread.daemon = True

    def addBroadcaster(self, broadcaster, key):
        if key in self.broadcasters:
            raise ValueError("Broadcaster with key exists.")

        self.broadcasters[key] = broadcaster

    def start(self):
        self.clientThread.start()

    #
    # Thread to handle connecting clients
    #
    def acceptClients(self):
        while True:
            clientsock, addr = self.acceptsock.accept()

            if self.kill:
                clientsock.close()
                return
            handlethread = threading.Thread(
                target=self.handleRequest, args=(clientsock,)
            )
            handlethread.start()

    #
    # Thread to process client requests
    #
    def handleRequest(self, clientsock):
        buff = ""
        while True:
            try:
                data = clientsock.recv(64).decode("utf-8")
                if data == "":
                    break

                buff += data

                if "\r\n\r\n" in buff or "\n\n" in buff:
                    break  # as soon as the header is sent - we only care about GET requests

            except Exception as e:
                print(e)
                break

        if buff != "":
            try:
                match = re.search("GET (.*) ", buff)

                requestPath = match.group(1)
            except Exception as e:
                print(e)
                return

            if "/stream/" in requestPath:
                try:
                    key = requestPath.split("/stream/")[1]

                    if key in self.broadcasters:
                        broadcaster = self.broadcasters[key]
                        if broadcaster.broadcasting:
                            clientsock.sendall(
                                self.header.format(
                                    boundaryKey=broadcaster.boundarySeparator
                                ).encode()
                            )
                            client = TCPStreamingClient(clientsock)
                            client.start()
                            broadcaster.clients.append(client)
                        else:
                            clientsock.close()

                        return
                except Exception:
                    pass

            clientsock.sendall(b"HTTP/1.0 302 FOUND")
            clientsock.close()
