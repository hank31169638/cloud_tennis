# Zeabur 部署指南

本專案已完成 Zeabur 部署的基本配置。請按照以下步驟進行部署。

## 📋 前置準備

1. **GitHub 倉庫** ✅
   - 已推送到: https://github.com/Winnie-0917/Table-tennis-AI

2. **Zeabur 帳號**
   - 註冊: https://zeabur.com
   - 連結你的 GitHub 帳號

3. **Gemini API Key** (必填)
   - 取得位置: https://makersuite.google.com/app/apikey
   - 用於 AI 失誤分析功能

## 🚀 部署步驟

### 1. 在 Zeabur 創建新專案

1. 登入 Zeabur Dashboard
2. 點擊「Create Project」
3. 選擇你的 GitHub 倉庫: `Winnie-0917/Table-tennis-AI`

### 2. 部署後端服務 (Backend)

1. **選擇服務**
   - Service Type: Git Repository
   - Branch: `main`
   - Root Directory: `backend`

2. **設定環境變數**
   點擊「Environment Variables」，添加：
   ```
   GEMINI_API_KEY=你的_Gemini_API_Key
   PORT=5000
   FLASK_ENV=production
   DEBUG=False
   ```

3. **部署設定**
   - Zeabur 會自動偵測 `Dockerfile`
   - 等待構建完成（約 2-5 分鐘）

4. **取得後端 URL**
   - 部署完成後，點擊「Networking」
   - 複製服務的公開 URL，格式類似：
     ```
     https://your-backend-service.zeabur.app
     ```

### 3. 部署前端服務 (Frontend)

1. **選擇服務**
   - Service Type: Git Repository
   - Branch: `main`
   - Root Directory: `frontend`

2. **設定環境變數**
   點擊「Environment Variables」，添加：
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-service.zeabur.app
   ```
   ⚠️ **重要**: 將上面的 URL 替換成你實際的後端服務 URL

3. **部署設定**
   - Zeabur 會自動偵測 `Dockerfile`
   - 等待構建完成（約 3-7 分鐘）

4. **啟用公開域名**
   - 點擊「Networking」
   - 點擊「Generate Domain」或綁定自訂域名

### 4. 更新後端 CORS 設定

部署完成後，需要更新後端允許的前端域名：

1. 在 Zeabur Backend 服務中，更新環境變數：
   ```
   ALLOWED_ORIGINS=https://your-frontend-service.zeabur.app
   ```

2. 或者在 `backend/app.py` 中直接修改 CORS 設定後重新部署

## ✅ 驗證部署

### 檢查後端
訪問: `https://your-backend-service.zeabur.app/health`
應該返回: `{"status":"ok"}`

### 檢查前端
訪問: `https://your-frontend-service.zeabur.app`
應該看到完整的桌球 AI 訓練系統

### 測試功能
1. **世界排名** - 應該能正常載入排名數據
2. **球員照片** - 測試 7 種照片回退機制
3. **AI 失誤分析** - 上傳測試影片（需要 Gemini API Key）
4. **訓練模型** - 測試模型訓練功能

## ⚠️ 重要注意事項

### 1. 檔案上傳限制
Zeabur 容器重啟時，上傳的檔案會消失。如需持久化：
- 考慮使用物件儲存服務（AWS S3, Cloudflare R2）
- 或使用 Zeabur 的 Volume 功能

### 2. API Key 安全
- ✅ 已將 `GEMINI_API_KEY` 設為環境變數
- ❌ 不要直接寫在程式碼中
- ❌ 不要提交 `.env` 到 Git

### 3. CORS 設定
確保後端允許前端域名：
```python
# backend/app.py
CORS(app, origins=['https://your-frontend-service.zeabur.app'])
```

### 4. 環境變數優先級
```
Zeabur 環境變數 > .env 檔案 > 程式碼預設值
```

## 🔧 常見問題

### Q: 前端無法連接後端
**A**: 檢查 `NEXT_PUBLIC_API_URL` 是否正確設定為後端的完整 URL（包含 https://）

### Q: Gemini AI 分析失敗
**A**: 
1. 檢查 `GEMINI_API_KEY` 是否正確
2. 確認 API Key 配額是否用完
3. 查看後端日誌: Zeabur Dashboard → 你的服務 → Logs

### Q: 照片無法載入
**A**: 
1. 這是正常的，因為 World Table Tennis 的照片 URL 格式不一致
2. 系統會自動嘗試 7 種不同格式
3. 最後會顯示預設的 SVG 頭像

### Q: 如何查看日誌
**A**: Zeabur Dashboard → 選擇你的服務 → 點擊「Logs」

### Q: 如何重新部署
**A**: 
1. 推送新的 commit 到 GitHub `main` 分支
2. Zeabur 會自動觸發重新部署
3. 或在 Zeabur Dashboard 手動點擊「Redeploy」

## 📊 服務架構

```
┌─────────────────┐
│   GitHub Repo   │
│  (main branch)  │
└────────┬────────┘
         │
         ├─────────────┬─────────────┐
         ▼             ▼             ▼
    ┌────────┐   ┌─────────┐   ┌─────────┐
    │Backend │   │Frontend │   │ Zeabur  │
    │(Flask) │   │(Next.js)│   │ (平台)   │
    └────┬───┘   └────┬────┘   └─────────┘
         │            │
         │◄───────────┤ API Calls
         │            │
         ├────────────┤ CORS
         │            │
         ▼            ▼
    使用者訪問前端網頁
```

## 🎯 部署後優化建議

1. **啟用 CDN**
   - Zeabur 預設提供 CDN
   - 可進一步使用 Cloudflare

2. **監控與日誌**
   - 定期檢查 Zeabur Logs
   - 設定錯誤通知

3. **資料庫**
   - 目前使用本地 JSON 檔案
   - 可考慮遷移到 PostgreSQL 或 MongoDB

4. **快取機制**
   - 排名數據已有 1 小時快取
   - 可增加 Redis 提升效能

## 📚 相關連結

- **Zeabur 官方文檔**: https://zeabur.com/docs
- **Next.js 環境變數**: https://nextjs.org/docs/app/building-your-application/configuring/environment-variables
- **Flask CORS**: https://flask-cors.readthedocs.io/
- **Gemini API**: https://ai.google.dev/gemini-api/docs

## 💡 技術支援

遇到問題？
1. 查看 Zeabur 服務日誌
2. 檢查環境變數設定
3. 確認 GitHub Actions（如果有）
4. 查閱本專案的 `README.MD`

---

**最後更新**: 2025-11-13
**版本**: v1.0.0
**狀態**: ✅ 已準備部署
