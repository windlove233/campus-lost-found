from io import BytesIO
import unittest

from PIL import ExifTags, Image, TiffImagePlugin

from photo_metadata import PhotoMetadata, read_photo_metadata


class PhotoMetadataTests(unittest.TestCase):
    def read_jpeg(self, exif: Image.Exif) -> PhotoMetadata:
        with BytesIO() as upload, Image.new("RGB", (8, 8)) as sample:
            sample.save(upload, format="JPEG", exif=exif)
            upload.seek(0)
            with Image.open(upload) as image:
                return read_photo_metadata(image)

    def test_reads_original_time_offset_and_signed_coordinates(self):
        exif = Image.Exif()
        exif[ExifTags.IFD.Exif] = {
            ExifTags.Base.DateTimeOriginal: "2026:11:23 14:30:00",
            ExifTags.Base.OffsetTimeOriginal: "+08:00",
        }
        ratio = TiffImagePlugin.IFDRational
        exif[ExifTags.IFD.GPSInfo] = {
            ExifTags.GPS.GPSLatitudeRef: "S",
            ExifTags.GPS.GPSLatitude: (ratio(30), ratio(18), ratio(0)),
            ExifTags.GPS.GPSLongitudeRef: "W",
            ExifTags.GPS.GPSLongitude: (ratio(120), ratio(9), ratio(0)),
        }
        result = self.read_jpeg(exif)
        self.assertEqual(result, PhotoMetadata("2026-11-23T14:30:00+08:00", -30.3, -120.15))

    def test_edit_timestamp_does_not_fill_missing_capture_time(self):
        exif = Image.Exif()
        exif[ExifTags.Base.DateTime] = "2026:11:23 14:30:00"
        self.assertEqual(self.read_jpeg(exif), PhotoMetadata())

    def test_incomplete_gps_and_invalid_timezone(self):
        exif = Image.Exif()
        exif[ExifTags.IFD.Exif] = {
            ExifTags.Base.DateTimeOriginal: "2026:11:23 14:30:00",
            ExifTags.Base.OffsetTimeOriginal: "+99:00",
        }
        ratio = TiffImagePlugin.IFDRational
        exif[ExifTags.IFD.GPSInfo] = {
            ExifTags.GPS.GPSLatitudeRef: "N",
            ExifTags.GPS.GPSLatitude: (ratio(30), ratio(18), ratio(0)),
        }
        self.assertEqual(self.read_jpeg(exif), PhotoMetadata("2026-11-23T14:30:00"))

    def test_missing_metadata(self):
        with Image.new("RGB", (8, 8)) as image:
            self.assertEqual(read_photo_metadata(image), PhotoMetadata())
