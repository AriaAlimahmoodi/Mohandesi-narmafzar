
# Digital Library — Sprint 1 Backend

This folder contains the backend foundation for Sprint 1, including authentication, user roles, resource registration and listing, PDF/EPUB validation, SHA-256 duplicate detection, basic access control, Django Admin, OpenAPI documentation, database migrations, and tests.

## Requirements

- Python 3.12 or newer
- PostgreSQL 19 (or a compatible supported version)
- Git

## Setup on Windows (PowerShell)

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and configure the PostgreSQL connection settings.

Create a PostgreSQL database named `digital_library` and configure its owner and credentials to match `.env`.

Then run:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
## Optional: Docker PostgreSQL

The project uses PostgreSQL through Docker Compose.

Configure `.env` with the following settings:

```env
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5433
POSTGRES_DB=digital_library
POSTGRES_USER=library
POSTGRES_PASSWORD=library
```

Start the database container:

```powershell
docker compose up -d db
```

Apply database migrations:

```powershell
python manage.py migrate
```

To check the database container:

```powershell
docker compose ps
```

## Tests

```powershell
python -m pytest -v
```

## API Documentation

- Swagger UI: http://127.0.0.1:8000/api/docs/
- OpenAPI schema: http://127.0.0.1:8000/api/schema/

## Django Admin

http://127.0.0.1:8000/admin/
