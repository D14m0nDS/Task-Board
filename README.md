# Task Board

Real-time developer task management: a Kanban board that links tasks to GitHub
branches, commits and pull requests.

## Structure

```text
backend/    FastAPI + PostgreSQL API
frontend/   React + TypeScript web client
android/    Kotlin companion app
docs/       Project documentation
```

## Running the stack

Requirements: Docker Desktop, Node.js.

```bash
cp .env.example .env     # then edit JWT_SECRET
docker compose up --build
```

With the default `.env`:

- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

Postgres and the backend run in Docker. The frontend is run locally
(`cd frontend && npm run dev`) so hot reload stays fast.

If ports 5432 or 8000 are already taken on your machine, change
`POSTGRES_PORT` / `BACKEND_PORT` in `.env`. Only the published host ports
change; nothing inside the containers is affected.

## Backend tests

```bash
docker compose exec backend pytest
```
