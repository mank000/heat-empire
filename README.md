# Империя тепла

Десктопный лендинг на Django 5.2, HTML и CSS. Целевой макет — [«Главная 1440px» в Figma](https://www.figma.com/design/bbgufdPCw8sVnFvTucYKmh/?node-id=4232-3293).

## Локальный запуск

Нужен Python 3.10 или новее.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
DJANGO_DEBUG=1 DJANGO_SECRET_KEY=local-development-only python manage.py runserver
```

Главная откроется по адресу http://127.0.0.1:8000/.


## Текущий объём

- Главная страница сверстана для окна браузера шириной 1440 px.
- Фотографии и иконки взяты из экспорта Figma. Для заголовков используется Fira Sans Extra Condensed из Impery. Остальные шрифты из макета, TikTok Sans и Manrope, хранятся локально вместе с лицензиями.
- В форме расчёта можно заполнить поля. Отправка заявок и адреса ссылок на мессенджеры и юридические страницы потребуют отдельного подключения.
