# Zetrix backend v2 — запуск и фактический контракт

Это инструкция к локальному backend v2 для React-кабинета `/app`. Целевой состав
MVP и дальнейшие этапы описаны в [MVP.md](MVP.md).

## Что реализовано

- Session-вход, выход, текущий пользователь, выдача CSRF token.
- Организации и членство: owner / admin / analyst / viewer.
- Проекты в USD, сценарии, последовательные неизменяемые версии вводных.
- Синхронный расчёт прямого изменения затрат на Decimal.
- Сохранённые inputs/results/engine_version/assumptions, JSON download.
- Идемпотентность запуска, контроль доступа, пагинация, audit записей.
- Ручные версии закупочного портфеля и CSV preview/confirm без файлового upload.
- Реестр источников, версии событий, публикация и отзыв редактором; сценарии
  закрепляют выбранную опубликованную версию события.
- Контекст и влияние расчёта по строкам портфеля; записи решений и CSV-экспорт.
- Миграции новой схемы; отдельные настройки тестов и MVP.

Нет публичной регистрации, email-приглашений, AI, фонового экспорта или платежей.
Нет проверенного набора реальных внешних источников: реестр и события пока
заполняются вручную. Первые пользователи создаются оператором.

## Изолированная проверка без PostgreSQL, Redis и секретов

Python 3.11+; из корня репозитория, в отдельном virtualenv:

```sh
python3.11 -m venv .venv-mvp
.venv-mvp/bin/python -m pip install -r requirements/mvp.txt
.venv-mvp/bin/python -m django test apps.workspaces apps.scenario_engine apps.evidence apps.decisions --settings=config.settings.workspace_test
.venv-mvp/bin/python -m django makemigrations workspaces evidence decisions --check --dry-run --settings=config.settings.workspace_test
```

`workspace_test` использует временную SQLite и быстрый тестовый password hasher.
**Не запускать сервер для пользователей с этими настройками.** Команда тестов
не применяет миграции к существующей базе проекта. SQLite не проверяет поведение
блокировок PostgreSQL; проверка гонок на PostgreSQL остаётся этапом перед пилотом.

## Профиль MVP

`DJANGO_SETTINGS_MODULE=config.settings.mvp` загружает изолированный контур v2:
auth, sessions, DRF, workspaces, evidence и decisions. URLConf
`config.workspace_urls` содержит только `/api/v2/`.
Нет legacy `/api/v1/`, admin UI, публичного MEDIA и прежних periodic tasks.
Обычные `base.py`/`config.urls` дополнительно знают v2 для разработки старого
проекта, но **не изолируют его старые API** — для пилота нужен отдельный профиль.

Переменные окружения передаются процессу сервером/секрет-хранилищем; этот профиль
не читает старый `.env` автоматически:

| Переменная | Назначение |
| --- | --- |
| `DJANGO_SECRET_KEY` | Секрет с достаточной энтропией, без значения по умолчанию |
| `DJANGO_ALLOWED_HOSTS` | Разрешённые hostnames через запятую |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Отдельная PostgreSQL база MVP и пользователь |
| `DB_HOST`, `DB_PORT` | По умолчанию 127.0.0.1:5432 |
| `REDIS_URL` | Приватный Redis для общего throttle cache |
| `CSRF_TRUSTED_ORIGINS` | HTTPS origins при необходимости, через запятую |
| `DJANGO_TRUST_HTTPS_PROXY` | `true` только за proxy, удаляющим чужие forwarding headers |
| `DJANGO_NUM_PROXIES` | Число доверенных proxy для определения IP; default 0 |

В согласованном окружении после создания БД и подготовки backup:

```sh
export DJANGO_SETTINGS_MODULE=config.settings.mvp
.venv-mvp/bin/python -m django check
.venv-mvp/bin/python -m django migrate --plan
.venv-mvp/bin/python -m django migrate
.venv-mvp/bin/python -m django createsuperuser
.venv-mvp/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000
```

Команды выше — инструкция, в текущей итерации к рабочей БД они не применялись.
Обычных пилотных пользователей оператор создаёт через доверенный provisioning
процесс с `create_user`/`set_password`; прав superuser для API не требуется.
Новый owner добавляет уже существующий username в организацию. Отправка писем
или самостоятельная регистрация требуют следующих этапов.

Профиль требует HTTPS: Secure cookies и redirect включены. Reverse proxy
публикует лендинг/кабинет и `/api/v2/` на одном origin. Redis cache необходим
для общего лимита между workers. DRF throttling — базовый лимит, не замена
edge-защите от перебора/DoS. Не запускать Celery worker для текущих расчётов:
они синхронны.

## Фактические маршруты

Префикс `/api/v2/`; `org`, `project`, `scenario`, `run`, `member` — UUID.
Пути заканчиваются `/`. DELETE/PUT/PATCH исторических записей отсутствуют.

| Метод | Путь | Результат |
| --- | --- | --- |
| GET | `auth/csrf/` | `data.csrf_token`, CSRF cookie |
| POST | `auth/login/` | Session cookie, user, новый CSRF token |
| POST | `auth/logout/` | Завершение session |
| GET | `auth/me/` | id, username |
| GET/POST | `organizations/` | Список своих / создать и стать owner |
| GET | `organizations/{org}/` | Организация и роль текущего участника |
| GET/POST | `organizations/{org}/projects/` | Список / создать `{title,currency}` |
| GET | `organizations/{org}/projects/{project}/` | Проект |
| GET/POST | `organizations/{org}/projects/{project}/portfolio/` | Версии портфеля / новая версия вручную |
| POST | `organizations/{org}/projects/{project}/portfolio/preview/` | Проверить CSV и показать предпросмотр |
| POST | `organizations/{org}/projects/{project}/portfolio/imports/{import}/confirm/` | Подтвердить импорт; повтор безопасен |
| GET/POST | `organizations/{org}/projects/{project}/scenarios/` | Список / создать `{title,inputs}` |
| GET | `organizations/{org}/projects/{project}/scenarios/{scenario}/` | Сценарий и последняя revision |
| GET/POST | `organizations/{org}/projects/{project}/scenarios/{scenario}/revisions/` | История / добавить `{inputs}` |
| GET/POST | `organizations/{org}/runs/` | История / запуск `{revision_id}` |
| GET | `organizations/{org}/runs/{run}/` | Сохранённый результат |
| GET | `organizations/{org}/runs/{run}/export/` | JSON attachment; analyst/admin/owner |
| GET | `organizations/{org}/runs/{run}/csv/` | CSV attachment; analyst/admin/owner |
| GET/POST | `organizations/{org}/decisions/` | Список / неизменяемая запись решения с `Idempotency-Key` |
| GET | `organizations/{org}/decisions/{decision}/` | Решение и снимки связанных расчётов |
| GET/POST | `organizations/{org}/members/` | Участники / добавить `{username,role}` |
| PATCH | `organizations/{org}/members/{member}/` | Изменить `{role,active}` с проверкой owner |
| GET/POST | `evidence/sources/` | Реестр источников / добавить (только staff) |
| GET/POST | `evidence/events/` | События / создать черновик (только staff) |
| GET | `evidence/events/{event}/` | Карточка и статус публикации |
| GET/POST | `evidence/events/{event}/revisions/` | Версии / новая версия (только staff) |
| POST | `evidence/events/{event}/publish/` | Опубликовать конкретную версию (только staff) |
| POST | `evidence/events/{event}/revoke/` | Отозвать публикацию (только staff) |

Списки: `?limit=20&offset=0`, limit максимум 50, offset максимум 100000.
Анонимный доступ к session API возвращает 403; клиент сверяется с `/auth/me/`
и кодом ошибки, не трактует каждый 403 как истечение сессии.

### Авторизация браузера

1. GET `auth/csrf/` с `credentials: 'same-origin'`.
2. POST login JSON `{username,password}`, header `X-CSRFToken` из ответа.
3. После login заменить token на новый `data.csrf_token` (session/CSRF rotation).
4. Во всех POST/PATCH отправлять CSRF header и session cookie. После обновления
   страницы кабинет восстанавливает сессию через `auth/me/`, а перед следующей
   записью получает актуальный token через `auth/csrf/`.
5. Refresh/access JWT в localStorage не нужны. Пароли не сохраняются в клиентском состоянии дольше запроса.

### Создание сценария и запуск

```json
{
  "title": "Удорожание импорта — 3 месяца",
  "inputs": {
    "kind": "trade",
    "monthly_cost": "1000000.00",
    "exposure": "35.00",
    "shock": "20.00",
    "months": 3,
    "currency": "USD"
  }
}
```

Ответ создания содержит `data.revisions[0].id`. Затем POST на
`organizations/{org}/runs/` с `{ "revision_id": "..." }` и уникальным
`Idempotency-Key`. Первый результат — 201, повтор того же запроса — 200 и тот
же run; ключ с другой revision — 409. Расчёт завершён в ответе: нет фиктивного queued.

В этом примере `additional_total` = `"210000.00"`, `baseline_total` =
`"3000000.00"`, `scenario_total` = `"3210000.00"`. Новая revision не меняет run.
JSON export содержит тот же объект результата в общей API-оболочке.

### Портфель, событие и решение

`POST .../portfolio/` создаёт полную новую версию из `lines` в USD. Для CSV
отправьте текст в `{ "csv": "..." }` на `.../portfolio/preview/`, проверьте
строки и сумму, затем подтвердите `.../portfolio/imports/{import}/confirm/`
с пустым JSON. Повтор confirm возвращает ту же версию. Сценарная revision может
закрепить `portfolio_revision_id`, список `affected_line_ids` и
`evidence_revision_id`; run сохраняет контекст и влияние каждой строки.

Событие создаётся черновиком, после проверки staff публикует конкретную версию.
Обычному участнику доступна опубликованная история, а новая черновая версия
не подменяет действующую публикацию. Решение с названием и обоснованием
сохраняет снимки выбранных run; CSV выдаётся только после проверки доступа.

### Формат и ошибки

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": { "request_id": "..." }
}
```

Ошибка: success=false, data=null, error содержит code/message/field_errors.
Также возвращается `X-Request-ID`. Ответы не кэшируются (`Cache-Control: no-store`).
Поля автора, организации, результатов и статуса нельзя подменить в теле;
неизвестные поля отклоняются. Неверные параметры — 400, роль — 403, чужой
ресурс — 404, конфликт — 409, throttle — 429. Необработанные ошибки дают
безопасный 500; подробности остаются в серверном журнале.

## Границы гарантии истории

Записи revision/run/audit защищены от изменения через instance save/delete
и обычные QuerySet update/delete. API не предоставляет изменяющие маршруты.
Администратор БД/raw SQL технически может изменить данные; защита уровня БД,
роль migration-only и криптографическая аттестация истории пока не реализованы.
Проверки FK и tenant выполняются сервисами; код вне этих сервисов обязан
соблюдать те же инварианты. Сервис блокирует строку организации для сериализации
записей и изменений членства. Это простой вариант для первого bounded workload.

## Фактические проверки

- В текущей локальной итерации прошли 55 backend unit/integration-тестов на
  временной SQLite, включая полный session/CSRF-путь.
- Покрытие `apps.workspaces`, `apps.evidence`, `apps.decisions` и
  `apps.scenario_engine` вместе — 95% с ветвлениями (1077 statements,
  182 branches); тестовые файлы, миграции и management-команды исключены.
  Покрытие всего репозитория не измерено.
- `makemigrations workspaces evidence decisions --check --dry-run`: нет
  незаписанных изменений модели.
- Профиль MVP загружается; legacy API, admin и media не маршрутизируются.
- Локально пройдены браузерные пути вход → организация → проект → портфель →
  сценарий → run → refresh и источник → публикация → выбор → run.
- PostgreSQL/Redis integration, гонки между процессами и production rollout ещё не проверены.

## Следующий этап

Локальный React `/app` подключён. Перед пилотом нужны отдельная PostgreSQL БД,
проверка конкурентных записей, Redis и reverse proxy, разрешённая реальная
выборка источников, процедуры доступа и восстановления. Публичный лендинг
по-прежнему использует локальный калькулятор и не отправляет его вводные в API.
