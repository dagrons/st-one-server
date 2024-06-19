import os
from pathlib import Path

from pydantic import BaseModel


class Setting(BaseModel):
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str= os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    EMBEDDING_PATH: str = str(Path.home() / 'emb' / 'm3e-base')
    MODEL_DIR: str = str(Path.home() / 'llm')


setting = Setting()

