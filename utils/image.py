from typing import List, BinaryIO

from PIL import Image


def check_image_is_in_formats(image_file: BinaryIO, formats: List[str]):
    image = Image.open(image_file)
    return image.format.lower() in formats
