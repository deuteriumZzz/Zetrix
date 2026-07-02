# Zetrix — Global Opportunity Explorer

Платформа для предпринимателей и людей, которые хотят купить недвижимость
или открыть бизнес за рубежом. Интерактивный 3D-глобус со всеми странами
мира, drill-down до регионов там, где они есть, и два переключаемых слоя
данных: **Housing** (тренд цен аренды/недвижимости, скрейпинг Airbnb/
Booking) и **Business** (юридическая сложность — право собственности
иностранцев, регистрация бизнеса, налоги, инвесторские визы — через
LLM-агрегацию с проверкой человеком перед публикацией).

Изначально проект стартовал как Bali-only трекер цен аренды; сейчас гео-
модель и весь бэкенд обобщены под любую страну мира — Бали остаётся
первым живым примером Housing-слоя (194 страны засеяны, но только
Индонезия/Бали имеет реальные скрейпленные данные).

## Что делает проект

1. **Скрейпит** Airbnb/Booking через headless Chromium (Playwright) —
   сейчас настроено на 6 районов Бали, инфраструктура работает для любой
   страны/региона в новой гео-модели.
2. **Агрегирует** дневные min/max/avg/median цены по стране/региону/типу
   рынка/типу недвижимости, с % изменения к предыдущему дню.
3. **Оценивает бизнес-климат**: для каждой страны (с опциональным
   переопределением по региону) — право собственности иностранцев,
   сложность регистрации бизнеса, налоги, инвесторские визы. Данные
   генерирует LLM (Groq), но **ничего не публикуется без ручной
   проверки** — защита от галлюцинаций.
4. **Оповещает** подписчиков в Telegram при изменении цены сверх порога.
5. **Формирует** PDF/CSV-отчёты по цене за период.
6. **Оркестрирует** весь дневной пайплайн (скрейп → агрегация → отчёт →
   уведомление) через Apache Airflow, читающий активные источники из
   Django API (не статичный YAML).
7. **Отдаёт** всё через REST API (DRF), 3D-глобус на React, и
   Telegram-бота со ступенчатым пикером continent→country→region.

## Архитектура

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Airflow    │────▶│  Django API  │◀───▶│  PostgreSQL  │
│ (оркестратор,│     │  (DRF, JWT + │     │  + PostGIS   │
│  DB-driven)  │     │   DRF Token) │     └─────────────┘
└─────────────┘     └──────┬───────┘
                            │
              ┌─────────────┼─────────────┬──────────────┐
              ▼             ▼             ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
        │  Celery   │  │  Celery   │  │ Telegram  │  │ Groq │
        │  Worker   │  │   Beat    │  │    Бот    │  │   LLM    │
        └────┬──────┘  └──────────┘  └──────────┘  └──────────┘
             │
             ▼
      ┌─────────────┐
      │  Playwright  │
      │  (Chromium)  │
      └─────────────┘

     React Frontend (глобус, Vite) ── обращается к ── Django API
```

Бэкенд на Django 5 + DRF, 9 приложений в `apps/`:

| Приложение | Зона ответственности |
| --- | --- |
| `core` | Общие абстрактные модели, миксины |
| `geo` | **Иерархия Continent → Country → Region** (самоссылочный, PostGIS-геометрия), 194 страны, публичный read-only API |
| `opportunity` | Бизнес-климат: `BusinessClimateProfile`, LLM-пайплайн (Groq), publish-gating через ревью-воркфлоу |
| `sources` | `Source`/`ScrapeJob`, скрейперы (Strategy+Factory) — обобщены под любую страну/регион |
| `prices` | `PriceRecord`/`DailyAggregate`, агрегация |
| `reports` | PDF/CSV-генерация |
| `notifications` | Подписки, алерты, Telegram/Slack-отправители |
| `users` | Профиль пользователя (Telegram chat ID, предпочитаемая страна/регион) |
| `bot` | Telegram-бот со ступенчатым пикером |

### Гео-модель (`apps/geo`)

`Continent` → `Country` (194, ISO-коды, центроид, граница-полигон через
PostGIS) → `Region` (самоссылочная: `parent` + `level` —
province/city/neighborhood, так Bali=province и Canggu=city внутри неё
живут в одной таблице). Большинство стран не имеют дочерних `Region` —
это нормальное состояние, не крайний случай.

### Бизнес-климат (`apps/opportunity`)

`BusinessClimateProfile` (страна, опционально регион-переопределение) +
`ClimateDataSource` (цитаты) + `BusinessClimateReview` (воркфлоу
модерации). **Ключевой механизм безопасности**: профиль виден в публичном
API только после `APPROVED`-ревью (`published_review`); регенерация не
отзывает уже опубликованную версию. Пайплайн: `apps/opportunity/llm.py`
(Groq через OpenAI-совместимый API) + `apps/opportunity/indexes/`
(заготовка под индексы вроде Heritage Economic Freedom, Property Rights
Alliance IPRI — сами клиенты пока не реализованы, нужна проверка
лицензий). Требует `GROQ_API_KEY` (бесплатный).

### Скрейпинг (`apps/sources/scrapers/`)

`BaseScraper` принимает `country`/`region` (объекты гео-модели, не
строки), строит поисковый запрос динамически (`f"{region.name}, {country.name}"`).
`run()` никогда не бросает исключение — сбой скрейпинга деградирует до
пустого результата. `AirbnbScraper`/`BookingScraper` парсят карточки
через BeautifulSoup + регэкспы, привязанные к стабильным ориентирам
(например рейтинг ищется как число прямо перед `(N reviews)`, чтобы не
спутать с количеством ванных комнат).

### Оркестрация

DAG `bali_market_analyzer` (`airflow/dags/market_analyzer.py`) читает
активные источники через Django API (`GET /sources/?is_active=true`,
постранично) — добавление источника теперь действие в БД, а не редеплой
DAG. Per-source: скрейп → агрегация → отчёт → Telegram. Проверено живым
прогоном — полный DagRun завершается `success` по всем 7 источникам.

## API

DRF, `/api/v1/`, JWT для пользователей + DRF `TokenAuthentication` для
сервисных вызовов (Airflow).

| Эндпоинт | Примечание |
| --- | --- |
| `/api/v1/geo/continents/`, `/countries/`, `/regions/` | Публичные, read-only, GeoJSON для стран |
| `/api/v1/opportunity/countries/{iso2}/[?region=uuid]` | Только опубликованные профили; region-override с фолбэком на страну |
| `/api/v1/sources/` | CRUD; `POST {id}/trigger/` — ставит скрейп в очередь |
| `/api/v1/prices/records/trend/?country=ISO2&region=uuid&days=30` | Тренд цен |
| `/api/v1/reports/`, `/api/v1/notifications/subscriptions/` | Как раньше, теперь с `country`/`region` FK вместо строки |

## Telegram-бот

Ступенчатый пикер: `/prices` без аргумента → континент → страна
(постранично, 8/стр.) → регион (если есть). `/prices Indonesia` —
текстовый поиск в обход пикера. Геолокация ищет ближайший `Region`/
`Country` в БД.

## Frontend (`frontend/`)

React 18 + Vite 5 + Tailwind + TanStack Query + Zustand.
Глобус (`components/Globe.tsx`) — точки по всем 194 странам (не полные
GeoJSON-полигоны — упрощение), клик по стране с регионами → drill-down,
без регионов → сразу страница страны. Переключатель Housing/Business
слоёв. `CountryDetail.tsx` ветвится на график цен (Housing) или
`BusinessScorecard.tsx` (Business). Поиск страны (`CountryPicker.tsx`)
переиспользуется в Reports/Subscriptions вместо `<select>` на 6 опций.

## Запуск

```bash
cp .env.example .env   # GROQ_API_KEY, TELEGRAM_BOT_TOKEN и т.д.
docker compose up -d
cd frontend && npm install && npm run dev
```

Сидинг гео-данных (194 страны + Бали-иерархия сеются миграцией
автоматически при `migrate`):
```bash
docker compose exec web python manage.py seed_geo   # доп. метаданные (валюта, флаг)
docker compose exec web python manage.py seed_data --days 30   # demo-цены для Бали
```

| Сервис | URL |
| --- | --- |
| Django API / Admin | http://localhost:8000 / `/admin/` |
| Swagger | http://localhost:8000/api/v1/docs/ |
| Frontend | http://localhost:3000 |
| Airflow | http://localhost:8088 |
| PostgreSQL (+PostGIS) | localhost:5432 |

## Тесты

```bash
docker compose exec web pytest        # 80 тестов
docker compose exec web coverage run -m pytest && docker compose exec web coverage report
```

`web` собирается с `requirements/development.txt` (build-arg
`REQUIREMENTS_FILE` в `Dockerfile`) — остальные сервисы на облегчённом
`production.txt`.

## Стек

Django 5 · DRF · PostgreSQL + PostGIS · Celery/Celery Beat · Redis ·
Apache Airflow 2.9 · Playwright · Groq (OpenAI SDK) · React 18/Vite 5 ·
react-globe.gl · python-telegram-bot · Docker Compose.
