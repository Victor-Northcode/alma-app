# Агенту: подпись Android, оплаты и что осталось до релиза

Ты общаешься с агентом у консолей, не с владельцем. Секреты (keystore, пароли,
сервис-аккаунты) заводит владелец сам — ты их не выдумываешь и в чат не тянешь.
Идентификаторы, цены и тексты витрины бери из готовых доков рядом, не сочиняй:

| За чем | Куда |
|---|---|
| Product ID и цены всех 8 IAP | `mobile/store/PRODUCTS.md` |
| Поля листинга, что вписывать в консоли | `mobile/store/CONSOLE-FILL.md`, `LISTING.md` |
| Play Data safety (анкета) | `mobile/store/DATA-SAFETY.md` |
| Заметки для ревью | `mobile/store/REVIEW-NOTES.md` |
| Скриншоты (готовы, точные размеры) | `apple-shots/` (iPhone 6.9" 1320×2868, iPad 13" 2064×2752) |

Приложение: iOS bundle `ai.pazl.alma.flutter` (App ID `6803672050`), Android
package `ai.pazl.alma`. Prod API: `https://api-alma.pazl.ai`.

---

## A. Подпись Android (то, ради чего «идеально для гугла»)

Код уже готов: `android/app/build.gradle.kts` подписывает релиз upload-ключом,
если есть `android/key.properties`, иначе debug. `.gitignore` держит `.jks` и
`key.properties` вне репозитория. Осталось завести ключ — **один раз**.

**1. Сгенерировать upload-keystore** (владелец запускает у себя, пароли — свои):

```
keytool -genkeypair -v -keystore alma-upload.jks -keyalg RSA -keysize 2048 \
  -validity 10000 -alias alma-upload
```

**2а. Собирать в Codemagic (рекомендуется — CI уже настроен).** В приложении
Codemagic → Environment variables → группа **`keystore`**, четыре переменные
(флаг Secure на первой):

- `CM_KEYSTORE` = вывод `base64 -w0 alma-upload.jks`
- `CM_KEYSTORE_PASSWORD` = store-пароль
- `CM_KEY_ALIAS` = `alma-upload`
- `CM_KEY_PASSWORD` = key-пароль

Всё — `android-release` сам разложит ключ, напишет `key.properties` и подпишет
бандл настоящим ключом. Без этой группы сборка идёт на debug.

**2б. Или собрать локально** (владелец, на машине с Flutter): положить рядом с
`android/` файл `android/key.properties`:

```
storeFile=/абсолютный/путь/alma-upload.jks
storePassword=<store-пароль>
keyAlias=alma-upload
keyPassword=<key-пароль>
```

затем `flutter build appbundle --release --dart-define=ALMA_API_BASE=https://api-alma.pazl.ai`.
AAB ляжет в `build/app/outputs/bundle/release/`.

**Про Play App Signing.** При первой заливке включи Play App Signing: Play хранит
боевой ключ (его SHA-256 `66:85:A7…` уже вписан в assetlinks.json — не трогать), а
твой upload-keystore регистрируется как upload-ключ. Если раньше уже заливали
debug-бандл и upload-ключ зарегистрирован на него — либо подписывай тем же, либо
сбрось через «Request upload key reset» и залей подписанный новым.

---

## B. Google Play — до заливки

1. **App integrity → Play App Signing** включён (см. выше).
2. **Monetize → Products → In-app products / Subscriptions**: создать 8 товаров
   строго по `PRODUCTS.md` (ID, тип consumable/non-consumable/subscription, цена).
   Подписка `ai.pazl.alma.sub.monthly` — период P1M.
3. **Policy → App content**: Data safety (по `DATA-SAFETY.md`), Content rating
   (анкета), Target audience, Privacy policy URL `https://alma.pazl.ai/privacy`.
4. **Testing → Internal testing → Create release** → загрузить подписанный AAB.
5. Заметки ревью — из `REVIEW-NOTES.md`.

## C. App Store Connect — до отправки

1. **Agreements, Tax, and Banking**: подписать Paid Apps соглашение — без него
   IAP не активируются вовсе.
2. **Features → In-App Purchases / Subscriptions**: создать те же 8 товаров по
   `PRODUCTS.md` под bundle `ai.pazl.alma.flutter`.
3. Скриншоты из `apple-shots/` в слоты iPhone 6.9" и iPad 13" (см.
   `mobile/store/AGENT-STORES-TODO.md`).
4. Листинг — из `LISTING.md`/`CONSOLE-FILL.md`. Экспортное шифрование уже закрыто
   в коде (`ITSAppUsesNonExemptEncryption=false`), вопрос не появится.

---

## D. Серверная верификация чеков — пусто, без неё оплаты не подтвердятся

На проде (Docker `alma-app-1`, `.env`/`.env.local` в `/srv/alma/backend`) эти
значения СЕЙЧАС пустые — проверено. Владелец вписывает и перезапускает
`docker compose up -d app`:

| Переменная | Значение | Секрет? |
|---|---|---|
| `APPLE_BUNDLE_ID` | `ai.pazl.alma.flutter` | нет |
| `GOOGLE_PLAY_PACKAGE_NAME` | `ai.pazl.alma` | нет |
| `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` | путь к сервис-аккаунту Play внутри контейнера, напр. `/run/alma-secrets/play-service-account.json` | **да** |

Сервис-аккаунт Play (роль в Play Console: доступ к Google Play Android Developer
API, права на просмотр покупок) владелец кладёт в `/srv/alma/backend/secrets/`
(смонтирована в `/run/alma-secrets` только на чтение) и указывает путь. Apple
серверная проверка в этой сборке принимает и sandbox (`apple_accept_sandbox=True`),
так что для теста достаточно `APPLE_BUNDLE_ID`.

---

## E. Пуши — уже готовы, проверять на устройстве

Серверная сторона настроена и сверена вживую: APNs (topic `ai.pazl.alma.flutter`,
production, ключ `NFR6V5NY25` минтит валидный JWT) и FCM (проект `alma-eaec8`,
сервис-аккаунт читается). Ежедневная рассылка `alma-daily` отрабатывает. В
консолях делать **ничего не нужно**. Остаётся один тест руками: на устройстве
разрешить уведомления и убедиться, что утренний пуш приходит.

---

## Итог: что мешает нажать «отправить»
- Android: завести upload-keystore (A) → подписанный AAB.
- Обе консоли: создать 8 IAP-товаров (B2, C2) и соглашения Apple (C1).
- Сервер: вписать 3 переменные верификации + сервис-аккаунт Play (D).
- Play: Data safety + Content rating (B3).
Пуши и код — готовы.
