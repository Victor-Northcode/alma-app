import 'package:flutter/material.dart';

import '../../billing/alma_store.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/sky/night_sky.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/models.dart';
import '../../state/session.dart';

/// W6 · карточка 2: оплаченная проверка пары, у которой нет человека.
///
/// Появляется в единственном честном случае: `pair.check` оплачен, магазинный
/// пейлоад пришёл без токена намерения, и локальной памяти о том, про кого
/// открывали покупку, тоже нет — платёж доехал с прошлого запуска. Сервер
/// записал деньги (`unbound`), долг закрывается одним выбором.
///
/// **Ни одного «извините» и ни слова о пропаже** — правило кадра W6. Оба
/// предложения подписи начинаются с того, что деньги на месте: заголовок
/// спрашивает, подпись объясняет, список отвечает.
///
/// **Выбор применяется по тапу, без второй кнопки.** Холст второй шаг не
/// нарисовал, и здесь он был бы вторым вопросом к человеку, который уже
/// ответил магазину деньгами. Ошибка выбора не фатальна и не молчалива:
/// сервер держит привязку однократной, а список — это свои же люди.
///
/// Язык вариантов — тот же, что у квиза V0: выбранное — золотой кант,
/// остальное — волосяной. Способ «выбрать одно из» в продукте один.
class PairBindScreen extends StatefulWidget {
  const PairBindScreen({super.key});

  @override
  State<PairBindScreen> createState() => _PairBindScreenState();
}

class _PairBindScreenState extends State<PairBindScreen> {
  bool _binding = false;

  Future<void> _pick(Profile person) async {
    if (_binding) return;
    setState(() => _binding = true);
    final done = await AlmaStore.shared.bindUnbound(person.id);
    if (!mounted) return;
    if (done) {
      Navigator.of(context).pop(person);
    } else {
      setState(() => _binding = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final session = SessionScope.of(context);
    // Свои люди, кроме самого читателя: совместимость с собой — не товар.
    final people =
        session.people.where((person) => !person.isSelf).toList();
    return Scaffold(
      backgroundColor: AlmaPalette.night,
      body: NightSky(
        seed: 0x57365542,
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: AlmaMetrics.pad),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 48),
                Text(l.stateUnboundTitle,
                    style: AlmaType.displayL.copyWith(height: 1.2)),
                const SizedBox(height: 10),
                Text(l.stateUnboundNote,
                    style: AlmaType.meta.copyWith(height: 1.5)),
                const SizedBox(height: 26),
                Expanded(
                  child: ListView(
                    children: [
                      for (final person in people)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: _PersonRow(
                            person: person,
                            muted: _binding,
                            onTap: () => _pick(person),
                          ),
                        ),
                      // Партнёров ноль — покупка пришла раньше, чем заведён
                      // человек. Дорога та же, что у пустой совместимости:
                      // добавить человека, вернуться сюда — список оживёт,
                      // потому что экран строится от session.people.
                      if (people.isEmpty)
                        Padding(
                          padding: const EdgeInsets.only(top: 12),
                          child: Text(
                            l.pairInputNote,
                            style: AlmaType.meta.copyWith(height: 1.5),
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Строка человека — язык вариантов V0: волосяной кант, радиус 12.
class _PersonRow extends StatelessWidget {
  const _PersonRow({
    required this.person,
    required this.onTap,
    this.muted = false,
  });

  final Profile person;
  final VoidCallback onTap;
  final bool muted;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final name = (person.name?.isNotEmpty ?? false)
        ? person.name!
        : l.scrPeopleUnnamed;
    return Opacity(
      opacity: muted ? 0.55 : 1,
      child: GestureDetector(
        onTap: muted ? null : onTap,
        behavior: HitTestBehavior.opaque,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
                color: AlmaPalette.body.withValues(alpha: 0.12)),
          ),
          child: Row(children: [
            Expanded(
              child: Text(
                name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: AlmaType.body.copyWith(
                    fontSize: 16, color: AlmaPalette.body),
              ),
            ),
            Icon(Icons.arrow_forward_rounded,
                size: 16,
                color: AlmaPalette.gold.withValues(alpha: 0.8)),
          ]),
        ),
      ),
    );
  }
}
