from __future__ import annotations
import os
import urllib.parse
from dataclasses import dataclass
from typing import Final, Optional
import requests
import telebot

OPEN_METEO_GEOCODE_URL: Final[str] = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_WEATHER_URL: Final[str] = "https://api.open-meteo.com/v1/forecast"

@dataclass
class WeatherInfo:
    city: str
    country: Optional[str]
    latitude: float
    longitude: float
    temperature_c: Optional[float]
    windspeed: Optional[float]
    winddirection: Optional[float]
    weathercode: int


def extract_city_with_ai(user_text: str) -> Optional[str]:
    """
    Использует pollinations.ai чтобы извлечь название города.
    Возвращает название города на английском.
    """
    prompt = (
        "Extract the city name from the user's text and translate it to English. "
        "Return ONLY the city name. If there is no city return NONE. "
        "User text: "
    )

    try:
        url = "https://text.pollinations.ai/" + urllib.parse.quote(prompt + user_text)

        response = requests.get(url)
        response.raise_for_status()

        result = response.text.strip()

        if result.upper() == "NONE" or not result:
            return None

        return result

    except Exception as e:
        print("AI request error:", e)
        return None

def fetch_weather(city: str) -> Optional[WeatherInfo]:
    """Получить текущую погоду через Open-Meteo."""

    try:
        geo_resp = requests.get(
            OPEN_METEO_GEOCODE_URL,
            params={
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json",
            },
            timeout=10,
        )

        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

        results = geo_data.get("results") or []
        if not results:
            return None

        place = results[0]
        lat = place["latitude"]
        lon = place["longitude"]

        weather_resp = requests.get(
            OPEN_METEO_WEATHER_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
                "timezone": "auto",
            },
            timeout=10,
        )

        weather_resp.raise_for_status()
        weather_data = weather_resp.json()

        current = weather_data.get("current_weather") or {}

        return WeatherInfo(
            city=place.get("name", city),
            country=place.get("country"),
            latitude=lat,
            longitude=lon,
            temperature_c=current.get("temperature"),
            windspeed=current.get("windspeed"),
            winddirection=current.get("winddirection"),
            weathercode=current.get("weathercode", -1),
        )

    except Exception as e:
        print("Weather error:", e)
        return None


def format_weather(info: WeatherInfo) -> str:

    location = info.city
    if info.country:
        location += f", {info.country}"

    temp = f"{info.temperature_c:.1f}" if info.temperature_c is not None else "?"
    wind = f"{info.windspeed:.1f}" if info.windspeed is not None else "?"
    direction = f"{info.winddirection:.0f}" if info.winddirection is not None else "?"

    return (
        f"Погода в {location}:\n"
        f"🌡 Температура: {temp} °C\n"
        f"💨 Ветер: {wind} м/с (направление {direction}°)"
    )


bot = telebot.TeleBot("7821308737:AAGKxSQAYehtTbIBg0Fdcg8a_DabuXmmjtU")


@bot.message_handler(commands=["start"])
def handle_start(message: telebot.types.Message):

    bot.reply_to(
        message,
        "Привет! Я бот погоды 🌤\n"
        "Напиши что-нибудь вроде:\n"
        "«Какая погода в Москве?»\n"
        "или\n"
        "«Погода Токио»",
    )


@bot.message_handler(func=lambda message: True, content_types=["text"])
def handle_message(message: telebot.types.Message):

    user_text = message.text.strip()

    if not user_text:
        bot.reply_to(message, "Напиши сообщение.")
        return

    bot.reply_to(message, "🔍 Ищу город...")

    city = extract_city_with_ai(user_text)

    if city is None:
        bot.reply_to(
            message,
            "Не смог найти город в сообщении.\n"
            "Например: «погода в Берлине».",
        )
        return

    weather = fetch_weather(city)

    if weather is None:
        bot.reply_to(
            message,
            f"Нашёл город «{city}», но не смог получить погоду.",
        )
        return

    text = format_weather(weather)

    bot.reply_to(message, text)



if __name__ == "__main__":
    print("Telegram weather bot is running")
    bot.infinity_polling()