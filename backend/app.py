import os
# ── Fix PyTorch DLL loading on Windows (must be set before torch import) ──
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

from flask import Flask, jsonify, request
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

app = Flask(__name__)
app.config["MONGO_URI"]                = os.getenv("MONGO_URI", "mongodb://localhost:27017/freshtrack")
app.config["MONGO_DB_NAME"]           = os.getenv("MONGO_DB_NAME", "freshtrack")
app.config["JWT_SECRET_KEY"]          = os.getenv("JWT_SECRET_KEY", "dev-only-change-me")
app.config["JWT_ALGORITHM"]           = "HS256"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)
app.config["CORS_ORIGINS"]            = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174",
    ).split(",")
    if origin.strip()
]

if os.getenv("FLASK_ENV", "production") == "production" and not os.getenv("JWT_SECRET_KEY"):
    print("WARNING: JWT_SECRET_KEY is not set. Using a development fallback secret.")

# ✅ ADD CORS HEADERS TO ALL RESPONSES
@app.after_request
def after_request(response):
    origin = request.headers.get("Origin")
    if origin in app.config["CORS_ORIGINS"]:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Vary'] = 'Origin'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return response

from database import init_db
init_db(app)

# ✅ INITIALIZE CACHING & RATE LIMITING
from caching import init_cache, init_rate_limiter, get_rate_limiter
from jwt_helper import decode_token

# Try to initialize Redis if available
try:
    import redis
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0,
        decode_responses=True
    )
    redis_client.ping()  # Test connection
    init_cache(redis_client)
except Exception:
    # Fallback to in-memory cache
    init_cache(None)

init_rate_limiter(requests_per_minute=int(os.getenv("RATE_LIMIT_RPM", 100)))

# ✅ UNIFIED REQUEST HANDLER
@app.before_request
def pre_request():
    """Handle preflight and rate limiting."""
    # Always handle OPTIONS (preflight) requests
    if request.method == 'OPTIONS':
        return '', 204
    
    # Skip rate limit for auth paths
    if request.path.startswith('/api/auth') or request.path == '/':
        return None
    
    # Get user ID from token or IP
    user_id = None
    try:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            decoded = decode_token(token)
            if decoded:
                user_id = decoded.get('sub')
    except:
        pass
    
    # Use user ID or IP address for rate limiting
    identifier = user_id or request.remote_addr
    limiter = get_rate_limiter()
    
    if not limiter.is_allowed(identifier):
        retry_after = limiter.get_retry_after(identifier)
        return jsonify({"error": "Rate limit exceeded"}), 429, {
            "Retry-After": retry_after
        }

from auth import auth_bp
from routes.ml_routes import ml_bp
from routes.dashboard_routes import dashboard_bp
from routes.alert_routes import alerts_bp
from routes.staff_routes import staff_bp
app.register_blueprint(staff_bp, url_prefix="/api")
app.register_blueprint(alerts_bp, url_prefix="/api")
from routes.onboarding_routes import onboarding_bp
from routes.pos_routes import pos_bp
from routes.seasonal_routes import seasonal_bp
from routes.ocr_routes import ocr_bp
from routes.event_routes import events_bp
app.register_blueprint(ocr_bp, url_prefix="/api")
app.register_blueprint(events_bp, url_prefix="/api")
app.register_blueprint(seasonal_bp, url_prefix="/api")
app.register_blueprint(pos_bp, url_prefix="/api")
app.register_blueprint(onboarding_bp, url_prefix="/api")
app.register_blueprint(auth_bp,      url_prefix="/api/auth")
app.register_blueprint(ml_bp,        url_prefix="/api")
app.register_blueprint(dashboard_bp, url_prefix="/api")

if __name__ == "__main__":
    # Security: only enable debug in development
    debug_mode = os.getenv("FLASK_ENV", "production") == "development"
    app.run(debug=debug_mode, port=5000)
