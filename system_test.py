#!/usr/bin/env python3
"""
Full System Test for FreshTrack
Tests all key flows: Auth, DB, API, ML predictions, Reorder workflow
"""

import requests
import json
import time
from datetime import datetime, timezone, timedelta

API_BASE = "http://localhost:5000/api"
TEST_EMAIL = f"test{int(time.time())}@test.com"
TEST_STORE_NAME = f"Test Store {int(time.time())}"
TEST_PASSWORD = "TestPass123!"

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
END = '\033[0m'

def print_test(name):
    print(f"\n{BLUE}{'='*60}{END}")
    print(f"{BLUE}TEST: {name}{END}")
    print(f"{BLUE}{'='*60}{END}")

def print_ok(msg):
    print(f"{GREEN}[OK] {msg}{END}")

def print_error(msg):
    print(f"{RED}[ERROR] {msg}{END}")

def print_info(msg):
    print(f"{YELLOW}[INFO] {msg}{END}")

# ============================================================================
# TEST 1: REGISTRATION & LOGIN
# ============================================================================
def test_auth():
    print_test("Authentication (Register & Login)")
    
    try:
        # Register
        print_info("Registering new user...")
        register_data = {
            "name": "Test Manager",
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "store_name": TEST_STORE_NAME,
            "address": "123 Test Street"
        }
        
        resp = requests.post(f"{API_BASE}/auth/register", json=register_data, timeout=10)
        if resp.status_code != 201:
            print_error(f"Registration failed: {resp.status_code} - {resp.text}")
            return None
        
        result = resp.json()
        token = result.get("token")
        user_id = result.get("user", {}).get("id")
        store_id = result.get("user", {}).get("store_id")
        
        print_ok(f"Registration successful!")
        print_info(f"  User ID: {user_id}")
        print_info(f"  Store ID: {store_id}")
        print_info(f"  Token: {token[:50]}...")
        
        # Login
        print_info("Testing login...")
        login_data = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        
        resp = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
        if resp.status_code != 200:
            print_error(f"Login failed: {resp.status_code} - {resp.text}")
            return None
        
        result = resp.json()
        token = result.get("token")
        
        print_ok("Login successful!")
        print_info(f"  New Token: {token[:50]}...")
        
        return {
            "token": token,
            "user_id": user_id,
            "store_id": store_id,
            "email": TEST_EMAIL
        }
        
    except Exception as e:
        print_error(f"Auth error: {str(e)}")
        return None

# ============================================================================
# TEST 2: INVENTORY MANAGEMENT
# ============================================================================
def test_inventory(auth):
    if not auth:
        print_error("Skipping inventory test - no auth")
        return
    
    print_test("Inventory Management")
    headers = {"Authorization": f"Bearer {auth['token']}"}
    
    try:
        # Add inventory items via onboarding
        print_info("Adding inventory items...")
        items_data = {
            "items": [
                {
                    "name": "Milk",
                    "category": "Dairy",
                    "stock": 50,
                    "cost_price": 40,
                    "selling_price": 60,
                    "unit": "L",
                    "emoji": "",
                    "reorder_point": 10,
                    "safety_stock": 5,
                    "shelf_life_days": 7,
                    "restock_days": 3
                },
                {
                    "name": "Bread",
                    "category": "Bakery",
                    "stock": 30,
                    "cost_price": 30,
                    "selling_price": 50,
                    "unit": "units",
                    "emoji": "",
                    "reorder_point": 5,
                    "safety_stock": 3,
                    "shelf_life_days": 2,
                    "restock_days": 1
                }
            ]
        }
        
        resp = requests.post(f"{API_BASE}/onboarding/inventory", json=items_data, headers=headers, timeout=10)
        if resp.status_code != 201:
            print_error(f"Add inventory failed: {resp.status_code} - {resp.text}")
            return None
        
        print_ok(f"Inventory items added!")
        
        # Get products
        print_info("Fetching products...")
        resp = requests.get(f"{API_BASE}/products", headers=headers, timeout=10)
        if resp.status_code != 200:
            print_error(f"Fetch products failed: {resp.status_code}")
            return None
        
        items = resp.json().get("data", [])
        print_ok(f"Fetched {len(items)} products")
        
        return items[0].get("id") if items else None
        
    except Exception as e:
        print_error(f"Inventory error: {str(e)}")
        return None

# ============================================================================
# TEST 3: POS / SALES
# ============================================================================
def test_sales(auth, item_id):
    if not auth:
        print_error("Skipping sales test - no auth")
        return
    
    print_test("POS / Sales")
    headers = {"Authorization": f"Bearer {auth['token']}"}
    
    try:
        # Create sale
        print_info("Creating POS sale...")
        sale_data = {
            "items": [
                {
                    "product_id": "TEST-001",
                    "product_name": "Test Milk",
                    "qty": 5,
                    "price": 60,
                    "subtotal": 300
                }
            ],
            "subtotal": 300,
            "tax": 30,
            "total": 330
        }
        
        resp = requests.post(f"{API_BASE}/sales", json=sale_data, headers=headers, timeout=10)
        if resp.status_code not in [200, 201]:
            print_error(f"Create sale failed: {resp.status_code} - {resp.text}")
            return None
        
        result = resp.json()
        sale_id = result.get("sale_id") or result.get("id")
        print_ok(f"Sale created successfully!")
        print_info(f"  Sale ID: {sale_id}")
        print_info(f"  Amount: {result.get('total', 330)}")
        
        # Check inventory was updated
        print_info("Verifying inventory was updated...")
        resp = requests.get(f"{API_BASE}/products", headers=headers, timeout=10)
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            for item in items:
                if item.get("product_name") == "Test Milk":
                    print_ok(f"Inventory updated! Stock now: {item.get('stock')}")
                    break
        
        return sale_id
        
    except Exception as e:
        print_error(f"Sales error: {str(e)}")
        return None

# ============================================================================
# TEST 4: ML PREDICTIONS & FORECASTING
# ============================================================================
def test_predictions(auth):
    if not auth:
        print_error("Skipping predictions test - no auth")
        return
    
    print_test("ML Predictions & Forecasting")
    headers = {"Authorization": f"Bearer {auth['token']}"}
    
    try:
        # Get reorder suggestions
        print_info("Fetching reorder suggestions...")
        resp = requests.get(f"{API_BASE}/reorder/suggestions", headers=headers, timeout=10)
        if resp.status_code != 200:
            print_error(f"Reorder suggestions failed: {resp.status_code}")
            return
        
        suggestions = resp.json().get("suggestions", [])
        print_ok(f"Found {len(suggestions)} reorder suggestions")
        
        if suggestions:
            for sugg in suggestions[:3]:
                print_info(f"  • {sugg.get('product_name')}: {sugg.get('reorder_qty')} units suggested")
        
        # Run predictions
        print_info("Running ML predictions...")
        resp = requests.post(f"{API_BASE}/ml/run-predictions", headers=headers, timeout=30)
        if resp.status_code not in [200, 400]:  # 400 = not enough data
            print_error(f"Run predictions failed: {resp.status_code}")
        else:
            result = resp.json()
            if result.get('ready'):
                print_ok("Predictions generated successfully!")
                predictions = result.get("predictions", [])
                print_info(f"  Generated {len(predictions)} predictions")
            else:
                print_info(f"  Not enough data: {result.get('message')}")
        
        # Get forecast accuracy
        print_info("Checking forecast accuracy...")
        resp = requests.get(f"{API_BASE}/forecast/accuracy", headers=headers, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            avg_acc = result.get("avg_accuracy", 0)
            products = len(result.get("data", []))
            print_ok(f"Forecast accuracy tracking {products} products (Avg: {avg_acc}%)")
        else:
            print_info(f"  No accuracy data yet")
        
    except Exception as e:
        print_error(f"Predictions error: {str(e)}")

# ============================================================================
# TEST 5: REORDER WORKFLOW
# ============================================================================
def test_reorder_workflow(auth):
    if not auth:
        print_error("Skipping reorder test - no auth")
        return
    
    print_test("Reorder Workflow (Suggest > Approve > Deliver)")
    headers = {"Authorization": f"Bearer {auth['token']}"}
    
    try:
        # Get reorder orders
        print_info("Fetching reorder orders...")
        resp = requests.get(f"{API_BASE}/reorder/orders", headers=headers, timeout=10)
        if resp.status_code != 200:
            print_error(f"Fetch orders failed: {resp.status_code}")
            return
        
        orders = resp.json().get("orders", [])
        print_ok(f"Found {len(orders)} reorder orders")
        
        if orders:
            order = orders[0]
            print_info(f"  First order: {order.get('product_name')} ({order.get('status')})")
            order_id = order.get("id")
            
            # Try to approve
            if order.get("status") == "pending":
                print_info(f"  Approving order...")
                resp = requests.post(
                    f"{API_BASE}/ml/reorder/{order_id}/approve",
                    headers=headers,
                    timeout=10
                )
                if resp.status_code == 200:
                    print_ok(f"  Order approved!")
                    
                    # Try to mark as delivered
                    print_info(f"  Marking as delivered...")
                    delivery_data = {
                        "received_qty": order.get("reorder_qty", 10)
                    }
                    resp = requests.post(
                        f"{API_BASE}/ml/reorder/{order_id}/delivered",
                        json=delivery_data,
                        headers=headers,
                        timeout=10
                    )
                    if resp.status_code == 200:
                        print_ok(f"  Order delivered!")
                    else:
                        print_error(f"  Delivery failed: {resp.status_code}")
                else:
                    print_error(f"  Approval failed: {resp.status_code}")
        else:
            print_info("  No pending orders to test")
        
    except Exception as e:
        print_error(f"Reorder workflow error: {str(e)}")

# ============================================================================
# TEST 6: DASHBOARD & STATS
# ============================================================================
def test_dashboard(auth):
    if not auth:
        print_error("Skipping dashboard test - no auth")
        return
    
    print_test("Dashboard & Analytics")
    headers = {"Authorization": f"Bearer {auth['token']}"}
    
    try:
        # Get dashboard stats
        print_info("Fetching dashboard stats...")
        resp = requests.get(f"{API_BASE}/dashboard/stats", headers=headers, timeout=10)
        if resp.status_code != 200:
            print_error(f"Dashboard stats failed: {resp.status_code}")
            return
        
        stats = resp.json()
        print_ok(f"Dashboard stats retrieved!")
        print_info(f"  Total Revenue: {stats.get('total_revenue', 0)}")
        print_info(f"  Total Sales: {stats.get('sales_count', 0)}")
        print_info(f"  Active Inventory: {stats.get('active_items', 0)}")
        print_info(f"  Low Stock Alerts: {stats.get('low_stock_count', 0)}")
        
    except Exception as e:
        print_error(f"Dashboard error: {str(e)}")

# ============================================================================
# TEST 7: ALERTS & NOTIFICATIONS
# ============================================================================
def test_alerts(auth):
    if not auth:
        print_error("Skipping alerts test - no auth")
        return
    
    print_test("Alerts & Notifications")
    headers = {"Authorization": f"Bearer {auth['token']}"}
    
    try:
        # Get alerts
        print_info("Fetching alerts...")
        resp = requests.get(f"{API_BASE}/alerts", headers=headers, timeout=10)
        if resp.status_code != 200:
            print_error(f"Fetch alerts failed: {resp.status_code}")
            return
        
        alerts = resp.json().get("alerts", [])
        print_ok(f"Found {len(alerts)} alerts")
        
        for alert in alerts[:3]:
            print_info(f"  • {alert.get('type')}: {alert.get('message')}")
        
    except Exception as e:
        print_error(f"Alerts error: {str(e)}")

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================
def main():
    print(f"\n{BLUE}{'='*60}{END}")
    print(f"{BLUE}FRESHTRACK FULL SYSTEM TEST{END}")
    print(f"{BLUE}{'='*60}{END}")
    print_info(f"API Base URL: {API_BASE}")
    print_info(f"Timestamp: {datetime.now()}")
    
    # Test 1: Auth
    auth = test_auth()
    time.sleep(1)
    
    if auth:
        # Test 2: Inventory
        item_id = test_inventory(auth)
        time.sleep(1)
        
        # Test 3: Sales
        test_sales(auth, item_id)
        time.sleep(1)
        
        # Test 4: Predictions
        test_predictions(auth)
        time.sleep(1)
        
        # Test 5: Reorder
        test_reorder_workflow(auth)
        time.sleep(1)
        
        # Test 6: Dashboard
        test_dashboard(auth)
        time.sleep(1)
        
        # Test 7: Alerts
        test_alerts(auth)
    
    print(f"\n{BLUE}{'='*60}{END}")
    print(f"{BLUE}OK - SYSTEM TEST COMPLETE{END}")
    print(f"{BLUE}{'='*60}{END}\n")

if __name__ == "__main__":
    main()
