import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import engine, Base
from app.model.api_key import APIKey, APIAccess
from app.model.user import User


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        async with session.begin():
            test_key = APIKey(key="test_key")
            session.add(test_key)
            session.add(APIAccess(api_key="test_key", api_name="/restricted-api", access_limit=5))
            user = User(username='heyuehui', email='heyuehuii@126.com', full_name='heyuehui', hashed_password='123456')
            session.add(user)
        await session.commit()


asyncio.run(init_db())
