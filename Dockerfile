# ==============================================
# 統一部署 Dockerfile - 前後端一起運行
# ==============================================

FROM python:3.11-slim

# 安裝 Node.js 和系統依賴
RUN apt-get update && apt-get install -y \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ===== 安裝後端依賴 =====
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# ===== 安裝前端依賴並構建 =====
COPY frontend/package*.json /app/frontend/
WORKDIR /app/frontend
RUN npm ci

COPY frontend/ /app/frontend/
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

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
python app.py &\n\
BACKEND_PID=$!\n\
\n\
# 等待後端啟動\n\
sleep 5\n\
\n\
# 啟動前端\n\
echo "🌐 Starting Frontend on port ${PORT:-8080}..."\n\
cd /app/frontend\n\
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


