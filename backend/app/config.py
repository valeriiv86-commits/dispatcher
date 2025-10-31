import os

class Settings:
    PROJECT_NAME: str = "Dispatcher"
    ENV: str = os.getenv("ENV", "dev")
    TELEGRAM_TOKEN: str | None = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID: str | None = os.getenv("TELEGRAM_CHAT_ID")

settings = Settings()
