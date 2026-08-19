# The pill — «All of Alma»: спека для разработчиков

Плавающая пилюля-приглашение для бесплатного тарифа. Эталоны на холсте: **S48** (появление), **S49** (морф в шит), **S50** (после отказа), **S32** (открытый шит), карточка **P0** (контракт). Экран под шитом всегда Today/система — он **не перезагружается** ни при открытии, ни при закрытии.

Это событие, а не мебель: статичная строка «Everything open, every day → See the plans» в залоченной секции Today остаётся всегда; пилюля лишь изредка указывает на неё.

## 1. Условия появления
- Только тому, кто ещё ничего не купил: подписчику и владельцу любой открытой системы — никогда (`main.dart` `_aimPill`: `unlocked.isNotEmpty || hasPlan` → пилюля уходит навсегда). Годового плана, к которому это правило отсылало раньше, в каталоге нет — подписка одна, месячная.
- Поверхности: Today и экраны систем. Никогда: пергамент главы, церемония расчёта, анкета (journey), любой шит/пейволл/диалог, People, Settings.
- Триггер: экран «уселся» — каскад появления отыгран **и** 6 с без ввода **и** скролл в покое. Клавиатура открыта → не появляется.
- Капы: ≤3 показов за сессию · ≥90 с тишины между показами · счётчик сбрасывается раз в календарные сутки (локальные).

## 2. Форма и метрики
- Контент: эмблема — ОТДЕЛЬНЫЙ слой (SVG 8-конечной звезды, #F6E7BC, 15 pt; именно он — Hero в морфе), отбивка 8, подпись «All of Alma» Golos 400 14, ivory #F6F1E4. Не инлайн-глиф «✦» — он рендерится по-разному на платформах и не может быть shared element.
- Геометрия: высота 44, паддинг 13×18, радиус 999; ширина по контенту, не фиксировать. Позиция — right 16, bottom = верх таб-бара + 16. Hit-area = сама пилюля (44), прозрачное поле не нужно.
- Фон — текстурное золото primary-кнопки (radial-свечение сверху + repeating-conic лучи + тёмная основа #1a1626→#0c0a14), кант rgba(228,196,138,.55).
- Тень: одна — 0 8 20 rgba(0,0,0,.45). Золотого ореола нет.
- Слой: поверх контента, **под** таб-баром/шитами/диалогами.

## 3. Жизнь (11 секунд)
- Вход: 380 мс, подъём 8 pt + fade, стандартная кривая (easeOutCubic).
- Кивки: wobble ±4° на 1-й и 6-й секунде (по 600 мс).
- Уход: 260 мс fade + осадка 8 pt вниз. 
- Немодальна: тапы мимо не закрывают; скролл контента уводит её вместе с инерцией (transform, не opacity) и по остановке скролла возвращает, если 11 с ещё не истекли.
- prefers-reduced-motion / системный reduce: без wobble и подъёма — только fade 260/260.

## 4. Нажатие — морф в шит (S49)
- Лёгкая хаптика (light impact).
- Скрим до 55 % за 240 мс; шит поднимается 380 мс (S32: скруглка 22 сверху, кант rgba(201,174,107,.3)).
- **Эмблема — shared element**: летит из пилюли в гнездо шита (по центру, над баннером), тело пилюли растворяется на месте (150 мс fade, без полёта).
- Закрытие (свайп вниз / «Not now» / тап по скриму) реверсирует всё; таймер жизни пилюли при этом не продолжается — она считается показанной.

## 5. Открытый шит (S32) — содержимое сверху вниз
1. Грабер 36×4.
2. Эмблема (дышит, scale 1→1.06, 5 с).
3. Арт-баннер (веер карт `art-fan`), 128, радиус 14.
4. Оверлайн «all of alma» · заголовок «Everything open, every day» (Playfair 26).
5. Подзаголовок: «Your chart is already calculated — and always free. The plan opens the writing.»
6. Три проверяемых факта (буллеты 15/1.5): утренний гороскоп из своей карты · транзиты/соляр/совместимость живут · 30 вопросов Alma в месяц.
7. Золотая CTA 56: «See the plans · from {price}» → открывает перечень планов (кадр **V8**; лестница S8 снята вместе с недельной и годовой подписками). Це́ны — только из каталога локали; `{price}` — самая дешёвая ступень, а не зашитое число.
8. «Not now» — текстовая, 15, hit-area ≥44.
9. Сноска честности: «One-time doors exist too · cancel any time in your Apple ID settings».

## 6. Память (persist, переживает перезапуск)
- `pill.notNowUntil[surface]` — «Not now» в шите → тишина 7 дней на этой поверхности.
- `pill.retired` — 3 «Not now» подряд (без покупок между) → пилюля навсегда выключена на этой установке; остаётся только статичная строка.
- Покупка любого продукта → `pill.retired = true`.
- Сессионные счётчики (показы, последний показ) — в памяти, не персистятся.

## 7. Строки (ключи + 7 языков)
`pillLabel`: en All of Alma · ru Вся Alma · de Ganz Alma · es Toda Alma · it Tutta Alma · fr Toute Alma · pt-BR Toda a Alma
`sheetOverline`: как pillLabel, lowercase.
`sheetTitle`: en Everything open, every day · ru Открыто всё — каждый день · de Alles offen, jeden Tag · es Todo abierto, cada día · it Tutto aperto, ogni giorno · fr Tout ouvert, chaque jour · pt-BR Tudo aberto, todos os dias
`sheetSub`: en Your chart is already calculated — and always free. The plan opens the writing. · ru Твоя карта уже рассчитана — и навсегда бесплатна. План открывает написанное. · de Deine Karte ist schon berechnet — für immer kostenlos. Der Plan öffnet das Geschriebene. · es Tu carta ya está calculada — y siempre gratis. El plan abre lo escrito. · it La tua carta è già calcolata — e sempre gratuita. Il piano apre ciò che è scritto. · fr Ta carte est déjà calculée — et gratuite pour toujours. Le forfait ouvre l'écrit. · pt-BR Seu mapa já está calculado — e sempre grátis. O plano abre o que foi escrito.
`sheetCta`: en See the plans · from {price} (аналогично остальным локалям: ru «К планам · от {price}», de „Zu den Plänen · ab {price}“, es «Ver los planes · desde {price}», it «Vedi i piani · da {price}», fr «Voir les forfaits · dès {price}», pt-BR «Ver os planos · a partir de {price}») — {price} из каталога.
`sheetNotNow`: en Not now · ru Не сейчас · de Nicht jetzt · es Ahora no · it Non ora · fr Pas maintenant · pt-BR Agora não
`sheetFootnote`: en One-time doors exist too · cancel any time in your Apple ID settings · ru Есть и разовые двери · отменить можно в любой момент в настройках Apple ID · de Es gibt auch Einmal-Türen · jederzeit in den Apple-ID-Einstellungen kündbar · es También hay puertas de pago único · cancela cuando quieras en los ajustes de tu Apple ID · it Esistono anche porte una tantum · annulla quando vuoi nelle impostazioni dell'ID Apple · fr Il existe aussi des portes à l'unité · annulable à tout moment dans les réglages de ton identifiant Apple · pt-BR Também existem portas avulsas · cancele quando quiser nos ajustes do seu ID Apple

Правило буллетов шита: три факта берутся из тех же ключей, что и перечень планов (**V8**) — не дублировать строки.

## 8. Аналитика (минимум)
`pill_shown {surface, session_count}` · `pill_expired` · `pill_tapped` · `sheet_dismissed {via}` · `sheet_cta_tapped` · `pill_retired {reason: three_dismissals|purchase}`.

## 9. Flutter-заметки
- Пилюля — `OverlayEntry` поверх таба (не в скролле!); скролл-увод — слушатель `ScrollController` ближайшего скролла поверхности.
- Морф эмблемы — `Hero` с общим tag между пилюлей и гнездом шита (шит открывать через route с `useSafeArea:false`), либо ручной `OverlayEntry`-полёт 380 мс, если шит — bottom sheet без route.
- Таймеры (6 с idle, 11 с жизни, кивки) гасить при `dispose`/уходе с поверхности; показ не переносится на другую поверхность.
- Ключи памяти — `SharedPreferences`, имена из §6.
