from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    app_name: str = "FastAPI OpenAI Assistant"
    environment: str = os.getenv("ENVIRONMENT", "development")
    

settings = Settings()