from __future__ import annotations

from enum import Enum

import cv2
import numpy as np

from nodes.groups import if_enum_group
from nodes.properties.inputs import EnumInput, ImageInput, SliderInput
from nodes.properties.outputs import ImageOutput

from .. import miscellaneous_group


class MorphOperation(Enum):
    EROSION = "erosion"
    DILATION = "dilation"
    OPENING = "opening"
    CLOSING = "closing"
    GRADIENT = "gradient"


MORPH_OPERATION_LABELS = {
    MorphOperation.EROSION: "Erosion",
    MorphOperation.DILATION: "Dilation",
    MorphOperation.OPENING: "Erosion, Dilation",
    MorphOperation.CLOSING: "Dilation, Erosion",
    MorphOperation.GRADIENT: "Dilation - Erosion",
}


class MorphShape(Enum):
    RECTANGLE = cv2.MORPH_RECT
    ELLIPSE = cv2.MORPH_ELLIPSE
    CROSS = cv2.MORPH_CROSS


@miscellaneous_group.register(
    schema_id="chainner:image:morphology",
    name="Morphology",
    description="Morphological transformations",
    icon="MdOutlineAutoFixHigh",
    inputs=[
        ImageInput(),
        EnumInput(
            MorphOperation,
            label="Operation",
            default=MorphOperation.EROSION,
            option_labels=MORPH_OPERATION_LABELS,
        ),
        EnumInput(
            MorphShape,
            label="Shape",
            option_labels={
                MorphShape.RECTANGLE: "Square",
                MorphShape.ELLIPSE: "Circle",
                MorphShape.CROSS: "Cross",
            },
        ),
        SliderInput(
            "Radius",
            minimum=0,
            maximum=1000,
            default=1,
            controls_step=1,
            scale="log",
        ),
        SliderInput(
            "Iterations",
            minimum=0,
            maximum=1000,
            default=1,
            controls_step=1,
            scale="log",
        ),
    ],
    outputs=[ImageOutput(image_type="Input0")],
)
def morphology_node(
    img: np.ndarray,
    morph_operation: MorphOperation,
    morph_shape: MorphShape,
    radius: int,
    iterations: int,
) -> np.ndarray:
    if radius == 0 or iterations == 0:
        return img

    size = 2 * radius + 1
    kernel = cv2.getStructuringElement(morph_shape.value, (size, size))

    transformed_image = img
    if morph_operation == MorphOperation.EROSION:
        transformed_image = cv2.erode(img, kernel, iterations=iterations)
    elif morph_operation == MorphOperation.DILATION:
        transformed_image = cv2.dilate(img, kernel, iterations=iterations)
    elif morph_operation == MorphOperation.OPENING:
        transformed_image = cv2.morphologyEx(
            img, cv2.MORPH_OPEN, kernel, iterations=iterations
        )
    elif morph_operation == MorphOperation.CLOSING:
        transformed_image = cv2.morphologyEx(
            img, cv2.MORPH_CLOSE, kernel, iterations=iterations
        )
    elif morph_operation == MorphOperation.GRADIENT:
        transformed_image = cv2.morphologyEx(
            img, cv2.MORPH_GRADIENT, kernel, iterations=iterations
        )

    return transformed_image
