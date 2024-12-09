from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

class Settings:
    # APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    # APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY")
    MODEL_TEMPERATURE: float = float(os.getenv("MODEL_TEMPERATURE"))
    # MODEL: str = os.getenv("MODEL")
    # DATABASE_URL : str = os.getenv("DATABASE_URL")

settings = Settings()
