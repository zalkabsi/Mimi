# Single-container Mimi: FastAPI + built React UI. Keys come from env vars at
# run time (NEBIUS_API_KEY, NEBIUS_PROJECT_ID, TAVILY_API_KEY, MIMI_JUDGE_KEY);
# never bake them into the image. PoC code never runs here, only in Sandboxes.
FROM node:20-slim AS ui
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_BASE=""
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/ /app/backend/
RUN pip install --no-cache-dir -e /app/backend
COPY --from=ui /ui/dist /app/ui
ENV MIMI_FRONTEND_DIST=/app/ui MIMI_DB_PATH=/data/mimi.db
VOLUME /data
EXPOSE 8000
WORKDIR /app/backend
CMD ["uvicorn", "mimi.api:app", "--host", "0.0.0.0", "--port", "8000"]
