import os

SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-key")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
SCREENSHOT_INTERVAL = float(os.environ.get("SCREENSHOT_INTERVAL", "0.5"))
MAX_SCREENSHOT_WIDTH = int(os.environ.get("MAX_SCREENSHOT_WIDTH", "1280"))
MAX_SCREENSHOT_HEIGHT = int(os.environ.get("MAX_SCREENSHOT_HEIGHT", "720"))
ALLOW_REMOTE = os.environ.get("ALLOW_REMOTE", "*").split(",")
