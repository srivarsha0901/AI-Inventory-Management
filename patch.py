import os

path = 'c:/Projects/AI Inventory Management/backend/routes/ml_routes.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """        # Detect active festivals
        from datetime import datetime as dt2
        current_month  = dt2.today().month
        next_month     = (current_month % 12) + 1
        active_boosts  = {}
        festival_names = []

        for fest in INDIAN_FESTIVALS:
            if fest["month"] in [current_month, next_month]:
                festival_names.append(fest["name"])
                for cat, mult in fest["boost"].items():
                    active_boosts[cat] = max(active_boosts.get(cat, 1.0), mult)"""

replacement = """        # Detect active festivals and custom store events
        from datetime import datetime as dt2, timedelta
        now_dt = dt2.now(timezone.utc)
        current_month  = now_dt.month
        next_month     = (current_month % 12) + 1
        active_boosts  = {}
        festival_names = []

        for fest in INDIAN_FESTIVALS:
            if fest["month"] in [current_month, next_month]:
                festival_names.append(fest["name"])
                for cat, mult in fest["boost"].items():
                    active_boosts[cat] = max(active_boosts.get(cat, 1.0), mult)

        # Apply active store events (promotions, local events)
        in_7_days = now_dt + timedelta(days=7)
        store_events = list(db.store_events.find({
            "store_id": {"$in": [store_id, store_id_obj]},
            "start_date": {"$lte": in_7_days},
            "end_date": {"$gte": now_dt}
        }))
        
        for evt in store_events:
            festival_names.append(evt.get("name", "Store Event"))
            evt_multiplier = evt.get("multiplier", 1.2)
            for cat in evt.get("boost_categories", []):
                active_boosts[cat] = max(active_boosts.get(cat, 1.0), evt_multiplier)"""

# Try matching with CRLF and LF
if target.replace('\n', '\r\n') in content:
    target = target.replace('\n', '\r\n')
    replacement = replacement.replace('\n', '\r\n')

new_content = content.replace(target, replacement)
if new_content == content:
    print('Failed to replace! Target not found.')
else:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Replaced successfully!')
