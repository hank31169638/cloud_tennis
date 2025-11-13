# ==============================================
# 統一部署 Dockerfile - 使用 Node.js 為基礎
# ==============================================

# 使用 Node.js 作為基礎鏡像（已包含 Node 和 npm）
FROM node:20-slim

# 安裝 Python 和系統依賴
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ===== 安裝後端依賴 =====
COPY backend/requirements.txt /app/backend/
RUN pip3 install --no-cache-dir --break-system-packages -r /app/backend/requirements.txt

# ===== 安裝前端依賴並構建 =====
COPY frontend/package*.json /app/frontend/
WORKDIR /app/frontend
RUN npm ci

COPY frontend/ /app/frontend/
ENV NEXT_TELEMETRY_DISABLED=1
# 在 Zeabur 上，前後端都在同一容器，前端可以通過 /api 代理訪問後端
ENV NEXT_PUBLIC_API_URL=/api
RUN npm run build

# 複製 standalone 輸出和靜態資源
RUN cp -r /app/frontend/.next/standalone/. /app/frontend-dist/ && \
    cp -r /app/frontend/.next/static /app/frontend-dist/.next/static && \
    cp -r /app/frontend/public /app/frontend-dist/public

# ===== 複製後端代碼 =====
WORKDIR /app
COPY backend/ /app/backend/

# ===== 創建啟動腳本 =====
RUN echo '#!/bin/bash\n\
set -e\n\
echo "🚀 Starting Table Tennis AI..."\n\
\n\
# 啟動後端\n\
echo "📡 Starting Backend on port 5000..."\n\
cd /app/backend\n\
PORT=5000 python3 app.py &\n\
BACKEND_PID=$!\n\
\n\
# 等待後端啟動\n\
sleep 5\n\
\n\
# 啟動前端\n\
echo "🌐 Starting Frontend on port ${PORT:-8080}..."\n\
cd /app/frontend-dist\n\
export NEXT_PUBLIC_API_URL=http://localhost:5000\n\
PORT=${PORT:-8080} node server.js &\n\
FRONTEND_PID=$!\n\
\n\
echo "✅ All services started!"\n\
echo "   - Backend: http://localhost:5000"\n\
echo "   - Frontend: http://localhost:${PORT:-8080}"\n\
\n\
# 保持運行\n\
wait -n $BACKEND_PID $FRONTEND_PID\n\
EXIT_CODE=$?\n\
\n\
# 清理\n\
echo "🛑 Shutting down..."\n\
kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true\n\
exit $EXIT_CODE\n\
' > /app/start.sh && chmod +x /app/start.sh

EXPOSE 8080

CMD ["/bin/bash", "/app/start.sh"]


