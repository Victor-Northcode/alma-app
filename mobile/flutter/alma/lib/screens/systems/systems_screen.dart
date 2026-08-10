import 'package:flutter/material.dart';

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
        if (rows.isNotEmpty) _section(title, [for (final e in rows) _row(l, e)]),
      if (pending.isNotEmpty)
        _section(l.cabStatusNotYet, [for (final e in pending) _row(l, e)]),
    ];
  }

  List<HubEntry> _of(List<HubEntry> entries, List<SystemSlug> slugs) => entries
      .where((e) => slugs.contains(e.slug) && CabinetWordsMore.isReady(e.status))
      .toList();

  List<Widget> _synthesis(L l, Hub hub) {
    final entry = hub.systems.where((e) => e.slug == SystemSlug.synthesis).toList();
    final status = entry.isEmpty ? 'not-yet' : entry.first.status;
    return [
      _section(l.cabGroupAllOfIt, [
        _row(l, HubEntry(slug: SystemSlug.synthesis, unlocked: entry.isNotEmpty && entry.first.unlocked, status: status)),
      ]),
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

  Widget _row(L l, HubEntry entry) {
    return InkWell(
      onTap: () => widget.onOpenSystem(entry.slug),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 18),
        decoration: BoxDecoration(
          border: Border(bottom: BorderSide(color: AlmaPalette.hairline)),
        ),
        child: Row(children: [
          Expanded(
            child: Text(CabinetWordsMore.system(l, entry.slug), style: AlmaType.headingM),
          ),
          Text(
            CabinetWordsMore.status(l, entry.status),
            style: AlmaType.meta.copyWith(color: AlmaPalette.gold),
          ),
        ]),
      ),
    );
  }
}
