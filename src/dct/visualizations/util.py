import os
import cv2

from PIL import ImageFont, Image, ImageDraw
import numpy as np


def get_font(font_name, font_size):
    """Helper method that returns an ImageFont object for the desired font if
       available otherwise returns default font

    Args:
        font_name (str): String of the desired font
        font_size (str): Size of the font in points

    Returns:
        ImageFont: ImageFont object with the given font name
    """
    try:
        font_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
        font_path = os.path.join(font_dir, font_name + ".ttf")
        font = ImageFont.truetype(font_path, font_size)
    except (OSError, IOError):
        print("%s unsupported font, using default font", font_name)
        font = ImageFont.load_default()
    return font


def write_text_on_image(
    image, text, loc, font, font_color, font_shadow_color, centered=False
):
    """This function is used to write the text on the image using cv2 writer

    Args:
        image (Image): The image where the text should be written
        text (str): The actual text data to be written on the image
        loc (tuple): Pixel location (x, y) where the text has to be written
        font (ImageFont): The font style object
        font_color (tuple): RGB value of the font
        font_shadow_color (tuple): RGB color of the font shawdow

    Returns:
        Image: Edited image
    """
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_im = Image.fromarray(image)
    draw = ImageDraw.Draw(pil_im)

    if centered:
        w, h = draw.textsize(text, font=font)
        loc = ((loc[0] - w / 2), (loc[1] - h / 2))

    draw_shadow(draw, text, font, loc[0], loc[1], font_shadow_color)
    draw.text(loc, text, font=font, fill=font_color)
    return cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)


def draw_shadow(draw_obj, text, font, x_loc, y_loc, shadowcolor):
    """Helper method that draws a shadow around given text for a given ImageDraw

    Args:
        draw_obj (ImageDraw): ImageDraw object where the shadow will drawn
        text (str): String to draw the shadow around
        font (ImageFont): The font of the string that the shadow will be drawn around
        x_loc (int): X location of the text string
        y_loc (int): Y location of text string
        shadowcolor (str): Color of the shadow
    """
    draw_obj.text((x_loc - 1, y_loc - 1), text, font=font, fill=shadowcolor)
    draw_obj.text((x_loc + 1, y_loc - 1), text, font=font, fill=shadowcolor)
    draw_obj.text((x_loc - 1, y_loc + 1), text, font=font, fill=shadowcolor)
    draw_obj.text((x_loc + 1, y_loc + 1), text, font=font, fill=shadowcolor)


def apply_gradient(main_image, gradient_img, gradient_alpha):
    """ The gradient on the image is overlayed so that text looks visible and clear.
    This leaves a good effect on the image.
    Args:
        main_image (Image): The main image where gradient has to be applied
        gradient_img (Image): The gradient image
        gradient_alpha (Numpy.Array): The 4th channel, the alpha channel of the gradient
    Returns:
        Image: Gradient applied image
    """
    for channel in range(0, 4):
        main_image[-gradient_img.shape[0] :, -gradient_img.shape[1] :, channel] = (
            gradient_alpha * gradient_img[:, :, channel]
        ) + (1 - gradient_alpha) * (
            main_image[-gradient_img.shape[0] :, -gradient_img.shape[1] :, channel]
        )
    return main_image
