from __future__ import annotations

import os
import sys
from enum import Enum

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import navi
from nodes.groups import if_enum_group
from nodes.impl.color.color import Color
from nodes.impl.image_utils import normalize
from nodes.impl.pil_utils import convert_to_BGRA
from nodes.properties.inputs import ColorInput, EnumInput, NumberInput, TextInput
from nodes.properties.outputs import ImageOutput

from .. import compositing_group


class TextAsImageFont(Enum):
    ROBOTO_REGULAR = "roboto_regular"
    ROBOTO_BOLD = "roboto_bold"
    ROBOTO_ITALIC = "roboto_italic"
    ROBOTO_BOLD_ITALIC = "roboto_bold_italic"
    ROBOTO_MONO_REGULAR = "roboto_mono_regular"
    ROBOTO_MONO_BOLD = "roboto_mono_bold"
    ROBOTO_MONO_ITALIC = "roboto_mono_italic"
    ROBOTO_MONO_BOLD_ITALIC = "roboto_mono_bold_italic"
    OPEN_SANS_REGULAR = "open_sans_regular"
    OPEN_SANS_BOLD = "open_sans_bold"
    OPEN_SANS_ITALIC = "open_sans_italic"
    OPEN_SANS_BOLD_ITALIC = "open_sans_bold_italic"


TEXT_AS_IMAGE_FONTS = {
    TextAsImageFont.ROBOTO_REGULAR: {
        "label": "Roboto",
        "path": "Roboto/Roboto-Regular.ttf",
    },
    TextAsImageFont.ROBOTO_BOLD: {
        "label": "Roboto Bold",
        "path": "Roboto/Roboto-Bold.ttf",
    },
    TextAsImageFont.ROBOTO_ITALIC: {
        "label": "Roboto Italic",
        "path": "Roboto/Roboto-Italic.ttf",
    },
    TextAsImageFont.ROBOTO_BOLD_ITALIC: {
        "label": "Roboto Bold Italic",
        "path": "Roboto/Roboto-BoldItalic.ttf",
    },
    TextAsImageFont.ROBOTO_MONO_REGULAR: {
        "label": "Roboto Mono",
        "path": "RobotoMono/RobotoMono-Regular.ttf",
    },
    TextAsImageFont.ROBOTO_MONO_BOLD: {
        "label": "Roboto Mono Bold",
        "path": "RobotoMono/RobotoMono-Bold.ttf",
    },
    TextAsImageFont.ROBOTO_MONO_ITALIC: {
        "label": "Roboto Mono Italic",
        "path": "RobotoMono/RobotoMono-Italic.ttf",
    },
    TextAsImageFont.ROBOTO_MONO_BOLD_ITALIC: {
        "label": "Roboto Mono Bold Italic",
        "path": "RobotoMono/RobotoMono-BoldItalic.ttf",
    },
    TextAsImageFont.OPEN_SANS_REGULAR: {
        "label": "Open Sans",
        "path": "OpenSans/OpenSans-VariableFont_wdth,wght.ttf",
    },
    TextAsImageFont.OPEN_SANS_BOLD: {
        "label": "Open Sans Bold",
        "path": "OpenSans/OpenSans-Bold.ttf",
    },
    TextAsImageFont.OPEN_SANS_ITALIC: {
        "label": "Open Sans Italic",
        "path": "OpenSans/OpenSans-Italic.ttf",
    },
    TextAsImageFont.OPEN_SANS_BOLD_ITALIC: {
        "label": "Open Sans Bold Italic",
        "path": "OpenSans/OpenSans-BoldItalic.ttf",
    },
}

TEXT_AS_IMAGE_FONT_LABELS = {
    key: TEXT_AS_IMAGE_FONTS[key]["label"] for key in TextAsImageFont
}


class TextAsImageAlignment(Enum):
    LEFT = "left"
    CENTERED = "center"
    RIGHT = "right"


TEXT_AS_IMAGE_ALIGNMENT_LABELS = {
    TextAsImageAlignment.LEFT: "Left",
    TextAsImageAlignment.CENTERED: "Centered",
    TextAsImageAlignment.RIGHT: "Right",
}


class TextAsImagePosition(Enum):
    TOP_LEFT = "top_left"
    TOP_CENTERED = "top_centered"
    TOP_RIGHT = "top_right"
    CENTERED_LEFT = "centered_left"
    CENTERED = "centered"
    CENTERED_RIGHT = "centered_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTERED = "bottom_centered"
    BOTTOM_RIGHT = "bottom_right"


TEXT_AS_IMAGE_POSITION_LABELS = {
    TextAsImagePosition.TOP_LEFT: "Top left",
    TextAsImagePosition.TOP_CENTERED: "Top centered",
    TextAsImagePosition.TOP_RIGHT: "Top right",
    TextAsImagePosition.CENTERED_LEFT: "Centered left",
    TextAsImagePosition.CENTERED: "Centered",
    TextAsImagePosition.CENTERED_RIGHT: "Centered right",
    TextAsImagePosition.BOTTOM_LEFT: "Bottom left",
    TextAsImagePosition.BOTTOM_CENTERED: "Bottom centered",
    TextAsImagePosition.BOTTOM_RIGHT: "Bottom right",
}

TEXT_AS_IMAGE_X_Y_REF_FACTORS = {
    TextAsImagePosition.TOP_LEFT:           {'x': np.array([0, 0.5]), 'y': np.array([0, 0.5])},
    TextAsImagePosition.TOP_CENTERED:       {'x': np.array([0.5, 0]), 'y': np.array([0, 0.5])},
    TextAsImagePosition.TOP_RIGHT:          {'x': np.array([1, -0.5]), 'y': np.array([0, 0.5])},
    TextAsImagePosition.CENTERED_LEFT:      {'x': np.array([0, 0.5]), 'y': np.array([0.5, 0])},
    TextAsImagePosition.CENTERED:           {'x': np.array([0.5, 0]), 'y': np.array([0.5, 0])},
    TextAsImagePosition.CENTERED_RIGHT:     {'x': np.array([1, -0.5]), 'y': np.array([0.5, 0])},
    TextAsImagePosition.BOTTOM_LEFT:        {'x': np.array([0, 0.5]), 'y': np.array([1, -0.5])},
    TextAsImagePosition.BOTTOM_CENTERED:    {'x': np.array([0.5, 0]), 'y': np.array([1, -0.5])},
    TextAsImagePosition.BOTTOM_RIGHT:       {'x': np.array([1, -0.5]), 'y': np.array([1, -0.5])},
}

@compositing_group.register(
    schema_id="chainner:image:text_as_image",
    name="Text as image",
    description="Converts a text to an image",
    icon="MdTextFields",
    inputs=[
        TextInput("Text", multiline=True),
        EnumInput(
            TextAsImageFont,
            label="Font",
            option_labels=TEXT_AS_IMAGE_FONT_LABELS,
            default=TextAsImageFont.ROBOTO_REGULAR,
        ),
        ColorInput(channels=[1, 3], default=Color.bgr((0, 0, 0))),
        EnumInput(
            TextAsImageAlignment,
            label="Text alignment",
            option_labels=TEXT_AS_IMAGE_ALIGNMENT_LABELS,
            default=TextAsImageAlignment.CENTERED,
        ),
        NumberInput(
            "Width",
            minimum=1,
            maximum=None,
            controls_step=1,
            precision=0,
            default=100,
        ),
        NumberInput(
            "Height",
            minimum=1,
            maximum=None,
            controls_step=1,
            precision=0,
            default=100,
        ),
        EnumInput(
            TextAsImagePosition,
            label="Position",
            option_labels=TEXT_AS_IMAGE_POSITION_LABELS,
            default=TextAsImagePosition.CENTERED,
        ),
    ],
    outputs=[
        ImageOutput(
            image_type="""
                Image {
                    width: Input4 & uint,
                    height: Input5 & uint,
                    channels: 4
                }
                """,
            assume_normalized=True,
        )
    ],
)
def text_as_image_node(
    text: str,
    font_name: TextAsImageFont,
    font_color: Color,
    alignment: TextAsImageAlignment,
    width: int,
    height: int,
    position: TextAsImagePosition,
) -> np.ndarray:

    font_path = os.path.join(
        os.path.dirname(sys.modules["__main__"].__file__),
        f"fonts",
        f"{TEXT_AS_IMAGE_FONTS[font_name]['path']}",
    )
    # print("---------------------------------------------------------------")

    lines = text.split("\n")
    line_count, max_line = len(lines), max(lines, key=len)
    # print(f"line_count: {line_count}")

    # Use a text as reference to get max size
    font = ImageFont.truetype(font_path, size=100)
    w_ref, h_ref = font.getsize(max_line)[0], font.getsize("[§]")[1]

    # Calculate font size to fill the specified image size
    w = int(width * 100.0 / w_ref)
    h = int(height * 100.0 / (h_ref * line_count))
    font_size = min(w, h)
    # print(f"max w, h: {w}x{h}")
    # print(f"calculated font size: {font_size}")
    # print(f"TextAsImageSizeConstraint.CONTAINER: {width}x{height}")

    font = ImageFont.truetype(font_path, size=font_size)
    w_text, h_text = font.getsize(max_line)
    h_text *= line_count
    # print(f"(w_text, h_text): {w_text}x{h_text}")

    color = 255 * np.array(font_color.value)
    color = tuple(color.astype("uint8"))

    pil_image = Image.new("RGBA", (width, height), (255, 0, 0, 0))
    drawing = ImageDraw.Draw(pil_image)

    # Use middle anchor to simplify
    # https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html#
    # https://pillow.readthedocs.io/en/stable/handbook/text-anchors.html#text-anchors
    x_ref = round(np.sum(np.array([width, w_text]) * TEXT_AS_IMAGE_X_Y_REF_FACTORS[position]['x'])) # type: ignore
    y_ref = round(np.sum(np.array([height, h_text]) * TEXT_AS_IMAGE_X_Y_REF_FACTORS[position]['y'])) # type: ignore

    # x0, y0 = x_ref - w_text/2, y_ref - h_text/2
    # x1, y1 = x0 + w_text, y0 + h_text
    # print(f"(x0,y0)(x1,y1): ({x0},{y0})({x1},{y1})")
    # outline_width = 3
    # drawing.rectangle(((x0, y0), (x1, y1)), outline ="black", width=outline_width)

    drawing.text(
        (x_ref, y_ref),
        text,
        font=font,
        anchor="mm",
        align=alignment.value,
        fill=color,
    )

    # cv2.rectangle(opencv_img, (x0, y0), (x1, y1), (128,128,128,128), 5)

    img = normalize(np.array(pil_image))
    img = convert_to_BGRA(img, img.shape[2])

    return img