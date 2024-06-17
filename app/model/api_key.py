from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey

from app.core.database import Base


class APIKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=func.now())


class APIAccess(Base):
    __tablename__ = "api_access"
    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String, ForeignKey("api_keys.key"), nullable=False)
    api_name = Column(String, index=True, nullable=False)
    access_limit = Column(Integer, nullable=False)
    access_count = Column(Integer, default=0)
