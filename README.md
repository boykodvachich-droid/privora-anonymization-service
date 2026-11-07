# DataMask

DataMask — REST API-сервис для обнаружения и маскирования чувствительной информации в текстах.

Проект позволяет находить и маскировать персональные данные, включая email, телефоны, ФИО, адреса, даты, паспортные данные, СНИЛС, ИНН и номера банковских карт.

## Возможности

- Обнаружение чувствительных данных с помощью регулярных выражений и валидаторов.
- Маскирование найденных персональных данных.
- Подсчёт количества обнаруженных типов данных.
- Синхронная обработка текста через REST API.
- Кэширование результатов синхронной обработки с помощью Redis.
- Асинхронная обработка задач через RabbitMQ.
- Фоновая обработка задач отдельным Worker.
- Хранение задач и результатов обработки в PostgreSQL.
- Получение статуса и результата асинхронной задачи через API.
- Автоматический запуск сервисов через Docker Compose.
- Автоматические тесты с использованием pytest.

## Технологии

- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy
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
          +-----------+-----------+
          |                       |
          v                       v
   Synchronous API          Async Tasks API
          |                       |
          v                       v
 Anonymization Engine       PostgreSQL
          |                       |
          v                       v
      Redis Cache             RabbitMQ
                                  |
                                  v
                                Worker
                                  |
                                  v
                         Anonymization Engine
                                  |
                                  v
                              PostgreSQL
                                  |
                                  v
                          Task Result API
```

**Роль компонентов:**

- FastAPI — обработка HTTP-запросов.
- Anonymization Engine — обнаружение и маскирование чувствительных данных.
- Redis — кэширование результатов синхронной анонимизации и вспомогательное кэширование задач.
- RabbitMQ — передача асинхронных задач Worker.
- Worker — фоновая обработка задач.
- PostgreSQL — постоянное хранение задач и результатов.
- SQLAlchemy — взаимодействие с PostgreSQL.

PostgreSQL является основным источником данных об асинхронных задачах. Redis не является обязательной зависимостью для их создания и получения результатов.

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

RabbitMQ Management в локальной конфигурации использует логин `guest` и пароль `guest`.

## API

### 1. Проверка состояния сервиса

```http
GET /health
```

Пример ответа:

```json
{
  "status": "ok",
  "service": "datamask"
}
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

Результат синхронного запроса кэшируется в Redis на 300 секунд.

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

После создания задача сохраняется в PostgreSQL и отправляется в RabbitMQ для фоновой обработки.

### 4. Получение результата задачи

```http
GET /api/v1/tasks/{task_id}
```

Пример:

```bash
curl http://localhost:8000/api/v1/tasks/UUID
```

Пример ответа после обработки:

```json
{
  "task_id": "UUID",
  "status": "completed",
  "anonymized_text": "И*** П*****, email i***@example.com",
  "detected": {
    "EMAIL": 1,
    "PERSON": 1
  },
  "processing_time_ms": 1.5
}
```

Возможные статусы задачи:

- `pending` — задача ожидает обработки.
- `completed` — задача успешно обработана.
- `failed` — при обработке произошла ошибка.

Информация о задаче и результат обработки хранятся в PostgreSQL.

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
│   ├── schemas.py
│   ├── database.py
│   └── models.py
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
- Для управления изменениями структуры базы данных можно внедрить Alembic.
- Необходимо добавить интеграционные тесты API, PostgreSQL и Worker.
- Для production необходимо настроить безопасное хранение секретов, мониторинг, обработку ошибок очереди, повторные попытки и защиту API.
- Текущие настройки RabbitMQ предназначены для локальной разработки.

## Лицензия

Пока лицензия проекта не определена.