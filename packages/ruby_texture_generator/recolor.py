"""Core image recoloring operations for Ruby toolset generation."""

import io
from typing import Union
from PIL import Image

from packages.ruby_texture_generator.palette import recolor_pixel


def recolor_rgba_buffer(buffer: bytes, width: int, height: int) -> bytes:
    """Recolor raw uncompressed RGBA pixel bytes into authentic Jappa Ruby.

    :param buffer: Raw RGBA pixel bytes of size width * height * 4.
    :param width: Image width in pixels.
    :param height: Image height in pixels.
    :return: Recolored uncompressed RGBA byte sequence.
    """
    total_pixels = width * height
    expected_len = total_pixels * 4
    if len(buffer) != expected_len:
        raise ValueError(
            f"Buffer length {len(buffer)} does not match expected {expected_len}"
        )

    out = bytearray(expected_len)
    for i in range(total_pixels):
        idx = i * 4
        px = buffer[idx:idx + 4]
        recolored = recolor_pixel(px[0], px[1], px[2], px[3])
        out[idx:idx + 4] = bytes(recolored)

    return bytes(out)


def recolor_image(image: Image.Image) -> Image.Image:
    """Recolor a PIL Image object into its Ruby variant.

    :param image: Input PIL Image instance.
    :return: Recolored PIL RGBA Image instance.
    """
    rgba_img = image.convert("RGBA")
    width, height = rgba_img.size
    raw_bytes = rgba_img.tobytes()
    recolored_bytes = recolor_rgba_buffer(raw_bytes, width, height)
    return Image.frombytes("RGBA", (width, height), recolored_bytes)


def recolor_image_bytes(image_bytes: Union[bytes, bytearray]) -> bytes:
    """Recolor encoded image bytes (such as PNG) and output optimized PNG bytes.

    :param image_bytes: Encoded input image bytes.
    :return: Encoded output PNG image bytes.
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        recolored = recolor_image(img)
        output_stream = io.BytesIO()
        recolored.save(output_stream, format="PNG", optimize=True)
        return output_stream.getvalue()
