import os
import requests
from dotenv import load_dotenv
import asyncio
from telegram import Bot
from collections import Counter
from datetime import datetime, timezone, timedelta

# LangChain 導入
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_models import ChatZhipuAI

load_dotenv()

# 設定
OWM_KEY = os.getenv("OPENWEATHER_API_KEY")       # OpenWeatherMap 2.5 API Key
LLM_KEY = os.getenv("LLM_API_KEY")                # 智譜 AI API Key
TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")
CHAT_IDS = [cid.strip() for cid in CHAT_IDS if cid.strip()]
CITY = os.getenv("CITY", "HongKong")              # 預設城市

# ---- LangChain 初始化 ----
llm = ChatZhipuAI(
    api_key=LLM_KEY,
    model="glm-4-flash",
    temperature=0.7,
    max_tokens=300
)

# 天氣提醒的 Prompt 模板
weather_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一個貼心的生活助理，用繁體中文產生一則早晨問候提醒。
語氣請溫暖幽默，總長度不超過 200 字。"""),
    ("human", """請根據以下天氣數據產生提醒，必須包含：
- 今天天氣：{weather_desc}，氣溫 {temp_min}°C 至 {temp_max}°C，體感溫度 {feels_like_now}°C
- 是否需要帶傘（最大降雨機率 {pop_max}%）
- 具體的穿衣搭配建議
- 適合的戶外活動建議

天氣原始資料：{weather_full}""")
])

# 建立 LCEL 鏈
weather_chain = weather_prompt | llm | StrOutputParser()

# ---- 1. 獲取天氣數據（OpenWeatherMap 2.5 免費方案）----
def get_weather():
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={CITY}&appid={OWM_KEY}&units=metric&lang=zh_cn"
    res = requests.get(url)
    data = res.json()

    if data.get("cod") != "200":
        error_msg = data.get("message", "Unknown error")
        raise Exception(f"OpenWeatherMap API 錯誤: {error_msg}")

    # 香港時間 (UTC+8) 的今天日期
    hk_tz = timezone(timedelta(hours=8))
    hk_now = datetime.now(hk_tz)
    hk_today_str = hk_now.strftime("%Y-%m-%d")

    # 篩選香港今天的時段
    today_items = [item for item in data["list"] if item["dt_txt"].startswith(hk_today_str)]

    # 備援：若 UTC 未跨日，改用 API 的第一筆日期
    if not today_items:
        fallback_date = data["list"][0]["dt_txt"].split(" ")[0]
        today_items = [item for item in data["list"] if item["dt_txt"].startswith(fallback_date)]

    if not today_items:
        raise Exception("今日無天氣數據")

    temps = [item["main"]["temp"] for item in today_items]
    feels_likes = [item["main"]["feels_like"] for item in today_items]
    humidities = [item["main"]["humidity"] for item in today_items]
    weather_descs = [item["weather"][0]["description"] for item in today_items]
    pops = [item.get("pop", 0) for item in today_items]

    most_common_desc = Counter(weather_descs).most_common(1)[0][0]

    return {
        "city": CITY,
        "date": hk_today_str,
        "temp_min": min(temps),
        "temp_max": max(temps),
        "feels_like_now": feels_likes[0],
        "humidity_avg": sum(humidities) // len(humidities),
        "weather_desc": most_common_desc,
        "pop_max": max(pops) * 100,
        "uvi": "無資料（API 未提供）"
    }

# ---- 2. LangChain 生成提醒 ----
def generate_advice(weather):
    response = weather_chain.invoke({
        "weather_desc": weather["weather_desc"],
        "temp_min": weather["temp_min"],
        "temp_max": weather["temp_max"],
        "feels_like_now": weather["feels_like_now"],
        "pop_max": weather["pop_max"],
        "weather_full": str(weather)  # 傳完整資料給模型參考
    })
    return response

# ---- 3. 發送 Telegram 訊息（多用戶）----
async def send_telegram(message):
    bot = Bot(token=TELE_TOKEN)
    for cid in CHAT_IDS:
        try:
            await bot.send_message(chat_id=cid, text=message)
            print(f"已發送給 {cid}")
        except Exception as e:
            print(f"發送給 {cid} 失敗: {e}")

async def main():
    try:
        weather = get_weather()
        advice = generate_advice(weather)
        full_msg = f"☀️ WeatherMind 早晨提醒\n\n{advice}"
        await send_telegram(full_msg)
        print("所有天氣提醒已發送！")
    except Exception as e:
        error_msg = f"⚠️ WeatherMind 執行失敗: {str(e)}"
        print(error_msg)
        await send_telegram(error_msg)

if __name__ == "__main__":
    asyncio.run(main())