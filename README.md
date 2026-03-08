# CareerMiner

A full-stack job scraping platform that aggregates job listings from multiple career portals. Built with FastAPI (backend) and Next.js (frontend), featuring automated scraping via configurable cron jobs.

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy (async), PostgreSQL, APScheduler, BeautifulSoup4
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, Redux Toolkit
- **Infrastructure**: Docker, Docker Compose

## Project Structure

```
backend/            FastAPI application
  app/
    config.py       Application settings
    database.py     Async SQLAlchemy setup
    main.py         FastAPI app entry point
    core/           Security, exceptions
    modules/
      auth/         User authentication
      job_site/     Job site management
      career_job/   Scraped job listings
      scrap_job/    Scraping job tracking
      scraper/      Cron job and scraping logic
frontend/           Next.js application
  src/
    app/            App Router pages
    components/     Reusable UI components
    services/       API service layer
    store/          Redux store and slices
    types/          TypeScript interfaces
docker/             Docker configuration files
docker-compose.yml  Multi-container orchestration
```

## Getting Started

### Prerequisites

- Docker and Docker Compose installed

### Running the Application

1. Clone the repository and navigate to the project root:

```bash
cd CareerMiner
```

2. Start all services:

```bash
docker-compose up --build
```

3. Run database migrations:

```bash
docker-compose exec backend alembic upgrade head
```

4. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Initial Setup

1. Register a new account at http://localhost:3000/register
2. Log in with your credentials
3. Add job sites to scrape from the Job Sites page
4. The scraper cron job runs every minute and processes active job sites

## Features

### Backend
- JWT-based authentication (register, login, forgot password)
- CRUD operations for job sites with configurable scraping intervals
- Automated background scraping with APScheduler
- Duplicate job detection
- Scraping job tracking with status management (pending, in_progress, completed, error, terminated)
- Max execution time enforcement for scraping jobs
- Dashboard analytics API

### Frontend
- Dark/Light theme toggle with blue accent theme
- Responsive sidebar navigation
- Dashboard with scraping analytics and job portal overview cards
- Job site management with inline add/edit forms
- Filterable job listings with search, site filter, and category filter
- Job detail modal view
- User profile with password management

## Environment Variables

### Backend

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | postgresql+asyncpg://postgres:postgres@db:5432/careerminer | Database connection string |
| SECRET_KEY | super-secret-key-change-in-production | JWT signing key |
| ALGORITHM | HS256 | JWT algorithm |
| ACCESS_TOKEN_EXPIRE_MINUTES | 1440 | Token expiry (24 hours) |
| MAX_SCRAP_EXECUTION_TIME_MINUTES | 30 | Max scraping job runtime |

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| NEXT_PUBLIC_API_URL | http://localhost:8000/api | Backend API base URL |

## Database Migrations

Generate a new migration after model changes:

```bash
docker-compose exec backend alembic revision --autogenerate -m "description"
```

Apply migrations:

```bash
docker-compose exec backend alembic upgrade head
```

## API Documentation

Once the backend is running, visit http://localhost:8000/docs for the interactive Swagger UI documentation.
