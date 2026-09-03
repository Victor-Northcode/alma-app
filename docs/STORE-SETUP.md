# Что нужно от владельца, чтобы продажи заработали

Кратко, по одному разу на каждую площадку. Код готов целиком; всё ниже —
действия в чужих консолях, которые может сделать только владелец аккаунтов.
После каждого блока — какие значения положить в прод `.env` (вводишь сам,
закон «все креды вводит владелец»).

## 1 · App Store Connect (Apple)

1. **Создать 12 товаров** — идентификатор = ключ каталога с приставкой
   `ai.pazl.alma.`, дефисы → подчёркивания (правило `store_product_id`):

   | Идентификатор | Тип в консоли | Цена US |
   |---|---|---|
   | `ai.pazl.alma.door.natal` | Non-Consumable | $4.99 |
   | `ai.pazl.alma.door.numerology` | Non-Consumable | $4.99 |
   | `ai.pazl.alma.door.birth_card` | Non-Consumable | $4.99 |
   | `ai.pazl.alma.door.astrocartography` | Non-Consumable | $4.99 |
   | `ai.pazl.alma.door.synthesis` | Non-Consumable | $4.99 |
   | `ai.pazl.alma.pair.check` | **Consumable** | $4.99 |
   | `ai.pazl.alma.bundle.static` | Non-Consumable | $19.99 |
   | `ai.pazl.alma.sub.monthly` | Auto-Renewable (месяц) | $9.99 |
   | `ai.pazl.alma.questions.5` | **Consumable** | $1.99 |
   | `ai.pazl.alma.questions.10` | **Consumable** | $3.49 |
   | `ai.pazl.alma.questions.25` | **Consumable** | $6.99 |
   | `ai.pazl.alma.report.year` | **Consumable** | $12.99 |

   Цены четырёх новых позиций продуманы по твоему поручению 02.09.2026
   («цены продумай все»): вход $1.99 — цена кофе, штука дешевеет с
   размером ($0.40 → $0.35 → $0.28), q25 стоит рядом с подпиской нарочно
   («или вся Alma за три доллара сверху»), год = 1.3 месяца. Все точки US
   есть в сетке Apple. Локальные цены — `backend/alma/billing/catalogue.py`.
2. **App Store Server Notifications V2** → URL
   `https://api-alma.pazl.ai/v1/billing/webhook` (продакшен и сандбокс).
3. **Sign in with Apple** — уже включён; ничего не трогать.
4. **Разрешение на внешнюю ссылку оплаты** (для кнопки Т-Банка в RU-сторе) —
   отдельная заявка Apple; до одобрения кнопки в iOS нет и не будет.
5. В `.env`: `APPLE_BUNDLE_ID=` (bundle приложения). Больше от Apple секретов
   не нужно — подпись транзакций проверяется цепочкой сертификатов.

## 2 · Google Play Console

1. **Создать те же 12 товаров** с теми же идентификаторами
   (`questions.5` → `ai.pazl.alma.questions.5`); типы: Managed product для
   дверей и бандла, Consumable-поведение у пары/пачек/года обеспечивает
   приложение, Subscription (месяц) для `sub.monthly`.
2. **Сервисный аккаунт** с правами Android Publisher → JSON-ключ.
3. **Real-time developer notifications**: Pub/Sub-топик → push-подписка на
   `https://api-alma.pazl.ai/v1/billing/webhook` с OIDC-токеном.
4. В `.env`: `GOOGLE_PLAY_PACKAGE_NAME=`,
   `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON=` (строка или путь), audience/сервисный
   аккаунт подписки — переменные ниже по `.env.example`.

## 3 · Т-Банк (веб-оплата, уже выкачена)

1. В личном кабинете эквайринга: взять **TerminalKey** и **пароль**;
   URL нотификаций — `https://api-alma.pazl.ai/v1/billing/webhook`.
2. Включить рекуррентные платежи (для подписки).
3. В `.env`: `ALMA_BILLING_PROVIDER=tbank`, `TBANK_TERMINAL_KEY=`,
   `TBANK_PASSWORD=`, `TBANK_MERCHANT_NAME=ИП Осипова Вероника Олеговна`,
   `TBANK_TAXATION=` (система налогообложения ИП, напр. `usn_income` — без
   неё чек 54-ФЗ не отправляется), `TBANK_NOTIFICATION_URL=` (тот же URL).
4. Включить таймер продлений: `systemctl enable --now alma-tbank-charges.timer`.

## 4 · Paddle (веб для остального мира — по желанию, позже)

`/ready` на проде отвечает `false` только из-за пустых `PADDLE_API_KEY` /
`PADDLE_WEBHOOK_SECRET`. Появится аккаунт — создать цены по `REGIONAL_CENTS`,
вписать их id в `processor_ids` каталога, ключи в `.env`.

## 5 · После заполнения — один прогон

1. Тестовая покупка каждой из четырёх новых позиций (sandbox).
2. `curl https://api-alma.pazl.ai/ready` → `true`.
3. Сказать мне «проверь продажи» — прогоню вебхуки и витрины по всем позициям.
