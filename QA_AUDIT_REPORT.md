# QA / Security Audit — Alma (независимый проход)

**ID отчёта: 856362**
Дата: 2026-08-20. Аудитор: автономный QA + Security агент.
Предыдущие проходы: **168404** (15 находок) и **608634** (4 находки: BUG-501…504).
Этот проход — свежая независимая проверка живого инстанса + верификация, что находки
прошлых проходов действительно закрыты в текущем коде.

## Что запускалось локально

- **backend** FastAPI на `127.0.0.1:8100` из venv (`backend/.venv/Scripts/python.exe`),
  SQLite `data/alma.db`. `ALMA_JWT_SECRET` задан агентом (в репо он пуст — «ещё не
  задан»), budgets=40. ai/billing выключены (нет ключей — по закону владельца).
- **web** Next.js 15.5.23 на `127.0.0.1:3000` (уже был поднят, PID 24284),
  `NEXT_PUBLIC_ALMA_API=http://localhost:8100`.

Прод/внешние серверы не трогались. Код проекта не менялся (только `QA_AUDIT_REPORT.md`,
`qa_evidence/`, `qa_progress.md`, `qa856362-*.png`). Среда: Windows 10.

---

## Главный итог

**Новых значимых дефектов не найдено. Все четыре находки прошлого прохода (608634)
подтверждены как ИСПРАВЛЕННЫЕ в текущем коде и проверены живьём.** Единственная новая
находка — мелкий hardening заголовков на backend-API (BUG-856-01, LOW).

Это зрелая, многократно проверенная кодовая база: валидация железная, аутентификация не
обходится, пейволл стоит перед моделью, инъекций нет, фронт устойчив к сетевым сбоям.

---

## Верификация находок прошлого прохода (608634) — все закрыты

| Прошлая находка | Проверка сейчас | Статус |
|---|---|---|
| BUG-501 NaN/Infinity в float-теле → 500 | `latitude:NaN` / `longitude:Infinity` → **422** (было 500). В `schemas.py:37-38` стоит `allow_inf_nan=False` | ✅ FIXED |
| BUG-502 пустой `ALMA_JWT_SECRET` → 500 на первом запросе | `config.py:95` `@field_validator` сводит пустую строку к дефолту, прод её же отвергает на старте | ✅ FIXED |
| BUG-503 двойная отправка формы входа | `SignInPanel.tsx:171` синхронный `sendingRef`; 3 быстрых клика → 1 запрос magic-link (второй — `/consume` авто-логина) | ✅ FIXED |
| BUG-504 тап-таргеты < 44px | утилита `.tap44::after` (globals.css:860) даёт 44px невидимую хит-эрию; навешена на футер и точки карусели | ✅ ADDRESSED |

Доказательства: `qa_evidence/` (см. ниже).

---

## НОВЫЕ находки

### BUG-856-01 — Backend-API отдаёт ответы без security-заголовков
**[ИСПРАВЛЕНО]** Добавлен внешний ASGI-middleware `SecurityHeaders`
(`backend/alma/api/app.py`), ставящий `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` на **каждый** ответ,
включая 413 от `MaxBodySize`. Заголовки не затираются, если маршрут поставил
свой. Проверено живьём (`curl -D-` на `/health`, `/v1/events`, `/v1/systems/natal`,
413) и тестом `test_every_api_response_carries_the_security_headers`
(`tests/test_hardening.py`). `Server: uvicorn` не трогаем на уровне приложения:
uvicorn дописывает его снаружи ASGI, а в проде край (`deploy/Caddyfile:87` `-Server`)
его уже срезает; на уровне приложения его можно убрать только флагом запуска
`--no-server-header`. Регрессий нет: весь `test_hardening.py` (30 тестов) зелёный.
**Приоритет: LOW (defense-in-depth)**
**Где:** `backend/alma/api/app.py:343-363` — на приложении навешены только `CORSMiddleware`
и `MaxBodySize`. Нет middleware, добавляющего `X-Content-Type-Options: nosniff`,
`X-Frame-Options`, `Referrer-Policy`. Также в ответе виден `server: uvicorn`.

**Проблема:** web-фронт (`next.config.ts:73-80`) отдаёт полный, продуманный набор
(CSP, HSTS, nosniff, frame DENY, Referrer-Policy, Permissions-Policy) — проверено живьём.
Backend-API (`:8100`) не отдаёт ничего из этого. Для чисто-JSON API риск невелик (тело
всегда `application/json`, не рендерится как HTML), но:
- JSON-ответ, открытый прямой ссылкой в браузере, без `nosniff` может быть подвергнут
  MIME-sniffing;
- `server: uvicorn` — раскрытие версии/стека сервера (мелкое info-disclosure).

**Как воспроизвести:**
```
curl -s -D - -o /dev/null -X POST http://127.0.0.1:8100/v1/systems/natal \
  -H "Authorization: Bearer <t>" -H "Content-Type: application/json" \
  -d '{"birth":{"birth_date":"1990-05-15","latitude":0,"longitude":0,"timezone":"UTC"}}'
# в заголовках: только `server: uvicorn`, `content-type: application/json`.
# Нет X-Content-Type-Options / X-Frame-Options / Referrer-Policy.
```
Контраст: `curl -D - http://localhost:3000/` отдаёт все шесть заголовков.

**Ожидается:** те же базовые заголовки (как минимум `X-Content-Type-Options: nosniff`)
на API-ответах; скрыть/переопределить `server`.
**Доказательство:** `qa_evidence/api_headers_856362.txt`, `qa_evidence/web_headers_856362.txt`.
**Что исправить:** в `backend/alma/api/app.py` добавить лёгкий middleware, ставящий на
каждый ответ `X-Content-Type-Options: nosniff` (и по вкусу `X-Frame-Options: DENY`,
`Referrer-Policy: no-referrer`), а также убрать/заменить `Server`-заголовок (например,
запускать uvicorn с `--no-server-header` или переопределять заголовок в middleware).
Тест: `curl -D-` любого `/v1/*` должен содержать `x-content-type-options: nosniff`.

---

## Что проверено вживую и признано крепким (без находок)

**ЭТАП 1 — запуск.** backend `/health` ok, `/ready` честно перечисляет `missing`
(ANTHROPIC_API_KEY, DATABASE_URL, PADDLE_*, sign-in method) — по закону владельца.
46 роутов. web 200, гидратация без краша.

**ЭТАП 2 — Backend/API.** Батарея валидации: `latitude` строкой / 91 / −91, пустое тело,
битый JSON, неизвестная TZ (`Mars/Olympus`), год 1000/3000, дата `15-05-1990`,
`birth_time` `99:99`/`24:00`, лишнее поле, `gender:"other"`, имя 10000 символов,
`profile_id` массивом, `birth` массивом/null, дата `1990-13-45`/`1990-02-30` — **всё 422/400,
ни одного 500**. Unicode-имя → 201. Методы PUT/OPTIONS/TRACE → 405.

**Аутентификация/авторизация.** Гостевой минт по `GET /v1/auth/session`. Форджинг JWT:
`alg=none` с чужим `sub` → 404 (не имперсонирует); HS256 с неправильным секретом → 404.
IDOR: B читает/удаляет профиль A → 404, A цел. Провайдеры google/apple без ключа → 401
с понятным текстом.

**Пейволл (законы владельца).** Закрытая глава `portrait` → **200 с `locked:true`,
`reading:null`, `access.allowed:false`, без обращения к модели** (нет 503) — стена прав
стоит перед генерацией. Бесплатная `core` → 503 (нет AI-ключа, ожидаемо). Второй
сохранённый человек сверх лимита → **402 `partner_limit`**. Числа отдаются бесплатно.

**Rate-limit / размеры.** 25× natal → 20×200, затем 429 (`SYSTEMS_CALCS_PER_MINUTE=20`).
Тело 2 МБ → 413. magic-link → есть окно.

**Инъекции / CORS.** SQLi `/places/search?q=' OR 1=1--` → 200 `[]` (параметризовано).
CORS: evil-origin → нет `Access-Control-Allow-Origin`; `localhost:3000` → ACAO есть.
`debug_token` в ответе magic-link гейтится `local_sandbox()` (белый список env **и**
localhost в base_url) — в проде не течёт (`deps.py:447`).

**ЭТАП 4/5 — Frontend.** home, sign-in и 7 legal-страниц — все 200, **0 console errors**
(7 warnings — dev-mode CSS preload от `next dev`, не продуктовый баг). Форма входа:
пустой submit → «That does not look like an email address»; XSS `<img onerror>` в поле →
**не исполнился**, вход санитайзится; сетевой сбой (fetch reject) → «The link could not be
sent. Try again in a moment.», кнопка снова активна для повтора. Мобильный бургер
(44×44) открывает/закрывает меню. Дата-пикер — доступный listbox (роли option/listbox).
Пустая дата на CTA «Show my first insight» → мягкий nudge, без навигации/краша.

**Responsive.** Нет горизонтального overflow документа на 320/375/390/414/768/1024/1280/
1440/1920 (декоративные aura/comet/marquee живут в overflow-hidden контейнерах). Дизайн
чистый и выровнен на 320/768/1920 (скриншоты). Зодиакальное колесо, липкий нижний бар,
FAQ-аккордеоны, карусель — целы.

**ЭТАП 7 — Performance.** health/catalogue/places — 2–6 мс; natal холодный 87 мс, тёплый
(кэш) 8 мс; compatibility 121 мс; transits(365) — 3.0 с (самая тяжёлая, документирована в
`schemas.py`, под throttle). Home-страница делает ровно 2 API-запроса на загрузку
(catalogue + events) — **дублей и N+1 нет**.

---

## «Требует проверки» / не покрыто и почему

- **Генеративные пути** (главы, чат, `/chat/stream`, spheres, текст дня) — требуют
  `ANTHROPIC_API_KEY` (нет по закону владельца). Проверены только гейты *до* модели: они
  корректно отдают 503 `ai_unavailable`, ничего не считая.
- **Реальные вебхуки платежей** (Paddle/Dodo/AppStore/GooglePlay) и **списание кредита
  пары** — нет секретов процессоров и активной подписки. Пейволл-гейты проверены,
  собственно верификация покупки — нет.
- **Push (APNs/FCM)** — нет ключей.
- **Многоворкерные гонки** — локально один uvicorn; гонки между воркерами не
  воспроизводятся.
- **Мобильный клиент `mobile/flutter`** — вне периметра запущенного web/backend.
- **Полный сквозной journey-overlay с реальной датой** — открытие оверлея и happy-path
  генерации завязаны на AI-ключ; проверены вход в оверлей и валидация пустой даты.
- **CSP-нюанс:** web-CSP содержит `script-src 'unsafe-inline' 'unsafe-eval'` — вынужденный
  компромисс Next.js + Google GSI, отдельно как дефект не заводится.

---

## Итоги

**Новых находок: 1.**
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 0
- LOW: 1 — BUG-856-01 (нет security-заголовков на backend-API)

**Все 4 находки прошлого прохода (608634) закрыты и подтверждены живьём.**

**Исправить в первую очередь:**
1. **BUG-856-01** — middleware с `X-Content-Type-Options: nosniff` на API-ответы,
   скрыть `Server`-заголовок. Дешёвый hardening, не эксплуатируемая дыра.

**Доказательства (`qa_evidence/`):** `api_headers_856362.txt`, `web_headers_856362.txt`,
`nan_infinity_500.txt` (было; теперь 422), а также скриншоты `qa856362-home-320.png`,
`qa856362-home-768.png`, `qa856362-home-1920.png` в корне.

ID отчёта: 856362
