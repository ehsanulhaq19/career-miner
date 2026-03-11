from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.exceptions import AppException, app_exception_handler
from app.modules.auth.api import router as auth_router
from app.modules.career_job.api import router as career_job_router
from app.modules.career_job.api import dashboard_router
from app.modules.job_site.api import router as job_site_router
from app.modules.scrap_job.api import router as scrap_job_router
from app.modules.llm.api import router as llm_router
from app.modules.scraper.cron import start_scheduler, stop_scheduler
from app.modules.websocket.api import router as websocket_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppException, app_exception_handler)

app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(job_site_router, prefix="/api/job-sites", tags=["Job Sites"])
app.include_router(career_job_router, prefix="/api/career-jobs", tags=["Career Jobs"])
app.include_router(scrap_job_router, prefix="/api/scrap-jobs", tags=["Scrap Jobs"])
app.include_router(websocket_router, tags=["WebSocket"])
app.include_router(llm_router, prefix="/api/llm", tags=["LLM"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
