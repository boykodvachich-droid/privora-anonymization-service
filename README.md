# Privora

**Your data. Your privacy. Your control.**

Privora is a privacy-focused text anonymization platform designed to detect and mask sensitive information before it is shared or processed elsewhere.

It combines a web interface, a REST API, synchronous anonymization, and background task processing in a Docker-based architecture.

## Features

- Detection and masking of sensitive information in text.
- Support for email addresses, phone numbers, names, addresses, dates, passport data, SNILS, Russian INN, and bank card numbers.
- Rule-based detection using regular expressions and validation logic.
- Synchronous text anonymization through a REST API.
- Background anonymization through RabbitMQ and a dedicated Worker.
- Persistent task and result storage in PostgreSQL.
- Redis caching for synchronous anonymization.
- Task history and task detail views in the web interface.
- Export of anonymization results in TXT and JSON formats.
- Task history export in CSV format.
- Configurable detection categories.
- Docker Compose-based local deployment.

## Technology Stack

### Frontend
- React
- TypeScript
- Vite
- Nginx
- CSS

### Backend
- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy
- Pytest
- HTTPX

### Infrastructure
- PostgreSQL 17
- Redis
- RabbitMQ
- Pika
- Docker
- Docker Compose

## Architecture

```text
                         User
                           |
                           v
                    React Frontend
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
                                        |
                                        v
                                  React Frontend
