import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.database import get_db
from app.model.api_key import APIKey, APIAccess

api_key_router = APIRouter()


@api_key_router.post("/generate-api-key")
async def generate_api_key(db: AsyncSession = Depends(get_db)):
    key = str(uuid.uuid4())
    api_key = APIKey(key=key)
    db.add(api_key)
    await db.commit()
    return {"api_key": key}


@api_key_router.post("/set-api-access")
async def set_api_access(key: str, api_name: str, access_limit: int, db: AsyncSession = Depends(get_db)):
    api_key = await db.execute(select(APIKey).where(APIKey.key == key))
    api_key = api_key.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_access = await db.execute(select(APIAccess).where(APIAccess.api_key == key, APIAccess.api_name == api_name))
    api_access = api_access.scalar_one_or_none()
    if not api_access:
        api_access = APIAccess(api_key=key, api_name=api_name, access_limit=access_limit)
        db.add(api_access)
    else:
        api_access.access_limit = access_limit
        api_access.access_count = 0  # reset the count when setting a new limit

    await db.commit()
    return {"message": "Access limit set successfully"}


@api_key_router.get("/get-api-key")
async def get_api_key(key: str, db: AsyncSession = Depends(get_db)):
    cache_key = f"api_key_{key}"
    api_key = await cache.get(cache_key)
    if not api_key:
        api_key = await db.execute(select(APIKey).where(APIKey.key == key))
        api_key = api_key.scalar_one_or_none()
        if api_key:
            await cache.set(cache_key, api_key)
    if not api_key:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key


@api_key_router.get("/check-api-access")
async def check_api_access(api_key: str, api_name: str, db: AsyncSession = Depends(get_db)):
    api_access = await db.execute(
        select(APIAccess).where(APIAccess.api_key == api_key, APIAccess.api_name == api_name))
    api_access = api_access.scalar_one_or_none()
    if not api_access:
        raise HTTPException(status_code=403, detail="API access not allowed")

    if api_access.access_count >= api_access.access_limit:
        raise HTTPException(status_code=403, detail="API quota exceeded")

    api_access.access_count += 1
    await db.commit()
