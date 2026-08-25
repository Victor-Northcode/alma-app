# Вход через Google и Apple — консоли

**Статус 25.08.2026: всё выполнено.** Консоли настроил браузерный Клод, прод
обновлён, `/v1/auth/providers` отвечает `{"google":true,"apple":true,"email":true}`.
Ниже — как это устроено, и одна переменная, которую надо не забыть в Codemagic.

Код готов целиком: сервер проверяет id_token (`backend/alma/auth/providers.py`),
приложение рисует кнопки и ходит в нативные SDK (`lib/net/providers_sign_in.dart`,
`lib/screens/settings/sign_in_screen.dart`), аккаунт держится на почте — вход
через Google, Apple и код из письма приводит в один аккаунт
(`backend/tests/test_social_binding.py`). Кнопки включаются сервером: приложение
спрашивает `/v1/auth/providers`, и кнопка появляется в ту же минуту, когда на
сервере появляется client id. Ничего пересобирать для этого не нужно —
**кроме одного**: свежий `google-services.json` требует новой сборки Android.

## 1 · Google (Android)

Проект Firebase: **alma-eaec8** (номер 636878220861), приложение `ai.pazl.alma`.

1. **Firebase Console** → Project settings → приложение Android `ai.pazl.alma` →
   **Add fingerprint**. Добавить три SHA-1:
   - отладочный (машина владельца): `85:2D:4B:02:0A:E9:E4:CF:FC:3D:43:A9:39:CD:CB:20:7D:7E:4D:09`
   - **App signing key SHA-1** — взять в Play Console → Test and release →
     Setup → App integrity → App signing;
   - **Upload key SHA-1** — там же, строкой ниже.
2. **Google Cloud Console** (тот же проект) → APIs & Services →
   **OAuth consent screen**: если не настроен — тип External, имя «Alma»,
   почта поддержки hello@pazl.ai, домен pazl.ai; опубликовать (In production,
   не Testing — иначе вход только для тестовых аккаунтов).
3. После добавления отпечатков в Firebase → Project settings → скачать свежий
   **google-services.json** и заменить им
   `mobile/flutter/alma/android/app/google-services.json` (в репозиторий он не
   коммитится — передать владельцу/локальному Клоду). В файле должны появиться
   блоки `oauth_client`, включая клиент с `client_type: 3` (Web).
4. В Cloud Console → Credentials найти **Web client** (создаётся Google
   автоматически, «Web client (auto created by Google Service)») и скопировать
   его `client_id` вида `636878220861-….apps.googleusercontent.com`.
5. На проде добавить в `/srv/alma/backend/.env`:
   `GOOGLE_CLIENT_ID=<тот самый Web client id>` — и перезапустить:
   `cd /srv/alma/backend && docker compose up -d --force-recreate app`.
   С этой секунды кнопка Google появится у всех Android-приложений сама.

Проверка: `curl https://api-alma.pazl.ai/v1/auth/providers` → `"google": true`.

## 2 · Apple (iOS)

1. **developer.apple.com** → Identifiers → App ID → включена capability
   **Sign In with Apple**. ⚠️ App ID приложения — **`ai.pazl.alma.flutter`**,
   не `ai.pazl.alma` (первая версия этой записки ошибалась; Android-package
   при этом ai.pazl.alma — у платформ разные идентификаторы, и это нормально).
   Профили после включения перевыпускаются; Codemagic с automatic signing
   подхватывает сам на следующей сборке.
2. Никакого Service ID и ключа `.p8` для нативного входа не нужно: сервер
   проверяет identity token по открытым ключам Apple, aud — bundle id.
3. На проде в `.env`: `APPLE_CLIENT_ID=ai.pazl.alma.flutter`. Кнопка Apple
   появляется на iOS сама (на Android не показывается по решению владельца).
4. **Порядок важен:** env только ПОСЛЕ включения capability — кнопка,
   за которой системный лист падает с ошибкой, хуже отсутствия кнопки.

## 2½ · Codemagic — не забыть одну переменную

Релизная сборка Android восстанавливает `google-services.json` из переменной
**`GOOGLE_SERVICES_JSON`** (группа `firebase`, base64, Secure). Пока там лежит
старый файл без `oauth_client` — релиз уедет с мёртвым Google-входом, хотя
локально всё работает. Обновить: содержимое свежего
`mobile/flutter/alma/android/app/google-services.json` → base64 одной строкой →
вставить в Codemagic UI вместо старого значения.

Проверка: `curl https://api-alma.pazl.ai/v1/auth/providers` → `"apple": true`;
на TestFlight-сборке — нажать кнопку, пройти системный лист, увидеть свою
почту в Настройках.

## 3 · Что проверить после (владелец, на устройстве)

- Android: Google-вход → в Настройках «Ты в аккаунте» + почта Google-аккаунта.
- iOS: Apple-вход тем же Apple ID, чья почта совпадает с Google, — аккаунт
  должен оказаться ТЕМ ЖЕ (покупки на месте). Это главный закон:
  одна почта — один аккаунт, любой дверью.
- Вход кодом из письма с той же почтой — снова тот же аккаунт.
