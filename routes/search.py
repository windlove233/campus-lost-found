from datetime import date

from flask import Blueprint, abort, render_template, request, send_from_directory

from database import get_found_photo_name, list_found_items
from found_items import UPLOAD_DIR
from image_search import rank_stored_items

search_bp = Blueprint("search", __name__)


@search_bp.get("/")
def search_page():
    query = request.args.get("q", "").strip()
    raw_date = request.args.get("lost_on", "").strip()
    lost_area = request.args.get("lost_area", "").strip()
    form = {"query": query, "lost_on": raw_date, "lost_area": lost_area}

    if len(lost_area) > 100:
        return render_template("search.html", **form, error="丢失地点最多 100 字。"), 400
    try:
        lost_on = date.fromisoformat(raw_date) if raw_date else None
    except ValueError:
        return render_template("search.html", **form, error="请填写有效的丢失日期。"), 400

    results = (
        rank_stored_items(query, list_found_items(), lost_on=lost_on, lost_area=lost_area or None)
        if query else []
    )
    return render_template("search.html", **form, results=results)


@search_bp.get("/found-photos/<int:item_id>")
def found_photo(item_id):
    photo_name = get_found_photo_name(item_id)
    if photo_name is None:
        abort(404)
    return send_from_directory(UPLOAD_DIR, photo_name)
