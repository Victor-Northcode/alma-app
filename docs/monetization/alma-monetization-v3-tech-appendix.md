# Приложение А · Технический дизайн монетизации v3

**К документу:** `alma-monetization-v3-tz.md` · **Дата:** 17.08.2026
**Аудитория:** Витя + Claude Code. Продуктовые решения — в основном ТЗ, здесь только «как».
**Основано на:** фактическом коде репозитория (`backend/alma/`, `mobile/flutter/alma/`) по состоянию на архив от 16.08.

---

## А1. Что уже есть (не изобретать заново)

| Нужное | Где уже реализовано | Вывод |
|---|---|---|
| Запись партнёра | `Profile` с `relation="partner"`, `gender`, `is_self` | Новая модель НЕ нужна |
| Верификация покупок | `POST /billing/iap/verify` + `appstore.py` / `googleplay.py` | Расширяем, не пишем с нуля |
| Идемпотентность | `webhook_event.id = "<platform>:<transaction_id>"`, PK | Работает и для consumable, см. А4 |
| Server Notifications | App Store SN V2 + Play RTDN (Pub/Sub) обработчики есть | Нужен только новый обработчик renew → сброс кредита |
| Ширина гранта | `Entitlement.scope` ∈ `system` / `all` / `live` | Добавляем `static` и `pair`, порядок проверки не менять |
| Разделение денег и доступа | `Purchase` (деньги) ↔ `Entitlement` (доступ) | Соблюдать: pair пишет обе строки |
| Модели трат | `cost.guard()`, потолки по тирам в `config.py` | Тизер пары должен проходить guard |

**Инвариант, который нельзя сломать:** `entitlements.covers()` и `unlocked_systems()` спрашивают `scope` **до** легаси-сентинела `system == "*"`. В коде это отдельно закомментировано: если проверить сентинел раньше, подписчик увидит натал открытым в хабе и получит отказ на входе в главу. Любой новый scope добавляется в обе функции одинаково, иначе хаб и `check()` разъедутся.

---

## А2. Модель данных

### А2.1 Новые значения `Entitlement.scope`

| scope | system | Что покрывает | Срок |
|---|---|---|---|
| `system` (есть) | `natal` и т.п. | одна статичная система | ∞ |
| `static` (**новый**) | `*` | 5 статичных систем (бандл $19.99) | ∞ |
| `all` (есть) | `*` | всё | до `expires_at` |
| `live` (есть, legacy) | `*` | только живые | до `expires_at` |
| `pair` (**новый**) | `pair:{profile_id}` | отчёт по одной паре | ∞ |

`live` остаётся в коде навсегда ради живых старых подписчиков (см. А6). Новых `live`-грантов не выписываем.

**Правки в `entitlements.py`:**

```python
SCOPE_STATIC = "static"
SCOPE_PAIR = "pair"
STATIC_SYSTEMS = frozenset({"natal", "numerology", "birth-card", "astrocartography", "synthesis"})

# covers(): порядок проверок — pair → live → all → static → system
if entitlement.scope == SCOPE_PAIR:
    return system == "compatibility" and entitlement.system == f"pair:{partner_id}"
if entitlement.scope == SCOPE_STATIC:
    return system in STATIC_SYSTEMS
```

`check()` получает новый необязательный параметр `partner_id: str | None`. Для `system="compatibility"` без `partner_id` — 400, а не «нет доступа»: это ошибка вызова, не отсутствие прав.

`unlocked_systems()`: `SCOPE_STATIC` → `unlocked |= STATIC_SYSTEMS`. `SCOPE_PAIR` — **не** добавляет `compatibility` в общий сет (доступ поштучный); для хаба отдаём отдельный список `unlocked_pairs: list[profile_id]`.

`tier_of()`: владелец бандла = `owner` (не `subscriber`) — иначе получит подписочные квоты чата бесплатно.

### А2.2 Кредит совместимости у подписчика

Новая таблица (не поле в `Entitlement` — кредит переживает смену грантов при апгрейде/восстановлении):

```python
class PairCredit(Base):
    __tablename__ = "pair_credit"
    id: str = PK
    user_id: FK user.id CASCADE, index
    period_start: datetime          # начало текущего billing-цикла
    period_end: datetime            # = renews_at подписки
    granted: int = 1                # сколько кредитов в периоде
    used: int = 0
    subscription_id: str | None     # чей цикл
    __table_args__ = (UniqueConstraint("user_id", "period_start"),)
```

Правила: период берётся из `Entitlement.renews_at` активной подписки, **не** из календарного месяца. Неиспользованный кредит **не** переносится (проговорить в копирайте: «1 проверка в этом месяце»). Отмена подписки: текущий период доживает до `expires_at`. Grace period (`status="past_due"`): кредит не начисляется, уже потраченный не отзывается.

### А2.3 Миграция

`migrations/versions/xxxx_monetization_v3.py`:
1. `CREATE TABLE pair_credit`.
2. Backfill scope: гранты архива ($38.99, `system="*"`, `kind="lifetime"`) → `scope="static"` (grandfathering, §А6).
3. Индекс `entitlement_user_scope (user_id, scope)` — `for_user()` вызывается на каждом входе в главу.
4. Никаких `DROP`: старые SKU живут в каталоге с `offered=False`.

Миграция обратимо-безопасная: `downgrade()` возвращает `scope="all"` для тронутых строк.

---

## А3. Каталог

`catalogue.py`, значения `cents` в USD; локальные цены — из сторов, сервер их не считает.

```python
Product(id="door.natal",        cents=499,  kind="one-time",  scope="system", system="natal",  offered=True)
Product(id="door.numerology",   cents=499,  ...)
Product(id="door.birth-card",   cents=499,  ...)
Product(id="door.astrocartography", cents=499, ...)
Product(id="door.synthesis",    cents=499,  ...)
Product(id="pair.check",        cents=499,  kind="consumable", scope="pair",   system=None,     offered=True)
Product(id="bundle.static",     cents=1999, kind="one-time",  scope="static", system="*",      offered=True)
Product(id="sub.monthly",       cents=999,  kind="subscription", scope="all",  system="*",     offered=True,
        pair_credits_monthly=1)
```

`offered=False`: `sub.weekly`, `sub.annual`, `archive`, `archive-bump`, `archive-upgrade`, `door.transits`, `door.solar`, `door.compatibility`.

**Store product IDs** (заводятся в App Store Connect и Play Console; менять после публикации нельзя):
`com.pazl.alma.door.natal` · `.door.numerology` · `.door.birthcard` · `.door.astrocartography` · `.door.synthesis` · `.pair.check` · `.bundle.static` · `.sub.monthly`

Типы: двери и бандл — **Non-Consumable**; `pair.check` — **Consumable**; подписка — **Auto-Renewable** в группе `alma_access` (одна группа: будущие weekly/annual должны быть взаимозаменяемы).

`GET /billing/catalogue` отдаёт только `offered=True` + флаг `owned` по каждому SKU. Тест-инвариант: **сумма цен статичных дверей > цены бандла** (иначе бандл бессмыслен) и **бандл < 3 × цена подписки** (иначе не якорь).

---

## А4. Привязка покупки пары (главная новая механика)

Consumable покупается многократно, и сервер обязан знать, **к какому партнёру** относится платёж. Механика — pending-intent, а не доверие клиенту.

### Поток

```
1. Клиент: POST /billing/pair/intent {profile_id}
   Сервер: проверяет, что profile принадлежит user и не is_self;
           создаёт PairIntent{id, user_id, profile_id, created_at, consumed_at=NULL};
           отвечает {intent_id, app_account_token}   # UUID v4, детерминированный от intent_id
2. Клиент: покупка в сторе, передавая
           iOS:     appAccountToken = <app_account_token>
           Android:  obfuscatedProfileId = <app_account_token>  (и obfuscatedAccountId = user_id)
3. Клиент: POST /billing/iap/verify {platform, product:"pair.check", transaction, intent_id}
4. Сервер: verify подписи у стора → сверяет appAccountToken/obfuscatedProfileId из
           подписанного пейлоада с тем, что ожидает intent → пишет Purchase +
           Entitlement{scope:"pair", system:"pair:{profile_id}"} → consumed_at=now
5. Клиент: finishTransaction / consumePurchase — только после 200 от сервера
```

**Ключевое правило:** `profile_id` берётся **из intent на сервере**, а не из тела `/verify`. Токен из стора — подписанный факт, intent — наша запись; клиент не может подсунуть чужой профиль.

**Расхождение intent и токена** (редкий, но реальный кейс: пользователь начал покупку для Маши, свернул приложение, начал для Кати): грант выписывается по **токену из подписанного пейлоада**, intent-несоответствие логируется как `pair_intent_mismatch`. Стор — источник правды.

**Отсутствующий токен** (старые версии клиента, редкие сбои): грант не выписывается, `Purchase` пишется со `status="unbound"`, клиенту 202 и экран «выберите, к кому применить покупку» → `POST /billing/pair/bind {transaction, profile_id}`. Деньги не теряются никогда.

**Idempotency:** `webhook_event.id = "<platform>:<transaction_id>"` — как у остальных. Повтор → `already_claimed`, ничего не пишется. Для consumable это корректно: каждая новая покупка имеет новый `transaction_id`.

**Restore purchases:** consumable через restore **не** восстанавливается — это правило Apple. Источник правды для истории пар — наши гранты, поэтому «Мои пары» строится из `Entitlement`, а не из StoreKit. При переустановке всё на месте, если пользователь вошёл в аккаунт (гостю — предупреждение перед покупкой, оно уже есть в guest-флоу).

---

## А5. Store Server Notifications: что добавляем

Инфраструктура есть, нужны новые ветки обработки.

| Событие | Apple `notificationType` | Google `notificationType` | Что делаем |
|---|---|---|---|
| Продление | `DID_RENEW` | `SUBSCRIPTION_RENEWED` (2) | `renews_at` вперёд; **закрыть текущий `PairCredit`, открыть новый** |
| Отмена (в конце периода) | `DID_CHANGE_RENEWAL_STATUS` + `AUTO_RENEW_DISABLED` | `SUBSCRIPTION_CANCELED` (3) | доступ до `expires_at`; кредит текущего периода живёт |
| Просрочка платежа | `DID_FAIL_TO_RENEW` | `SUBSCRIPTION_IN_GRACE_PERIOD` (6) | `status="past_due"`, доступ сохраняется, новый кредит НЕ начисляем |
| Истечение | `EXPIRED` | `SUBSCRIPTION_EXPIRED` (13) | `expires_at=now`; **статичные и pair-гранты не трогать** |
| Возврат | `REFUND` | `SUBSCRIPTION_REVOKED` (12) / voided purchase | `refunded_cents`, отзыв гранта — см. А7 |
| Восстановление | `DID_RENEW` после expired | `SUBSCRIPTION_RESTARTED` (7) | новый период, новый кредит |

Обработчик продления — единственная новая бизнес-логика; остальные ветки уже написаны, им добавляется только «не трогать `scope in (system, static, pair)`».

---

## А6. Миграция существующих пользователей

| Было куплено | Становится | Почему |
|---|---|---|
| Архив $38.99 (`system="*"`, lifetime) | `scope="static"` (все 5 статичных навсегда) | Он платил за «все написанные разборы» — получает ровно это; живое ушло в подписку, но он за него и не платил |
| Дверь любой статичной системы | без изменений | |
| Дверь транзитов / соляра / совместимости | грант живёт, SKU снят с продажи | Обещание держим |
| Активная weekly / annual | доживает до `expires_at` со старым scope | Ничего не отбираем; после истечения — только новая полка |
| Отдельные главы (legacy `system:chapter`) | без изменений | |

Отдельный тест: `test_grandfathered_archive_still_reads_all_static_systems`.

---

## А7. Edge-кейсы (матрица приёмки)

| # | Ситуация | Ожидаемое поведение |
|---|---|---|
| 1 | Подписка активна + тап по закрытой главе натала | Открывается, пейволла нет |
| 2 | Подписка истекла, натал куплен дверью | Натал читается, транзиты закрыты |
| 3 | Подписка истекла, натал был доступен только по подписке | Закрыт; на пейволле — оффер двери $4.99 |
| 4 | Кредит пары потрачен, вторая проверка в том же цикле | Пейволл $4.99, копирайт «сверх месячной проверки» |
| 5 | Кредит не потрачен, подписка отменена, период не истёк | Кредит доступен до `expires_at` |
| 6 | Рефанд `pair.check` | Отзыв `pair:{id}`-гранта, отчёт закрывается, `refunded_cents` |
| 7 | Рефанд бандла при купленной ранее двери | Отзывается только `static`-грант; дверь остаётся |
| 8 | Два аккаунта на одном Apple ID покупают пару | Первый выигрывает (`already_claimed`); второму 409 + текст поддержки |
| 9 | Покупка при офлайне / сервер недоступен | StoreKit-транзакция не финишится, повтор на следующем запуске, `/verify` идемпотентен |
| 10 | Оплата прошла, `/verify` упал 500 | Клиент ретраит с backoff (5 попыток, до 2 мин), потом баннер «покупка обрабатывается» + ручной ретрай; транзакцию не финишить |
| 11 | Гость покупает, потом входит в аккаунт | Гранты переносятся существующим `accounts.by_email`-мержем |
| 12 | Профиль партнёра удалён после покупки | Грант живёт (`pair:{id}` осиротел), отчёт доступен из «Мои пары»; удаление профиля → soft-delete, если есть грант |
| 13 | Смена локали после покупки | Уже сгенерированный текст не переписывается; новые главы — на новой локали |
| 14 | Апгрейд двери → бандл | Отдельного кредитного SKU в v3 нет; бандл покупается полной ценой (записать в известные ограничения) |
| 15 | `interest` не задан (старые пользователи) | NBO работает по дефолтной ветке «Понять себя» |

---

## А8. API-контракты (новое и изменённое)

```
POST /billing/pair/intent       {profile_id} → {intent_id, app_account_token}
POST /billing/pair/bind         {transaction, profile_id} → {granted: bool}   # аварийный путь, А4
GET  /pairs                     → [{profile_id, name, purchased_at, source: "purchase"|"credit"}]
GET  /pairs/{profile_id}/teaser → {text, cached: bool}                        # бесплатный тизер, кап А9
GET  /billing/credits           → {pair: {granted, used, period_end}}
GET  /billing/catalogue         → + owned: bool на каждый SKU (изменение)
POST /billing/iap/verify        → + intent_id: str | null (изменение)
GET  /offers/next               → {surface, sku, reason, ttl}                 # NBO, А10
POST /events                    → без изменений, новые типы событий (§7 ТЗ)
```

Все новые эндпоинты — под `CurrentUser`, гостю доступны `/pairs/*/teaser` и `catalogue`.

---

## А9. Бюджеты генерации

| Что | Модель | Расчёт | Потолок |
|---|---|---|---|
| Тизер «Притяжение» | mid | ~2 абзаца, ~3¢ | внутри `free_month_budget`; кап **3 тизера/мес** на free-тир |
| Отчёт по паре (4 главы) | strong | ~26¢ | внутри `owner`-потолка |
| Кредитная пара подписчика | strong | ~26¢ | внутри `subscriber_month_budget` ($4.50) |

Кап тизеров — серверный (`UsageCounter`, ключ `pair_teaser`), не клиентский. Превышение → сразу пейволл вместо тизера, без ошибки.

Тизер кэшируется по `(profile_id, locale)`: повторный вход в уже проверенного партнёра не тратит токены.

---

## А10. Конфиг NBO

Схема в `Setting` (ключ `nbo.weights`), правится без релиза:

```json
{
  "version": 3,
  "cards": {
    "compatibility": {"base": 1.0, "interest": {"love": 2.0, "money": 0.4, "self": 0.6, "future": 0.5},
                      "gender_female": 1.5, "after_love_chapter_hours": 72, "after_love_chapter_boost": 3.0},
    "natal":         {"base": 1.2, "interest": {"love": 0.8, "money": 1.8, "self": 2.0, "future": 0.9}},
    "horoscope":     {"base": 0.9, "interest": {"future": 2.0}, "day2_badge": true},
    "bundle":        {"base": 0.0, "free_chapters_read_min": 3, "boost_when_eligible": 1.7},
    "astrocarto":    {"base": 0.5, "interest": {"money": 1.4}},
    "synthesis":     {"base": 0.5, "interest": {"self": 1.3}}
  },
  "rules": {
    "max_proactive_per_session": 1,
    "first_session_only_p1": true,
    "dismiss_cooldown_hours": 48,
    "hide_all_when_fully_owned": true
  }
}
```

Скор = `base × interest[user.interest] × модификаторы`. Сортировка по убыванию, ties — по `base`. Клиент кэширует конфиг на 24ч, при отсутствии — зашитый дефолт (порядок как в таблице §4 ТЗ).

---

## А11. Новые ключи локализации (7 локалей)

Префикс `paywall.v3.*`. Полный список — 41 ключ:

**Дверь (P1, P2):** `door.title` `door.price` `door.forever` `door.chapters_count` `door.cta` `door.bundle_link`
**Бандл:** `bundle.title` `bundle.price` `bundle.saving` `bundle.includes` `bundle.cta`
**Пара (P4):** `pair.input_title` `pair.input_name` `pair.input_date` `pair.teaser_title` `pair.teaser_cta` `pair.price` `pair.forever` `pair.included_badge` `pair.beyond_credit` `pair.my_pairs_title` `pair.check_another`
**Подписка (P5, P6):** `sub.title` `sub.price` `sub.renewal_disclosure` `sub.includes_transits` `sub.includes_solar` `sub.includes_pair` `sub.includes_questions` `sub.forever_stays` `sub.cta` `quota.title` `quota.cta`
**Все планы (P7):** `plans.group_forever` `plans.group_subscription` `plans.divider_note`
**Отмена (P8):** `cancel.save_title` `cancel.save_cta` `cancel.just_cancel`
**Состояния:** `state.processing` `state.error_retry` `state.restore_done`

Правила из существующего аудита локализации соблюдать: plural-ключи для «N глав» во всех локалях; `sub.renewal_disclosure` не сокращать при переводе (требование ревью сторов); валюта и цена подставляются из стора, не переводятся.

---

## А12. Порядок работ и проверки

| Фаза | Содержание | Тесты, без которых не мержим |
|---|---|---|
| Ф0.1 | scope `static` + `pair`, миграция, grandfathering | `covers`/`unlocked_systems` согласованы; архив→static |
| Ф0.2 | Каталог v3, `offered=False` для старых | инварианты цен; каталог не отдаёт снятое |
| Ф0.3 | PairIntent, `/pair/intent`, `/verify` с токеном | подмена `profile_id` отбита; replay ничего не грантит |
| Ф0.4 | `PairCredit` + обработчик продлений | цикл по `renews_at`, не по календарю; grace не начисляет |
| Ф1 | Экраны P1–P8, `ladder.dart` | golden-тесты пейволлов; «одна цена на экране» |
| Ф2 | NBO + `interest` в квизе | матрица §4 воспроизводится; дефолт при пустом `interest` |
| Ф3 | События, A/B | все события §7 ТЗ приходят с `surface` |

**Общий gate:** существующий тест `test_no_tier_is_promised_more_than_its_ceiling_can_fund` должен проходить с новым составом подписки (всё + 1 пара + 30 вопросов против $4.50) — если не проходит, поднимаем потолок, а не режем обещание.
