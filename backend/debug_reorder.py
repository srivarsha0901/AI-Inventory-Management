from database import get_db

db = get_db()

# Check all inventory items
items = list(db.inventory.find().limit(10))
print('=== Sample Inventory Items ===')
for item in items:
    print(f"{item.get('product_name')}: stock_status={item.get('stock_status')}, stock={item.get('stock')}, safety={item.get('safety_stock')}, reorder={item.get('reorder_point')}")

print()
print('=== Low Stock / Out of Stock Items ===')
low_stock = list(db.inventory.find({'stock_status': {'$in': ['Low Stock', 'Out of Stock']}}))
print(f'Total found: {len(low_stock)}')
for item in low_stock[:5]:
    print(f"  {item.get('product_name')}: {item.get('stock_status')} (stock={item.get('stock')})")

print()
print('=== Alerts in DB ===')
alerts = list(db.alerts.find({'status': 'active'}).limit(5))
print(f'Total active alerts: {len(alerts)}')
for alert in alerts:
    print(f"  {alert.get('product_name')}: {alert.get('type')} - {alert.get('message')[:60]}")
