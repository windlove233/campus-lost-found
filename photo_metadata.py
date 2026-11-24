import argparse
from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path

from PIL import ExifTags, Image


@dataclass(frozen=True)
class PhotoMetadata:
    captured_at: str | None = None
    latitude: float | None = None
    longitude: float | None = None


def _capture_time(fields: dict) -> str | None:
    original = fields.get(ExifTags.Base.DateTimeOriginal)
    if not isinstance(original, str):
        return None

    timestamp = original.strip().strip("\0")
    date_format = "%Y:%m:%d %H:%M:%S"
    try:
        captured = datetime.strptime(timestamp, date_format)
    except ValueError:
        return None

    offset = fields.get(ExifTags.Base.OffsetTimeOriginal)
    if isinstance(offset, str):
        try:
            captured = datetime.strptime(timestamp + offset.strip().strip("\0"), date_format + "%z")
        except ValueError:
            pass
    return captured.isoformat()


def _coordinate(values, direction, positive: str, negative: str, maximum: int) -> float | None:
    if direction not in (positive, negative):
        return None
    try:
        degrees, minutes, seconds = map(float, values)
    except (ValueError, TypeError, ZeroDivisionError, OverflowError):
        return None
    if not (0 <= degrees <= maximum and 0 <= minutes < 60 and 0 <= seconds < 60):
        return None

    decimal = degrees + minutes / 60 + seconds / 3600
    if decimal > maximum:
        return None
    return -decimal if direction == negative else decimal


def read_photo_metadata(image: Image.Image) -> PhotoMetadata:
    """Read original capture details from the uploaded image's EXIF data."""
    exif = image.getexif()
    captured_at = _capture_time({**exif, **exif.get_ifd(ExifTags.IFD.Exif)})
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    tags = ExifTags.GPS
    latitude = _coordinate(gps.get(tags.GPSLatitude), gps.get(tags.GPSLatitudeRef), "N", "S", 90)
    longitude = _coordinate(gps.get(tags.GPSLongitude), gps.get(tags.GPSLongitudeRef), "E", "W", 180)
    if latitude is None or longitude is None:
        latitude = longitude = None
    return PhotoMetadata(captured_at, latitude, longitude)


def main() -> None:
    parser = argparse.ArgumentParser(description="读取照片的 EXIF 拍摄时间和 GPS。")
    parser.add_argument("photo", type=Path, help="一张照片的文件路径")
    args = parser.parse_args()
    try:
        with Image.open(args.photo) as image:
            metadata = read_photo_metadata(image)
    except (OSError, Image.DecompressionBombError):
        parser.error(f"无法打开照片 {args.photo}")
    print(json.dumps(asdict(metadata), indent=2))


if __name__ == "__main__":
    main()
