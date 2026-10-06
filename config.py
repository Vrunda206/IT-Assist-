import os
from dotenv import load_dotenv

load_dotenv()  # reads the .env file


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "it-assist-demo-secret")
    DB = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", "Root@123"),
        "database": os.getenv("DB_NAME", "it_assist"),
    }
    # Demo login (academic project only)
    ADMIN_USER = "admin"
    ADMIN_PASS = "admin123"
    # Analytics: expected daily usage hours per asset
    EXPECTED_HOURS = 8
