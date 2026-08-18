import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "linkedin-lead-system-secret-2024")
    SQLALCHEMY_DATABASE_URI = "sqlite:///leads.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
    LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")
    HEADLESS_BROWSER = os.getenv("HEADLESS_BROWSER", "true").lower() == "true"
    SCRAPE_DELAY_MIN = float(os.getenv("SCRAPE_DELAY_MIN", "2.0"))
    SCRAPE_DELAY_MAX = float(os.getenv("SCRAPE_DELAY_MAX", "5.0"))
    EXPORTS_DIR = os.path.join(os.path.dirname(__file__), "exports")
