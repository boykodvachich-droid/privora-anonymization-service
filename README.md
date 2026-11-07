
# DataMask

DataMask — REST API-сервис для обнаружения и маскирования чувствительной информации в текстах.

Проект позволяет находить персональные данные, включая email, телефоны, ФИО, адреса, даты, паспортные данные, СНИЛС, ИНН и номера банковских карт.

## Возможности

- Обнаружение чувствительных данных с помощью регулярных выражений и валидаторов.
- Маскирование найденных персональных данных.
- Подсчёт количества обнаруженных типов данных.
- Синхронная обработка текста через REST API.
- Асинхронная обработка задач через RabbitMQ.
- Кэширование результатов с помощью Redis.
- Хранение результатов фоновых задач в Redis.
- Автоматический запуск worker через Docker Compose.
- Автоматические тесты с использованием pytest.

## Технологии

- Python 3.12
- FastAPI
- Pydantic
- PostgreSQL 17
- Redis 7
- RabbitMQ
- Pika
- Docker и Docker Compose
- Pytest

## Архитектура

```text
Client
  |
  v
FastAPI
  |
  +----------------------+
  |                      |
  v                      v
Synchronous API       Async Tasks API
  |                      |
  v                      v
Anonymization Engine  RabbitMQ
  |                      |
  v                      v
Redis Cache             Worker
                         |
                         v
                  Anonymization Engine
                         |
                         v
                  Redis Task Results
```

## Обнаруживаемые данные

| Тип | Описание |
|---|---|
| EMAIL | Электронная почта |
| PHONE | Номер телефона |
| PERSON | ФИО |
| ADDRESS | Адрес |
| DATE | Дата |
| PASSPORT | Паспортные данные |
| SNILS | СНИЛС |
| INN | ИНН |
| BANK_CARD | Номер банковской карты |

## Запуск проекта

Требуется установленный Docker Desktop и Docker Compose.

Клонирование репозитория:

```bash
git clone <repository-url>
cd datamask
```

Запуск всех сервисов:

```bash
docker compose up -d --build
```

Проверка состояния контейнеров:

```bash
docker compose ps
```

Остановка сервисов:

```bash
docker compose down
```

## Доступные сервисы

| Сервис | Адрес |
|---|---|
| FastAPI | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |
| RabbitMQ Management | http://localhost:15672 |

RabbitMQ Management по умолчанию использует логин `guest` и пароль `guest`.

## API

### 1. Проверка состояния сервиса

```http
GET /health
```

### 2. Синхронная анонимизация

```http
POST /api/v1/anonymize
```

Пример:

```bash
curl -X POST http://localhost:8000/api/v1/anonymize \
  -H "Content-Type: application/json" \
  -d '{"text":"Иван Петров, email ivan@example.com, телефон +7 999 123-45-67"}'
```

Пример ответа:

```json
{
  "anonymized_text": "И*** П*****, email i***@example.com, телефон +* *** ***-**-67",
  "detected": {
    "EMAIL": 1,
    "PERSON": 1,
    "PHONE": 1
  },
  "processing_time_ms": 8.0
}
```

Результат синхронного запроса кэшируется в Redis.

### 3. Создание асинхронной задачи

```http
POST /api/v1/tasks
```

Пример:

```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"text":"Иван Петров, email ivan@example.com"}'
```

Пример ответа:

```json
{
  "task_id": "UUID",
  "status": "pending"
}
```

### 4. Получение результата задачи

```http
GET /api/v1/tasks/{task_id}
```

Пример:

```bash
curl http://localhost:8000/api/v1/tasks/UUID
```

После обработки worker возвращает результат со статусом `completed`.

## Тестирование

Запуск тестов внутри Docker-контейнера:

```bash
docker compose exec api pytest -v
```

На текущем этапе успешно проходят 31 автоматический тест.

## Структура проекта

```text
datamask/
├── app/
│   ├── anonymizer/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   └── rules.py
│   ├── queue/
│   │   ├── __init__.py
│   │   ├── rabbitmq.py
│   │   └── worker.py
│   ├── main.py
│   └── schemas.py
├── tests/
│   ├── __init__.py
│   └── test_anonymizer.py
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Ограничения и дальнейшее развитие

- Распознавание ФИО основано на регулярных выражениях и может ошибаться.
- Для повышения точности можно добавить NER-модель.
- PostgreSQL подключён в инфраструктуре, но полноценная работа с ним в бизнес-логике пока не реализована.
- Для production необходимо настроить безопасное хранение секретов, мониторинг, обработку ошибок очереди и защиту API.
- Текущие настройки RabbitMQ предназначены для локальной разработки.

## Лицензия

Пока лицензия проекта не определена.
