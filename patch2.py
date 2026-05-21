import os

path = 'c:/Projects/AI Inventory Management/backend/routes/seasonal_routes.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """INDIAN_FESTIVALS = [
    { "name": "Diwali",     "month": 10, "boost_categories": ["Sweets","Snacks","Oils","Beverages"], "multiplier": 1.8 },
    { "name": "Christmas",  "month": 12, "boost_categories": ["Bakery","Beverages","Dairy","Eggs"],  "multiplier": 1.6 },
    { "name": "Holi",       "month": 3,  "boost_categories": ["Beverages","Dairy","Snacks"],         "multiplier": 1.4 },
    { "name": "Eid",        "month": 4,  "boost_categories": ["Grains","Dairy","Oils"],              "multiplier": 1.5 },
    { "name": "Pongal",     "month": 1,  "boost_categories": ["Grains","Dairy","Vegetables"],        "multiplier": 1.4 },
    { "name": "Navratri",   "month": 10, "boost_categories": ["Dairy","Fruits","Grains"],            "multiplier": 1.3 },
    { "name": "New Year",   "month": 1,  "boost_categories": ["Beverages","Bakery","Snacks"],        "multiplier": 1.5 },
]"""

replacement = """import holidays
from datetime import timedelta

HOLIDAY_BOOSTS = {
    "diwali": {"boost_categories": ["Sweets","Snacks","Oils","Beverages","Dairy"], "multiplier": 1.5},
    "holi": {"boost_categories": ["Beverages","Dairy","Snacks"], "multiplier": 1.4},
    "christmas": {"boost_categories": ["Bakery","Beverages","Dairy","Eggs"], "multiplier": 1.4},
    "eid": {"boost_categories": ["Grains","Dairy","Oils"], "multiplier": 1.4},
    "new year": {"boost_categories": ["Beverages","Bakery","Snacks"], "multiplier": 1.3},
    "independence day": {"boost_categories": ["Snacks","Beverages"], "multiplier": 1.2},
    "republic day": {"boost_categories": ["Snacks","Beverages"], "multiplier": 1.2},
}

def get_indian_festivals(year):
    ind_holidays = holidays.India(years=year)
    festivals = []
    for dt, name in sorted(ind_holidays.items()):
        boost_cats = []
        mult = 1.0
        for k, v in HOLIDAY_BOOSTS.items():
            if k in name.lower():
                boost_cats = v["boost_categories"]
                mult = v["multiplier"]
                break
        if boost_cats:
            # We must serialize datetime to ISO string or remove it if not needed,
            # but seasonal_routes expects 'month' 
            festivals.append({
                "name": name,
                "month": dt.month,
                "boost_categories": boost_cats,
                "multiplier": mult
            })
    return festivals"""

target2 = """    upcoming = [
        f for f in INDIAN_FESTIVALS
        if f["month"] in [current_month, next_month]
    ]"""

replacement2 = """    fests = get_indian_festivals(now.year)
    upcoming = [
        f for f in fests
        if f["month"] in [current_month, next_month]
    ]"""

target3 = """        # Find the festival
        fest = next((f for f in INDIAN_FESTIVALS if f["name"] == festival), None)"""

replacement3 = """        # Find the festival
        fests = get_indian_festivals(now.year)
        fest = next((f for f in fests if f["name"] == festival), None)"""

target4 = """        # Upcoming festivals
        upcoming_festivals = [
            f for f in INDIAN_FESTIVALS
            if f["month"] in [month, next_month]
        ]"""

replacement4 = """        # Upcoming festivals
        fests = get_indian_festivals(now.year)
        upcoming_festivals = [
            f for f in fests
            if f["month"] in [month, next_month]
        ]"""

target5 = """        # 1. Upcoming festival alerts
        for fest in INDIAN_FESTIVALS:"""

replacement5 = """        # 1. Upcoming festival alerts
        fests = get_indian_festivals(now.year)
        for fest in fests:"""

def do_replace(content, t, r):
    if t.replace('\\n', '\\r\\n') in content:
        return content.replace(t.replace('\\n', '\\r\\n'), r.replace('\\n', '\\r\\n'))
    return content.replace(t, r)

content = do_replace(content, target, replacement)
content = do_replace(content, target2, replacement2)
content = do_replace(content, target3, replacement3)
content = do_replace(content, target4, replacement4)
content = do_replace(content, target5, replacement5)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
