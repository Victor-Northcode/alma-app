# Заполнение консолей — актуальная правда (v3)

**Этот файл заменяет** устаревшие `SUBMISSION-CHECKLIST.md` (§0.0b, B5, C7) и
`mobile/store/README.md` ②, которые всё ещё называют старую полку из 12 товаров
(`alma.archive $38.99`, `alma.annual $78.99`) и «нерешённую» приставку. Полка ниже
сверена с `backend/alma/billing/catalogue.py` — **источник правды**. Заполнять
консоли только по нему: id из документа против id в бинарнике = Guideline 2.1
«unable to locate the in-app purchases», повторной подачей не чинится.

Приставка решена: **`ai.pazl.alma`** (`store_product_prefix`, `ladder.dart:89`).
Дефис в ключе → подчёркивание в id (`door.birth-card` → `…door.birth_card`).

---

## 1. Идентификаторы приложения

| | Apple | Google Play |
|---|---|---|
| Bundle / package | `ai.pazl.alma.flutter` (iOS App ID) | `ai.pazl.alma` |
| ID в консоли | Apple ID **6803672050** | App ID **4975658889900065554** |
| Название (29/30) | Alma: Natal Chart & 8 Systems | Alma: Natal Chart & 8 Systems |
| Категория | Образ жизни (осн.) · Справочники (доп.) | Lifestyle |

> ⚠️ Android package `ai.pazl.alma` ≠ iOS bundle `ai.pazl.alma.flutter` — так и
> задумано, платформы независимы. APNs-topic = iOS bundle; FCM = Android package.

---

## 2. Полка IAP — восемь товаров, ни одним больше

Заводится **ровно это**. Базовая цена — USD; регионы в §2.1.

| Ключ | Product ID (обе консоли) | Тип | USD |
|---|---|---|---|
| door.natal | `ai.pazl.alma.door.natal` | non-consumable / one-time | 4.99 |
| door.numerology | `ai.pazl.alma.door.numerology` | non-consumable | 4.99 |
| door.birth-card | `ai.pazl.alma.door.birth_card` | non-consumable | 4.99 |
| door.astrocartography | `ai.pazl.alma.door.astrocartography` | non-consumable | 4.99 |
| door.synthesis | `ai.pazl.alma.door.synthesis` | non-consumable | 4.99 |
| pair.check | `ai.pazl.alma.pair.check` | **consumable** | 4.99 |
| bundle.static | `ai.pazl.alma.bundle.static` | non-consumable | 19.99 |
| sub.monthly | `ai.pazl.alma.sub.monthly` | **auto-renewable P1M** | 9.99 |

**Подписка:**
- Apple: одна группа подписок, reference name `alma_access`, отображаемое имя
  **Alma**, уровень 1. Товар `sub.monthly`, период 1 месяц.
- Play: одна подписка `ai.pazl.alma.sub.monthly`, базовый план `monthly` (P1M,
  авто-продление).

**Display-name товаров** — из `Product.name` в каталоге: Natal chart, Numerology,
Birth Card, Astrocartography, Cross-synthesis, One compatibility report, All five
readings, Everything monthly.

### 2.1. Региональные цены — сверить и утвердить ДО сохранения

Точные суммы по валютам лежат в `catalogue.py → REGIONAL_CENTS`. Правило: сумма в
консоли **обязана совпасть** с числом там (иначе витрина назовёт цену, которой
магазин не возьмёт). Утверждены: EUR, GBP, CHF, AUD, CAD, NOK, DKK. **Не
утверждены владельцем** (помечены «выведено» в коде) — подтвердить до ввода:
- полоса **bundle** целиком;
- пять **PPP**-строк: BRL, MXN, PLN, TRY, INR.

Family Sharing на разовых (`door.*`, `bundle.static`) — решение владельца.

---

## 3. Метаданные листинга (что уже введено)

### Apple — App Store Connect
| Поле | Значение |
|---|---|
| Подзаголовок | Real ephemeris, no predictions |
| Рекламный текст | заполнен (164/170) |
| Описание | заполнено (3912/4000) — **только EN актуален** |
| Ключевые слова | заполнены (96/100 байт) |
| URL поддержки | `https://alma.pazl.ai/support` |
| Приватность | `https://alma.pazl.ai/privacy` |
| Копирайт | 2026 Pazl LLC |
| Демо-аккаунт | «Необходимо войти» снято (у Alma нет пароля, REVIEW-NOTES §0) |
| Релиз | ручной (после аппрува вручную) |

### Google Play — Console
| Поле | Значение |
|---|---|
| Краткое описание | заполнено (76/80) |
| Полное описание | заполнено (3948/4000) — **только EN актуален** |
| Категория | Lifestyle |
| Контакты | `hello@pazl.ai` · `https://alma.pazl.ai` |
| Язык / тип / цена | en-US · App · Free (тип/цена необратимы после публикации) |

> ⚠️ Описания **es/de/it/fr/pt-BR** в `LISTING.md`/`PRODUCTS.md` всё ещё продают
> старую полку (архив, годовая). Актуален только EN-абзац про покупки. Пять
> языков переписать под §2 (режут под 4000). **ru-витрины нет вовсе** — решение
> по русской локали не зафиксировано, хотя README заявляет 7 языков.

Все URL из таблиц **зависят от поднятого сайта** — см. `docs/SITE-TZ.md`. Пока
`alma.pazl.ai` = NXDOMAIN, Apple отклонит по мёртвой privacy-ссылке.

---

## 4. Скриншоты — 0 из 72 готовых

Спека — `SCREENSHOTS.md`. 6 кадров × 6 локалей × 2 пропорции. Apple 1320×2868,
Play 1080×1920 — разные пропорции, кроп не пройдёт, рендерить **с устройства**
(iOS — macOS-симулятор, Android — эмулятор). Готовы только `play-icon-512.png` и
`play-feature-graphic-1024x500.png`. Нужна ещё **иконка App Store 1024×1024 без
альфа-канала** (в asset-каталоге iOS 1024 есть — проверить на альфу).

Решить **до рендера**: iPad. `project.pbxproj:214,240` → `TARGETED_DEVICE_FAMILY
= "1,2"`, значит iPad-набор обязателен (+36 картинок). iPhone-only — правка одной
строки.

---

## 5. Требует ФАКТИЧЕСКИХ ответов владельца (я их не знаю)

Это декларации, не текст — заполняет владелец:

**Возрастной рейтинг** (Apple 4 вопроса + Play IARC):
- Health/Wellness — главы «Work and rhythms», «Shadow and wound». Любой ответ
  кроме None → 9+. Самый решающий.
- Horror/Fear — рисует ли Birth Card Смерть/Башню картинкой или только текстом.
- Mature/Suggestive — откровенность совместимости (Infrequent→9+, Frequent→16+).
- Medical — оставить None (стережёт `validator.py:153-161`).
- Play может спросить про оккультизм/гадание (в справке нет — читать в консоли).
- Play target audience — только взрослые (группа <13 тянет в Families Policy).

**Приватность / Data safety** — не заполнять, пока нет ответов:
- Есть ли DPA с **Anthropic** и **Resend**? Без него «Shared: No» переворачивается
  на Yes для 4 строк (Anthropic получает дату/время до минуты, координату
  рождения, имя, 12 сообщений чата).
- Где хостится бэкенд, что и насколько пишет в access-логи (поиск места рождения
  едет URL-строкой, `places.py:17-27`). Решает «servers in the EU» — iOS-текст
  это утверждает, веб оставляет пустым.
- Birth data в Apple «Sensitive Info» → **Yes** (манифест уже говорит Yes;
  `PrivacyInfo.xcprivacy` менять в ту же посадку).

**Контакт ревьюера** (ASC): имя, фамилия, телефон, email. `REVIEW-NOTES.md §0` —
6 плейсхолдеров (`⟨REVIEW CONTACT⟩`, `⟨VERSION⟩`…) заполнить перед подачей.

---

## 6. Аккаунтское (не задним числом)

- Apple Small Business Program — пониженная комиссия не бэкдейтится.
- Play payments profile.
- Подтвердить DE440s на проде (`ephemeris.py:66-84` тихо откатывается на DE421).
- Один вебхук не примет Apple и Play одновременно (`billing.py:420`) — продления
  и возвраты не придут, пока не разведены.
