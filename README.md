# DataMask

Сервис для обнаружения и маскирования чувствительных данных в тексте.

## Текущий статус

Стартовый этап: синхронный REST API и базовые правила EMAIL, PHONE, PASSPORT, SNILS.
PostgreSQL, Redis и RabbitMQ поднимаются через Compose; подключение хранилища,
кэша и фоновых задач будет реализовано на следующих этапах.

## Запуск локально

Требуется Docker и Docker Compose.

```bash
docker compose up --build
```

API: http://localhost:8000  
Swagger: http://localhost:8000/docs  
Health: http://localhost:8000/health

## Пример запроса

```bash
curl -X POST http://localhost:8000/api/v1/anonymize \
  -H "Content-Type: application/json" \
  -d '{"text":"Email ivan@example.com, phone +7 (999) 123-45-67"}'
```

## Тесты

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

## Важные ограничения начальной версии

- ФИО пока не распознаются: для этого нужен NER-модуль или отдельный словарь/плагин.
- Regex-правила являются базовыми и требуют проверки на целевых данных.
- Не отправляйте реальные персональные данные в публичные тестовые окружения.
- Сейчас API не сохраняет исходный текст и не подключает Redis/PostgreSQL/RabbitMQ к бизнес-логике.
