from pathlib import Path
from typing import Dict
from jinja2 import Template
from spec_engine import AppSpec

class DevOpsGenerator:
    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self):
        return {
            "docker_compose": Template("""version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
      POSTGRES_DB: app_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://app:${DB_PASSWORD:-changeme}@postgres:5432/app_db
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY:-generate-a-strong-secret}
      - ENVIRONMENT=production
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./backend/uploads:/app/uploads
    restart: unless-stopped

  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A tasks.celery_app worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgresql://app:${DB_PASSWORD:-changeme}@postgres:5432/app_db
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY:-generate-a-strong-secret}
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  celery_beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A tasks.celery_app beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql://app:${DB_PASSWORD:-changeme}@postgres:5432/app_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
"""),
            "backend_dockerfile": Template("""FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "python init_db.py && uvicorn main:app --host 0.0.0.0 --port 8000"]
"""),
            "frontend_dockerfile": Template("""FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
"""),
            "nginx_conf": Template("""server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws/ {
        proxy_pass http://backend:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
"""),
            "github_ci": Template("""name: CI/CD Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test-and-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Backend Dependencies
        run: |
          cd backend
          pip install -r requirements.txt

      - name: Run Pytest
        run: |
          cd backend
          pytest

      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Build Frontend
        run: |
          cd frontend
          npm ci
          npm run build
"""),
        }

    def generate(self, spec: AppSpec) -> Dict[str, str]:
        files = {}
        files["docker-compose.yml"] = self.templates["docker_compose"].render()
        files["backend/Dockerfile"] = self.templates["backend_dockerfile"].render()
        files["frontend/Dockerfile"] = self.templates["frontend_dockerfile"].render()
        files["frontend/nginx.conf"] = self.templates["nginx_conf"].render()
        files[".github/workflows/deploy.yml"] = self.templates["github_ci"].render()
        return files

    def write(self, spec: AppSpec, base_path: str) -> str:
        files = self.generate(spec)
        output = Path(base_path)

        for filename, content in files.items():
            target = output / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content.strip(), encoding="utf-8")

        return str(output)
