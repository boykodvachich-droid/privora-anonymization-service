# DataMask

DataMask — REST API-сервис для обнаружения и маскирования чувствительной информации в текстах.

Проект позволяет находить и маскировать персональные данные: email, телефоны, ФИО, адреса, даты, паспортные данные, СНИЛС, ИНН и номера банковских карт.

## Возможности

- Обнаружение чувствительных данных с помощью регулярных выражений и валидаторов.
- Маскирование найденных персональных данных.
- Подсчёт количества обнаруженных типов данных.
- Синхронная обработка текста через REST API.
- Кэширование результатов синхронной обработки с помощью Redis.
- Асинхронная обработка задач через RabbitMQ.
- Фоновая обработка задач отдельным Worker.
- Постоянное хранение задач и результатов в PostgreSQL.
- Получение статуса и результата асинхронной задачи через API.
- Обработка ошибок при публикации и выполнении задач.
- Автоматический запуск сервисов через Docker Compose.
- Автоматизированное тестирование с использованием pytest.

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
- HTTPX

## Архитектура

```text
                         Client
                           |
                           v
                         FastAPI
                           |
              +------------+------------+
              |                         |
              v                         v
       Synchronous API            Async Tasks API
              |                         |
              v                         v
     Anonymization Engine           PostgreSQL
              |                         |
              v                         v
         Redis Cache                 RabbitMQ
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

### Роль компонентов

- **FastAPI** — обработка HTTP-запросов и предоставление REST API.
- **Anonymization Engine** — обнаружение и маскирование чувствительных данных.
- **Redis** — кэширование результатов синхронной анонимизации и вспомогательное кэширование задач.
- **RabbitMQ** — передача асинхронных задач Worker.
- **Worker** — фоновая обработка задач из очереди.
- **PostgreSQL** — постоянное хранение задач и результатов обработки.
- **SQLAlchemy** — взаимодействие с PostgreSQL.
- **Pika** — взаимодействие с RabbitMQ.

PostgreSQL является основным источником данных об асинхронных задачах. Redis не является обязательной зависимостью для создания и получения результатов асинхронных задач.

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

Для запуска требуется установленный Docker Desktop и Docker Compose.

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd datamask
```

### 2. Запуск сервисов

```bash
docker compose up -d --build
```

Docker Compose запускает следующие сервисы:

- API;
- Worker;
- PostgreSQL;
- Redis;
- RabbitMQ.

### 3. Проверка состояния контейнеров

```bash
docker compose ps
```

### 4. Просмотр логов

```bash
docker compose logs -f api
```

Логи Worker:

```bash
docker compose logs -f worker
```

### 5. Остановка сервисов

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

**Запрос:**

```http
GET /health
```

**Пример ответа:**

```json
{
  "status": "ok",
  "service": "datamask"
}
```

### 2. Синхронная анонимизация

**Запрос:**

```http
POST /api/v1/anonymize
```

**Пример:**

```bash
curl -X POST http://localhost:8000/api/v1/anonymize \
  -H "Content-Type: application/json" \
  -d '{"text":"Иван Петров, email ivan@example.com, телефон +7 999 123-45-67"}'
```

**Пример ответа:**

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

**Запрос:**

```http
POST /api/v1/tasks
```

**Пример:**

```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"text":"Иван Петров, email ivan@example.com"}'
```

**Пример ответа:**

```json
{
  "task_id": "UUID",
  "status": "pending"
}
```

После создания задача сохраняется в PostgreSQL и отправляется в RabbitMQ для фоновой обработки.

### 4. Получение результата задачи

**Запрос:**

```http
GET /api/v1/tasks/{task_id}
```

**Пример:**

```bash
curl http://localhost:8000/api/v1/tasks/UUID
```

**Пример ответа после обработки:**

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

Для запуска автоматических тестов внутри Docker-контейнера:

```bash
docker compose exec api pytest -v
```

Текущий набор включает **39 автоматических тестов**:

- 31 тест анонимизатора;
- 6 интеграционных тестов API;
- 2 теста Worker с PostgreSQL.

Проверяются обнаружение и маскирование персональных данных, работа REST API, создание и получение асинхронных задач, сохранение результатов в PostgreSQL и обработка ошибок Worker.

Все 39 тестов успешно проходят.

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
│   ├── conftest.py
│   ├── test_anonymizer.py
│   ├── test_api.py
│   └── test_worker.py
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── large_test.json
└── README.md
```

## Ограничения и дальнейшее развитие

- Распознавание ФИО основано на регулярных выражениях и может ошибаться.
- Для повышения точности распознавания можно добавить NER-модель.
- Для управления изменениями структуры базы данных можно внедрить Alembic.
- Для production необходимо настроить безопасное хранение секретов.
- Можно добавить мониторинг, метрики и централизованное логирование.
- Можно улучшить обработку ошибок очереди, повторные попытки и dead-letter queue.
- Для production необходимо предусмотреть аутентификацию, авторизацию и защиту API.
- Текущие настройки RabbitMQ предназначены для локальной разработки.

## Лицензия

Пока лицензия проекта не определена.