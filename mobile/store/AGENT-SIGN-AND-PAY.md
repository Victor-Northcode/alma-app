# Агенту в сторах: всё, что осталось до релиза (единый чек-лист)

Ты — агент у консолей. Секреты (keystore, пароли, сервис-аккаунты) вводит владелец
сам; ты их не выдумываешь и в чат не тянешь. Тексты, ID и цены НЕ сочиняешь — всё
ниже и в файлах рядом:

| За чем | Куда |
|---|---|
| Product ID, типы и цены всех 8 IAP | `mobile/store/PRODUCTS.md` (истина — `backend/alma/billing/catalogue.py`) |
| Тексты витрины | `mobile/store/LISTING.md`, `CONSOLE-FILL.md` |
| Play Data safety | `mobile/store/DATA-SAFETY.md` |
| Заметки ревьюеру | `mobile/store/REVIEW-NOTES.md` |
| Скриншоты (готовые, точные размеры) | `apple-shots/` |

Приложение: iOS bundle `ai.pazl.alma.flutter` (App ID `6803672050`), Android
package `ai.pazl.alma`. Prod API `https://api-alma.pazl.ai` — жив и проверен.

---

## 1 · App Store Connect

**1.1 Скриншоты.** Версия iOS → язык **English (U.S.)** → App Previews and
Screenshots:
- слот **iPhone 6.7"** ← `apple-shots/iphone-01…04.png` (1284×2778, размер уже
  из принятого списка — ресайзить нельзя);
- слот **iPad 13"** ← `apple-shots/ipad-01…03.png` (2064×2752).
Порядок = порядок в сторе. Save. Попросит другой размер — не выдумывать, сказать владельцу.

**1.2 Соглашения.** Agreements, Tax, and Banking → **Paid Apps** подписано.
Без этого IAP не активируются вовсе — проверить первым делом.

**1.3 Создать 8 IAP** (Features → In-App Purchases / Subscriptions), ID и тип —
строго по `PRODUCTS.md`:
- 5 non-consumable «дверей» `ai.pazl.alma.door.*` — база **$4.99**;
- consumable `ai.pazl.alma.pair.check` — **$4.99**;
- non-consumable `ai.pazl.alma.bundle.static` — **$19.99**;
- auto-renewable `ai.pazl.alma.sub.monthly` — **$9.99 / P1M** (создать
  Subscription Group, если нет).

**1.4 Валюты — автоценами Apple, и это решение, а не лень.** База — USD;
галка **автоматических региональных цен** включена: Apple сам выставит €, £,
CHF, CAD, AUD и т.д. по своим таблицам, и лист покупки печатает локальную
валюту покупателя — приложение показывает ровно её (`AlmaStore.price`).
Руками по странам ничего не перебивать: серверная таблица валют
(`catalogue.py REGIONAL_CENTS`) — про карточный фолбэк, не про IAP, и ей
консоль соответствовать не обязана.

**1.5 Картинка у покупки.** Владелец видел лист покупки «без картинки»: у
каждого IAP есть поле **Promotional Image / Review screenshot**. Review
screenshot обязателен для ревью каждого IAP — использовать кадры из
`apple-shots/` (для дверей — `iphone-01-reader.png`, для подписки —
`iphone-03-today.png`); отдельный promo-арт, если владелец захочет красивее, —
попросить у него, не рисовать самому.

**1.6 Локализация IAP-названий** — из `PRODUCTS.md`/`LISTING.md`; языков там
семь, не сочинять.

---

## 2 · Google Play Console

**2.1 Подпись.** Play App Signing включён (боевой ключ у Play, его SHA-256
`66:85:A7…` уже в assetlinks.json — не трогать). Для НАСТОЯЩЕЙ подписи бандла
владелец заводит группу **`keystore`** в Codemagic: `CM_KEYSTORE` (.jks в
base64, Secure), `CM_KEYSTORE_PASSWORD`, `CM_KEY_ALIAS`, `CM_KEY_PASSWORD`.
Генерация ключа (владелец, у себя):
`keytool -genkeypair -v -keystore alma-upload.jks -keyalg RSA -keysize 2048 -validity 10000 -alias alma-upload`.
Без группы CI подписывает debug-ключом, и такой бандл Play **не принимает
никогда** (проверено 24 авг: «signed in debug mode. You need to sign in release
mode») — группа keystore обязательна до первой заливки. Если консоль ждёт
другой upload-ключ — прислать владельцу текст ошибки целиком, самому не
подписывать.

**2.2 Создать 8 товаров** (Monetize → Products): те же ID/типы/базовые цены,
что в 1.3. Подписка — Base plan P1M.

**2.3 Валюты** — тем же правилом: базовая цена USD, автоконвертация Play по
странам. Руками не перебивать.

**2.4 Обязательное перед публикацией:** Data safety (по `DATA-SAFETY.md`),
Content rating (анкета), Target audience, Privacy policy
`https://alma.pazl.ai/privacy`, страны распространения.

**2.5 Релиз:** Testing → Internal testing → загрузить AAB из Codemagic
(`android-release` собирает main).

---

## 3 · Codemagic (владелец, 10 минут)

- Группа `firebase`: `GOOGLE_SERVICES_JSON` = base64 файла
  `android/app/google-services.json`, Secure. (Только для Android-сборки.)
- Группа `keystore` — см. 2.1.
- iOS уже готов: интеграция `synapse_asc`, bundle id, build-number, экспортное
  шифрование закрыты в codemagic.yaml/Info.plist.

## 4 · Сервер (владелец): включить верификацию оплат

В `/srv/alma/backend/.env.local` вписать и перезапустить
(`docker compose up -d app`):

```
APPLE_BUNDLE_ID=ai.pazl.alma.flutter
GOOGLE_PLAY_PACKAGE_NAME=ai.pazl.alma
GOOGLE_PLAY_SERVICE_ACCOUNT_JSON=/run/alma-secrets/play-service-account.json
```

Сервис-аккаунт Play (доступ к Android Developer API, права на покупки) владелец
кладёт в `/srv/alma/backend/secrets/`. Без этих трёх строк сервер не подтвердит
ни одну покупку — это ЕДИНСТВЕННЫЙ серверный блокер оплат; пуши уже работают.

## 5 · Чего НЕ делать
- Не коммитить и не пересылать ключи/keystore/сервис-аккаунты.
- Не менять SHA в assetlinks.json.
- Не сочинять тексты, цены и размеры — нет данных → вопрос владельцу.
