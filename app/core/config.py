import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_key_123")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:xm6idbip@localhost:5432/text_card")


settings = Settings()
