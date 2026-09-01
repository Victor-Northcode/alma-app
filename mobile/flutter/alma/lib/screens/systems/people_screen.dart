import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:share_plus/share_plus.dart';

import '../../design/buttons.dart';
import '../../design/emblem.dart';
import '../../design/metrics.dart';
import '../../design/night_sheet.dart';
import '../../design/palette.dart';
import '../../design/screen_scaffold.dart';
import '../../design/section_label.dart';
import '../../design/typography.dart';
import '../../design/wheel.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/session.dart';
import 'birth_form_parts.dart';

/// Люди, с которыми сравнивают: список, добавление и удаление.
///
/// Порт `PeopleScreen.swift`. Без него совместимость недостижима в принципе —
/// сервер требует второго человека, а завести его было нечем: метод сохранения
/// с `isSelf: false` существовал в клиенте и не вызывался ниоткуда.
///
/// Форма нарочно короче анкеты: имя, дата, время (можно не знать) и место.
/// Пол здесь не спрашивают — он влияет на род в письме о *читателе*, а не о
/// том, с кем его сравнивают.
class PeopleScreen extends StatefulWidget {
  const PeopleScreen({super.key, this.picking = false});

  /// Экран открыт **за ответом**: кого читать в главе про пару.
  ///
  /// **Разница не в оформлении, а в том, чем экран кончается.** В обычном
  /// режиме это управление списком: сохранил — остался, форма опустела, можно
  /// добавить второго. В режиме выбора экран обязан вернуть человека тому, кто
  /// его звал, — `Navigator.pop(context, profile)`, — потому что глава
  /// совместимости не имеет права угадывать пару: сервер подставляет второго
  /// сам только пока он ровно один, а при двоих отвечает 422
  /// `partner_required`. Названный человек — единственный способ не сломать
  /// главу ровно у того, кто добавил двоих.
  ///
  /// Заодно сохранённые люди становятся строками-кнопками: список, из которого
  /// нельзя выбрать, — тот же тупик, ради снятия которого затевалась карточка
  /// совместимости в «Моих системах».
  final bool picking;

  @override
  State<PeopleScreen> createState() => _PeopleScreenState();
}

class _PeopleScreenState extends State<PeopleScreen> {
  final _name = TextEditingController();
  final _place = TextEditingController();
  int _day = 1, _month = 1, _year = 1990, _hour = 12, _minute = 0;
  bool _timeUnknown = false;
  Place? _chosen;
  List<Place> _found = const [];
  bool _saving = false;
  String? _failure;

  /// Живые связи по id профиля: кто из списка — не запись с датой, а человек
  /// с аккаунтом, пришедший по ссылке-приглашению. Пусто до ответа сервера и
  /// при отказе сети — бейдж «в Alma» тогда просто не рисуется: список людей
  /// не имеет права ждать сеть или падать из-за неё.
  Map<String, FriendLink> _live = const {};
  bool _inviting = false;

  /// Отказ приглашения — своей строкой под своей кнопкой, а не в `_failure`
  /// формы внизу: ошибка, всплывшая в другом конце экрана, читается как чужая.
  String? _inviteFailure;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadFriends());
  }

  Future<void> _loadFriends() async {
    if (!mounted) return;
    try {
      final links = await SessionScope.of(context).client.friends();
      if (mounted) {
        setState(() =>
            _live = {for (final link in links) link.profileId: link});
      }
    } on AlmaError {
      // Молча: связи — украшение списка, не его условие.
    }
  }

  /// **Позвать в Alma** — ссылка «проверь нас» в системный шэр.
  ///
  /// Цикл роста (владелец, 31.08.2026): ссылка уходит человеку, тот вводит
  /// свою дату на веб-странице, и совместимость появляется у обоих — второй
  /// приходит живым аккаунтом, а не записью. 422 `no_self_birth` отвечает
  /// словами о причине: без своей даты приглашение обещает сравнение,
  /// половины которого нет.
  Future<void> _invite() async {
    if (_inviting) return;
    final l = L.of(context);
    final session = SessionScope.of(context);
    setState(() {
      _inviting = true;
      _inviteFailure = null;
    });
    try {
      final url = await session.client.createFriendInvite();
      if (!mounted) return;
      setState(() => _inviting = false);
      await Share.share(l.scrPeopleInviteShare(url));
    } on AlmaError catch (error) {
      if (!mounted) return;
      setState(() {
        _inviting = false;
        _inviteFailure =
            error is ServerRefused && error.code == 'no_self_birth'
                ? l.scrPeopleInviteNeedsBirth
                : (error is ServerRefused && error.message.isNotEmpty
                    ? error.message
                    : null);
      });
    }
  }

  @override
  void dispose() {
    _name.dispose();
    _place.dispose();
    super.dispose();
  }

  Future<void> _search(String query) async {
    if (query.trim().length < 2) return;
    try {
      final session = SessionScope.of(context);
      final found =
          await session.client.searchPlaces(query, locale: session.locale);
      if (mounted) setState(() => _found = found.take(5).toList());
    } on AlmaError {
      // Молча: место можно поискать ещё раз.
    }
  }

  Future<void> _save() async {
    final place = _chosen;
    if (place == null || _saving) return;
    final session = SessionScope.of(context);
    setState(() {
      _saving = true;
      _failure = null;
    });
    try {
      // Сохранение — общее с W2 (`birth_form_parts.dart`): язык отказа,
      // `isSelf: false` и перечитанная сессия живут там ровно один раз.
      final saved = await savePartner(
        session,
        birthDate: '${_year.toString().padLeft(4, '0')}-'
            '${_month.toString().padLeft(2, '0')}-'
            '${_day.toString().padLeft(2, '0')}',
        birthTime: _timeUnknown
            ? null
            : '${_hour.toString().padLeft(2, '0')}:${_minute.toString().padLeft(2, '0')}',
        place: place,
        name: _name.text,
      );
      if (!mounted) return;
      // **За человеком пришли — человека и возвращаем.** Оставить того, кто
      // только что назвал пару, на пустой форме значило бы потребовать от него
      // ещё одного действия ради того, что он уже сделал: самый дорогой импульс
      // продукта гасится именно такими лишними шагами.
      if (widget.picking) {
        Navigator.of(context).pop(saved);
        return;
      }
      setState(() {
        _saving = false;
        _name.clear();
        _place.clear();
        _chosen = null;
        _found = const [];
      });
    } on AlmaError catch (error) {
      if (mounted) {
        setState(() {
          _saving = false;
          _failure = error is ServerRefused && error.message.isNotEmpty
              ? error.message
              : null;
        });
      }
    }
  }

  /// **Подтверждение, а не одно нажатие.** Удаление человека уносит и каждое
  /// чтение совместимости, написанное из его рождения, — а оплаченное чтение
  /// нельзя переписать слово в слово. Одно нажатие рядом с именем это ровно
  /// тот случай, ради которого подтверждения и существуют.
  Future<void> _confirmRemove(Profile person) async {
    final l = L.of(context);
    final yes = await showDialog<bool>(
      context: context,
      // Затемнение из макета: почти чёрное небо на шесть десятых, а не
      // материаловская серая вуаль.
      barrierColor: AlmaPalette.voidDark.withValues(alpha: 0.6),
      // **`Dialog`, а не `AlertDialog`.**
      //
      // `AlertDialog` меряет свои действия внутренними размерами
      // (`getMinIntrinsicWidth`), а подпись `AlmaButton` стоит в
      // `LayoutBuilder` — тот внутренних размеров не отдаёт и падает
      // «LayoutBuilder does not support returning intrinsic dimensions».
      // То есть кнопки продукта в `AlertDialog.actions` не живут вообще;
      // проверено зондом, а не на глаз. Ручная колонка ничего не меряет.
      builder: (context) => Dialog(
        backgroundColor: Colors.transparent,
        elevation: 0,
        insetPadding: const EdgeInsets.symmetric(horizontal: 34),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 26),
          decoration: BoxDecoration(
            // Ночная плашка с золотым кантом и скруглением 22 — форма из
            // дизайн-проекта (s41). Material 3 рисовал здесь свою поверхность
            // и своё скругление, и диалог выходил чужим на экране, у которого
            // всё остальное небо и золото.
            color: AlmaPalette.night700,
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.3)),
            boxShadow: const [
              BoxShadow(
                  color: Color(0x99000000),
                  blurRadius: 60,
                  offset: Offset(0, 24)),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Ступень между заголовком экрана (29) и заголовком строки
              // (17.5) — ровно та, которой в макете набран вопрос диалога.
              Text(l.scrPeopleRemoveTitle,
                  style: AlmaType.displayL.copyWith(fontSize: 22, height: 1.2)),
              const SizedBox(height: 12),
              Text(l.scrPeopleRemoveWhat, style: AlmaType.meta),
              const SizedBox(height: 22),
              // **Кнопки продукта, а не материаловские.** «Оставить» — тихая
              // вуаль, «Удалить» — `danger`, то есть всегда обводка: красную
              // заливку нажимают рефлексом, а это ровно тот экран, где рефлекс
              // уносит оплаченные чтения. Разная высота (50 против 44) — не
              // недосмотр: иерархия в этой дизайн-системе держится высотой, и
              // разрушающее действие обязано быть ниже безопасного.
              //
              // `Wrap`, а не `Row`: `Row` раздал бы кнопкам неограниченную
              // ширину, а подпись внутри `AlmaButton` стоит во `Flexible` —
              // упало бы на «RenderFlex … constraints are unbounded». `Wrap`
              // даёт ограниченную ширину и переносит вторую кнопку под первую,
              // когда перевод длиннее строки, — а языков здесь семь.
              Wrap(
                alignment: WrapAlignment.end,
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 10,
                runSpacing: 10,
                children: [
                  AlmaButton(
                    kind: AlmaButtonKind.veil,
                    fills: false,
                    label: l.scrKeep,
                    onTap: () => Navigator.of(context).pop(false),
                  ),
                  AlmaButton(
                    kind: AlmaButtonKind.danger,
                    fills: false,
                    label: l.scrPeopleRemove,
                    onTap: () => Navigator.of(context).pop(true),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
    if (yes == true && mounted) await _remove(person);
  }

  Future<void> _remove(Profile person) async {
    final session = SessionScope.of(context);
    try {
      await session.client.deleteProfile(person.id);
      await session.start(force: true);
      if (mounted) setState(() {});
    } on AlmaError {
      if (mounted) setState(() {});
    }
  }

  /// Три факта через точку: дата, время (или что оно неизвестно) и город.
  /// Пропущенное не оставляет пустого места между разделителями.
  String _facts(L l, Profile person) => [
        _civilDate(l.localeName, person.birthDate),
        person.birthTime ?? l.cabUnknownTime,
        person.placeLabel,
      ].whereType<String>().where((s) => s.isNotEmpty).join(' · ');

  /// Гражданская дата — не мгновение: разбор её как времени в поясе устройства
  /// делал бы 11 мая десятым для всех западнее Лондона.
  static String _civilDate(String locale, String civil) {
    final parts = civil.split('-');
    if (parts.length != 3) return civil;
    return DateFormat.yMMMMd(locale).format(
        DateTime.utc(int.parse(parts[0]), int.parse(parts[1]), int.parse(parts[2])));
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final session = SessionScope.of(context);
    return Scaffold(
      backgroundColor: AlmaPalette.night,
      // **Своя material-поверхность — иначе экран не открывается вовсе.**
      //
      // `ScreenScaffold` — это небо и колонка, а не `Material`: на вкладках его
      // держит `Scaffold` кабинета. Сюда же приходят маршрутом
      // (`CupertinoPageRoute`, из главы — вообще через корневой навигатор), и
      // над экраном нет ни одного `Material`. А `TextField`, `ListTile`,
      // `SwitchListTile` и `InkWell` его требуют утверждением
      // `debugCheckHasMaterial` — то есть страница людей падала «No Material
      // widget found» ровно в тот момент, когда за вторым человеком приходили
      // из закрытой главы совместимости. Ту же дыру уже закрыли в витрине
      // (`offer_screen.dart`), и закрывается она тем же способом.
      body: ScreenScaffold(
        seed: 0x50454F50,
        title: l.cabPeopleTitle,
        children: [
          // **«Позвать в Alma» — над списком.** Рост важнее менеджмента
          // записей: ссылка «проверь нас» — то, ради чего фича друзей
          // заведена (31.08.2026), и прятать её под форму значило бы
          // спрятать самый ценный жест экрана.
          AlmaButton(
            label: l.scrPeopleInvite,
            onTap: _inviting ? null : _invite,
          ),
          if (_inviteFailure != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(_inviteFailure!, style: AlmaType.meta),
            ),
          const SizedBox(height: AlmaMetrics.gapLarge),
          if (session.people.isNotEmpty) ...[
            SectionLabel(l.cabPeopleTitle, trailing: '${session.people.length}'),
            const SizedBox(height: 8),
            // **Строка человека — это его данные, а не только имя.** Раньше
            // здесь стояло имя или голая дата «1992-05-11», и человек,
            // добавивший двоих, не мог отличить их иначе как по имени: ни
            // города, ни времени, ни кем приходится. Три факта через точку —
            // как на нативе и как в макете.
            for (final person in session.people)
              GestureDetector(
                // Строка отвечает на тап только тогда, когда за ответом
                // пришли: в обычном режиме это список, которым управляют, и
                // молчаливый `pop` с человеком отсюда выбросил бы с экрана
                // того, кто зашёл добавить второго.
                behavior: HitTestBehavior.opaque,
                onTap: widget.picking
                    ? () => Navigator.of(context).pop(person)
                    : null,
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 15),
                  decoration: BoxDecoration(
                    border:
                        Border(bottom: BorderSide(color: AlmaPalette.hairline)),
                  ),
                  child: Row(children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(children: [
                            Flexible(
                              child: Text(
                                person.name?.isNotEmpty == true
                                    ? person.name!
                                    : l.scrPeopleUnnamed,
                                style: AlmaType.headingM,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            // «В ALMA» — живой аккаунт, пришедший по
                            // приглашению, а не запись с датой. Золотом:
                            // это событие списка, ради которого фича и
                            // заведена, — не мебель.
                            if (_live.containsKey(person.id)) ...[
                              const SizedBox(width: 8),
                              Text(l.scrPeopleLive.toUpperCase(),
                                  style: AlmaType.tag
                                      .copyWith(color: AlmaPalette.gold)),
                            ],
                          ]),
                          const SizedBox(height: 4),
                          Text(_facts(l, person), style: AlmaType.meta),
                          if (person.relation?.isNotEmpty == true) ...[
                            const SizedBox(height: 4),
                            // Приглушённым, а не золотом: золото на каждой
                            // строке перестаёт значить «вот это главное».
                            Text(person.relation!.toUpperCase(),
                                style: AlmaType.tag
                                    .copyWith(color: AlmaPalette.muted3)),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(width: 14),
                    TextButton(
                      onPressed: () => _confirmRemove(person),
                      child: Text(l.scrPeopleRemove,
                          style: AlmaType.meta.copyWith(
                              color: AlmaPalette.disagree
                                  .withValues(alpha: 0.85))),
                    ),
                  ]),
                ),
              ),
            const SizedBox(height: AlmaMetrics.gapLarge),
          ],
          SectionLabel(l.cabPeopleAdd),
          const SizedBox(height: 12),
          // **Поле продукта, а не материаловское.** Здесь стоял `TextField` с
          // `OutlineInputBorder` — то есть чужая форма с плавающей подписью и
          // материаловским фокусом. У продукта поля пилюлями: в покое тёмная
          // плашка с бледным кантом, под курсором — золотое кольцо, сквозь
          // которое видно небо. `CeremonialField` рисует ровно это, и её
          // собственный комментарий ссылается на «Hamb» из этого же макета.
          CeremonialField(controller: _name, hint: l.journeyNamePlaceholder),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(
                child: _number(l.journeyCaptureDayShort, _day, 1, 31,
                    (v) => setState(() => _day = v))),
            const SizedBox(width: 8),
            Expanded(
                child: _number(l.journeyCaptureMonthShort, _month, 1, 12,
                    (v) => setState(() => _month = v))),
            const SizedBox(width: 8),
            Expanded(
                child: _number(l.journeyCaptureYearShort, _year, 1900,
                    DateTime.now().year, (v) => setState(() => _year = v))),
          ]),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(
                child: _number(l.journeyHourLabel, _hour, 0, 23,
                    (v) => setState(() => _hour = v))),
            const SizedBox(width: 8),
            Expanded(
                child: _number(l.journeyMinuteLabel, _minute, 0, 59,
                    (v) => setState(() => _minute = v))),
          ]),
          // **Строка с тумблером, а не `SwitchListTile`.** В макете это подпись
          // слева и тумблер справа — ровно строка. `ListTile` же красит фон и
          // всплеск на ближайшем `Material`, а между ним и этой строкой стоит
          // небо (`ColoredBox`); Flutter ловит это утверждением «ListTile
          // background color or ink splashes may be invisible» и роняет экран.
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 14),
            child: Row(children: [
              Expanded(child: Text(l.cabUnknownTime, style: AlmaType.meta)),
              Switch(
                value: _timeUnknown,
                activeThumbColor: AlmaPalette.gold,
                inactiveThumbColor: AlmaPalette.body.withValues(alpha: 0.6),
                inactiveTrackColor: AlmaPalette.body.withValues(alpha: 0.12),
                onChanged: (v) => setState(() => _timeUnknown = v),
              ),
            ]),
          ),
          CeremonialField(
            controller: _place,
            hint: l.journeyCaptureSearchPlace,
            onChanged: _search,
          ),
          PlaceSuggestions(
            found: _found,
            onPick: (place) => setState(() {
              _chosen = place;
              _place.text = place.label;
              _found = const [];
            }),
          ),
          if (_failure != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(_failure!, style: AlmaType.meta),
            ),
          const SizedBox(height: 16),
          // **Кнопка продукта, а не своя.** Здесь стояла плоская золотая
          // заливка с чернильной подписью — та самая, которую дизайн-система
          // запрещает словом «никогда» (`gold_texture.dart`): читается она
          // пластиковой наклейкой, а не ключом от двери. `AlmaButton` берёт на
          // себя и текстуру, и высоту 56, и выключенное состояние — а `Opacity`
          // 0.5 поверх живого `InkWell` гасила кнопку, не отменяя нажатия.
          AlmaButton(
            // Пока сохраняем — так и сказано. Строка уже есть в семи языках,
            // и до сих пор ею никто не пользовался: кнопка просто тускнела.
            label: _saving ? l.scrAddPersonSaving : l.cabPeopleAdd,
            onTap: _chosen == null || _saving ? null : _save,
          ),
        ],
      ),
    );
  }

  /// Число называют барабаном на общем листе — тем же, каким его называют в W2.
  ///
  /// Здесь стоял `showModalBottomSheet` с единственной настройкой
  /// `backgroundColor: night700` и голым `ListView` из `ListTile`: плоская
  /// синяя плашка поверх неба и список цифр системным шрифтом. Ровно это на
  /// экране совместимости владелец назвал «просто синим экраном». Рама
  /// (`design/night_sheet.dart`) и барабан (`design/wheel.dart`) теперь общие,
  /// и своих чисел — ни высоты, ни цвета, ни радиуса — этот экран не держит.
  ///
  /// **Что не изменилось — когда значение считается названным.** Список отдавал
  /// число нажатием на строку; лист отдаёт его нажатием «Готово». Закрытый
  /// свайпом вниз или тапом по затемнению, он по-прежнему не меняет ничего:
  /// поворот барабана правит копию, а не поле экрана.
  Widget _number(String label, int value, int min, int max, ValueChanged<int> onPick) =>
      InkWell(
        onTap: () async {
          var picked = value;
          final done = await showAlmaSheet<bool>(
            context: context,
            // Заголовок листа — подпись самой пилюли: своих слов лист не
            // заводит, он называет то, по чему постучали. Поэтому и подпись
            // над барабаном погашена — иначе одно слово стояло бы дважды.
            title: label,
            builder: (context, refresh) => [
              AlmaWheel(
                label: label,
                showLabel: false,
                min: min,
                max: max,
                value: picked,
                // `refresh`, а не голое присваивание: `value` барабана читает
                // ещё и `Semantics`, и без перестройки голос называл бы то
                // число, на котором лист открылся, сколько его ни крути.
                onChanged: (v) => refresh(() => picked = v),
              ),
              const SizedBox(height: 18),
              // Единственное действие листа — золотое, как на W2: лист и есть
              // отдельная поверхность со своим единственным ключом.
              AlmaButton(
                label: L.of(context).scrDone,
                onTap: () => Navigator.of(context).pop(true),
              ),
            ],
          );
          if (done == true) onPick(picked);
        },
        child: Container(
          height: 54,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.4)),
            borderRadius: BorderRadius.circular(28),
          ),
          child: Text('$value', style: AlmaType.body),
        ),
      );
}
