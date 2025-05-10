# Платформа чат-ботов для повышения эффективности коммуникации с административными подразделениями
## Дипломная работа

---
В проекте используется:
- <a href="https://docs.aiogram.dev/">aiogram</a>
- <a href="https://www.postgresql.org/docs/">PostgreSQL</a>
- <a href="https://yandex.cloud/ru/docs/foundation-models/concepts/">YandexGPT</a>

---
Перед запуском добавьте переменные окружения в **app/.env**:
```shell
# Из BotFather
BOT_TOKEN= 
PUBLIC_BOT_TOKEN= 

# Данные для сборки
POSTGRES_PASSWORD=
POSTGRES_DATABASE=
POSTGRES_USER=
POSTGRES_TZ= # Например, Asia/Novosibirsk

# Смотреть "Начало работы с YandexGPT"
YANDEX_CLOUD_ID= 
YANDEX_API_TOKEN=

# Telegram аккаунт с логином и паролем для приватного чат-бота (первый владелец)
OWNER_TG_ID=
OWNER_USERNAME=
OWNER_PASSWORD=
```

---
## Запуск

1) Для первого внесения схемы базы данных убрать # из Dockerfile на 3 строке
2) Выполнить сборку:
```commandline
make migrate
make build
make run_db
make run
```
3) После добавления данных в ботах можно сделать бэкап БД:
```commandline
make backup
```

---
## Пересборка контейнера с восстановлением данных из БД
1) Выполнить:
```commandline
make stop_db
make del_cont
make del_image
```
2) Установить # в Dockerfile на 3 строке
3) Выполнить 2 пункт **Запуска** без ```make run```
4) Выполнить ```make recovery``` и ```make run```

---

[MIT 2025](LICENSE)