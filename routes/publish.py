from datetime import date

from flask import Blueprint, render_template, request
from mysql.connector import Error
from PIL import Image

from found_items import publish_found_item

publish_bp = Blueprint("publish", __name__)


@publish_bp.route("/publish", methods=["GET", "POST"])
def publish_page():
    if request.method == "GET":
        return render_template("publish.html")

    photo = request.files.get("photo")
    if photo is None or not photo.filename:
        return render_template("publish.html", error="请先选择一张照片。"), 400

    found_area = request.form.get("found_area", "").strip() or None
    raw_date = request.form.get("found_on", "").strip()

    if found_area and len(found_area) > 100:
        return render_template("publish.html", error="拾取地点最多 100 字。"), 400

    try:
        found_on = date.fromisoformat(raw_date) if raw_date else None
    except ValueError:
        return render_template("publish.html", error="请填写有效的拾取日期。"), 400

    try:
        with Image.open(photo.stream, formats=["JPEG", "PNG", "WEBP", "BMP"]) as image:
            item_id, metadata = publish_found_item(
                image, found_on=found_on, found_area=found_area
            )
    except (OSError, Image.DecompressionBombError):
        return render_template("publish.html", error="照片无法读取或保存。"), 400
    except Error:
        return render_template("publish.html", error="数据库写入失败。"), 500

    return render_template("publish.html", item_id=item_id, metadata=metadata)
