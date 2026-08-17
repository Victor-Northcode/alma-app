# Alma Design System — SKILL

Ночная люкс-система «интерактивной книги»: глубокая ночь, античное золото, гравюра и арт-вклейки. Всё, что ниже, — единственный источник правды для новых экранов Alma (Flutter-порт и веб-мокапы).

## 1 · Токены

### Цвет (ночь)
- `night.top #0A0D1C` → `night.mid #090C1A` → `night.deep #070A16` — базовый вертикальный градиент экрана
- `indigo.veil #101636` — панели, шиты, диалоги (градиент к `#0d1230`)
- `gold #C9AE6B` — акцент, overline, активные глифы
- `gold.light #E4D3A2` — вторичный золотой текст
- `gold.deep #A8873C` — золото на пергаменте, тени золота
- `gold.bright #F6E7BC` — точки планет, свечения
- `ivory #F6F1E4` — заголовки, главный текст
- `body #EDE7DA` — основной текст; muted: `rgba(237,231,218,.72 / .62 / .5)`
- `hairline rgba(237,231,218,.10)` — разделители строк
- `line.gold rgba(201,174,107,.34)` — гаснущая линейка: `linear-gradient(90deg,transparent,rgba(201,174,107,.34),transparent)`
- `error #E0917F`, бордер `rgba(140,58,43,.55)` — только контуром, никогда заливкой
- Пергамент (главы): фон `linear-gradient(135deg,#EDE3CC 0%,#EFE3C9 60%,#DFD0AF 100%)`, чернила `#1C1A17`, muted `rgba(28,26,23,.72)`, золото `#A8873C`

### Фон экрана (обязательный слой)
`background: <звёзды radial-gradient точками>, linear-gradient(180deg,rgba(10,13,28,.5),rgba(9,12,26,.68) 55%,rgba(7,10,22,.94)), url(./assets/bg-sky.png) center top/cover no-repeat`
Туманность всегда под скримом; текст читается на нижних 2/3.

### Типографика
- Дисплей: **Playfair Display** — 39/1.08 (имя дня), 29/1.12 (титулы экранов), 26 (шит), 22–23 (диалоги), 17.5/1.25 (строки-заголовки), numerals 14 (I…XVI, счётчики), italic 18.5/1.5 (голос Alma), italic 22/1.32 (церемония)
- Текст: **Golos Text** — 15.5/1.55 body, 13/1.45 meta, 16.5 CTA, overline `600 11.5px, letter-spacing 2.5px, uppercase, gold`, микро-лейбл `600 10px ls 1.6`
- Минимум на телефоне: 11px; хиты ≥44px

### Метрики
- Паддинг экрана 22 · статус-зона 64 · таб-бар 84 (blur + градиент к `rgba(7,10,22,.98)`)
- Радиусы: пилюли/поля 27–28 (h 54–56) · карточки/баннеры 14 · арка-вклейка `85px 85px 12px 12px` · шит/диалог 22–24 · CTA Journey 15
- Кнопочные высоты: primary 54–56, secondary 50–52, compact 44–46

## 2 · Компоненты (рецепты)

### Кнопка Primary — «текстурное золото» (эталон S44)
```css
background:
 radial-gradient(140% 220% at 50% -80%, rgba(228,196,138,.55), rgba(20,16,25,.05) 55%),
 repeating-conic-gradient(from -8deg at 50% 130%, rgba(201,174,107,.4) 0deg 1.8deg, transparent 1.8deg 7deg),
 linear-gradient(180deg,#1a1626,#0c0a14);
border:1px solid rgba(228,196,138,.55); border-radius:28px; height:56px;
color:#F6F1E4; font:600 16.5px 'Golos Text';
```
Никогда: плоская золотая заливка с тёмным текстом.

### Кнопка Secondary — вуаль
`background:rgba(237,231,218,.1); border-radius:26px; color:#F6F1E4`

### Кнопка Outline gold / Destructive
`border:1px solid rgba(201,174,107,.5); color:#E4D3A2` · destructive: `border:1px solid rgba(224,145,127,.5); color:#E0917F` — красное только контуром.

### Поле ввода
`height:54–56; background:rgba(13,16,28,.85); border:1px solid rgba(237,231,218,.12); border-radius:28px; padding:0 20px` — плейсхолдер `rgba(237,231,218,.45)` справа, значение слева.

### Overline-заголовок секции
gold overline + гаснущая линейка справа (`flex`, rule `height:1px`, gradient line.gold), опционально счётчик Playfair 14 gold справа.

### Строка списка
`padding 15–18px 0; border-bottom:hairline` — слева Playfair 17.5 ivory (или Golos 15 muted для лейбла), справа Playfair 14–17 gold (значение/статус).

### Строка главы
Роман-нумерал Playfair 14 gold (w44) + титул Playfair 17.5 + вопрос Golos 13 muted.

### Арка-вклейка (plate)
`width 148–170; height 182–210; border-radius:85px 85px 12px 12px; border:1px solid rgba(201,174,107,.5); inner border inset:5px rgba(246,231,188,.4)`; на пергаменте бордеры `#A8873C`.

### Карта (арт)
`border-radius:12–14; border:1px solid rgba(201,174,107,.5); внутренний кант inset:5px rgba(246,231,188,.45); плашка снизу: gradient rgba(7,10,22,0→.85), подпись Playfair 15 #F6E7BC`.

### Диалог-церемония
Панель `linear-gradient(180deg,#131a3f,#0d1230); border:1px solid rgba(201,174,107,.5); radius 24; двойной внутренний кант; знак Alma в кольце сверху; заголовок по центру; кнопки Keep(вуаль)/Remove(красный контур) пополам`.

### Таб-бар
4 вкладки: Today (солнце-лучи), My systems (двойное кольцо), Alma (radial-орб), Settings (штифты). Активная — gold, остальные `rgba(237,231,218,.5)`; лейбл 10px. В чате бар скрыт: композер внизу + «Swipe up for tabs».

### Эмблема Alma
Ромб 64px `linear-gradient(135deg,#FBEDC4,#E0C077 34%,#B3913F 70%,#8A6F2E)` rotate 45°, чёрная 4-луч звезда внутри, вокруг два встречных лучевых кольца (repeating-conic + radial-mask, spin 70/90s).

## 3 · Правила композиции
1. Один акцент на экран: либо большая цифра/медальон, либо арт-герой — не оба.
2. Пороги (вход, двери, церемония, пейволлы) — богатые: арт, филигрань `assets/art-divider.png` (masked), рубашки карт по краям. Ежедневные (Today, чат, настройки) — тихие: небо+типографика.
3. Рисунки данных (колёса, кольца, карта линий) — только код+анимация; арт — в карточках, баннерах, вклейках.
4. Каждая глава открывается аркой-вклейкой своей темы (см. `assets/plate-*.png`, 41 глава = доска «The chapter plates»).
5. Витрины: «Every calculation stays free» — ДО цен; условия продления — до кнопки; validator-строка дословно.
6. Эмодзи запрещены; глифы — типографские (☽ ☉ ♀ …) с `&#xFE0E;`.

## 4 · Движение
- Микро 120–260ms, переходы 380–620ms, каскад появления 70ms / 16pt
- Дыхание (breathe) 4–6s; вращение колец (spinSlow) 70–200s; shimmer скелетонов 1.9s
- «Небо движется — интерфейс нет»: анимируются свечения и кольца, не layout.

## 5 · Ассеты
- `assets/bg-sky.png` — туманность-фон (всегда под скримом); `bg-globe-wide.png` — резерв для астро.
- Колода систем: `card-natal/-birthcard/-solar/-astro/-numerology/-transits/-compat/-synthesis.png`
- Вклейки глав: `plate-*.png` (16 natal + числа/год/транзиты/соляр/совместимость/карта/астро/синтез; дубли допустимы и помечены)
- Продающий слой: `art-gates`, `art-fan`, `art-couple`, `art-globe`, `art-divider`
- Референс живых экранов: S44 (вход), S46/S42 (двери), S41 (диалог), S47 (колода).
