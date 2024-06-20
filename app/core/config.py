import importlib
import os
import platform
from pathlib import Path

from pydantic import BaseModel


def get_device():
    if platform.system() in ['Windows', 'Linux']:
        device = "cpu"
        try:
            pynvml = importlib.import_module('pynvml')
            h = pynvml.nvmlDeviceGetHandleByIndex(0)
            info = pynvml.nvmlDeviceGetMemoryInfo(h)
            free_mem_in_GB = info.free // 1024 ** 2
            if free_mem_in_GB >= 8:
                device = "cuda"
        except Exception:
            pass
    elif platform.system() == 'Darwin':
        device = "mps"
    return device


class Setting(BaseModel):
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    EMBEDDING_PATH: str = os.getenv('EMBEDDING_PATH') or str(Path.home() / 'emb' / 'm3e-base')
    MODEL_DIR: str = os.getenv('MODEL_DIR') or str(Path.home() / 'llm')
    DEVICE: str = os.getenv('DEVICE') or get_device()


setting = Setting()
