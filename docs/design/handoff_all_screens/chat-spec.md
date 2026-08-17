# Чат Alma — «живое присутствие»: спека для разработчиков

Эталоны: **Alma — Chat States.dc.html** (A1–A5, цепочка одного вопроса) + S6/S7 на основном холсте. Механика бара/грабера — отдельно в чат-разделе screen-map и ниже §7.

Принцип: Alma — не аватар и не «печатающий бот». Она — **свет, который дышит**, и её думание **называет настоящий расчёт**. Ничего не движется, пока человек читает текст (закон движения).

## 1. Свет-присутствие
- Радиальный глоу (как иконка таба): `radial-gradient(circle, rgba(246,231,188,.9) 0%, rgba(201,174,107,.4) 45%, transparent 75%)`.
- Размеры: приветствие 64 · в шапке ответа 26 · думание 70 (внутри кольца 110).
- Дыхание: scale 1→1.07, 5 с ease-in-out, на своих часах; в думании учащается до 2.6 с.
- На отправку вопроса свет «наклоняется»: яркость +15 % за 240 мс.

## 2. Состояния (цепочка A1→A5)
**A1 Приветствие** — свет по центру, оверлайн `alma`, курсив Playfair 19: приветствие по имени + одна правда из сегодняшнего транзита (пишется движком, с датой). Гаснущий разделитель с ✦. Под ним тихая строка «I answer from your chart, never from a template».
**A2 Думание** — вокруг света кольцо лучей (`repeating-conic` 2.2°/8°, маска в кольцо 46–66 %), вращение **9 с** linear (не 70–200 с фоновых — это активная работа, но и не спиннер). Под светом пульсирующая строка (glowPulse 2.4 с): `reading your fourth house…` — **имя дома/планеты из реального запроса движка**. Ниже мелкой строкой тела: `sun 17°46′ ♓︎ · saturn 4°09′ ♑︎`. Композер на время думания — opacity .55, не disabled-серый.
**A3 Источник первым** — шапка ответа (свет 26 + `alma` + линейка) и **мета-строка «read from» появляются ДО текста**: она открыла карту, потом заговорила. Первая строка ответа тлеет на opacity .18.
**A4 Чернильное проявление** — строки ответа оседают каскадом: fade + подъём 4–8 pt, **70 мс на строку**; по эталону: строка N = opacity 1, N+1 = .55, N+2 = .22. Никакого посимвольного тайпрайтера. Золотая линейка под `alma` дорисовывается последней (width 34 %→100 %).
**A5 Осевший ответ** — полный текст, карточка-ссылка «Read the chapter it comes from — {chapter}» (кант rgba(201,174,107,.3), радиус 12), счётчик «Questions available» уменьшился, композер шепчет следующий живой плейсхолдер.

## 3. Живой плейсхолдер композера
- Не «Ask Alma», а вопрос из карты пользователя: `Ask about the knot in your seventh house…`, `Ask about Saturn on your Midheaven…`.
- Источник: движок отдаёт 3–5 подсказок из реальных позиций; ротация — раз в визит на таб (не таймером в фокусе).
- Цвет rgba(237,231,218,.5); после ответа плейсхолдер меняется на следующий.
- Строки подсказок — из каталога, шаблон `askHint{N}` с плейсхолдерами тел/домов.

## 4. Тайминги (словарь движения)
- Отправка вопроса: пузырь оседает 240 мс; свет наклоняется 240 мс.
- Вход в думание: кольцо проявляется 380 мс; строка «reading…» сменяется при смене дома без анимации текста (fade 120 мс).
- A3: мета-строка появляется 240 мс; A4 каскад 70 мс/строка; линейка 420 мс.
- Reduced motion: без кольца и каскада — состояния сменяются fade 260 мс; дыхание отключено.

## 5. Строки (ключи, 7 языков — ru на «ты»)
`chatReadingHouse` — en `reading your {house} house…` · ru `читаю твой {house} дом…` · de `lese dein {house} Haus…` · es `leyendo tu casa {house}…` · it `leggo la tua {house} casa…` · fr `je lis ta {house} maison…` · pt-BR `lendo sua casa {house}…` ({house} — порядковое из каталога).
`chatOpeningBody` — en `opening {body}…` · ru `открываю {body}…` · de `öffne {body}…` · es `abriendo {body}…` · it `apro {body}…` · fr `j'ouvre {body}…` · pt-BR `abrindo {body}…`.
`chatFromChapter` — en `Read the chapter it comes from — {chapter}` · ru `Прочитай главу, из которой это — {chapter}` · de `Lies das Kapitel dahinter — {chapter}` · es `Lee el capítulo del que viene — {chapter}` · it `Leggi il capitolo da cui viene — {chapter}` · fr `Lis le chapitre d'où ça vient — {chapter}` · pt-BR `Leia o capítulo de onde isso vem — {chapter}`.
`chatNotTemplate` — en `I answer from your chart, never from a template.` · ru `Я отвечаю из твоей карты — никогда по шаблону.` · de `Ich antworte aus deiner Karte — nie aus einer Vorlage.` · es `Respondo desde tu carta, nunca desde una plantilla.` · it `Rispondo dalla tua carta, mai da un modello.` · fr `Je réponds depuis ta carte, jamais d'après un modèle.` · pt-BR `Respondo a partir do seu mapa, nunca de um modelo.`
Приветствия и подсказки (`askHint*`) пишутся движком из позиций — клиент не хардкодит.

## 6. Правила честности
- «reading your …» показывается только с настоящими данными запроса; если движок не отдал контекст — нейтральное `reading your chart…`, никаких выдуманных домов.
- Мета-строка «read from» — по meta-line-spec.md (тело словом, глиф знака `\uFE0E`, регистр по языку).
- Счётчик вопросов виден до отправки и убавляется после ответа, не после отправки.

## 7. Каркас экрана
- Таб Alma живёт без таб-бара: композер 54/27 + грабер («Swipe up for tabs», ключ `scrChatSwipeForTabs`) — механика в решениях чата: свайп по граберу открывает бар оверлеем 380 мс, автоскрытие ~3 с; клавиатура прячет грабер.
- Черновик и тред переживают смену таба и перезапуск (state is never lost).
- Свет — вне колонки текста; при скролле треда шапочный свет не следует (никаких sticky-аватаров).

## 8. Flutter-заметки
- Свет и кольцо — `CustomPaint`/`ShaderMask` + `AnimationController` на своих часах; **не** Lottie.
- Каскад A4 — `AnimatedOpacity`+`Transform.translate` по строкам layout'а (разбивка по `TextPainter.computeLineMetrics`), не по словам.
- Состояние думания — стрим от движка: `{stage: house|body, name}` → строка меняется по факту работы.
- Плейсхолдеры — из ответа `/v1/chat/hints`, кэш на сессию.
