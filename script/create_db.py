import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import engine, Base
from app.model.acl import APIKey, APIAccess


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        async with session.begin():
            test_key = APIKey(key="test_key")
            session.add(test_key)
            session.add(APIAccess(api_key="test_key", api_name="/restricted-api", access_limit=5))
        await session.commit()


asyncio.run(init_db())
