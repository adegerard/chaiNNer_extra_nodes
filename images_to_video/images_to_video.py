from __future__ import annotations

from enum import Enum

import ffmpeg
import os
import re
from tempfile import mkdtemp
import time
from sanic.log import logger
from nodes.groups import if_enum_group
from nodes.properties.inputs import (
    EnumInput,
    DirectoryInput,
    SliderInput,
    TextInput,
    VideoPresetDropdown,
    VideoContainerDropdown,
    VideoCodecDropdown,
)
from .. import io_group

ffmpeg_path = os.environ.get("STATIC_FFMPEG_PATH", "ffmpeg")
ffprobe_path = os.environ.get("STATIC_FFPROBE_PATH", "ffprobe")


class ImageExtension(Enum):
    BMP = ".bmp"
    JPEG = ".jpeg"
    JPG = ".jpg"
    PNG = ".png"

IMAGE_EXTENSION_LABELS = {
    ImageExtension.BMP: "BMP",
    ImageExtension.JPEG: "JPEG",
    ImageExtension.JPG: "JPG",
    ImageExtension.PNG: "PNG",
}

def get_extension(filepath: str) -> str:
    return os.path.splitext(filepath)[1].lower()


class FrameRate(Enum):
    FRAME_RATE_23_976_FPS = "23.976"
    FRAME_RATE_24_FPS = "24"
    FRAME_RATE_25_FPS = "25"
    FRAME_RATE_29_97_FPS = "29.97"
    FRAME_RATE_30_FPS = "30"
    FRAME_RATE_60_FPS = "60"
    FRAME_RATE_CUSTOM = "custom"

FRAME_RATE_LABELS = {
    FrameRate.FRAME_RATE_23_976_FPS: "23.976",
    FrameRate.FRAME_RATE_24_FPS: "24",
    FrameRate.FRAME_RATE_25_FPS: "25",
    FrameRate.FRAME_RATE_29_97_FPS: "29.97",
    FrameRate.FRAME_RATE_30_FPS: "30",
    FrameRate.FRAME_RATE_60_FPS: "60",
    FrameRate.FRAME_RATE_CUSTOM: "custom",
}


@io_group.register(
    schema_id="chainner:image:images_to_video",
    name="Images to Video",
    description="Combine all images of a directory into a video.",
    icon="BsFillImageFill",
    inputs=[
        DirectoryInput(
            "Input Images Directory",
            must_exist=True,
            has_handle=True
        ),
        EnumInput(
            ImageExtension,
            label="extension",
            option_labels=IMAGE_EXTENSION_LABELS,
            default=ImageExtension.PNG,
        ),
        DirectoryInput(
            "Output Video Directory",
            must_exist=False,
            has_handle=True
        ),
        TextInput("Output Video Name"),
        EnumInput(
            FrameRate,
            label="Frame rate",
            option_labels=FRAME_RATE_LABELS,
            default=FrameRate.FRAME_RATE_25_FPS,
        ),
        if_enum_group(4, (FrameRate.FRAME_RATE_CUSTOM))(
            SliderInput(
                "Frame rate",
                precision=3,
                controls_step=1,
                minimum=5,
                maximum=240,
                default=25,
                unit="fps",
            ),
        ),
        VideoContainerDropdown().with_docs("Only the video stream is embedded in this file"),
        VideoCodecDropdown().with_docs("Video codec"),
        VideoPresetDropdown().with_docs(
            "For more information on presets, see [here](https://trac.ffmpeg.org/wiki/Encode/H.264#Preset)."
        ),
        SliderInput(
            "Quality (CRF)",
            precision=0,
            controls_step=1,
            slider_step=1,
            minimum=0,
            maximum=51,
            default=23,
            ends=("Best", "Worst"),
        ).with_docs(
            "For more information on CRF, see [here](https://trac.ffmpeg.org/wiki/Encode/H.264#crf)."
        ),
    ],
    outputs=[],
    side_effects=True,
)


def images_to_video_node(
    image_directory: str,
    image_extension: ImageExtension,
    video_directory: str,
    video_name: str,
    framerate: FrameRate,
    custom_frame_rate: float,
    video_container: str,
    video_codec: str,
    video_preset: str,
    crf: int,
) -> None:

    # List files
    content = list([os.path.join(image_directory, i) for i in os.listdir(image_directory)])
    filepaths = list()
    for fp in content:
        if (os.path.isfile(fp)
            and get_extension(fp) == image_extension.value):
            filepaths.append(fp)

    assert (
        len(filepaths) >= 5
    ), "Not enough images to generate a video"

    # Create a concatenation file used by FFmpeg
    concatenation_filepath = os.path.join(
        mkdtemp(prefix="chaiNNer-"),  f"{time.time()}.txt")
    concatenation_file = open(concatenation_filepath, "w")
    for p in sorted(filepaths):
        concatenation_file.write(f"file \'{p}\' \n")
    concatenation_file.close()

    # Output video file
    video_filepath = os.path.join(video_directory, f"{video_name}.{video_container}")

    # Generate and execute FFmpeg command
    process = (
        ffmpeg
        .input(
            concatenation_filepath,
            f='concat',
            r=framerate.value if framerate != FrameRate.FRAME_RATE_CUSTOM else custom_frame_rate,
            safe=0,
        )
        .output(
            video_filepath,
            pix_fmt='yuv420p',
            preset=video_preset if video_preset != "none" else None,
            vcodec=f"{video_codec}",
            crf=crf,
        )
        .overwrite_output()
        .run_async(pipe_stdout=True, pipe_stderr=True, cmd=ffmpeg_path)
        # .run_async(pipe_stdout=False, pipe_stderr=False, cmd=ffmpeg_path)
    )
    _, stderr = process.communicate()

    # Verify that nothing went wrong
    erroneous_file = ''
    if len(stderr) > 0:
        stderr = stderr.decode('utf-8').split('\n')

        # Detect error
        for line in reversed(stderr):
            if not line.startswith('['):
                continue
            if (match := re.search(re.compile(r"Impossible to open \'(.*)\'"), line)):
                # https://stackoverflow.com/questions/3411771/best-way-to-replace-multiple-characters-in-a-string
                erroneous_file = match.group(1) \
                    .replace('\\n', '') \
                    .replace('\"', '') \
                    .replace('\'', '')

                os.remove(video_filepath)
                break
    assert (
        erroneous_file == ''
    ), f"erroneous file: {erroneous_file}"


