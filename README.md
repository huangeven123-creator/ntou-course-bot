# 海大選課名額監控通知機器人 🤖

這是一個基於 Python FastAPI 與 Playwright 瀏覽器自動化開發的 LINE 搶課名額監控機器人。它會定時（每 30 分鐘）自動查詢海大課程查詢系統，並在監控的課程名額釋出（由額滿轉為有缺額）時，向訂閱的用戶發送即時推播通知。

---

## 🚀 部署至 Render 步驟說明

本專案需要執行無頭瀏覽器（Playwright Chromium），因此在 Render 部署時必須使用 **Docker 容器**。

### 1. 準備 Firebase 與 LINE 憑證
* **LINE Developers 後台**：
  * 取得 `Channel Access Token` 與 `Channel Secret`。
  * 設定 Webhook URL：`https://您的服務網址.onrender.com/webhook`。
* **Firebase 控制台**：
  * 建立一個新專案並啟用 **Firestore Database**。
  * 進入「專案設定」->「服務帳戶」-> 點擊「產生新的私鑰」，下載 JSON 金鑰檔案。

### 2. 在 Render 上建立服務
1. 登入 Render 控制台，點擊 **New** -> **Web Service**。
2. 連結您的 GitHub 專案儲存庫。
3. **Runtime** 請選擇 **Docker**（Render 會自動偵測目錄下的 `Dockerfile` 進行編譯與安裝，包含 Chromium 核心）。
4. 點擊 **Advanced** 開始設定環境變數：

| 環境變數名稱 | 範例值 / 說明 |
| :--- | :--- |
| `LINE_CHANNEL_ACCESS_TOKEN` | 您的 LINE 密鑰 (Channel Access Token) |
| `LINE_CHANNEL_SECRET` | 您的 LINE 頻道金鑰 (Channel Secret) |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | 將下載下來的 Firebase 金鑰 JSON 檔案的**所有內容複製並壓縮成一行文字**貼上。 |
| `CRON_SECRET` | 自訂一個隨機字串（例如 `my_super_secret_123`），用來防護定時排程 API。 |
| `PORT` | `8000` |

5. 點擊 **Deploy Web Service** 開始部署。

---

## ⏰ 設定定時排程 (Cron Job)

為了讓機器人每 30 分鐘自動檢查一次名額，我們使用免費的外部定時服務（如 [Cron-Job.org](https://cron-job.org/)）來呼叫機器人的排程 API。

1. 註冊並登入 **Cron-Job.org**。
2. 點擊 **Create Cronjob**。
3. **Title** 自訂（例如 `NTOU Course Monitor`）。
4. **Address (URL)** 填寫：
   `https://您的服務網址.onrender.com/cron/check-courses?secret=您的CRON_SECRET`
   *(請將 `您的CRON_SECRET` 替換為剛才在 Render 設定的隨機密鑰字串，例如 `my_super_secret_123`)*
5. **Schedule**：選擇 **Every 30 minutes**（每 30 分鐘一次）。
6. 點擊 **Create** 即可完成！

---

## 📱 LINE 使用說明
* 加入好友後，機器人會發送歡迎引導語。
* **新增監控**：直接輸入要監控的**課程課號**（4 到 12 碼英數混合，例如 `B33035PR`），並在彈出的確認選單中點選「開始監控名額」。
* **查看與取消監控**：輸入「**清單**」或「**查詢**」，即可查看您目前監控中的所有課號，並能點擊下方快捷按鈕一鍵取消監控。
