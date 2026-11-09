# Империя тепла

Основа лендинга на Django 5.2. Целевой макет — [«Главная 1440px» в Figma](https://www.figma.com/design/bbgufdPCw8sVnFvTucYKmh/?node-id=4232-3293).

## Локальный запуск

Нужен Python 3.10 или новее.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
DJANGO_DEBUG=1 DJANGO_SECRET_KEY=local-development-only python manage.py runserver
```

Главная откроется по адресу http://127.0.0.1:8000/.
