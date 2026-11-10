# Империя тепла

Адаптивный лендинг на Django 5.2, HTML и CSS. Макеты главной в Figma: [1440 px](https://www.figma.com/design/bbgufdPCw8sVnFvTucYKmh/?node-id=4232-3293), [768 px](https://www.figma.com/design/bbgufdPCw8sVnFvTucYKmh/?node-id=4238-655) и [368 px](https://www.figma.com/design/bbgufdPCw8sVnFvTucYKmh/?node-id=4240-1694).

## Запуск через Docker

```sh
docker compose up --build -d --wait
docker compose exec web python manage.py createsuperuser
```

Главная откроется по адресу http://127.0.0.1:8000/, админка — по адресу http://127.0.0.1:8000/admin/.
Если порт занят, задай другой, например `HEAT_PORT=8125 docker compose up -d --wait`.
Миграции выполняются при старте. Контакты и учётные записи хранятся в томе `site_data`.

## Запуск без Docker

Нужен Python 3.10 или новее.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export DJANGO_DEBUG=1 DJANGO_SECRET_KEY=local-development-only
python manage.py migrate
python manage.py runserver
```

## Редактирование контактов

При запуске без Docker создай учётную запись командой `python manage.py createsuperuser`.
Откройте http://127.0.0.1:8000/admin/ и выберите **Настройки сайта → Контакты сайта**.
Телефон и адрес из макета уже заполнены. Укажите полные ссылки для Telegram, WhatsApp и MAX.
Пустое поле оставляет соответствующую иконку без ссылки.

## Публикация

Направь DNS домена на сервер, открой входящие TCP-порты 80 и 443 и установи Docker Compose 2.24.4 или новее.
Скопируй `.env.example` в `.env` и укажи `SITE_DOMAIN` без схемы и порта. Для `DJANGO_SECRET_KEY` сгенерируй случайный ключ командой `openssl rand -hex 32` и сохрани его в `.env`.

```sh
docker compose -f compose.yaml -f compose.prod.yaml up --build -d --wait
docker compose -f compose.yaml -f compose.prod.yaml exec web python manage.py createsuperuser
```

Caddy получает и обновляет сертификаты. Gunicorn доступен внутри сети Compose.
Django работает с выключенным режимом отладки, защищёнными cookies и версионированной статикой. SQLite рассчитана на один экземпляр приложения. Том `site_data` нужно сохранять при обновлениях. Команда `docker compose down -v` удаляет тома.
HSTS действует на домен сайта. Включение HSTS для всех поддоменов и добавление домена в preload-список браузеров требуют отдельной проверки домена.

Чтобы сделать согласованную резервную копию базы работающего сайта, выполни команду ниже и сохрани файл вне сервера.

```sh
docker compose -f compose.yaml -f compose.prod.yaml exec -T web python /app/backup.py > heat-empire-backup.sqlite3
```

## Текущий объём

- На телефонах сравнение, этапы работ и кейсы листаются горизонтально внутри своих блоков.
- Фотографии и иконки взяты из экспорта Figma. Для заголовков используется Fira Sans Extra Condensed из Impery. Остальные шрифты из макета, TikTok Sans и Manrope, хранятся локально вместе с лицензиями.
- В форме расчёта можно заполнить поля. Отправка заявок и ссылки на юридические страницы потребуют отдельного подключения.
