# Today (подписка) + читалка длинного гороскопа — спека

Эталон: **Alma — Today Reading.dc.html** (R1 Today · R2 читалка · R3 сноска термина · R4 конец чтения · F1 шрифт · F2 правила).
Проблема, которую это решает: у подписчика гороскоп на 2 000+ знаков вылит прямо на Today курсивным дисплейным шрифтом — два экрана скролла, бар наезжает на текст, области уезжают за сгиб.

## 1. Шрифты — три роли, три гарнитуры
| Роль | Гарнитура | Применение |
|---|---|---|
| Дисплей | **Playfair Display** 400/500 | имя дня, титулы экранов, цифры, мета-строка «read from» |
| Чтение | **Lora** 400/500 (+ italic) | гороскоп, главы, голос Alma, длинные строки областей |
| Интерфейс | **Golos Text** 400/500/600 | подписи, оверлайны, кнопки, юридика |

**Замена курсива Playfair на Lora — главное решение.** Причина: Playfair — дисплейная антиква с высоким контрастом; на 17–18.5 pt тонкие штрихи на тёмном пропадают, курсив добавляет наклон и «Ъ»-образные связки — читать 2 000 знаков больно. Lora: умеренный контраст, крупная x-height, каллиграфическое тепло, рисована под экран, полная кириллица + latin-ext (все 7 локалей). Playfair остаётся — но только в дисплее.

Голос Alma: **Lora upright 17/1.65** по умолчанию; если голос обязан быть курсивным — Lora italic 17, но не длиннее ~400 знаков на ответ, дальше переключаться на прямое.

Размеры чтения: лид 500 20/1.42 · тело 17/1.65 · сноска 15/1.6 · мета Playfair 14. «Aa» даёт три ступени (16 / 17 / 19), выбор хранится per user.

## 2. R1 — Today у подписчика
- Шапка без изменений (дата, имя Playfair 39, фаза, медальон 86 с дыханием 7 с).
- Карточка гороскопа: оверлайн + «3 min» справа, **лид одной фразой** (Lora 500 20), **один абзац** (17/1.62), мета-строка, кнопка-контур 50 «Read the whole sky →».
- Ниже — блок областей (30-дневный горизонт: дальше 30 дней — без даты).
- Экран обязан заканчиваться до бара 84 без скролла. Полный текст на Today не выводится **никогда**.

## 3. R2 — читалка
- Отдельный маршрут (push), **таб-бара нет**: чтение — комната.
- Верхняя панель 100: «←», центр «AUGUST 16 · YOUR SKY» (Golos 600 10.5, ls 2.2), «Aa» справа; под ней прогресс-полоса 2 px, золото по заполнению.
- Колонка: паддинг 22, одна мера строки; лид → ✦-разделитель → абзацы 17/1.65 с отбивкой 15.
- Смысловые части получают тихий подзаголовок (Golos 600 11, ls 2.2, «the steady part») с гаснущей линией — движок помечает части, клиент не разрезает текст сам.
- Справа нить прогресса 2 px с бусиной (позиция чтения).
- Низ: мета-строка «read from» + карточка «Ask Alma about {aspect} →» (ведёт в чат с подставленным вопросом).
- Позиция чтения сохраняется; возврат на Today не сбрасывает её.

## 4. R3 — термины объясняют себя
- Терминам движок ставит разметку; в тексте — точечное подчёркивание rgba(201,174,107,.85) и цвет #F6E7BC. Активный термин — сплошное подчёркивание.
- Тап → карточка-сноска над текстом (индиго, двойная рамка, радиус 20): имя термина Playfair 19, **одна простая фраза** Lora 15/1.6, строка «yours» с личными позициями, ссылка «Read it in {system} — {chapter} →».
- Текст под карточкой притушен до .4, скролл заблокирован; закрытие — «×», тап вне, свайп вниз.
- Следствие для движка: **в прозе больше не нужны пояснения в скобках** («Chiron — a small planet that marks…»), их место — сноска. Это укорачивает текст примерно на четверть.

## 5. R4 — конец дня
Вклейка луны (150, кант + внутренний штрих) с подписью фазы → «the areas» списком (область 74 колонка, факт Lora 15, дата Playfair 13 справа; «Nothing exact here today» — .55) → ✦-разделитель → одна строка про завтра → «Written at 06:00, your time». Никакой ленты и «дальше по теме».

## 6. Строки (7 языков, ru на «ты»)
`todayReadWholeSky` — en `Read the whole sky` · ru `Прочитать всё небо` · de `Den ganzen Himmel lesen` · es `Leer todo el cielo` · it `Leggi tutto il cielo` · fr `Lire tout le ciel` · pt-BR `Ler todo o céu`
`todayReadMinutes` — en `{n} min` · ru `{n} мин` · de `{n} Min.` · es `{n} min` · it `{n} min` · fr `{n} min` · pt-BR `{n} min`
`readerHeader` — en `{date} · your sky` · ru `{date} · твоё небо` · de `{date} · dein Himmel` · es `{date} · tu cielo` · it `{date} · il tuo cielo` · fr `{date} · ton ciel` · pt-BR `{date} · seu céu`
`readerAskAboutIt` — en `Ask Alma about {aspect}` · ru `Спросить Alma про {aspect}` · de `Frag Alma zu {aspect}` · es `Pregúntale a Alma sobre {aspect}` · it `Chiedi ad Alma di {aspect}` · fr `Demande à Alma à propos de {aspect}` · pt-BR `Pergunte à Alma sobre {aspect}`
`readerTermYours` — en `yours` · ru `у тебя` · de `bei dir` · es `en tu carta` · it `nella tua carta` · fr `chez toi` · pt-BR `no seu mapa`
`readerReadInChapter` — en `Read it in {system} — {chapter}` · ru `Прочитать в «{system}» — {chapter}` · de `Lies es in {system} — {chapter}` · es `Léelo en {system} — {chapter}` · it `Leggilo in {system} — {chapter}` · fr `Lis-le dans {system} — {chapter}` · pt-BR `Leia em {system} — {chapter}`
`readerTomorrow` — en `Tomorrow {event}` · ru `Завтра {event}` · de `Morgen {event}` · es `Mañana {event}` · it `Domani {event}` · fr `Demain {event}` · pt-BR `Amanhã {event}`
`readerWrittenAt` — en `Written at {time}, your time` · ru `Написано в {time} по твоему времени` · de `Geschrieben um {time}, deine Zeit` · es `Escrito a las {time}, tu hora` · it `Scritto alle {time}, ora tua` · fr `Écrit à {time}, ton heure` · pt-BR `Escrito às {time}, seu horário`
`readerTextSize` — en `Text size` · ru `Размер текста` · de `Textgröße` · es `Tamaño del texto` · it `Dimensione del testo` · fr `Taille du texte` · pt-BR `Tamanho do texto`

## 7. Flutter-заметки
- Шрифт: `GoogleFonts.lora()` — добавить в бандл вариативный TTF вместе с Playfair/Golos, кириллицу не вырезать.
- Читалка — отдельный роут `/today/reading`; `PageStorageKey` + сохранение офсета в prefs (ключ = дата гороскопа).
- Прогресс: `ScrollController.offset / maxScrollExtent` → верхняя полоса и нить справа (одно значение, два рисунка).
- Термины: движок отдаёт `spans: [{start, end, termId}]` — рендерить `TextSpan` с `recognizer`, не парсить текст регулярками на клиенте.
- Сноска: `showGeneralDialog` с barrier .62 + blur, тап вне и свайп вниз закрывают.
- Части текста: `sections: [{title?, paragraphs[]}]` — заголовок опционален, клиент сам текст не режет.
- Кнопка «Ask Alma about {aspect}» открывает таб Alma с предзаполненным композером (черновик не отправляется сам).
- «Aa» — три ступени, `MediaQuery.textScaler` уважать сверху (макс 1.3, дальше колонка становится 1 мерой без обрезки).
