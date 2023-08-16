from __future__ import annotations

from enum import Enum

import numpy as np

from nodes.groups import if_enum_group
from nodes.impl.blend import BlendMode, blend_images
from nodes.impl.image_utils import as_2d_grayscale
from nodes.impl.pil_utils import convert_to_BGRA
from nodes.properties.inputs import EnumInput, ImageInput, NumberInput, SliderInput
from nodes.properties.outputs import ImageOutput
from nodes.utils.utils import get_h_w_c

from .. import compositing_group


class OverlayPosition(Enum):
    TOP_LEFT = "top_left"
    TOP_CENTERED = "top_centered"
    TOP_RIGHT = "top_right"
    CENTERED_LEFT = "centered_left"
    CENTERED = "centered"
    CENTERED_RIGHT = "centered_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTERED = "bottom_centered"
    BOTTOM_RIGHT = "bottom_right"
    PERCENT_OFFSET = "percent_offset"
    PIXEL_OFFSET = "pixel_offset"


OVERLAY_POSITION_LABELS = {
    OverlayPosition.TOP_LEFT: "Top left",
    OverlayPosition.TOP_CENTERED: "Top centered",
    OverlayPosition.TOP_RIGHT: "Top right",
    OverlayPosition.CENTERED_LEFT: "Centered left",
    OverlayPosition.CENTERED: "Centered",
    OverlayPosition.CENTERED_RIGHT: "Centered right",
    OverlayPosition.BOTTOM_LEFT: "Bottom left",
    OverlayPosition.BOTTOM_CENTERED: "Bottom centered",
    OverlayPosition.BOTTOM_RIGHT: "Bottom right",
    OverlayPosition.PERCENT_OFFSET: "Offset (%)",
    OverlayPosition.PIXEL_OFFSET: "Offset (pixels)",
}

OVERLAY_X0_Y0_FACTORS = {
    OverlayPosition.TOP_LEFT: np.array([0, 0]),
    OverlayPosition.TOP_CENTERED: np.array([0.5, 0]),
    OverlayPosition.TOP_RIGHT: np.array([1, 0]),
    OverlayPosition.CENTERED_LEFT: np.array([0, 0.5]),
    OverlayPosition.CENTERED: np.array([0.5, 0.5]),
    OverlayPosition.CENTERED_RIGHT: np.array([1, 0.5]),
    OverlayPosition.BOTTOM_LEFT: np.array([0, 1]),
    OverlayPosition.BOTTOM_CENTERED: np.array([0.5, 1]),
    OverlayPosition.BOTTOM_RIGHT: np.array([1, 1]),
    OverlayPosition.PERCENT_OFFSET: np.array([1, 1]),
    OverlayPosition.PIXEL_OFFSET: np.array([0, 0]),
}


@compositing_group.register(
    schema_id="chainner:image:overlay",
    name="Overlay Images",
    description="""Overlay images with blend adjustment.""",
    icon="BsLayersHalf",
    inputs=[
        ImageInput("Base", channels=[1, 3, 4]),
        ImageInput("Overlay", channels=[1, 3, 4]),
        SliderInput(
            "Opacity",
            maximum=100,
            default=50,
            precision=1,
            controls_step=1,
            unit="%",
        ),
        EnumInput(
            OverlayPosition,
            label="Position",
            option_labels=OVERLAY_POSITION_LABELS,
            default=OverlayPosition.CENTERED,
        ),
        if_enum_group(3, (OverlayPosition.PERCENT_OFFSET))(
            SliderInput(
                "X offset",
                precision=0,
                controls_step=1,
                minimum=-100,
                maximum=100,
                default=0,
                unit="%",
            ),
            SliderInput(
                "Y offset",
                precision=0,
                controls_step=1,
                minimum=-100,
                maximum=100,
                default=0,
                unit="%",
            ),
        ),
        if_enum_group(3, (OverlayPosition.PIXEL_OFFSET))(
            NumberInput("X offset", controls_step=1, minimum=None, unit="px").with_docs(
                """X offset range: (-1 * (base_width + overlay_width) / 2  + 1) .
                        . ((base_width + overlay_width) / 2) + 1)"""
            ),
            NumberInput("Y offset", controls_step=1, minimum=None, unit="px").with_docs(
                """Y offset range: (-1 * (base_height + overlay_height) / 2  + 1) .
                        . ((base_height + overlay_height) / 2) + 1)"""
            ),
        ),
    ],
    outputs=[
        ImageOutput(
            image_type="""
                def isOffsetValid(offset: int, base_dim: int, overlay_dim: int): bool {
                    let max_dim = round((base_dim + overlay_dim) / 2);
                    bool::and(offset >= 1 - max_dim, offset <= max_dim - 1)
                }

                let valid: bool = match Input3 {
                    OverlayPosition::PixelOffset => bool::and(
                        isOffsetValid(Input6, Input0.width, Input1.width),
                        isOffsetValid(Input7, Input0.height, Input1.height)),
                    _ => true,
                };

                if valid {
                    Image {
                        width: Input0.width,
                        height: Input0.height,
                        channels: max(Input0.channels, Input1.channels)
                    }
                } else {
                    never
                }

            """,
            assume_normalized=True,
        ).with_never_reason("At least one layer must be an image"),
    ],
)
def overlay_images_node(
    base: np.ndarray,
    overlay: np.ndarray,
    opacity: float,
    overlay_position: OverlayPosition,
    x_percent: int,
    y_percent: int,
    x_px: int,
    y_px: int,
) -> np.ndarray:
    if opacity == 0:
        return base

    base_height, base_width, base_channel_count = get_h_w_c(base)
    overlay_height, overlay_width, overlay_channel_count = get_h_w_c(overlay)

    # Calculate coordinates of the overlay layer
    #   origin: top-let point of the base layer
    #   (x0, y0): top-left point of the overlay layer
    #   (x1, y1): bottom-right point of the overlay layer
    if overlay_position == OverlayPosition.PERCENT_OFFSET:
        x0, y0 = [
            int((50 + (x_percent / 2)) * base_width / 100 - overlay_width / 2),
            int((50 + (y_percent / 2)) * base_height / 100 - overlay_height / 2),
        ]
    elif overlay_position == OverlayPosition.PIXEL_OFFSET:
        x0, y0 = [
            round(x_px + (base_width - overlay_width) / 2),
            round(y_px + (base_height - overlay_height) / 2),
        ]

        max_dim = int((base_width + overlay_width) / 2)
        print(f"max X: {max_dim}, p_x= {x_px}")
        assert (
            -1 * max_dim < x_px < max_dim
        ), f"""X offset must be in {1 - max_dim}..{max_dim - 1} range"""

        max_dim = int((base_height + overlay_height) / 2)
        print(f"max Y: {max_dim}, p_y= {y_px}")
        assert (
            -1 * max_dim < y_px < max_dim
        ), f"""Y offset must be in {1 - max_dim}..{max_dim - 1} range"""

    else:
        x0, y0 = np.array(
            [base_width - overlay_width, base_height - overlay_height]
            * OVERLAY_X0_Y0_FACTORS[overlay_position]
        ).astype("int")
    x1, y1 = x0 + overlay_width, y0 + overlay_height

    # Coordinates of intersection area
    i_x0, i_x1 = max(0, x0), min(x1, base_width)
    i_y0, i_y1 = max(0, y0), min(y1, base_height)
    if not (0 <= i_x0 < i_x1 and 0 <= i_y0 < i_y1):
        return base

    ov_x0 = max(0, -1 * x0)
    ov_x1 = ov_x0 + i_x1 - i_x0
    ov_y0 = max(0, -1 * y0)
    ov_y1 = ov_y0 + i_y1 - i_y0

    # Crop overlay image
    if ov_y1 - ov_y0 > 0 or ov_x1 - ov_x0 > 0:
        overlay = overlay[
            ov_y0:ov_y1,
            ov_x0:ov_x1,
        ]

    # Copy base image
    base = base.copy()

    # Apply opacity
    if not (opacity == 100 and overlay_channel_count == 4):
        overlay = convert_to_BGRA(overlay, overlay_channel_count)
        opacity /= 100
        overlay[:, :, 3] *= opacity

    # Overlay areas
    blended_img = blend_images(
        overlay,
        base[i_y0:i_y1, i_x0:i_x1],
        BlendMode.NORMAL,
    )

    # Blended area and ouput shall have the same channel count
    output = base
    blended_channel_count = blended_img.shape[2]
    if base_channel_count < blended_channel_count:
        if blended_channel_count == 4:
            output = convert_to_BGRA(output, base_channel_count)
        else:
            output = as_2d_grayscale(output)
            output = np.dstack((output, output, output))

    # Overwrite base area
    output[i_y0:i_y1, i_x0:i_x1] = blended_img

    return output
