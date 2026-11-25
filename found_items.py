from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from mysql.connector import DataError, IntegrityError, ProgrammingError
from PIL import Image, ImageOps

from database import insert_found_item
from image_search import encode_image
from photo_metadata import read_photo_metadata

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"


def publish_found_item(image: Image.Image, *, found_on=None, found_area=None):
    metadata = read_photo_metadata(image)
    clean_image = ImageOps.exif_transpose(image).convert("RGB")
    embedding = encode_image(clean_image)

    UPLOAD_DIR.mkdir(exist_ok=True)
    path = UPLOAD_DIR / f"{uuid4().hex}.jpg"

    with path.open("xb") as output:
        try:
            clean_image.save(output, format="JPEG", quality=90)
        except OSError:
            output.close()
            path.unlink(missing_ok=True)
            raise

    try:
        item_id = insert_found_item(
            path.name, asdict(metadata), embedding,
            found_on=found_on, found_area=found_area,
        )
    except (DataError, IntegrityError, ProgrammingError):
        path.unlink(missing_ok=True)
        raise

    return item_id, metadata
