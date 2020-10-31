from .util import get_font, write_text_on_image


class ConnectionOverlay:
    def __init__(self):
        self.amazon_ember_regular_20px = get_font("AmazonEmber-Regular", 20)
        self.dots = ""

    def placeholder(self, input_frame):
        width = input_frame.shape[1]
        height = input_frame.shape[0]

        # Overlay connection lost message.
        frame = write_text_on_image(
            image=input_frame,
            text="Connection Lost{}".format(self.dots),
            loc=(width / 2, height / 2),
            font=self.amazon_ember_regular_20px,
            font_color=(255, 255, 255),
            font_shadow_color=(26, 26, 26),
            centered=True,
        )

        if len(self.dots) < 3:
            self.dots += "."
        else:
            self.dots = ""

        return frame

    def frame(self, input_frame):
        return input_frame
