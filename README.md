# Alma

Приложение-астролог: восемь систем (натальная карта, карта рождения, соляр,
астрокартография, нумерология, транзиты, совместимость, перекрёстный синтез),
расчёт всех восьми бесплатен навсегда, продаются написанные главы и подписка.
Семь языков: en, es, de, it, fr, pt-BR, ru.

Прод: API `https://api-alma.pazl.ai` · админка владельца `/admin` · сборки —
Codemagic → TestFlight (`codemagic.yaml`).

## Устройство репозитория

| Где | Что |
|---|---|
| `backend/` | FastAPI + Postgres (локально SQLite). Расчёты, генерация глав (Claude), письма, пуши, касса, админка |
| `mobile/flutter/alma/` | Приложение (iOS + Android, один код). **Единственное отгружаемое** |
| `mobile/ios/`, `mobile/android/` | Прежние нативные приложения — заморожены, не развиваются |
| `mobile/store/` | Данные сторов: `PRODUCTS.md` (товары и цены), `LISTING.md` (витрина), `DATA-INVENTORY.md` (что храним) — их читают тесты и гейт `check-listing.py` |
| `src/` | Сайт (Next.js) |
| `docs/DEPLOY.md` | Выкатка и эксплуатация сервера — инструкция владельца, её проверяют тесты |
| `CLAUDE.md` | Законы владельца и правила работы для Claude-сессий |

## Запуск локально

Бэкенд (порт 8018; для веб-клиента нужен CORS):

```bash
cd backend && ALMA_CORS_ORIGINS="http://127.0.0.1:8080,http://localhost:8080" \
  .venv/Scripts/python -m uvicorn alma.api.app:app --port 8018
```

Приложение — веб-сборкой (на Windows нет симулятора iOS):

```bash
cd mobile/flutter/alma
flutter build web --dart-define=ALMA_API_BASE=http://127.0.0.1:8018
cd build/web && python -m http.server 8080     # смотреть на 430×932
```

На маке — симулятор iPhone 17 Pro:

```bash
flutter build ios --simulator --debug --dart-define=ALMA_API_BASE=http://127.0.0.1:8018
```

После правки бэкенда **перезапускать процесс**: старый uvicorn держит старый
код и «чинит» уже починенное.

## Проверка перед коммитом

```bash
cd mobile/flutter/alma && flutter analyze && flutter test
cd backend && .venv/Scripts/python -m pytest -q      # ~10 минут
python mobile/store/check-listing.py
```

После правки любого `lib/l10n/app_*.arb` гонять **обе** стороны: серверные
тесты читают ARB напрямую (мягкие переносы, французские пробелы, паритет
ключей). «Готов» значит «видел на устройстве», не «тест зелёный».

## Выкатка бэкенда

Сервер: `ssh -i ~/.ssh/alma_deploy root@45.88.174.63` (хост `alma.pazl.ai`).
`/srv/alma` — **не** git-чекаут; код доставляется архивом, секреты (`.env`,
`secrets/`) живут только на сервере и архивом не задеваются:

```bash
git archive HEAD backend -o /tmp/b.tar
scp -i ~/.ssh/alma_deploy /tmp/b.tar root@45.88.174.63:/root/
ssh -i ~/.ssh/alma_deploy root@45.88.174.63 '
  cd /srv/alma && tar -xf /root/b.tar && rm /root/b.tar && cd backend &&
  docker compose exec -T db pg_dump -U alma alma | gzip > /srv/backups/before-deploy-$(date +%F).sql.gz &&
  docker compose build &&
  docker compose run --rm --no-deps app python -m tools.migrate &&
  docker compose up -d --force-recreate app'
curl -s https://api-alma.pazl.ai/health
```

Подробности эксплуатации (таймеры, копии, логи, откат) — `docs/DEPLOY.md`.
Клиент выкатывается сборкой в Codemagic; владелец запускает workflow сам.

## Законы продукта — коротко

Полный список с историей — `CLAUDE.md`. Несущие:

* **Бесплатное остаётся бесплатным.** Расчёты всех систем свободны навсегда;
  продаются слова. Никакого триала.
* **Цены не выдумываются** — только из каталога магазина (`AlmaStore.price`).
  Число на кнопке обязано совпасть со списанным.
* **Строки не выдумываются** ни на одном из семи языков; русский целиком на
  «ты»; французский несёт узкий неразрывный пробел перед `?!;:` и в «ёлочках».
* **Закрытая глава не пишется до оплаты** — стена прав стоит до вызова модели.
* **Никаких GPL-зависимостей и Swiss Ephemeris**; атрибуция данных —
  `backend/data/ATTRIBUTION.md`.
* **Секреты не коммитятся** (`backend/.env`, keystore, `.p8`); креды вводит
  владелец сам. Проверка: `git status --porcelain | grep -iE "\.env$|keystore|local\.properties|\.jks|\.p8"`.
