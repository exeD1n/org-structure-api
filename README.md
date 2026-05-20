# Organization Structure API

API для управления организационной структурой: подразделения, сотрудники и дерево вложенных подразделений.

Проект реализован как тестовое задание на **FastAPI + SQLAlchemy ORM + PostgreSQL + Alembic + Docker Compose**.

## Что реализовано

- Создание подразделений.
- Создание сотрудников внутри подразделений.
- Получение подразделения вместе с сотрудниками и поддеревом дочерних подразделений.
- Обновление названия подразделения.
- Перемещение подразделения в другое подразделение.
- Удаление подразделения в режиме `cascade`.
- Удаление подразделения в режиме `reassign` с переводом сотрудников в другое подразделение.
- Проверка циклов в дереве подразделений.
- Проверка уникальности названия подразделения внутри одного родителя.
- Валидация входных данных через Pydantic.
- Миграция БД через Alembic.
- Docker-сборка и запуск через `docker compose up`.
- Тесты на pytest.
- Автоматическая OpenAPI-документация FastAPI.

Исходное тестовое задание вынесено в файл [`TASK.md`](TASK.md).

---

## Стек

- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x ORM
- PostgreSQL 16
- Alembic
- Docker / Docker Compose
- pytest

---

## Структура проекта

```text
.
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 0001_initial.py
├── app/
│   ├── api/
│   │   └── departments.py
│   ├── core/
│   │   ├── config.py
│   │   └── logging.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   ├── department.py
│   │   └── employee.py
│   ├── schemas/
│   │   ├── department.py
│   │   └── employee.py
│   ├── services/
│   │   └── departments.py
│   └── main.py
├── tests/
│   ├── conftest.py
│   └── test_departments.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── .env.example
├── .gitignore
├── .dockerignore
├── TASK.md
└── README.md
```

Разделение по слоям:

- `app/api` — HTTP-эндпоинты FastAPI;
- `app/schemas` — Pydantic-схемы запросов и ответов;
- `app/models` — SQLAlchemy ORM-модели;
- `app/services` — бизнес-логика;
- `app/db` — подключение к БД и сессии;
- `alembic` — миграции;
- `tests` — pytest-тесты.

---

## Быстрый запуск через Docker

### 1. Клонировать репозиторий

```bash
git clone https://github.com/exeD1n/org-structure-api.git
cd org-structure-api
```

### 2. Создать `.env`

```bash
cp .env.example .env
```

Содержимое по умолчанию:

```env
DATABASE_URL=postgresql+psycopg://org_user:org_password@db:5432/org_structure
LOG_LEVEL=INFO
```

### 3. Запустить приложение

```bash
docker compose up --build
```

При старте контейнера `api` автоматически выполняется:

```bash
alembic upgrade head
```

После этого запускается сервер:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Адреса после запуска

- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- Healthcheck: <http://localhost:8000/health>

Проверка healthcheck:

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:

```json
{
  "status": "ok"
}
```

---

## Миграции

Применить миграции вручную:

```bash
docker compose exec api alembic upgrade head
```

Откатить последнюю миграцию:

```bash
docker compose exec api alembic downgrade -1
```

Создать новую миграцию после изменения моделей:

```bash
docker compose exec api alembic revision --autogenerate -m "change schema"
```

---

## Тесты

Запуск тестов внутри контейнера:

```bash
docker compose exec api pytest -q
```

Тесты покрывают базовые сценарии:

- создание подразделения;
- создание сотрудника;
- получение дерева подразделений;
- запрет перемещения подразделения внутрь собственного поддерева;
- запрет дублей названий в одном родителе;
- разрешение одинаковых названий в разных родителях;
- удаление с переводом сотрудников через `mode=reassign`.

В тестах используется SQLite in-memory для скорости и изоляции бизнес-логики. Основное приложение в Docker работает с PostgreSQL.

---

## API

### 1. Создать подразделение

```http
POST /departments/
```

Пример запроса:

```bash
curl -X POST http://localhost:8000/departments/ \
  -H "Content-Type: application/json" \
  -d '{"name": "IT", "parent_id": null}'
```

Пример ответа:

```json
{
  "id": 1,
  "name": "IT",
  "parent_id": null,
  "created_at": "2026-05-20T10:00:00Z"
}
```

---

### 2. Создать дочернее подразделение

```bash
curl -X POST http://localhost:8000/departments/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Backend", "parent_id": 1}'
```

---

### 3. Создать сотрудника в подразделении

```http
POST /departments/{id}/employees/
```

Пример:

```bash
curl -X POST http://localhost:8000/departments/2/employees/ \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Ivan Ivanov", "position": "Backend Developer", "hired_at": "2024-01-15"}'
```

Если подразделение не существует, API вернёт `404`.

---

### 4. Получить подразделение с деревом

```http
GET /departments/{id}?depth=2&include_employees=true
```

Пример:

```bash
curl "http://localhost:8000/departments/1?depth=2&include_employees=true"
```

Параметры:

- `depth` — глубина дочерних подразделений, диапазон `0..5`, по умолчанию `1`;
- `include_employees` — включать ли сотрудников, по умолчанию `true`.

Пример структуры ответа:

```json
{
  "department": {
    "id": 1,
    "name": "IT",
    "parent_id": null,
    "created_at": "2026-05-20T10:00:00Z"
  },
  "employees": [],
  "children": [
    {
      "department": {
        "id": 2,
        "name": "Backend",
        "parent_id": 1,
        "created_at": "2026-05-20T10:01:00Z"
      },
      "employees": [
        {
          "id": 1,
          "department_id": 2,
          "full_name": "Ivan Ivanov",
          "position": "Backend Developer",
          "hired_at": "2024-01-15",
          "created_at": "2026-05-20T10:02:00Z"
        }
      ],
      "children": []
    }
  ]
}
```

---

### 5. Обновить / переместить подразделение

```http
PATCH /departments/{id}
```

Переименовать подразделение:

```bash
curl -X PATCH http://localhost:8000/departments/2 \
  -H "Content-Type: application/json" \
  -d '{"name": "Platform"}'
```

Переместить подразделение в другое:

```bash
curl -X PATCH http://localhost:8000/departments/2 \
  -H "Content-Type: application/json" \
  -d '{"parent_id": 3}'
```

Сделать подразделение корневым:

```bash
curl -X PATCH http://localhost:8000/departments/2 \
  -H "Content-Type: application/json" \
  -d '{"parent_id": null}'
```

Ограничения:

- нельзя сделать подразделение родителем самого себя;
- нельзя переместить подразделение внутрь собственного поддерева;
- нельзя создать дубликат названия внутри одного `parent_id`.

При нарушении дерева API возвращает `409 Conflict`.

---

### 6. Удалить подразделение каскадом

```http
DELETE /departments/{id}?mode=cascade
```

Пример:

```bash
curl -X DELETE "http://localhost:8000/departments/2?mode=cascade"
```

Удаляет:

- само подразделение;
- всех сотрудников подразделения;
- все дочерние подразделения;
- сотрудников дочерних подразделений.

Каскад реализован через ORM-связи и `ON DELETE CASCADE` в PostgreSQL.

---

### 7. Удалить подразделение с переводом сотрудников

```http
DELETE /departments/{id}?mode=reassign&reassign_to_department_id={target_id}
```

Пример:

```bash
curl -X DELETE "http://localhost:8000/departments/2?mode=reassign&reassign_to_department_id=3"
```

Поведение режима `reassign`:

1. сотрудники удаляемого подразделения переводятся в `reassign_to_department_id`;
2. прямые дочерние подразделения удаляемого подразделения поднимаются на уровень родителя удаляемого подразделения;
3. если при подъёме дочерних подразделений возникает конфликт имён внутри одного родителя, API возвращает `409 Conflict`;
4. удаляемое подразделение удаляется.

---

## Бизнес-валидация

### Department

- `name` обязателен;
- пробелы по краям удаляются;
- после trim значение не может быть пустым;
- длина `1..200`;
- название уникально внутри одного `parent_id`;
- для корневых подразделений `parent_id = null` название также уникально.

### Employee

- `full_name` обязателен;
- `position` обязателен;
- пробелы по краям удаляются;
- после trim значения не могут быть пустыми;
- длина каждого поля `1..200`;
- `hired_at` опционален.

### Tree constraints

- нельзя назначить подразделение родителем самого себя;
- нельзя переместить подразделение внутрь собственного поддерева;
- нельзя создать цикл в дереве подразделений.

---

## Проверка через Swagger UI

1. Запустить проект:

```bash
docker compose up --build
```

2. Открыть:

```text
http://localhost:8000/docs
```

3. Выполнить запросы в таком порядке:

```text
POST /departments/                  создать IT
POST /departments/                  создать Backend с parent_id = IT.id
POST /departments/{id}/employees/   создать сотрудника в Backend
GET  /departments/{id}              получить IT с depth=2
PATCH /departments/{id}             переименовать или переместить Backend
DELETE /departments/{id}            удалить подразделение
```

---

## Публикация в GitHub

Рекомендуемое имя публичного репозитория:

```text
org-structure-api
```

### Вариант 1. Через GitHub CLI

```bash
git init
git add .
git commit -m "Initial commit: organization structure API"

gh auth login
gh repo create exeD1n/org-structure-api \
  --public \
  --description "FastAPI API for organization departments and employees" \
  --source=. \
  --remote=origin \
  --push
```

После публикации репозиторий будет доступен по адресу:

```text
https://github.com/exeD1n/org-structure-api
```

### Вариант 2. Через сайт GitHub

1. Открыть GitHub.
2. Создать новый публичный репозиторий `org-structure-api`.
3. Не добавлять README, `.gitignore` и license через интерфейс GitHub, потому что эти файлы уже есть в проекте.
4. Выполнить локально:

```bash
git init
git add .
git commit -m "Initial commit: organization structure API"
git branch -M main
git remote add origin https://github.com/exeD1n/org-structure-api.git
git push -u origin main
```

---

## Полная перезагрузка Docker-окружения

Если нужно удалить контейнеры и volume PostgreSQL:

```bash
docker compose down -v
```

После этого можно заново поднять проект:

```bash
docker compose up --build
```

---

## Возможные проблемы

### Порт 8000 уже занят

Изменить порт в `docker-compose.yml`:

```yaml
ports:
  - "8001:8000"
```

После этого API будет доступен на:

```text
http://localhost:8001
```

### Порт 5432 уже занят

Если локально уже запущен PostgreSQL, можно изменить внешний порт:

```yaml
ports:
  - "5433:5432"
```

Внутри Docker-сети приложение всё равно подключается к `db:5432`, поэтому `DATABASE_URL` менять не нужно.

### Нужно пересоздать базу

```bash
docker compose down -v
docker compose up --build
```

---

## Пример сценария проверки

```bash
# 1. Создать корневой департамент
curl -X POST http://localhost:8000/departments/ \
  -H "Content-Type: application/json" \
  -d '{"name": "IT"}'

# 2. Создать дочерний департамент
curl -X POST http://localhost:8000/departments/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Backend", "parent_id": 1}'

# 3. Создать сотрудника
curl -X POST http://localhost:8000/departments/2/employees/ \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Ivan Ivanov", "position": "Backend Developer"}'

# 4. Получить дерево
curl "http://localhost:8000/departments/1?depth=2&include_employees=true"

# 5. Проверить запрет цикла
curl -X PATCH http://localhost:8000/departments/1 \
  -H "Content-Type: application/json" \
  -d '{"parent_id": 2}'
```

Ожидаемо последний запрос вернёт `409 Conflict`.
