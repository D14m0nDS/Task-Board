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

If ports 5432 or 8000 are already taken on your machine, change
`POSTGRES_PORT` / `BACKEND_PORT` in `.env`. Only the published host ports
change; nothing inside the containers is affected.

Apply database migrations:

```bash
docker compose exec backend alembic upgrade head
```

## Frontend

Postgres and the backend run in Docker; the frontend runs locally so hot
reload stays fast.

```bash
cd frontend
cp .env.example .env.local     # point VITE_API_URL at your BACKEND_PORT
npm install
npm run dev
```

Available at http://localhost:5173. The URL must be listed in `CORS_ORIGINS`
in the root `.env`.

## Tests

```bash
docker compose exec backend pytest                    # backend
cd frontend && npm test && npx tsc -b && npm run lint  # frontend
```
