# QA Progress — Alma (ID 269866) — ЗАВЕРШЕНО. Фокус: локализация/языки/оплаты/покупки

Прошлый аудит ID 550775 (29.08) покрыл общий backend/security (фиксы применены, commit 697bb84).
МОЙ прогон сфокусирован на НОВОМ коде: Т-Банк веб-оплата, рублёвые цены, 7-я локаль ru.

- ЭТАП 1/7 Запуск — DONE. backend :8018/:8100/:8109 (SQLite, billing off), сайт Next :3009 (из Desktop\Alma).
- ЭТАП 2/7 Backend/API — DONE. Каталог RUB верен; checkout 404/503/валидация ок; НАШёл: T-Bank Amount не фиксирует RUB.
- ЭТАП 3/7 Security — DONE. Подпись T-Bank вебхука отвергает тампер/нет-токена/пустой-пароль; live 401 на подделку; CF-IPCountry спуф игнорируется; фаззинг страны→USD, инъекций нет.
- ЭТАП 4/7 Frontend — DONE. /pay email→code→shop через ru magic-link; консоль чистая.
- ЭТАП 5/7 Визуал — DONE. /pay 390/1280 чисто; НАШёл: клиппинг ≤320px (nowrap-кнопка «Обновить доступ»).
- ЭТАП 6/7 Edge — DONE. checkout unknown→404, billing off→503, country-фаззинг→USD.
- ЭТАП 7/7 Performance — DONE. /pay = 2 вызова (catalogue+entitlements), N+1 нет.

Находки: HIGH×1 (T-Bank RUB), MEDIUM×1 (320px клиппинг), LOW/verify×1 (web checkout доверяет stated country).
Локализация 7 локалей — ЧИСТО (паритет ключей TS, ru на «ты», fr узкий nbsp, письма полны по 7).
Отчёт: QA_AUDIT_REPORT_269866.md

01.09 (фикс-проход): BUG-269-001 исправлен (`open_session` фиксирует RUB, регресс-тест красный-на-старом),
BUG-269-002 исправлен (`.btn-block` переносится; живьём 320/390/1280 чисто), OBS-269-003 открыт до
Paddle/Dodo-санбокса. Регрессии: backend 2216 pass / 23 = виндовый базлайн; сайт vitest 272 pass.
