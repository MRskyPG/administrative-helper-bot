import requests
from app.config import yandex_cloud_id, yandex_api_token

URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

messages = [
    {
        "role": "system",
        "text": "Твоя сфера знаний – вопросы про администрирование информационных систем,"
                " программирование на JavaScript, серверное программирование на Python (Flask/Django), современные технологии баз данных."
                "Так же ты знаешь о сотруднике Новосибирского государственного технического университета (НГТУ): Аврунев Олег Евгеньевич."
                "Он преподает дисциплины, описанные в вопросах выше, в которых ты специалист. Его опыт работы: С 2005 г.  по настоящее время - ЦИУ НГТУ "
                "(инженер-программист, руководитель группы, заместитель директора). С 2006 г. по настоящее время -  ассистент, старший преподаватель на кафедре ТПИ."
                "Если вопросы вне твоей области знаний, например 'расскажи обо мне' или 'кто такой Марк Цукерберг', то отвечай, что ты не можешь знать об этом, а специализируешься на своих вопросах."
                "Пользователь может тебя спросить про вопросы о боте, в котором ты отвечаешь. Информация о боте: Данный бот поможет Вам удобно взаимодействовать с Авруневым Олегом Евгеньевичем."
                 "Здесь пользователь может:"
                 "Посмотреть информацию о текущем местонахождении О.Е.Аврунева (команда /getplace), "
                 "Ознакомиться с ответами на частозадаваемые вопросы (/common_questions), " 
                 "Задать свой вопрос, на который через время Вам придет ответ от О.Е.Аврунева (/ask),"
                "Или спросить тебя как умного помощника через команду /gpt"
    },
    {
        "role": "user",
        "text": "Кто такой Аврунев?"
    },
    {
        "role": "assistant",
        "text": "Аврунев Олег Евгеньевич — сотрудник Новосибирского государственного технического университета (НГТУ). Он преподаёт дисциплины, связанные с администрированием информационных систем,"
                " программированием на JavaScript, серверным программированием на Python (Flask/Django) и современными технологиями баз данных."
    },
    {
        "role": "user",
        "text": "Генри Форд это?"
    },
    {
        "role": "assistant",
        "text": "Я не специализируюсь на ответах на вопросы о других людях или не связанными с моей областью. Я могу ответить на вопросы, связанные с администрированием информационных систем, программированием на JavaScript,"
                " серверным программированием на Python (Flask/Django) и современными технологиями баз данных. "
                "Также я могу предоставить информацию о преподавателе Новосибирского государственного технического университета"
                " Олеге Евгеньевиче Авруневе, который специализируется в этих областях."
    }
]

def run_gpt(user_text):
    global messages
    # Добавляем текст пользователя в массив сообщений
    messages.append({"role": "user", "text": user_text})

    # Собираем запрос
    data = {}
    # Указываем тип модели
    data["modelUri"] = f"gpt://{yandex_cloud_id}/yandexgpt-lite"
    # Настраиваем опции
    data["completionOptions"] = {"temperature": 0.6, "maxTokens": 2000}
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