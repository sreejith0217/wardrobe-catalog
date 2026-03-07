import io
import os
import tempfile
import uuid

import anthropic
from flask import Flask, render_template, abort, request, redirect, session, flash
from PIL import Image, ImageOps

from catalog import extract_care_data, generate_qr
from db import load_db, save_item, delete_item, upload_photo

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")


def is_admin():
    return session.get("admin") is True


@app.route("/")
def index():
    key = request.args.get("key", "")
    admin_key = os.environ.get("ADMIN_KEY", "")
    if key and key == admin_key:
        session["admin"] = True
    items = load_db()
    return render_template("index.html", items=items)


@app.route("/add", methods=["GET", "POST"])
def add_item():
    if request.method == "GET":
        key = request.args.get("key", "")
        admin_key = os.environ.get("ADMIN_KEY", "")
        if key and key == admin_key:
            session["admin"] = True
        if not is_admin():
            flash("This is a live demo — adding items is restricted to the owner.")
            return redirect("/")
        return render_template("add.html")

    if not is_admin():
        return redirect("/")

    label_file = request.files.get("label_photo")
    garment_file = request.files.get("garment_photo")
    item_name = request.form.get("item_name", "").strip()

    if not label_file or label_file.filename == "":
        return render_template("add.html", error="Care label photo is required.")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return render_template("add.html", error="ANTHROPIC_API_KEY is not set on the server.")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            label_ext = os.path.splitext(label_file.filename)[1] or ".jpg"
            label_path = os.path.join(tmpdir, f"label{label_ext}")
            label_file.save(label_path)

            if garment_file and garment_file.filename:
                garment_ext = os.path.splitext(garment_file.filename)[1] or ".jpg"
                garment_path = os.path.join(tmpdir, f"garment{garment_ext}")
                garment_file.save(garment_path)
            else:
                garment_path = label_path

            client = anthropic.Anthropic(api_key=api_key)
            care_data = extract_care_data(client, label_path, garment_path)

            # Auto-rotate and store garment photo bytes before tmpdir is cleaned up
            garment_bytes = None
            if garment_file and garment_file.filename:
                img = Image.open(garment_path)
                img = ImageOps.exif_transpose(img)
                img = img.convert("RGB")
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                garment_bytes = buf.getvalue()

        item_id = f"ITEM{str(uuid.uuid4())[:6].upper()}"
        care_data["item_id"] = item_id
        if item_name:
            care_data["name"] = item_name

        if garment_bytes:
            try:
                photo_url = upload_photo(item_id, garment_bytes)
                care_data["photo_url"] = photo_url
            except Exception as e:
                print(f"Photo upload failed: {e}")

        save_item(item_id, care_data)
        try:
            generate_qr(item_id)
        except Exception:
            pass  # QR generation is local-only, not needed on server

        return redirect(f"/item/{item_id}")

    except Exception as e:
        print(f"ERROR: {e}")
        return render_template("add.html", error=f"Something went wrong: {str(e)}")


@app.route("/item/<item_id>")
def care_page(item_id):
    items = load_db()
    item = items.get(item_id.upper())
    if not item:
        abort(404)
    return render_template("item.html", item=item, admin=is_admin())


@app.route("/item/<item_id>/photo", methods=["POST"])
def update_photo(item_id):
    if not is_admin():
        return redirect("/")
    item_id = item_id.upper()
    items = load_db()
    item = items.get(item_id)
    if not item:
        abort(404)
    photo_file = request.files.get("photo")
    if photo_file and photo_file.filename:
        img = Image.open(photo_file)
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        try:
            photo_url = upload_photo(item_id, buf.getvalue())
            item["photo_url"] = photo_url
            save_item(item_id, item)
        except Exception as e:
            print(f"Photo upload failed: {e}")
    return redirect(f"/item/{item_id}")


@app.route("/item/<item_id>/rename", methods=["POST"])
def rename_item(item_id):
    if not is_admin():
        return redirect("/")
    item_id = item_id.upper()
    items = load_db()
    item = items.get(item_id)
    if not item:
        abort(404)
    new_name = request.form.get("name", "").strip()
    if new_name:
        item["name"] = new_name
        save_item(item_id, item)
    return redirect(f"/item/{item_id}")


@app.route("/item/<item_id>/delete", methods=["POST"])
def delete_item_route(item_id):
    if not is_admin():
        return redirect("/")
    delete_item(item_id.upper())
    return redirect("/")


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
