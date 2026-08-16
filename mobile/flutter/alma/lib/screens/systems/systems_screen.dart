import 'package:flutter/material.dart';

import '../../design/art.dart';
import '../../design/palette.dart';
import '../../design/screen_scaffold.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/models.dart';
import '../../state/session.dart';
import '../cabinet_words.dart';

/// Хаб: восемь систем, сгруппированные по вопросу человека, а не по имени
/// традиции.
///
/// Порт `mobile/ios/Alma/Screens/Systems/SystemsScreen.swift`. Наверху — три
/// строки собственных позиций (Солнце, Луна, Асцендент), причём с градусами:
/// градусы — та часть, которая доказывает, что это настоящий расчёт, а не знак
/// Солнца. Ниже — группы «Кто я», «Прямо сейчас», «В этом году», «Мы вдвоём»,
/// «Где быть», и отдельным блоком — синтез.
class SystemsScreen extends StatefulWidget {
  const SystemsScreen({super.key, required this.onOpenSystem});

  final void Function(SystemSlug slug) onOpenSystem;

  @override
  State<SystemsScreen> createState() => _SystemsScreenState();
}

class _SystemsScreenState extends State<SystemsScreen> {
  CalcResult? _portrait;
  String? _loadedForProfile;

  @override
  Widget build(BuildContext context) {
    final session = SessionScope.of(context);
    final l = L.of(context);
    final hub = session.hub;

    final profileId = session.profile?.id;
    if (profileId != null && profileId != _loadedForProfile) {
      _loadedForProfile = profileId;
      session.client.compute(SystemSlug.natal).then((result) {
        if (mounted) setState(() => _portrait = result);
      }).catchError((Object _) {
        // Пиллы — украшение хаба, не его условие: без них экран полон.
      });
    }

    return ScreenScaffold(
      seed: 0x53595354,
      title: l.tabSystems,
      trailing: _tally(l, hub),
      children: [
        ..._pills(l),
        if (hub != null) ...[
          const SizedBox(height: 10),
          ..._groups(l, hub),
          ..._synthesis(l, hub),
        ],
      ],
    );
  }

  /// «7/8 рассчитано» — рядом с заголовком, засечным, как на iOS. Слово
  /// счётчика своё, не слово строки: в четырёх языках им нужны разные числа́ —
  /// calculés против calculé, — и одна строка на обе роли уже была ошибкой.
  Widget? _tally(L l, Hub? hub) {
    if (hub == null) return null;
    final ready = hub.systems.where((e) => CabinetWordsMore.isReady(e.status)).length;
    return Padding(
      padding: const EdgeInsets.only(top: 18),
      child: Text(
        '$ready/${hub.systems.length} ${l.cabCalculatedWord}',
        style: AlmaType.numeral,
      ),
    );
  }

  /// Солнце, Луна, Асцендент — с градусами и домом. Асцендент существует
  /// только вместе со временем рождения; запасного варианта нет: у карты без
  /// горизонта нет восходящего градуса, и строка уходит, а не показывает знак,
  /// который был бы в полдень.
  List<Widget> _pills(L l) {
    final chart = _portrait?.data;
    if (chart == null) return const [];

    (String, String)? placement(String body, String fallbackSign) {
      final label = CabinetWords.body(l, body);
      final placements = chart['placements'];
      if (placements is Map) {
        final own = placements[body];
        if (own is Map) {
          final formatted = own['formatted'];
          if (formatted is String) {
            final houseNumber = (own['house'] as num?)?.toInt();
            final house = houseNumber == null
                ? ''
                : ' · ${CabinetWordsMore.house(l, houseNumber)}';
            return (label, CabinetWordsMore.spellSigns(l, formatted) + house);
          }
        }
      }
      final sign = chart[fallbackSign];
      if (sign is String) return (label, CabinetWordsMore.sign(l, sign));
      return null;
    }

    final rows = <(String, String)>[
      ?placement('sun', 'sun_sign'),
      ?placement('moon', 'moon_sign'),
    ];
    final angles = chart['angles'];
    if (angles is Map &&
        angles['formatted'] is Map &&
        (angles['formatted'] as Map)['ascendant'] is String) {
      rows.add((
        l.cabAscendant,
        CabinetWordsMore.spellSigns(
            l, (angles['formatted'] as Map)['ascendant'] as String),
      ));
    } else if (chart['rising_sign'] is String) {
      rows.add((l.cabAscendant, CabinetWordsMore.sign(l, chart['rising_sign'] as String)));
    }

    return [
      for (final row in rows)
        Container(
          padding: const EdgeInsets.symmetric(vertical: 14),
          decoration: BoxDecoration(
            border: Border(bottom: BorderSide(color: AlmaPalette.hairline)),
          ),
          child: Row(children: [
            Text(row.$1, style: AlmaType.meta),
            const Spacer(),
            Text(row.$2,
                style: AlmaType.numeral.copyWith(fontSize: 17), textAlign: TextAlign.end),
          ]),
        ),
    ];
  }

  /// Группы по вопросу. Готовые системы стоят под своими вопросами, неготовые
  /// собраны под «пока нет» — вместе с причиной в статусе каждой строки.
  List<Widget> _groups(L l, Hub hub) {
    final entries = hub.systems.where((e) => e.slug != SystemSlug.synthesis).toList();
    final pending = entries.where((e) => !CabinetWordsMore.isReady(e.status)).toList();

    final groups = <(String, List<HubEntry>)>[
      (l.cabGroupWhoAmI, _of(entries, const [SystemSlug.natal, SystemSlug.numerology, SystemSlug.birthCard])),
      (l.cabGroupRightNow, _of(entries, const [SystemSlug.transits])),
      (l.cabGroupThisYear, _of(entries, const [SystemSlug.solarReturn])),
      (l.cabGroupHowWeMatch, _of(entries, const [SystemSlug.compatibility])),
      (l.cabGroupWhereToBe, _of(entries, const [SystemSlug.astrocartography])),
    ];

    return [
      for (final (title, rows) in groups)
        if (rows.isNotEmpty) _section(title, _deck(l, rows)),
      if (pending.isNotEmpty) _section(l.cabStatusNotYet, _deck(l, pending)),
    ];
  }

  List<HubEntry> _of(List<HubEntry> entries, List<SystemSlug> slugs) => entries
      .where((e) => slugs.contains(e.slug) && CabinetWordsMore.isReady(e.status))
      .toList();

  List<Widget> _synthesis(L l, Hub hub) {
    final entry = hub.systems.where((e) => e.slug == SystemSlug.synthesis).toList();
    final status = entry.isEmpty ? 'not-yet' : entry.first.status;
    return [
      _section(l.cabGroupAllOfIt, _deck(l, [
        HubEntry(
            slug: SystemSlug.synthesis,
            unlocked: entry.isNotEmpty && entry.first.unlocked,
            status: status),
      ])),
    ];
  }

  Widget _section(String label, List<Widget> children) {
    return Padding(
      padding: const EdgeInsets.only(top: 26),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text(label.toUpperCase(), style: AlmaType.overline),
            const SizedBox(width: 12),
            Expanded(
              child: Container(
                height: 1,
                decoration: BoxDecoration(gradient: AlmaGradient.fadedRule),
              ),
            ),
          ]),
          ...children,
        ],
      ),
    );
  }

  /// Карточка системы: арт, золотой кант, имя понизу.
  ///
  /// **Строкой список быть перестал.** В эталоне (`s47`) восемь систем стоят
  /// карточками 172×156 по две в ряд, у каждой своя картина: в них и вся
  /// разница между «список пунктов меню» и «полка, с которой берут». Порт
  /// показывал строки с надписью «open» — арт лежал в пакете и не был виден
  /// нигде.
  ///
  /// Закрытая система отличается не замком, а тишиной: картина приглушена и
  /// вместо «открыть» стоит своё состояние. Замок на витрине читается запретом,
  /// а здесь всё рассчитано — закрыт только текст.
  Widget _card(L l, HubEntry entry) {
    final ready = CabinetWordsMore.isReady(entry.status);
    return GestureDetector(
      onTap: ready ? () => widget.onOpenSystem(entry.slug) : null,
      behavior: HitTestBehavior.opaque,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(13),
        child: AspectRatio(
          // 172×156 в эталоне — на телефоне это две карточки в ряд с полем 22
          // и зазором 12, то есть ровно та же пропорция.
          aspectRatio: 172 / 156,
          child: Stack(fit: StackFit.expand, children: [
            Opacity(
              opacity: ready ? 1 : 0.45,
              child: Image.asset(AlmaArt.card(entry.slug), fit: BoxFit.cover),
            ),
            DecoratedBox(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(13),
                border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.5)),
                // Имя стоит на своей земле: без затемнения книзу светлая
                // картина съедает подпись целиком.
                gradient: const LinearGradient(
                  begin: Alignment.center,
                  end: Alignment.bottomCenter,
                  colors: [Color(0x00070A16), Color(0xE6070A16)],
                ),
              ),
            ),
            Align(
              alignment: Alignment.bottomLeft,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(11, 0, 11, 9),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      CabinetWordsMore.system(l, entry.slug),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: AlmaType.headingM.copyWith(
                          fontSize: 16, color: AlmaPalette.starFill),
                    ),
                    if (!ready) ...[
                      const SizedBox(height: 2),
                      Text(CabinetWordsMore.status(l, entry.status),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: AlmaType.meta.copyWith(fontSize: 11.5)),
                    ],
                  ],
                ),
              ),
            ),
          ]),
        ),
      ),
    );
  }

  /// Ряд из двух карточек. `GridView` здесь не нужен: список короткий и живёт
  /// внутри чужой прокрутки, а вложенная сетка потребовала бы своей высоты.
  List<Widget> _deck(L l, List<HubEntry> entries) {
    final rows = <Widget>[];
    for (var i = 0; i < entries.length; i += 2) {
      rows.add(Padding(
        padding: const EdgeInsets.only(top: 12),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Expanded(child: _card(l, entries[i])),
          const SizedBox(width: 12),
          Expanded(
            child: i + 1 < entries.length
                ? _card(l, entries[i + 1])
                : const SizedBox.shrink(),
          ),
        ]),
      ));
    }
    return rows;
  }

}
