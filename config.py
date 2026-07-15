# config.py
import os
DB_CONFIG = {
    "HOST": os.getenv("DB_HOST", "localhost"),
    "USER": os.getenv("DB_USER", "root"),
    "PASSWORD": os.getenv("DB_PASSWORD", "root"),
    "NAME": os.getenv("DB_NAME","la_masia"),
}
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")