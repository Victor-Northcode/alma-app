# ТЗ · Поднять сайт pazl.ai для подачи в сторы

Задача для Claude Code, исполняемая с сервера (SSH). Цель узкая и проверяемая:
**сделать так, чтобы Apple и Google при ревью получили живые страницы.** Ничего
«на будущее» — только то, без чего билд не подать.

Контекст: страницы **уже написаны** — `src/app/(legal)/{privacy,terms,subscription-terms,refunds,imprint,support,delete-account}/page.tsx`. Их не надо
создавать, их надо **задеплоить**. Сейчас `alma.pazl.ai` и `api.pazl.ai` — `NXDOMAIN`.

---

## 0. Критерии приёмки (Definition of Done)

Готово, когда **все** команды ниже дают то, что написано, с валидным TLS (не
self-signed):

```bash
for u in privacy terms subscription-terms refunds imprint support delete-account; do
  printf "%-22s " "$u"; curl -s -o /dev/null -w "%{http_code}\n" "https://alma.pazl.ai/$u"
done
# ожидается: 200 на каждой из семи

curl -s -o /dev/null -w "%{http_code}\n" https://api.pazl.ai/health          # 200
curl -s https://api.pazl.ai/ready | grep -o '"ephemeris":[a-z]*'             # true
curl -s https://alma.pazl.ai/.well-known/assetlinks.json | head -c 40        # валидный JSON
openssl s_client -connect alma.pazl.ai:443 -servername alma.pazl.ai </dev/null 2>/dev/null | grep "Verify return code"  # 0 (ok)
```

Почему именно это: Apple во время ревью **фетчит privacy URL** и отклоняет по
мёртвой ссылке ещё до открытия билда; Play **валидирует delete-account URL** и не
примет форму приватности без живого 200.

---

## 1. Архитектура (два хоста, один сервер)

| Хост | Что | Отдаёт |
|---|---|---|
| `alma.pazl.ai` | Next.js фронт (этот репозиторий, корень) | лендинг + 7 юр-страниц + `.well-known/*` |
| `api.pazl.ai` | FastAPI бэкенд (`backend/`) | `/v1/*`, `/health`, `/ready` |

`pazl.ai` уже указывает на `95.81.101.52` — там и разворачиваем оба поддомена.
Бэкенд разворачивается по готовому **`docs/DEPLOY.md`** (docker-compose + Caddy);
фронт — рядом, отдельным vhost.

---

## 2. DNS (делает владелец у регистратора — Claude Code только проверяет)

Добавить две A-записи на `95.81.101.52`:

```
alma.pazl.ai.  A  95.81.101.52
api.pazl.ai.   A  95.81.101.52
```

Проверка: `dig +short alma.pazl.ai api.pazl.ai` → обе строки = `95.81.101.52`.
Пока `NXDOMAIN` — дальше идти нельзя: Caddy не выпустит сертификат (ACME ходит по
80-му порту на этот адрес).

---

## 3. Бэкенд на `api.pazl.ai`

Идти строго по **`docs/DEPLOY.md`**. Кратко:

1. `backend/.env` (или `.env.local`) с боевыми значениями. **Секреты вводит
   владелец сам** — не подставлять. Обязательный минимум для прода (см.
   `/ready` → `missing`): `ALMA_JWT_SECRET` (сгенерировать
   `python -c "import secrets;print(secrets.token_urlsafe(48))"`),
   `ALMA_DATABASE_URL` (Postgres из compose), `ANTHROPIC_API_KEY`, метод входа,
   billing. Push-креды APNs/FCM уже настроены (лежат в `backend/secrets/`).
2. `ALMA_DOMAIN=api.pazl.ai`, `ALMA_ACME_EMAIL=<почта>` — Caddyfile берёт их.
3. **DE440s обязателен.** `ephemeris.py:66-84` молча откатывается на DE421, если
   нет `backend/data/de440s.bsp`, а витрина обещает DE440s на шести языках.
   Проверить: `/ready` → `"ephemeris_kernel":"de440s.bsp"`. Нет файла — положить.
4. `docker compose up -d` из `backend/`. Поднять systemd-таймеры
   (`backend/deploy/systemd/*`) — иначе утренняя рассылка и продления не идут.
5. Проверка: `curl https://api.pazl.ai/health` → 200; `/ready` → `ai:true`.

**Подводный камень (лог приватности):** поиск места рождения едет строкой
запроса — `api/routers/places.py:17-27`, — значит координата/город попадают в
любой access-лог по умолчанию. Решить до заполнения Data safety: отключить
логирование query-строки на этом пути **или** честно задекларировать. См.
блок «приватность» в `mobile/store/`.

---

## 4. Фронт на `alma.pazl.ai`

Приложение Next.js в корне репозитория. CSP в `next.config.ts` требует, чтобы
`connect-src` знал origin API — он читается из `NEXT_PUBLIC_ALMA_API` **на этапе
сборки**, поэтому переменная должна быть выставлена ДО `build`.

```bash
# на сервере, в корне репозитория
export NEXT_PUBLIC_ALMA_API=https://api.pazl.ai
npm ci
npm run build
# запуск: next start за реверс-прокси (Caddy vhost для alma.pazl.ai → :3000)
#   pm2 start "npm run start" --name alma-web   # или systemd-юнит
```

Добавить в реверс-прокси vhost `alma.pazl.ai` с авто-TLS (по образцу
`backend/deploy/Caddyfile`, но `reverse_proxy 127.0.0.1:3000` и без `/v1/*`).
Порты 80/443 открыты — ACME ходит по 80-му.

Проверка: семь URL из §0 отдают 200 по HTTPS.

---

## 5. `.well-known/` — App Links и Universal Links

Ни `assetlinks.json`, ни `apple-app-site-association` в репозитории **нет** — создать.
Оба отдаются с `https://alma.pazl.ai/.well-known/` как статические файлы
(Content-Type: `application/json`, без редиректов, без auth).

**`assetlinks.json`** (Android App Links, требуется Play):

```json
[{
  "relation": ["delegate_permission/common.handle_all_urls"],
  "target": {
    "namespace": "android_app",
    "package_name": "ai.pazl.alma",
    "sha256_cert_fingerprints": ["<SHA256 из Play App Signing>"]
  }
}]
```

SHA-256 брать из **Play Console → Test and release → App integrity → App signing**
(это ключ, которым Google подписывает прод; upload-ключ не подойдёт).

**`apple-app-site-association`** (для Sign in with Apple web / Universal Links;
файл **без расширения**, Content-Type `application/json`):

```json
{
  "applinks": { "apps": [], "details": [
    { "appID": "SHM4X4CMUY.ai.pazl.alma.flutter", "paths": ["*"] }
  ] },
  "webcredentials": { "apps": ["SHM4X4CMUY.ai.pazl.alma.flutter"] }
}
```

Проверка: оба URL отдают 200 и валидный JSON (см. §0).

---

## 6. Согласованность региона (иначе одна из политик врёт)

iOS-текст утверждает «servers in the European Union», веб-страница оставляет
регион пустым. Определить, **где реально хостится** `api.pazl.ai` (у `95.81.101.52`),
и привести оба текста к правде. Это же решает строку в Data safety про хранение.
Не деплоить приватность, пока значения не совпали.

---

## 7. Порядок и зависимости

1. DNS (§2) — без него не выпустится TLS.
2. Бэкенд (§3) — фронту нужен живой `api.pazl.ai` для CSP/связи.
3. Фронт (§4).
4. `.well-known` (§5) — нужен SHA-256 из Play (зависит от заведённого App Signing).
5. Регион (§6) — текстовая правка, можно параллельно.
6. Прогнать §0 целиком. Всё зелёное — сайт готов к ревью.

---

## Что НЕ входит в это ТЗ

Кодовые фиксы приложения (удаление аккаунта гостем, кросс-синтез «8 vs 3», имя в
Anthropic, аналитика без opt-out) — отдельно, `APP-CHANGES-NEEDED.md`. Скриншоты,
IAP-товары, анкеты рейтинга/приватности — не сайт.
