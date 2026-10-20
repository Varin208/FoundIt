"""
reports.py - save lost/found reports (with photos) and list a user's reports.

Endpoints:
    POST /api/reports/lost    multipart form: itemName, description, location,
                              dateTime (ISO, UTC), photo (optional)      -> {report}
    POST /api/reports/found   multipart form: photo (required), location,
                              description (optional)                     -> {report}
    GET  /api/reports/mine                                               -> {lost: [...], found: [...]}
    GET  /api/photos/<name>   the saved photo (login required)

Photos are never saved as uploaded. Each one is opened with Pillow (proving it
really is an image), rotated upright, stripped of metadata such as GPS
location, shrunk to at most 1280px, and re-saved as a JPEG under a random name.
"""
import io
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from PIL import Image, ImageOps, UnidentifiedImageError

from auth import current_user, error, login_required
from models import Report, db, utcnow

reports_bp = Blueprint("reports", __name__, url_prefix="/api")

ALLOWED_FORMATS = {"JPEG", "MPO", "PNG", "WEBP", "GIF"}  # MPO = some phone JPEGs
MAX_SIDE = 1280
PHOTO_NAME = re.compile(r"^[0-9a-f]{32}\.jpg$")

Image.MAX_IMAGE_PIXELS = 50_000_000  # refuse "decompression bomb" images


class PhotoError(Exception):
    pass


def save_photo(file_storage):
    """Validate, clean and save an uploaded image. Returns the new filename."""
    try:
        img = Image.open(io.BytesIO(file_storage.read()))
        if img.format not in ALLOWED_FORMATS:
            raise PhotoError
        img.load()
        img = ImageOps.exif_transpose(img)  # apply phone rotation
        if img.mode in ("RGBA", "LA", "P"):  # flatten transparency onto white
            img = img.convert("RGBA")
            background = Image.new("RGB", img.size, "white")
            background.paste(img, mask=img.split()[-1])
            img = background
        else:
            img = img.convert("RGB")
        img.thumbnail((MAX_SIDE, MAX_SIDE))
    except (PhotoError, UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
        raise PhotoError("Please upload a JPG, PNG or WEBP photo.")

    filename = uuid.uuid4().hex + ".jpg"
    img.save(os.path.join(current_app.config["UPLOAD_DIR"], filename), "JPEG", quality=85, optimize=True)
    return filename


def delete_photo(filename):
    if filename:
        try:
            os.remove(os.path.join(current_app.config["UPLOAD_DIR"], filename))
        except OSError:
            pass


def parse_event_time(value):
    """ISO string -> naive UTC datetime, or None if it can't be read."""
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def get_uploaded_photo():
    """The uploaded file, or None if the form had no photo."""
    photo = request.files.get("photo")
    return photo if photo and photo.filename else None


def store_report(report, photo):
    """Save the photo (if any) and the report row; clean up if the database fails."""
    try:
        if photo:
            report.photo_filename = save_photo(photo)
        db.session.add(report)
        db.session.commit()
    except PhotoError as e:
        return error(str(e), 400)
    except Exception:
        db.session.rollback()
        delete_photo(report.photo_filename)
        raise
    return jsonify(report=report.to_dict()), 201


@reports_bp.post("/reports/lost")
@login_required
def create_lost_report():
    user = current_user()
    item_name = request.form.get("itemName", "").strip()
    description = request.form.get("description", "").strip()
    location = request.form.get("location", "").strip()
    lost_at = parse_event_time(request.form.get("dateTime", ""))

    if not item_name or len(item_name) > 200:
        return error("Tell us what the item is (up to 200 characters).", 400)
    if not description or len(description) > 2000:
        return error("Add a short description (up to 2000 characters).", 400)
    if not location or len(location) > 200:
        return error("Add the location (up to 200 characters).", 400)
    if lost_at is None:
        return error("Add the date and time you lost it.", 400)
    if lost_at > utcnow() + timedelta(minutes=5):
        return error("The date and time can't be in the future.", 400)

    report = Report(
        owner_id=user.id, kind="lost", item_name=item_name, description=description,
        location=location, event_time=lost_at, status="searching",
    )
    return store_report(report, get_uploaded_photo())


@reports_bp.post("/reports/found")
@login_required
def create_found_report():
    user = current_user()
    description = request.form.get("description", "").strip()
    location = request.form.get("location", "").strip()
    photo = get_uploaded_photo()

    if photo is None:
        return error("Add a photo of the item.", 400)
    if not location or len(location) > 200:
        return error("Add the location (up to 200 characters).", 400)
    if len(description) > 2000:
        return error("The description is too long (up to 2000 characters).", 400)

    report = Report(
        owner_id=user.id, kind="found", item_name="Found item", description=description,
        location=location, event_time=utcnow(), status="searching",
    )
    return store_report(report, photo)


@reports_bp.get("/reports/mine")
@login_required
def my_reports():
    user = current_user()
    rows = Report.query.filter_by(owner_id=user.id).order_by(Report.created_at.desc()).all()
    return jsonify(
        lost=[r.to_dict() for r in rows if r.kind == "lost"],
        found=[r.to_dict() for r in rows if r.kind == "found"],
    )


@reports_bp.get("/photos/<name>")
@login_required
def photo(name):
    # Names are random 32-character hex, so they can't be guessed; the pattern
    # check also blocks anything like "../app.py".
    if not PHOTO_NAME.match(name):
        return error("Not found.", 404)
    return send_from_directory(current_app.config["UPLOAD_DIR"], name, mimetype="image/jpeg")
