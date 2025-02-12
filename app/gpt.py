import requests
from app.config import yandex_cloud_id, yandex_api_token

URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

messages = [
    {
        "role": "system",
        "text": "Ты умный ассистент",
    }
]

def run_gpt(user_text):
    global messages
    # Добавляем текст пользователя в массив сообщений
    messages.append({"role": "user", "text": user_text})

    # Собираем запрос
    data = {}
    # Указываем тип модели
    data["modelUri"] = f"gpt://{yandex_cloud_id}/yandexgpt"
    # Настраиваем опции
    data["completionOptions"] = {"temperature": 0.3, "maxTokens": 1000}
    # Указываем контекст для модели
    data["messages"] = messages

    # Отправляем запрос
    response = requests.post(
        URL,
        headers={
            "Accept": "application/json",
            "Authorization": f"Api-Key {yandex_api_token}"
        },
        json=data,
    ).json()

    response_text = response["result"]["alternatives"][0]["message"]["text"]

    messages.append({"role": "assistant", "text": response_text})

    return response_text