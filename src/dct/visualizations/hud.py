import os
import cv2

from dct.visualizations.base import VisualizationOverlay
from dct.util.silverstone import DeepRacerCar
from dct.visualizations.util import (
    get_font,
    apply_gradient,
    write_text_on_image,
)

OVERLAY_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "assets",
    "DRL_video_oa_overlay_league_leaderboard.png",
)

FONT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "assets", "fonts", "AmazonEmber-Regular.ttf"
)


class HudOverlay(VisualizationOverlay):
    def __init__(self, car: DeepRacerCar):
        super().__init__()

        self.car = car
        self.overlay = None
        self.amazon_ember_regular_16px = get_font("AmazonEmber-Regular", 16)
        self.amazon_ember_light_13px = get_font("AmazonEmber-Light", 13)
        self.amazon_ember_regular_20px = get_font("AmazonEmber-Regular", 20)

    def load_overlay(self, width, height):
        return cv2.resize(
            cv2.imread(OVERLAY_PATH, cv2.IMREAD_UNCHANGED),
            (width, height),
        )

    def placeholder(self, input_frame):
        width = input_frame.shape[1]
        height = input_frame.shape[0]

        if self.overlay is None:
            self.overlay = self.load_overlay(width, height)

        frame = cv2.cvtColor(input_frame, cv2.COLOR_RGB2RGBA)
        frame_overlay = self.overlay.copy()
        frame_overlay[height - int(height / 4) :, :width, :] = 0

        gradient_alpha = frame_overlay[:, :, 3] / 255.0

        frame = apply_gradient(frame, frame_overlay, gradient_alpha)
        frame = write_text_on_image(
            image=frame,
            text=self.car.name,
            loc=(7, 1),
            font=self.amazon_ember_regular_20px,
            font_color=(255, 255, 255),
            font_shadow_color=(26, 26, 26),
        )

        return frame

    def frame(self, input_frame):
        width = input_frame.shape[1]
        height = input_frame.shape[0]

        if self.overlay is None:
            self.overlay = self.load_overlay(width, height)

        frame = cv2.cvtColor(input_frame, cv2.COLOR_RGB2RGBA)
        gradient_alpha = self.overlay[:, :, 3] / 255.0

        frame = apply_gradient(frame, self.overlay, gradient_alpha)
        frame = write_text_on_image(
            image=frame,
            text=self.car.name,
            loc=(7, 1),
            font=self.amazon_ember_regular_20px,
            font_color=(255, 255, 255),
            font_shadow_color=(26, 26, 26),
        )

        if self.car.model_name is not None:
            frame = write_text_on_image(
                image=frame,
                text="Model | {}".format(self.car.model_name),
                loc=(7, 35),
                font=self.amazon_ember_light_13px,
                font_color=(255, 255, 255),
                font_shadow_color=(26, 26, 26),
            )

        if self.car.car_driving is not None:
            frame = write_text_on_image(
                image=frame,
                text="{}".format("Driving" if self.car.car_driving else "Stopped"),
                loc=(7, 306),
                font=self.amazon_ember_light_13px,
                font_color=(255, 255, 255),
                font_shadow_color=(26, 26, 26),
            )

        if self.car.throttle is not None:
            frame = write_text_on_image(
                image=frame,
                text="Speed {:d}%".format(int(round(self.car.throttle))),
                loc=(7, 332),
                font=self.amazon_ember_regular_16px,
                font_color=(255, 255, 255),
                font_shadow_color=(26, 26, 26),
            )

        return frame
