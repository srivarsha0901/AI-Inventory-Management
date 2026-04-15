from flask import Blueprint, jsonify, request
from jwt_helper import jwt_required
from database import get_db
from bson import ObjectId
from datetime import datetime, timezone
import os, re

ocr_bp = Blueprint("ocr", __name__)


# ── Attempt real OCR (Tesseract), fallback to regex parser ──────────
def _extract_text_from_image(file_bytes):
    """Try Tesseract OCR first, fallback to None."""
    try:
        from PIL import Image
        import pytesseract, io
        img = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(img)
        return text
    except ImportError:
        return None
    except Exception:
        return None


def _extract_text_from_pdf(file_bytes):
    """Try PyPDF2 / pdfplumber, fallback to None."""
    try:
        import pdfplumber, io
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        return text
    except ImportError:
        return None
    except Exception:
        return None


def _parse_invoice_text(raw_text):
    """
    Parse raw OCR text into structured line items.
    Handles common invoice formats:
      ProductName   Qty   UnitPrice   Total
    or:
      ProductName x Qty @ Price = Total
    """
    items = []
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

    # Pattern 1: "ProductName  50  kg  28  1400"
    pat1 = re.compile(
        r"^(.+?)\s+(\d+(?:\.\d+)?)\s*(kg|pcs|L|packs|loaves|cups|bottles|cans|dozen|bunches|bags|units)?\s+"
        r"(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)$", re.IGNORECASE
    )
    # Pattern 2: "ProductName x 50 @ 28 = 1400"
    pat2 = re.compile(
        r"^(.+?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*[@]\s*(\d+(?:\.\d+)?)\s*[=]\s*(\d+(?:\.\d+)?)$", re.IGNORECASE
    )
    # Pattern 3: simple "Name   Qty   Price"
    pat3 = re.compile(
        r"^([A-Za-z][\w\s]+?)\s{2,}(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)$"
    )

    idx = 0
    for line in lines:
        m = pat1.match(line)
        if m:
            idx += 1
            qty = float(m.group(2))
            price = float(m.group(4))
            total = float(m.group(5))
            items.append({
                "id": idx,
                "name":      m.group(1).strip(),
                "qty":       qty,
                "unit":      (m.group(3) or "units").lower(),
                "price":     price,
                "total":     total,
                "confirmed": True,
            })
            continue

        m = pat2.match(line)
        if m:
            idx += 1
            qty = float(m.group(2))
            price = float(m.group(3))
            total = float(m.group(4))
            items.append({
                "id": idx,
                "name":      m.group(1).strip(),
                "qty":       qty,
                "unit":      "units",
                "price":     price,
                "total":     total,
                "confirmed": True,
            })
            continue

        m = pat3.match(line)
        if m:
            idx += 1
            qty = float(m.group(2))
            price = float(m.group(3))
            items.append({
                "id": idx,
                "name":      m.group(1).strip(),
                "qty":       qty,
                "unit":      "units",
                "price":     price,
                "total":     round(qty * price, 2),
                "confirmed": True,
            })

    return items


def _detect_supplier(raw_text):
    """Try to extract supplier name from invoice header."""
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    # Usually first non-empty line is the supplier/company name
    for line in lines[:5]:
        if len(line) > 3 and not line.replace(" ", "").isdigit():
            # Skip lines that look like dates, totals, headers
            if any(kw in line.lower() for kw in ["invoice", "date", "total", "qty", "amount", "sl.", "#"]):
                continue
            return line
    return "Unknown Supplier"


# ── Routes ────────────────────────────────────────────────────────────

@ocr_bp.route("/ocr/upload", methods=["POST"])
@jwt_required
def upload_invoice():
    """Upload an invoice image/PDF, run OCR, parse items."""
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        file     = request.files.get("invoice") or request.files.get("file")

        if not file:
            return jsonify({"message": "No file uploaded"}), 400

        file_bytes = file.read()
        filename   = file.filename or "unknown"
        raw_text   = None

        # Try OCR
        if filename.lower().endswith(".pdf"):
            raw_text = _extract_text_from_pdf(file_bytes)
        else:
            raw_text = _extract_text_from_image(file_bytes)

        if not raw_text or len(raw_text.strip()) < 10:
            raw_text = "(OCR extraction failed — Tesseract not installed or image unreadable)"

        # Parse items from text
        items    = _parse_invoice_text(raw_text)
        supplier = _detect_supplier(raw_text)
        total    = sum(i.get("total", 0) for i in items)

        # Save to MongoDB
        now = datetime.now(timezone.utc)
        doc = {
            "store_id":     store_id,
            "filename":     filename,
            "supplier":     supplier,
            "raw_text":     raw_text,
            "parsed_items": items,
            "total_amount": total,
            "item_count":   len(items),
            "status":       "pending",  # pending | confirmed | rejected
            "uploaded_by":  request.current_user.get("sub"),
            "created_at":   now,
        }
        result = db.invoices.insert_one(doc)

        return jsonify({
            "message":  f"Invoice processed — {len(items)} items extracted",
            "id":       str(result.inserted_id),
            "items":    items,
            "supplier": supplier,
            "total":    total,
            "raw_text": raw_text[:500],
        })

    except Exception as e:
        return jsonify({"message": str(e)}), 500


@ocr_bp.route("/ocr/<invoice_id>", methods=["GET"])
@jwt_required
def get_extracted(invoice_id):
    """Get a specific invoice's extracted data."""
    try:
        db  = get_db()
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
    """Confirm extracted items and update inventory."""
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")
        data     = request.get_json()
        items    = data.get("items", [])
        now      = datetime.now(timezone.utc)

        updated = 0
        for item in items:
            if not item.get("confirmed", True):
                continue

            name = item.get("name", "").strip()
            qty  = float(item.get("qty", 0))
            if not name or qty <= 0:
                continue

            # Update inventory — add stock
            result = db.inventory.update_one(
                {"store_id": store_id, "product_name": name},
                {"$inc": {"stock": qty}, "$set": {"last_updated": now}}
            )
            if result.modified_count:
                updated += 1

                # Check if stock is back to healthy
                inv_item = db.inventory.find_one({"store_id": store_id, "product_name": name})
                if inv_item:
                    stock  = inv_item.get("stock", 0)
                    safety = inv_item.get("safety_stock", 10)
                    status = ("Out of Stock" if stock == 0 else
                              "Low Stock"    if stock < safety else "Healthy")
                    db.inventory.update_one(
                        {"_id": inv_item["_id"]},
                        {"$set": {"stock_status": status}}
                    )
                    # Resolve alerts if stock is healthy now
                    if status == "Healthy":
                        db.alerts.update_many(
                            {"product_name": name, "store_id": store_id, "status": "active"},
                            {"$set": {"status": "resolved", "updated_at": now}}
                        )

        # Update invoice status
        if invoice_id != "latest":
            db.invoices.update_one(
                {"_id": ObjectId(invoice_id)},
                {"$set": {"status": "confirmed", "confirmed_at": now}}
            )

        return jsonify({
            "message": f"✅ {updated} items updated in inventory",
            "updated": updated,
        })

    except Exception as e:
        return jsonify({"message": str(e)}), 500


@ocr_bp.route("/ocr/history", methods=["GET"])
@jwt_required
def get_history():
    """Get past invoice uploads for this store."""
    try:
        db       = get_db()
        store_id = request.current_user.get("store_id")

        invoices = list(
            db.invoices.find({"store_id": store_id})
            .sort("created_at", -1)
            .limit(20)
        )
        for inv in invoices:
            inv["id"] = str(inv.pop("_id"))
            if "created_at" in inv:
                inv["created_at"] = inv["created_at"].isoformat()
            # Don't send raw_text in listing
            inv.pop("raw_text", None)
            inv.pop("parsed_items", None)

        return jsonify({"data": invoices})

    except Exception as e:
        return jsonify({"message": str(e)}), 500
