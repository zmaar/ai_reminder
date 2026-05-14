# WeatherMind Agent 🌤️

一個每天定時推送天氣與生活提醒的 AI Agent，基於 Zhipu/Python，透過 Telegram 發送。

## ✨ 特色
- 🧠 使用 LLM 即時生成自然語言建議，非死板模板
- 🌍 支援任意經緯度，可自訂位置
- ⏰ 使用 GitHub Actions 免費定時運行
- 🔒 所有敏感資訊以 GitHub Secrets 保存

## 🤖 Agent 架構
`感知 (天氣 API) ➜ 推理 (Gemini) ➜ 行動 (Telegram Bot)`

## 📦 快速開始
1. Clone 本倉庫
2. 安裝依賴：`pip install -r requirements.txt`
3. 建立 `.env` 並填入密鑰
4. 測試：`python agent.py`
5. 部署：設定 GitHub Secrets 並啟用 Actions
