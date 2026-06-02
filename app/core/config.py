import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings:
    PROJECT_NAME: str = "readflow-server"

    MONGO_URI: str = os.getenv("MONGO_URI", "")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "")

    ML_SERVER_URL: str = os.getenv("ML_SERVER_URL", "")

    BASE_MODEL: str = "monologg/koelectra-base-v3-discriminator"
    WEIGHTS_DIR: str = os.path.join(BASE_DIR, "weights")
    WEIGHTS_PATH: str = os.path.join(BASE_DIR, "weights", "difficulty_regression_model.pt")

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

settings = Settings()