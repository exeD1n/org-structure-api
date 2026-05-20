# Тестовое задание: API организационной структуры

Реализовать API для подразделений и сотрудников.

## Модели

### Department

- id: int
- name: str
- parent_id: int | null
- created_at: datetime

### Employee

- id: int
- department_id: int
- full_name: str
- position: str
- hired_at: date | null
- created_at: datetime

## Основные методы API

- POST /departments/
- POST /departments/{id}/employees/
- GET /departments/{id}
- PATCH /departments/{id}
- DELETE /departments/{id}

## Требования

- FastAPI или Django
- ORM
- PostgreSQL
- Миграции
- Docker Compose
- README.md
- Тесты pytest приветствуются
