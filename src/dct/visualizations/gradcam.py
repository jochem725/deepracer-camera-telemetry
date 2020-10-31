import tensorflow as tf
import numpy as np
import cv2
import threading
import time
from dct.util.model import Model


class GradCamOverlay:
    def __init__(self, car):
        self.car = car
        self.gradcamThread = threading.Thread(target=self.monitor_model)
        self.gradcamThread.daemon = True

        self.active_model_name = None
        self.model = None
        self.metadata = None
        self.cam = None

        self.gradcamThread.start()

    def placeholder(self, input_frame):
        return input_frame

    def frame(self, input_frame):
        if self.cam is None:
            return input_frame

        result, frame = self.cam.process(input_frame)

        return frame

    def monitor_model(self):
        while True:
            if self.active_model_name != self.car.model_name:
                self.cam = None

                self.model, self.metadata = self.car.load_model(self.car.model_name)
                self.cam = GradCam(self.model)
                self.active_model_name = self.car.model_name

            time.sleep(0.1)


class GradCam:
    def __init__(self, model: Model):
        self.model = model

        # Extract gradcam logic from model.
        self.input_layer = self.model.get_model_input()
        self.output_layer = self.model.get_model_output()
        self.conv_output = self.model.get_model_convolutional_output()

        # Get output for this action
        y_c = tf.reduce_sum(
            tf.multiply(
                self.output_layer,
                tf.one_hot(
                    [tf.argmax(self.output_layer)], self.output_layer.shape[-1]
                ),  # TODO: Argmax selects target action for PPO, also allow manual action idx to be specified.
            ),
            axis=1,
        )

        # Compute gradients based on last cnn layer
        self.target_grads = tf.gradients(y_c, self.conv_output)[0]

    def process(self, input):
        input_resized = cv2.resize(input, self.model.input_size())
        input_preprocessed = cv2.cvtColor(input_resized, cv2.COLOR_BGR2GRAY)

        input_frame = np.expand_dims(input_preprocessed, axis=2)
        ops = [self.output_layer, self.conv_output, self.target_grads]

        feed_dict = {self.input_layer: [input_frame]}

        result, out, grads_value = self.model.session.run(ops, feed_dict=feed_dict)
        result, out, grads_value = result[0, :], out[0, :], grads_value[0, :, :, :]

        weights = np.mean(grads_value, axis=(0, 1))
        cam = np.dot(out, weights)

        # ReLU (only positive values are of interest)
        cam = np.maximum(0, cam)
        cam = cam / np.max(cam)

        # Scale back to resized input frame dimensions.
        input_h, input_w = input_resized.shape[:2]
        cam = cv2.resize(cam, (input_w, input_h))

        # Blend
        cam = cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET)
        cam = np.float32(cam) + np.float32(input_resized)
        cam = 255 * cam / np.max(cam)
        cam = np.uint8(cam)

        cam = cv2.cvtColor(cam, cv2.COLOR_BGR2RGB)

        # Scale back to original frame dimensions.
        input_h, input_w = input.shape[:2]
        cam = cv2.resize(cam, (input_w, input_h))

        return result, cam
