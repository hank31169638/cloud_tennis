# 部署 Table Tennis AI 到 Zeabur 指南

這份指南將協助你將前後端應用程式部署到 [Zeabur](https://zeabur.com) 平台。

## 專案結構設定

我已經為你建立了 `zeabur.toml` 設定檔，這會告訴 Zeabur 如何識別和啟動你的服務：
- **frontend**: Next.js 應用程式
- **backend**: Flask 應用程式 (使用 Gunicorn + Eventlet 運行以支援 Socket.IO)

同時，我也微調了 `backend/app.py` 以支援透過環境變數 `ASYNC_MODE` 切換運行模式，確保在生產環境下 WebSocket 能正常運作。

## 部署步驟

### 1. 連接 GitHub

1. 登入 [Zeabur Dashboard](https://dash.zeabur.com)。
2. 建立一個新專案 (Project)。
3. 點擊 **Deploy New Service** -> **GitHub**。
4. 選擇你的儲存庫 (Repo)。

Zeabur 會自動讀取 `zeabur.toml` 並建立兩個服務：`frontend` 和 `backend`。

### 2. 設定環境變數 (Environment Variables)

在服務部署啟動之前（或第一次失敗後），你需要設定必要的環境變數。

#### Backend 服務
進入 Backend 服務的 **Variables** 頁籤，新增以下變數：

| 變數名稱 | 範例值 | 說明 |
|----------|--------|------|
| `GEMINI_API_KEY` | `Your-Gemini-Key` | **(必要)** Google Gemini API Key |
| `ALLOWED_ORIGINS` | `https://your-frontend.zeabur.app` | **(建議)** 設定前端網域名稱，避免 CORS 錯誤。初期測試可設為 `*`，但生產環境建議指定。 |
| `SECRET_KEY` | `random_secret_string` | Flask Session 加密金鑰 |

> **注意**：`ASYNC_MODE=eventlet` 已經在啟動指令中自動設定，不需要手動添加。

#### Frontend 服務
進入 Frontend 服務的 **Variables** 頁籤，新增以下變數：

| 變數名稱 | 範例值 | 說明 |
|----------|--------|------|
| `NEXT_PUBLIC_API_URL` | `https://your-backend.zeabur.app` | **(必要)** 後端服務的網址 |

**重要流程**：
1. 先讓 Backend 部署成功，並在 Zeabur **Domain** 頁籤綁定或複製後端的公開網址 (例如 `xxx-backend.zeabur.app`)。
2. 將此網址填入 Frontend 的 `NEXT_PUBLIC_API_URL` 變數中。
3. **Redeploy** (重新部署) Frontend 服務，確保環境變數生效 (因為 Next.js 在 build time 會將 `NEXT_PUBLIC_` 變數打包進程式碼)。

### 3. 驗證部署

1. 開啟 Frontend 的公開網址。
2. 檢查是否能正常獲取排名資料 (這表示 API 連線正常)。
3. 檢查即時分析或 WebSocket 功能是否連線成功。

## 常見問題

- **WebSocket 連線失敗 / 400 Bad Request**:
  - 確保 Backend 的 `ALLOWED_ORIGINS` 包含前端的網址 (不要有結尾斜線)。
  - 確保啟動指令使用的是 `gunicorn -k eventlet ...` (已在 `zeabur.toml` 設定)。

- **前端顯示 "無法連接到後端"**:
  - 檢查 `NEXT_PUBLIC_API_URL` 是否正確且不包含結尾斜線 (例如 `https://api.example.com`)。
  - 修改 `NEXT_PUBLIC_` 變數後，務必**重新部署 (Redeploy)** Frontend，而不僅僅是 Restart。
