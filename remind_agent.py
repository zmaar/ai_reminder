import os
import requests
from dotenv import load_dotenv
import asyncio
from telegram import Bot
from zhipuai import ZhipuAI
from collections import Counter

load_dotenv()

# 設定
OWM_KEY = os.getenv("OPENWEATHER_API_KEY")       # OpenWeatherMap 2.5 API Key
LLM_KEY = os.getenv("LLM_API_KEY")                # 智譜 AI API Key
TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CITY ="HongKong"           # 預設城市

# 初始化智譜客戶端（只做一次）
zhipu_client = ZhipuAI(api_key=LLM_KEY)

# 1. 獲取天氣數據（OpenWeatherMap 2.5 免費方案）
def get_weather():
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={CITY}&appid={OWM_KEY}&units=metric&lang=zh_cn"
    res = requests.get(url)
    data = res.json()

    if data.get("cod") != "200":
        error_msg = data.get("message", "Unknown error")
        raise Exception(f"OpenWeatherMap API 錯誤: {error_msg}")

    first_dt = data["list"][0]["dt_txt"]
    today = first_dt.split(" ")[0]

    today_items = [item for item in data["list"] if item["dt_txt"].startswith(today)]

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
        "date": today,
        "temp_min": min(temps),
        "temp_max": max(temps),
        "feels_like_now": feels_likes[0],
        "humidity_avg": sum(humidities) // len(humidities),
        "weather_desc": most_common_desc,
        "pop_max": max(pops) * 100,  # 百分比
        "uvi": "無資料（API 未提供）"
    }

# 2. 用智譜 GLM-4-Flash 生成結構化提醒
def generate_advice(weather):
    prompt = f"""你是一個貼心的生活助理，請根據以下天氣數據，用繁體中文產生一則早晨問候提醒。
提醒中**必須明確包含**以下資訊：
- 今天天氣：{weather['weather_desc']}，氣溫 {weather['temp_min']}°C 至 {weather['temp_max']}°C，體感溫度 {weather['feels_like_now']}°C
- 是否需要帶傘（最大降雨機率 {weather['pop_max']}%）
- 具體的穿衣搭配建議
- 適合的戶外活動建議

語氣請溫暖幽默，總長度不超過 200 字。直接回覆提醒內容，不要加上前綴詞。"""

    response = zhipu_client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=300
    )
    return response.choices[0].message.content

# 3. 發送 Telegram 訊息
async def send_telegram(message):
    bot = Bot(token=TELE_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=message)

async def main():
    try:
        weather = get_weather()
        advice = generate_advice(weather)
        full_msg = f"☀️ WeatherMind 早晨提醒\n{advice}"
        await send_telegram(full_msg)
        print("天氣提醒已發送！")
    except Exception as e:
        error_msg = f"⚠️ WeatherMind 執行失敗: {str(e)}"
        print(error_msg)
        await send_telegram(error_msg)

if __name__ == "__main__":
    asyncio.run(main())