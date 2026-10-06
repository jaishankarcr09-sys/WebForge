FROM node:22-bookworm-slim

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 python3-venv bash ca-certificates \
  && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY frontend/package.json ./frontend/package.json
RUN cd frontend && npm install

COPY frontend ./frontend
RUN cd frontend && npm run build

COPY backend ./backend
COPY start-all.sh ./start-all.sh
RUN chmod +x ./start-all.sh && playwright install --with-deps chromium

ENV NODE_ENV=production
ENV BACKEND_URL=http://127.0.0.1:8000
EXPOSE 3000

CMD ["/bin/bash", "/app/start-all.sh"]
