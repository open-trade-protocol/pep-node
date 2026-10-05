# PEP Node — Agent Instructions

## Архитектура
- FastAPI приложение в `main.py`
- Модели данных в Pydantic (должны соответствовать `../spec/openapi/openapi.yaml`)
- Миграции БД в `migrations/`
- Тесты в `tests/`

## Правила
- Все эндпоинты должны строго соответствовать OpenAPI спецификации в `spec/`
- Используйте SQLModel для работы с PostgreSQL
- Не импортируйте модули из других репозиториев напрямую
- Конфигурация через переменные окружения (`.env.example`)

## Команды
- Запуск: `uvicorn main:app --reload`
- Тесты: `pytest tests/`
