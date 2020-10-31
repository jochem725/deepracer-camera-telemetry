import cv2
from dct.camera.stream import StreamConsumer

import numpy as np
from .connection import ConnectionOverlay


class VisualizationOverlay:
    def placeholder(self, input_frame):
        raise NotImplementedError

    def frame(self, input_frame):
        raise NotImplementedError


class BaseFrameVisualizer:
    """Base class which serves as a starting point for frame visualizations."""

    def __init__(self, stream: StreamConsumer, width=480, height=360):
        self.input_stream = stream
        self.width = width
        self.height = height
        self.last_frame = np.zeros((height, width, 3), dtype=np.uint8)
        self.visualizations = [ConnectionOverlay()]

    def add(self, viz: VisualizationOverlay):
        self.visualizations.append(viz)

    def placeholder(self):
        frame = self.last_frame.copy()

        # Apply added placeholder modifications in order.
        for viz in self.visualizations:
            frame = viz.placeholder(frame)

        return cv2.imencode(".jpg", frame)[1].tobytes()

    def generate_frames(self):
        for input_frame in self.input_stream.frame_iterator():
            frame = input_frame.copy()

            if frame is None:
                return

            # Apply added visualizations in order.
            for viz in self.visualizations:
                frame = viz.frame(frame)

            self.last_frame = input_frame
            yield cv2.imencode(".jpg", frame)[1].tobytes()
