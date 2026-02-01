from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    app_name: str = "FastAPI OpenAI Assistant"
    environment: str = os.getenv("ENVIRONMENT", "development")
    env: str = os.getenv("ENV", "dev")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    

settings = Settings()