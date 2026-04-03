from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import settings

import ssl as _ssl

_connect_args = {}
if settings.database_url.startswith("postgresql") and "ssl=require" in settings.database_url:
    _ctx = _ssl.create_default_context()
    _ctx.check_hostname = False
    _ctx.verify_mode = _ssl.CERT_NONE
    _connect_args = {"ssl": _ctx}

engine = create_async_engine(
    settings.database_url.replace("?ssl=require", "").replace("&ssl=require", ""),
    echo=False,
    connect_args=_connect_args,
    pool_pre_ping=True,
    pool_recycle=1800,
)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    from db import models  # noqa — импорт чтобы модели зарегистрировались
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
