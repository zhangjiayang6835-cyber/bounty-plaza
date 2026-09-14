"""
Deterministic generator for transforming Minecraft diamond toolset textures into ruby red.
"""

from __future__ import annotations
import base64
import binascii
import math
import struct
import zlib
from pathlib import Path
from typing import NamedTuple

TOOLSET_ITEMS: tuple[str, ...] = ("sword", "pickaxe", "axe", "shovel", "hoe")

CANONICAL_DIAMOND_BASE64: dict[str, str] = {
    "sword": (
        "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAAJFBMVEUAAAAOPzYIJSAz68uk"
        "/fArx6weincVY1VoTh5JNhUoHguJZycazUdMAAAAAXRSTlMAQObYZgAAAExJREFUGNN1jsEN"
        "wDAMAgGndpLuv29/jZFa/+4QwkA/ks5jyPky8cHxwyQAxslZNAaYiux9Zlb4A0XjNcVu1r0h"
        "vYacGwB0Rq0OSC4ehwkBE0lygnsAAAAASUVORK5CYII="
    ),
    "pickaxe": (
        "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQBAMAAADt3eJSAAAAHlBMVEUAAAAz68srx6wnspqJ"
        "ZydoTh5JNhUOPzYoHgsIJSBDqdTeAAAAAXRSTlMAQObYZgAAAEZJREFUeNpjwArKywvANLuQ"
        "sXoqmFU509iDAQKSLCE0W4TRBDAjpWHyBIgAw+QJEAGGSRMgAgwTJ0AEGDihAlAtUEYHms0A"
        "O88PQ5cytswAAAAASUVORK5CYII="
    ),
    "axe": (
        "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQBAMAAADt3eJSAAAAIVBMVEUAAAAz68srx6wnspqJ"
        "ZyceindoTh5JNhUOPzYoHgsIJSBnmo+OAAAAAXRSTlMAQObYZgAAAEBJREFUeNpjQAEcDVBG"
        "owRUQFgDKmBsngBmLFQOngBmcC03tYLIlU2GMNg9uRZABCYwQAQyGSCgBJcAw0wGVAAAdKIM"
        "O6K/xjAAAAAASUVORK5CYII="
    ),
    "shovel": (
        "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAAHlBMVEUAAABJNhUoHgsz68sI"
        "JSAOPzaJZycrx6wnsppoTh6NJ1OoAAAAAXRSTlMAQObYZgAAADhJREFUGFeVyTkCACAMAkFy"
        "qv//sG3Ayu0GgJ+qkh2x51KxdiR7zQGmbleDfBwzazH/9vxiwHWgLn4QANVOSXqPAAAAAElF"
        "TkSuQmCC"
    ),
    "hoe": (
        "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQBAMAAADt3eJSAAAAHlBMVEUAAAAz68srx6wnspqJ"
        "ZydoTh5JNhUOPzYoHgsIJSBDqdTeAAAAAXRSTlMAQObYZgAAADFJREFUeNpjQAbs5VBGoVIB"
        "hME5WT0VyjL2YICAJEsIzRYxAcJIaYAJMJAqwNDBgAoA50AJ6TlXpBwAAAAASUVORK5CYII="
    ),
}

PNG_MAGIC_SIGNATURE: bytes = b"\x89PNG\r\n\x1a\n"


class ColorHsv(NamedTuple):
    """HSV color tuple representation."""

    hue: float
    saturation: float
    value: float


class ColorRgba(NamedTuple):
    """RGBA pixel representation with 8-bit channels."""

    red: int
    green: int
    blue: int
    alpha: int


def calculate_crc32(chunk_type: bytes, chunk_payload: bytes) -> int:
    """
    Computes standard CRC32 checksum for a PNG chunk.

    :param chunk_type: 4-byte ASCII chunk tag
    :param chunk_payload: Binary data payload
    :return: Unsigned 32-bit CRC checksum
    """
    combined_data = chunk_type + chunk_payload
    return binascii.crc32(combined_data) & 0xFFFFFFFF


def create_png_chunk(chunk_type: bytes, chunk_payload: bytes) -> bytes:
    """
    Constructs a well-formed PNG binary chunk including length, type, data, and CRC.

    :param chunk_type: 4-byte ASCII chunk type
    :param chunk_payload: Raw payload bytes
    :return: Formatted PNG chunk bytes
    """
    length_prefix = struct.pack(">I", len(chunk_payload))
    crc_bytes = struct.pack(">I", calculate_crc32(chunk_type, chunk_payload))
    return length_prefix + chunk_type + chunk_payload + crc_bytes


def paeth_predictor(left: int, above: int, upper_left: int) -> int:
    """
    Computes Paeth distance predictor for PNG reverse scanline filtering.

    :param left: Left neighbor byte
    :param above: Above neighbor byte
    :param upper_left: Diagonal upper-left neighbor byte
    :return: Selected predictor byte
    """
    base = left + above - upper_left
    d_left = abs(base - left)
    d_above = abs(base - above)
    d_diag = abs(base - upper_left)

    if d_left <= d_above and d_left <= d_diag:
        return left
    if d_above <= d_diag:
        return above
    return upper_left


def rgb_to_hsv(red: int, green: int, blue: int) -> ColorHsv:
    """
    Converts 8-bit RGB color channels into normalized HSV color space.

    :param red: Red channel in [0, 255]
    :param green: Green channel in [0, 255]
    :param blue: Blue channel in [0, 255]
    :return: ColorHsv instance
    """
    norm_r = red / 255.0
    norm_g = green / 255.0
    norm_b = blue / 255.0

    max_v = max(norm_r, norm_g, norm_b)
    min_v = min(norm_r, norm_g, norm_b)
    delta = max_v - min_v

    hue = 0.0
    saturation = 0.0 if max_v == 0.0 else delta / max_v

    if delta != 0.0:
        if max_v == norm_r:
            offset = 6.0 if norm_g < norm_b else 0.0
            hue = ((norm_g - norm_b) / delta) + offset
        elif max_v == norm_g:
            hue = ((norm_b - norm_r) / delta) + 2.0
        else:
            hue = ((norm_r - norm_g) / delta) + 4.0
        hue *= 60.0

    return ColorHsv(hue=hue, saturation=saturation, value=max_v)


def _sector_rgb(
    sector: int, val: float, p_val: float, q_val: float, t_val: float
) -> tuple[float, float, float]:
    """
    Dispatches RGB triplet according to HSV hue sector.

    :param sector: Hexagonal hue sector index [0..5]
    :param val: Maximum brightness
    :param p_val: Minimum brightness
    :param q_val: Descending slope
    :param t_val: Ascending slope
    :return: Tuple of floating RGB channels
    """
    mapping = {
        0: (val, t_val, p_val),
        1: (q_val, val, p_val),
        2: (p_val, val, t_val),
        3: (p_val, q_val, val),
        4: (t_val, p_val, val),
        5: (val, p_val, q_val),
    }
    return mapping.get(sector, (val, p_val, q_val))


def hsv_to_rgb(hue: float, saturation: float, value: float) -> tuple[int, int, int]:
    """
    Converts normalized HSV parameters back to clamped 8-bit RGB components.

    :param hue: Hue angle in [0.0, 360.0)
    :param saturation: Saturation in [0.0, 1.0]
    :param value: Value/lightness in [0.0, 1.0]
    :return: Tuple of red, green, blue integers in [0, 255]
    """
    norm_h = ((hue % 360.0) + 360.0) % 360.0
    sector = int(norm_h // 60.0) % 6
    frac = (norm_h / 60.0) - math.floor(norm_h / 60.0)

    val_p = value * (1.0 - saturation)
    val_q = value * (1.0 - (frac * saturation))
    val_t = value * (1.0 - ((1.0 - frac) * saturation))

    cr, cg, cb = _sector_rgb(sector, value, val_p, val_q, val_t)
    return (
        min(255, max(0, round(cr * 255.0))),
        min(255, max(0, round(cg * 255.0))),
        min(255, max(0, round(cb * 255.0))),
    )


def is_diamond_color(hue: float, saturation: float, value: float) -> bool:
    """
    Determines if an HSV color belongs to vanilla diamond tool palette.

    :param hue: Hue degree angle
    :param saturation: Saturation fraction
    :param value: Brightness fraction
    :return: True if color matches diamond gem hues
    """
    return (150.0 <= hue <= 230.0) and (saturation >= 0.15) and (value >= 0.05)


def shift_pixel_to_ruby(pixel: ColorRgba, target_hue: float = 352.0) -> ColorRgba:
    """
    Transforms an individual diamond pixel to authentic ruby red while preserving alpha.

    :param pixel: ColorRgba source pixel
    :param target_hue: Base target hue for ruby palette
    :return: Transformed ColorRgba pixel
    """
    if pixel.alpha == 0:
        return ColorRgba(0, 0, 0, 0)

    hsv = rgb_to_hsv(pixel.red, pixel.green, pixel.blue)
    if not is_diamond_color(hsv.hue, hsv.saturation, hsv.value):
        return ColorRgba(pixel.red, pixel.green, pixel.blue, pixel.alpha)

    temperature_shift = (hsv.value - 0.5) * 6.0
    computed_hue = (target_hue + temperature_shift + 360.0) % 360.0

    nr, ng, nb = hsv_to_rgb(computed_hue, hsv.saturation, hsv.value)
    return ColorRgba(nr, ng, nb, pixel.alpha)


class _PngHeader(NamedTuple):
    """Internal PNG header container."""

    width: int
    height: int
    bit_depth: int
    color_type: int
    palette: list[tuple[int, int, int]]
    transparency: list[int]
    idat_bytes: bytes


def _parse_png_streams(png_bytes: bytes) -> _PngHeader:
    """
    Parses PNG chunks into header parameters, palette, and concatenated IDAT buffer.

    :param png_bytes: Raw PNG bytes
    :return: Parsed _PngHeader tuple
    """
    if not png_bytes.startswith(PNG_MAGIC_SIGNATURE):
        raise ValueError("Invalid PNG magic signature.")

    offset = 8
    width = height = bit_depth = color_type = 0
    palette: list[tuple[int, int, int]] = []
    transparency: list[int] = []
    idat_slices: list[bytes] = []

    while offset < len(png_bytes):
        chunk_len = struct.unpack(">I", png_bytes[offset : offset + 4])[0]
        ctype = png_bytes[offset + 4 : offset + 8]
        cdata = png_bytes[offset + 8 : offset + 8 + chunk_len]
        offset += 12 + chunk_len

        if ctype == b"IHDR":
            width, height = struct.unpack(">II", cdata[0:8])
            bit_depth, color_type = cdata[8], cdata[9]
        elif ctype == b"PLTE":
            for p_idx in range(0, len(cdata), 3):
                palette.append((cdata[p_idx], cdata[p_idx + 1], cdata[p_idx + 2]))
        elif ctype == b"tRNS":
            transparency.extend(cdata)
        elif ctype == b"IDAT":
            idat_slices.append(cdata)
        elif ctype == b"IEND":
            break

    return _PngHeader(
        width=width,
        height=height,
        bit_depth=bit_depth,
        color_type=color_type,
        palette=palette,
        transparency=transparency,
        idat_bytes=b"".join(idat_slices),
    )


def _reconstruct_scanline(
    filter_type: int, line: bytearray, prev: bytearray, step: int
) -> bytearray:
    """
    Applies inverse scanline filter to recover raw uncompressed bytes.

    :param filter_type: PNG filter method [0..4]
    :param line: Current filtered line bytes
    :param prev: Previous scanline bytes
    :param step: Bytes per pixel channel step
    :return: Unfiltered scanline bytearray
    """
    unfiltered = bytearray(len(line))
    for c_idx, raw_byte in enumerate(line):
        left_byte = unfiltered[c_idx - step] if c_idx >= step else 0
        above_byte = prev[c_idx]
        diag_byte = prev[c_idx - step] if c_idx >= step else 0

        recon = raw_byte
        if filter_type == 1:
            recon = (raw_byte + left_byte) & 0xFF
        elif filter_type == 2:
            recon = (raw_byte + above_byte) & 0xFF
        elif filter_type == 3:
            recon = (raw_byte + ((left_byte + above_byte) // 2)) & 0xFF
        elif filter_type == 4:
            recon = (raw_byte + paeth_predictor(left_byte, above_byte, diag_byte)) & 0xFF
        unfiltered[c_idx] = recon
    return unfiltered


def _decode_palette_pixel(
    raw_row: bytearray, x_idx: int, hdr: _PngHeader
) -> ColorRgba:
    """
    Decodes an individual indexed color pixel from palette table.

    :param raw_row: Unfiltered row buffer
    :param x_idx: X coordinate
    :param hdr: Parsed image header
    :return: Resolved ColorRgba pixel
    """
    if hdr.bit_depth == 4:
        byte_pos = x_idx // 2
        p_code = (
            (raw_row[byte_pos] >> 4) & 0x0F
            if x_idx % 2 == 0
            else raw_row[byte_pos] & 0x0F
        )
    else:
        p_code = raw_row[x_idx]

    entry = hdr.palette[p_code] if p_code < len(hdr.palette) else (0, 0, 0)
    alpha = hdr.transparency[p_code] if p_code < len(hdr.transparency) else 255
    return ColorRgba(entry[0], entry[1], entry[2], alpha)


def _decode_row_pixels(raw_row: bytearray, hdr: _PngHeader) -> list[ColorRgba]:
    """
    Converts an unfiltered scanline into ColorRgba pixels based on color type.

    :param raw_row: Unfiltered bytearray
    :param hdr: PNG metadata header
    :return: List of ColorRgba pixels for the row
    """
    pixels: list[ColorRgba] = []
    if hdr.color_type == 6:
        for x_idx in range(hdr.width):
            px_start = x_idx * 4
            pixels.append(
                ColorRgba(
                    raw_row[px_start],
                    raw_row[px_start + 1],
                    raw_row[px_start + 2],
                    raw_row[px_start + 3],
                )
            )
    elif hdr.color_type == 2:
        for x_idx in range(hdr.width):
            px_start = x_idx * 3
            pixels.append(
                ColorRgba(
                    raw_row[px_start],
                    raw_row[px_start + 1],
                    raw_row[px_start + 2],
                    255,
                )
            )
    elif hdr.color_type == 3:
        for x_idx in range(hdr.width):
            pixels.append(_decode_palette_pixel(raw_row, x_idx, hdr))
    return pixels


def decode_png(png_bytes: bytes) -> tuple[int, int, list[list[ColorRgba]]]:
    """
    Parses a PNG binary stream into dimensions and a 2D matrix of ColorRgba pixels.

    :param png_bytes: Raw PNG file data
    :return: Tuple of (width, height, pixel_rows)
    """
    hdr = _parse_png_streams(png_bytes)
    decomp = zlib.decompress(hdr.idat_bytes)

    bpp = 4 if hdr.color_type == 6 else (3 if hdr.color_type == 2 else 1)
    is_4bit_palette = (hdr.color_type == 3 and hdr.bit_depth == 4)
    step = 1 if is_4bit_palette else bpp
    data_width = math.ceil(hdr.width / 2.0) if is_4bit_palette else hdr.width * bpp
    stride = 1 + data_width

    rows: list[list[ColorRgba]] = []
    prev_row = bytearray(stride - 1)
    cursor = 0

    for _ in range(hdr.height):
        ftype = decomp[cursor]
        cursor += 1
        fline = bytearray(decomp[cursor : cursor + stride - 1])
        cursor += stride - 1

        unfiltered = _reconstruct_scanline(ftype, fline, prev_row, step)
        prev_row = unfiltered
        rows.append(_decode_row_pixels(unfiltered, hdr))

    return hdr.width, hdr.height, rows


def encode_png(width: int, height: int, pixel_matrix: list[list[ColorRgba]]) -> bytes:
    """
    Serializes a 2D matrix of ColorRgba pixels into standard 32-bit RGBA PNG binary bytes.

    :param width: Image width
    :param height: Image height
    :param pixel_matrix: 2D list of ColorRgba pixels
    :return: Full PNG byte payload
    """
    ihdr_payload = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr_chunk = create_png_chunk(b"IHDR", ihdr_payload)

    row_bytes_len = 1 + (width * 4)
    raw_buffer = bytearray(row_bytes_len * height)

    for y_idx in range(height):
        row_start = y_idx * row_bytes_len
        raw_buffer[row_start] = 0
        for x_idx in range(width):
            pixel = pixel_matrix[y_idx][x_idx]
            px_start = row_start + 1 + (x_idx * 4)
            raw_buffer[px_start] = pixel.red
            raw_buffer[px_start + 1] = pixel.green
            raw_buffer[px_start + 2] = pixel.blue
            raw_buffer[px_start + 3] = pixel.alpha

    compressed_idat = zlib.compress(bytes(raw_buffer), level=9)
    idat_chunk = create_png_chunk(b"IDAT", compressed_idat)
    iend_chunk = create_png_chunk(b"IEND", b"")

    return PNG_MAGIC_SIGNATURE + ihdr_chunk + idat_chunk + iend_chunk


def generate_ruby_texture(input_bytes: bytes, target_hue: float = 352.0) -> bytes:
    """
    Converts a single diamond texture PNG buffer into its ruby counterpart.

    :param input_bytes: Raw PNG bytes
    :param target_hue: Base hue for ruby red shift
    :return: Transformed PNG bytes
    """
    width, height, pixel_grid = decode_png(input_bytes)
    transformed_rows: list[list[ColorRgba]] = []

    for row in pixel_grid:
        transformed_row = [shift_pixel_to_ruby(px, target_hue=target_hue) for px in row]
        transformed_rows.append(transformed_row)

    return encode_png(width, height, transformed_rows)


class RubyTextureGenerator:
    """Orchestrator for batch generating ruby toolset textures."""

    def __init__(self, target_hue: float = 352.0) -> None:
        """
        Initializes generator with target hue.

        :param target_hue: Target hue angle
        """
        self.target_hue = target_hue

    @staticmethod
    def get_canonical_bytes(item_name: str) -> bytes:
        """
        Retrieves base64-decoded canonical binary texture for a diamond item.

        :param item_name: Name of tool item
        :return: Decoded PNG binary bytes
        """
        if item_name not in CANONICAL_DIAMOND_BASE64:
            raise KeyError(f"Unknown item identifier: {item_name}")
        return base64.b64decode(CANONICAL_DIAMOND_BASE64[item_name])

    def generate_single_item(
        self,
        item_name: str,
        input_dir: Path | None = None,
        output_dir: Path | None = None,
    ) -> Path:
        """
        Transforms a single tool asset and writes the ruby output PNG.

        :param item_name: Item name
        :param input_dir: Optional source directory
        :param output_dir: Optional output directory
        :return: Path to generated PNG
        """
        resolved_out = output_dir if output_dir is not None else Path("textures/items")
        resolved_out.mkdir(parents=True, exist_ok=True)

        source_file = input_dir / f"diamond_{item_name}.png" if input_dir is not None else None
        if source_file and source_file.exists():
            source_data = source_file.read_bytes()
        else:
            source_data = self.get_canonical_bytes(item_name)

        ruby_bytes = generate_ruby_texture(source_data, target_hue=self.target_hue)
        destination_path = resolved_out / f"ruby_{item_name}.png"
        destination_path.write_bytes(ruby_bytes)
        return destination_path

    def generate_toolset(
        self,
        input_dir: Path | None = None,
        output_dir: Path | None = None,
        items: tuple[str, ...] = TOOLSET_ITEMS,
    ) -> list[Path]:
        """
        Generates full ruby toolset texture suite.

        :param input_dir: Optional directory to search for source diamond PNGs
        :param output_dir: Destination directory for generated ruby PNGs
        :param items: Sequence of item identifiers
        :return: List of generated output file paths
        """
        generated_paths: list[Path] = []
        for item_name in items:
            path_result = self.generate_single_item(
                item_name, input_dir=input_dir, output_dir=output_dir
            )
            generated_paths.append(path_result)
        return generated_paths
