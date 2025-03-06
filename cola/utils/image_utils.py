from PIL import Image
from io import BytesIO
import base64
from functools import singledispatch
from pathlib import Path


def encode_pil_image_to_base64(image: Image) -> str:
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


def decode_base64_to_pil_image(base64_str: str) -> Image:
    type_id: str = "data:image/jpeg;base64,"
    if base64_str.startswith(type_id):
        base64_str = base64_str[len(type_id):]
    decoded = base64.b64decode(base64_str)
    return Image.open(BytesIO(decoded))


@singledispatch
def save_image(image, path: str | Path):
    pass


@save_image.register(str)
def _(image: str, path: str | Path):
    image = decode_base64_to_pil_image(image)
    image.save(str(path))


@save_image.register(Image.Image)
def _(image: Image.Image, path: str | Path):
    image.save(str(path))


