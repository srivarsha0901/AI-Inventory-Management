import re
from difflib import SequenceMatcher
from bson import ObjectId


def store_id_values(store_id):
    """Return both string and ObjectId variants for mixed legacy store_id data."""
    values = []
    if store_id:
        values.append(store_id)
        try:
            store_id_obj = ObjectId(store_id)
            if store_id_obj not in values:
                values.append(store_id_obj)
        except Exception:
            pass
    return values


def cashier_id_values(cashier_id):
    """Return string and ObjectId variants for cashier_id / user_id lookups."""
    values = []
    if cashier_id:
        values.append(cashier_id)
        try:
            cid_obj = ObjectId(cashier_id)
            if cid_obj not in values:
                values.append(cid_obj)
        except Exception:
            pass
    return values


def normalize_product_name(name):
    """Normalize product names for CSV/POS/OCR matching."""
    value = str(name or "").lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    tokens = []
    stop_words = {"fresh", "new", "the", "packet", "pack", "pkt"}
    for token in value.split():
        if token in stop_words:
            continue
        tokens.append(token)
    return " ".join(tokens).strip()


def _similarity(left, right):
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0

    left_tokens = set(left.split())
    right_tokens = set(right.split())
    token_score = 0.0
    if left_tokens and right_tokens:
        token_score = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)

    sequence_score = SequenceMatcher(None, left, right).ratio()
    return max(token_score, sequence_score)


def load_inventory_name_index(db, store_id):
    """Build a searchable product index for one store."""
    store_ids = store_id_values(store_id)
    query = {"store_id": {"$in": store_ids}} if store_ids else {}
    items = list(db.inventory.find(query, {
        "_id": 1,
        "product_id": 1,
        "product_name": 1,
        "category": 1,
        "unit": 1,
    }))

    index = []
    for item in items:
        canonical = item.get("product_name", "")
        normalized = normalize_product_name(canonical)
        if not normalized:
            continue
        index.append({
            "normalized": normalized,
            "canonical": canonical,
            "item": item,
        })
    return index


def match_inventory_product(raw_name, inventory_index, threshold=0.74):
    """Return the best inventory match for an uploaded product name."""
    normalized = normalize_product_name(raw_name)
    if not normalized:
        return None

    best = None
    best_score = 0.0
    for entry in inventory_index:
        score = _similarity(normalized, entry["normalized"])
        if score > best_score:
            best = entry
            best_score = score

    if not best or best_score < threshold:
        return None

    return {
        "canonical_name": best["canonical"],
        "inventory": best["item"],
        "score": round(best_score, 3),
    }
