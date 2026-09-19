import threading
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

_default_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

_thread_local = threading.local()


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Return the session maker for the current thread (API vs workflow worker)."""
    maker = getattr(_thread_local, "session_maker", None)
    if maker is not None:
        return maker
    return _default_session_maker


class _AsyncSessionMakerProxy:
    """Route ``async_session()`` to the current thread's session maker when set."""

    def __call__(self, *args, **kwargs):
        return get_session_maker()(*args, **kwargs)

    def __getattr__(self, item):
        return getattr(get_session_maker(), item)


async_session = _AsyncSessionMakerProxy()

Base = declarative_base()


def init_thread_local_db() -> None:
    """Create an isolated async engine/session maker for a background worker thread."""
    if getattr(_thread_local, "session_maker", None) is not None:
        return
    thread_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )
    _thread_local.engine = thread_engine
    _thread_local.session_maker = async_sessionmaker(
        thread_engine, class_=AsyncSession, expire_on_commit=False
    )


async def dispose_thread_local_db() -> None:
    """Dispose the worker-thread engine created by ``init_thread_local_db``."""
    thread_engine = getattr(_thread_local, "engine", None)
    if thread_engine is not None:
        await thread_engine.dispose()
        del _thread_local.engine
        del _thread_local.session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session and ensure it is closed after use."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
