from flask import Blueprint, jsonify, request
from jwt_helper import jwt_required
from database import get_db
from bson import ObjectId
from datetime import datetime, timezone
import os
import re
import pandas as pd
from product_matching import load_inventory_name_index, match_inventory_product, store_id_values

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.getcwd(), ".matplotlib"))

ocr_bp = Blueprint("ocr", __name__)

_ocr_reader = None
_paddle_reader = None


def _get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        from rapidocr_onnxruntime import RapidOCR
        print("Initializing RapidOCR...")
        _ocr_reader = RapidOCR()
        print("RapidOCR ready")
    return _ocr_reader


def _get_paddle_reader():
    global _paddle_reader
    if _paddle_reader is None:
        from paddleocr import PaddleOCR
        print("Initializing PaddleOCR fallback...")
        _paddle_reader = PaddleOCR(
            lang="en",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        print("PaddleOCR fallback ready")
    return _paddle_reader


def _box_center(box):
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _reconstruct_lines(ocr_rows, y_tolerance=12):
    cells = []
    for row in ocr_rows or []:
        if len(row) < 2:
            continue
        box = row[0]
        text = str(row[1]).strip()
        if not text:
            continue
        x, y = _box_center(box)
        cells.append({"x": x, "y": y, "text": text})

    lines = []
    for cell in sorted(cells, key=lambda c: (c["y"], c["x"])):
        for line in lines:
            if abs(line["y"] - cell["y"]) <= y_tolerance:
                line["cells"].append(cell)
                line["y"] = (line["y"] + cell["y"]) / 2
                break
        else:
            lines.append({"y": cell["y"], "cells": [cell]})

    text_lines = []
    for line in sorted(lines, key=lambda l: l["y"]):
        ordered = sorted(line["cells"], key=lambda c: c["x"])
        text_lines.append(" ".join(c["text"] for c in ordered))
    return "\n".join(text_lines)

def _tesseract_executable():
    import shutil
    cmd = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if cmd and os.path.isfile(cmd):
        return cmd
    return shutil.which("tesseract")


def _log_ocr_output(engine_name, text):
    if text and text.strip():
        print(f"========== {engine_name} OUTPUT ==========")
        print(text)
        print("======================================")


def _extract_text_rapidocr(file_bytes):
    try:
        reader = _get_ocr_reader()
        result, _ = reader(file_bytes)
        if not result:
            return ""
        text = _reconstruct_lines(result)
        _log_ocr_output("RAPIDOCR", text)
        return text or ""
    except Exception as e:
        print(f"RapidOCR failed: {e}")
        return ""


def _extract_text_paddleocr(file_bytes):
    try:
        import io
        import numpy as np
        from PIL import Image

        reader = _get_paddle_reader()
        img = np.array(Image.open(io.BytesIO(file_bytes)).convert("RGB"))
        raw = reader.ocr(img, cls=False)
        if not raw or not raw[0]:
            return ""
        rows = [[line[0], line[1][0], line[1][1]] for line in raw[0]]
        text = _reconstruct_lines(rows)
        _log_ocr_output("PADDLEOCR", text)
        return text or ""
    except Exception as e:
        print(f"PaddleOCR failed: {e}")
        return ""


def _extract_text_tesseract(file_bytes):
    try:
        import pytesseract
        from PIL import Image, ImageEnhance
        import io
    except ImportError:
        print("pytesseract not installed — run: pip install pytesseract")
        return ""

    tesseract_cmd = _tesseract_executable()
    if not tesseract_cmd:
        print("Tesseract binary not found — install from https://github.com/UB-Mannheim/tesseract/wiki")
        return ""

    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    try:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
        img = ImageEnhance.Contrast(img).enhance(1.8)

        df = pytesseract.image_to_data(
            img, config="--psm 6", output_type=pytesseract.Output.DATAFRAME
        )
        df = df[df.conf > 30].dropna(subset=["text"])
        df = df[df["text"].str.strip() != ""]
        df = df.sort_values(["top", "left"])

        lines = []
        current_line = []
        current_top = None
        for _, row in df.iterrows():
            if current_top is None or abs(row["top"] - current_top) < 15:
                current_line.append(row)
                current_top = row["top"] if current_top is None else (current_top + row["top"]) / 2
            else:
                if current_line:
                    lines.append(current_line)
                current_line = [row]
                current_top = row["top"]
        if current_line:
            lines.append(current_line)

        text_lines = []
        for line in lines:
            words = sorted(line, key=lambda r: r["left"])
            text_lines.append("  ".join(str(w["text"]).strip() for w in words))

        text = "\n".join(text_lines)
        _log_ocr_output("TESSERACT", text)
        return text or ""
    except Exception as e:
        print(f"Tesseract failed: {e}")
        return ""


def _extract_text_from_image(file_bytes):
    """Try OCR engines in order: RapidOCR → PaddleOCR → Tesseract."""
    for extract in (_extract_text_rapidocr, _extract_text_paddleocr, _extract_text_tesseract):
        text = extract(file_bytes)
        if text and len(text.strip()) >= 10:
            return text
    return ""

def _extract_text_from_pdf(file_bytes):
    try:
        import pdfplumber
        import io
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        return text if text.strip() else None
    except Exception as e:
        print(f"PDF extraction failed: {e}")
        return None


_UNIT_ALIASES = {
    "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
    "l": "L", "ltr": "L", "litre": "L", "litres": "L", "liter": "L", "liters": "L",
    "pcs": "pcs", "pc": "pcs", "piece": "pcs", "pieces": "pcs",
    "pack": "packs", "packs": "packs",
    "loaf": "loaves", "loaves": "loaves",
    "cup": "cups", "cups": "cups",
    "bottle": "bottles", "bottles": "bottles",
    "can": "cans", "cans": "cans",
    "dozen": "dozen", "doz": "dozen", "dozens": "dozen",
    "bunch": "bunches", "bunches": "bunches",
    "bag": "bags", "bags": "bags",
    "unit": "units", "units": "units",
    "box": "boxes", "boxes": "boxes",
    # Common OCR mistakes for "dozen"/"dozens" in invoice tables.
    "suazop": "dozen", "sua2op": "dozen", "dozens": "dozen",
}
_UNIT_PATTERN = "|".join(sorted(map(re.escape, _UNIT_ALIASES.keys()), key=len, reverse=True))

def _normalise_unit(raw):
    if not raw:
        return "units"
    cleaned = re.sub(r"[^a-zA-Z]", "", raw.lower().strip())
    if cleaned in _UNIT_ALIASES:
        return _UNIT_ALIASES[cleaned]
    # Fuzzy match for OCR errors
    from difflib import get_close_matches
    matches = get_close_matches(cleaned, _UNIT_ALIASES.keys(), n=1, cutoff=0.6)
    if matches:
        return _UNIT_ALIASES[matches[0]]
    return cleaned or "units"

def _clean_item_name(raw):
    return re.sub(r"^\s*\d+\s+", "", raw or "").strip()


def _money(raw):
    return float(str(raw).replace(",", "").strip())


def _parse_invoice_text(raw_text):
    print("\n--- PARSING OCR TEXT ---")

    items = []
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    skip_words = [
        "invoice", "date", "subtotal", "tax", "total amount", "payment",
        "thank you", "supplier", "item details",
    ]
    header_words = ["product", "qty", "unit", "price", "amount", "total"]

    for line in lines:
        lower = line.lower()
        print("LINE:", lower)
        if any(w in lower for w in skip_words):
            continue
        if sum(1 for w in header_words if w in lower) >= 2:
            continue

        # Table rows with serial number + arbitrary OCR unit:
        # "5 Bananas 30 suazop 38.00 1,140.00"
        m = re.match(
            r"^(?:\d+\s+)?(.+?)\s+(\d+(?:\.\d+)?)\s+([A-Za-z][A-Za-z0-9]*)\s+([\d,]+(?:\.\d+)?)\s+([\d,]+(?:\.\d+)?)$",
            line,
            re.IGNORECASE,
        )
        if m:
            idx = len(items) + 1
            qty = float(m.group(2))
            price = _money(m.group(4))
            total = _money(m.group(5))
            if qty > 0 and total > 0 and abs((qty * price) - total) / total > 0.2:
                price = round(total / qty, 2)
            items.append({
                "id": idx,
                "name": _clean_item_name(m.group(1)),
                "qty": qty,
                "unit": _normalise_unit(m.group(3)),
                "price": price,
                "total": total,
                "confirmed": True,
            })
            continue

        m = re.match(
            rf"(.+?)\s+(\d+(?:\.\d+)?)\s*({_UNIT_PATTERN})?\s+([\d,]+(?:\.\d+)?)\s+([\d,]+(?:\.\d+)?)$",
            line,
            re.IGNORECASE,
        )
        if m:
            idx = len(items) + 1
            qty = float(m.group(2))
            price = _money(m.group(4))
            total = _money(m.group(5))
            if qty > 0 and total > 0 and abs((qty * price) - total) / total > 0.2:
                price = round(total / qty, 2)
            items.append({
                "id": idx,
                "name": _clean_item_name(m.group(1)),
                "qty": qty,
                "unit": _normalise_unit(m.group(3)),
                "price": price,
                "total": total,
                "confirmed": True,
            })
            continue

        m = re.match(r"(.+?)\s+(\d+(?:\.\d+)?)\s+([\d,]+(?:\.\d+)?)$", line)
        if m:
            qty = float(m.group(2))
            price = _money(m.group(3))
            idx = len(items) + 1
            items.append({
                "id": idx,
                "name": _clean_item_name(m.group(1)),
                "qty": qty,
                "unit": "units",
                "price": price,
                "total": round(qty * price, 2),
                "confirmed": True,
            })

    print(f"Parsed {len(items)} items\n")
    return items


def _extract_items_from_image(file_bytes):
    text = _extract_text_from_image(file_bytes)
    if text and len(text.strip()) > 10:
        return _parse_invoice_text(text)
    return []


def _detect_supplier(raw_text):
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    for line in lines[:8]:
        lower = line.lower()
        if len(line) > 3 and not line.replace(" ", "").isdigit():
            if any(kw in lower for kw in ["invoice", "date", "total", "qty", "amount", "sl.", "#"]):
                continue
            return line
    return "Unknown Supplier"


@ocr_bp.route("/ocr/upload", methods=["POST"])
@jwt_required
def upload_invoice():
    try:
        db = get_db()
        store_id = request.current_user.get("store_id")
        try:
            store_id_obj = ObjectId(store_id)
        except Exception:
            store_id_obj = store_id

        file = request.files.get("invoice") or request.files.get("file")
        if not file:
            return jsonify({"message": "No file uploaded"}), 400

        file_bytes = file.read()
        filename = file.filename or "unknown"

        if filename.lower().endswith(".pdf"):
            raw_text = _extract_text_from_pdf(file_bytes) or ""
        else:
            raw_text = _extract_text_from_image(file_bytes)

        if raw_text and len(raw_text.strip()) >= 10:
            items = _parse_invoice_text(raw_text)
            supplier = _detect_supplier(raw_text)
            ocr_status = "ok" if items else "text_only"
            message = f"Invoice processed - {len(items)} items extracted"
        else:
            items = _extract_items_from_image(file_bytes)
            supplier = "Manual Entry (OCR Failed)"
            ocr_status = "failed"
            raw_text = ""
            message = "OCR could not read this invoice. Please enter items manually."

        total = sum(i.get("total", 0) for i in items)
        now = datetime.now(timezone.utc)
        doc = {
            "store_id": store_id_obj,
            "filename": filename,
            "supplier": supplier,
            "document_type": request.form.get("mode", "customer_bill"),
            "raw_text": raw_text,
            "parsed_items": items,
            "total_amount": total,
            "item_count": len(items),
            "status": "pending",
            "uploaded_by": request.current_user.get("sub"),
            "created_at": now,
            "ocr_status": ocr_status,
        }
        result = db.invoices.insert_one(doc)

        return jsonify({
            "message": message,
            "ocr_status": ocr_status,
            "id": str(result.inserted_id),
            "items": items,
            "supplier": supplier,
            "total": total,
            "raw_text": raw_text[:1000],
        })
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@ocr_bp.route("/ocr/<invoice_id>", methods=["GET"])
@jwt_required
def get_extracted(invoice_id):
    try:
        db = get_db()
        inv = db.invoices.find_one({"_id": ObjectId(invoice_id)})
        if not inv:
            return jsonify({"message": "Invoice not found"}), 404

        inv["id"] = str(inv.pop("_id"))
        if "created_at" in inv:
            inv["created_at"] = inv["created_at"].isoformat()
        return jsonify(inv)
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@ocr_bp.route("/ocr/<invoice_id>/confirm", methods=["POST"])
@jwt_required
def confirm_items(invoice_id):
    try:
        db = get_db()
        store_id = request.current_user.get("store_id")
        store_ids = store_id_values(store_id)
        try:
            store_id_obj = ObjectId(store_id)
        except Exception:
            store_id_obj = store_id

        data = request.get_json() or {}
        items = data.get("items", [])
        mode = data.get("mode", "sale")
        now = datetime.now(timezone.utc)
        inventory_index = load_inventory_name_index(db, store_id)

        updated = 0
        unmatched = []
        insufficient = []
        sale_items = []
        for item in items:
            if not item.get("confirmed", True):
                continue

            uploaded_name = item.get("name", "").strip()
            qty = float(item.get("qty", 0))
            if not uploaded_name or qty <= 0:
                continue

            match = match_inventory_product(uploaded_name, inventory_index)
            if match:
                name = match["canonical_name"]
                matched_inventory = match["inventory"]
            else:
                name = uploaded_name
                unmatched.append(uploaded_name)
                continue

            inv_item = db.inventory.find_one({"store_id": {"$in": store_ids}, "product_name": name})
            if not inv_item:
                unmatched.append(uploaded_name)
                continue

            if mode == "receive":
                stock_delta = qty
            else:
                current_stock = float(inv_item.get("stock", 0) or 0)
                if current_stock < qty:
                    insufficient.append({
                        "name": name,
                        "requested": qty,
                        "available": current_stock,
                    })
                    continue
                stock_delta = -qty

            result = db.inventory.update_one(
                {"_id": inv_item["_id"]},
                {"$inc": {"stock": stock_delta}, "$set": {"last_updated": now}},
            )
            if result.modified_count:
                updated += 1
                inv_item = db.inventory.find_one({"_id": inv_item["_id"]})
                if inv_item:
                    stock = inv_item.get("stock", 0)
                    safety = inv_item.get("safety_stock", 10)
                    shelf_life = int(inv_item.get("shelf_life_days", 0) or 0)
                    expiry_date = None
                    if item.get("expiry_date"):
                        try:
                            expiry_date = pd.to_datetime(item.get("expiry_date")).to_pydatetime()
                            if expiry_date.tzinfo is None:
                                expiry_date = expiry_date.replace(tzinfo=timezone.utc)
                        except Exception:
                            expiry_date = None
                    elif shelf_life > 0:
                        expiry_date = now + pd.Timedelta(days=shelf_life)

                    if mode == "receive":
                        db.inventory_batches.insert_one({
                            "store_id": inv_item.get("store_id", store_id_obj),
                            "inventory_id": inv_item["_id"],
                            "product_id": inv_item.get("product_id"),
                            "product_name": name,
                            "qty_received": qty,
                            "qty_remaining": qty,
                            "expiry_date": expiry_date,
                            "source": "ocr_invoice",
                            "invoice_id": ObjectId(invoice_id) if invoice_id != "latest" else None,
                            "created_at": now,
                        })
                    else:
                        sale_items.append({
                            "product_id": str(inv_item.get("product_id") or matched_inventory.get("_id") or inv_item["_id"]),
                            "inventory_id": str(inv_item["_id"]),
                            "name": name,
                            "uploaded_name": uploaded_name,
                            "qty": qty,
                            "unit": item.get("unit", inv_item.get("unit", "units")),
                            "price": float(item.get("price", inv_item.get("selling_price", 0)) or 0),
                            "total": float(item.get("total", 0) or 0),
                            "source": "ocr_customer_bill",
                        })

                    status = "Out of Stock" if stock == 0 else "Low Stock" if stock < safety else "Healthy"
                    db.inventory.update_one({"_id": inv_item["_id"]}, {"$set": {"stock_status": status}})
                    if status == "Healthy":
                        db.alerts.update_many(
                            {"product_name": name, "store_id": {"$in": store_ids}, "status": "active"},
                            {"$set": {"status": "resolved", "updated_at": now}},
                        )

        sale_id = None
        if mode != "receive" and sale_items:
            subtotal = sum(i.get("total", 0) for i in sale_items)
            sale_doc = {
                "store_id": store_id_obj,
                "items": sale_items,
                "subtotal": subtotal,
                "tax": 0,
                "total": subtotal,
                "payment_method": "offline_bill",
                "source": "ocr_customer_bill",
                "invoice_id": ObjectId(invoice_id) if invoice_id != "latest" else None,
                "created_at": now,
            }
            sale_result = db.sales.insert_one(sale_doc)
            sale_id = str(sale_result.inserted_id)

        if invoice_id != "latest":
            db.invoices.update_one(
                {"_id": ObjectId(invoice_id)},
                {"$set": {
                    "status": "confirmed",
                    "confirmed_at": now,
                    "document_type": "supplier_invoice" if mode == "receive" else "customer_bill",
                    "sale_id": sale_id,
                }},
            )

        action = "received into inventory" if mode == "receive" else "sold from inventory"
        return jsonify({
            "message": f"{updated} items {action}",
            "updated": updated,
            "unmatched_products": sorted(set(unmatched))[:20],
            "insufficient_stock": insufficient,
            "sale_id": sale_id,
        })
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@ocr_bp.route("/ocr/history", methods=["GET"])
@jwt_required
def get_history():
    try:
        db = get_db()
        store_id = request.current_user.get("store_id")
        print("DEBUG history - store_id:", store_id, type(store_id))

        try:
            store_id_obj = ObjectId(store_id)
        except Exception:
            store_id_obj = store_id

        invoices = list(
            db.invoices.find({"store_id": {"$in": [store_id, store_id_obj]}})
            .sort("created_at", -1)
            .limit(20)
        )
        for inv in invoices:
            inv["id"] = str(inv.pop("_id"))
            # Convert ALL ObjectId fields to strings
            for key, val in list(inv.items()):
                if isinstance(val, ObjectId):
                    inv[key] = str(val)
            if "created_at" in inv:
                try:
                    inv["created_at"] = inv["created_at"].isoformat()
                except Exception:
                    inv["created_at"] = str(inv["created_at"])
            inv.pop("raw_text", None)
            inv.pop("parsed_items", None)


        return jsonify({"data": invoices})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"message": str(e)}), 500
