import cv2
import numpy as np
import threading
import time
import queue
import uuid
import logging

from dct.util.silverstone import DeepRacerCar


class StreamConsumer:
    def __init__(self):
        self.queue = queue.Queue()

    def notify(self, frame):
        self.queue.put(frame)

    def frame_iterator(self):
        try:
            while True:
                # If no new frame in queue for 1 second, stop iterating.
                frame = self.queue.get(timeout=1)

                if frame is None:
                    return

                yield frame
        except queue.Empty:
            return


class BaseStream:
    """Base class which serves as a blueprint for frame providing objects."""

    def __init__(self):
        self.identifier = uuid.uuid4()
        self.consumers = []

        logging.info("Creating source stream {}".format(self.identifier))

    def publish_frame(self, frame):
        for consumer in self.consumers:
            consumer.notify(frame)

    def subscribe(self, consumer: StreamConsumer):
        self.consumers.append(consumer)

    def unsubscribe(self, consumer: StreamConsumer):
        if consumer in self.consumers:
            self.consumers.remove(consumer)

    @property
    def fps(self):
        raise NotImplementedError

    @property
    def width(self):
        raise NotImplementedError

    @property
    def height(self):
        raise NotImplementedError


class DeepRacerMJPEGStream(BaseStream):
    def __init__(
        self, car: DeepRacerCar, width=480, height=360, quality=90, min_fps=10.0
    ):
        super().__init__()

        self.car = car
        self.videoThread = threading.Thread(target=self.process_frames)
        self.videoThread.daemon = True

        self.video_url = car.camera_feed(width=width, height=height, quality=quality)
        self.video_width = width
        self.video_height = height

        if quality <= 0 or quality > 100:
            raise ValueError("Video quality should be in range [1, 100]")

        self.quality = quality  # Minimum quality of the video stream, lower will use less data at the cost of lower video quality.
        self.min_fps = min_fps  # Minimum FPS required for broadcasting, if approx fps too low the stream will disconnect.
        self.framerate = None  # Stores current framerate approximation.

    def start(self):
        self.videoThread.start()
        logging.debug("Starting streaming thread for stream {}".format(self.identifier))

    def process_frames(self):
        while True:
            try:
                logging.info(
                    "Attempting to connect to stream {}".format(self.identifier)
                )

                if not self.car.connected:
                    logging.info(
                        "Car '{}' not connected for input stream {}".format(
                            self.car.name, self.identifier
                        )
                    )
                    continue

                bytebuffer = bytes()

                response = self.car.session.get(self.video_url, stream=True, timeout=6)
                response.raise_for_status()

                chunk_size = 10 * 1024 * 1024

                start_frame = time.time()
                framerate_counter = 0

                for chunk in response.iter_content(chunk_size=chunk_size):
                    bytebuffer += chunk
                    a = bytebuffer.find(b"\xff\xd8")
                    b = bytebuffer.find(b"\xff\xd9")

                    if a != -1 and b != -1:
                        framerate_counter += 1
                        frame_time = time.time()

                        jpg = bytebuffer[a : b + 2]
                        bytebuffer = bytebuffer[b + 2 :]
                        frame = cv2.imdecode(
                            np.fromstring(jpg, dtype=np.uint8), cv2.IMREAD_COLOR
                        )

                        # Car will start "enqueing" frames if it cannot send them fast enough causing huge delays on the stream after a period of bad connection.
                        # Workaround: monitor framerate, if it drops try to reconnect.
                        if (frame_time - start_frame) > 1:
                            self.framerate = framerate_counter / (
                                frame_time - start_frame
                            )

                            framerate_counter = 0
                            start_frame = frame_time
                            logging.debug("FPS: {}".format(self.framerate))

                        # If no approximate framerate yet, don't broadcast the frames to prevent lag when low framerate occurs.
                        if self.framerate is None:
                            continue
                        elif self.framerate < self.min_fps:
                            logging.debug(
                                "Stopping because of low framerate: {}".format(
                                    self.framerate
                                )
                            )
                            self.framerate = None
                            break

                        self.publish_frame(frame)
            except Exception as e:
                logging.debug(e)
                pass
            finally:
                retry_rate = 5
                logging.debug(
                    "Finish stream for {}, retry in {} seconds...".format(
                        self.identifier, retry_rate
                    )
                )

                # Notify no frame is sent.
                self.publish_frame(None)

                # On failure try to reconnect to stream every 5 seconds.
                time.sleep(retry_rate)

    @property
    def width(self):
        return self.video_width

    @property
    def height(self):
        return self.video_height
