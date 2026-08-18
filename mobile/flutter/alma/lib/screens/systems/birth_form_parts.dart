import 'package:flutter/material.dart';

import '../../design/palette.dart';
import '../../design/typography.dart';
import '../../net/models.dart';
import '../../state/session.dart';

/// Общие части формы «второй человек», живущие в двух местах сразу.
///
/// До W2 форма партнёра существовала в одном экземпляре — `people_screen.dart`.
/// Кадр W2 («ввод прямо в самой совместимости») повторяет её по смыслу, но не
/// по вёрстке, и скопировать значило бы завести вторую копию поведения,
/// которая молча разойдётся с первой: у сохранения здесь есть три невидимых
/// глазу правила (язык отказа, `isSelf: false`, перечитанная сессия), и каждое
/// уже было багом, прежде чем стать комментарием.

/// Сохранить второго человека — и не перепутать его с владельцем аккаунта.
///
/// **`isSelf: false` — ключевое слово всей формы**: `true` здесь стирает
/// собственную карту читателя вместе с главами. `locale` — язык *отказа*:
/// единственная фраза этой ручки для читателя — 402 `partner_limit`, и без
/// языка первому гостю отказывали по-английски посреди русского экрана.
/// После сохранения сессия перечитывается принудительно: новый человек обязан
/// появиться в `session.people` до того, как экран решит, куда вести дальше, —
/// иначе глава пары откроется против списка, в котором партнёра ещё нет.
Future<Profile> savePartner(
  AlmaSession session, {
  required String birthDate,
  required String? birthTime,
  required Place place,
  String? name,
}) async {
  final saved = await session.client.saveProfile(
    BirthInput(
      birthDate: birthDate,
      birthTime: birthTime,
      latitude: place.latitude,
      longitude: place.longitude,
      timezone: place.timezone,
      placeLabel: place.label,
      placeId: place.id,
      name: name == null || name.trim().isEmpty ? null : name.trim(),
    ),
    locale: session.locale,
    isSelf: false,
  );
  await session.start(force: true);
  // §7 ТЗ: «≥25% купивших натал добавляют партнёра» — числитель этой цифры.
  // Шлётся после удавшегося сохранения, а не по нажатию кнопки: партнёр,
  // которого сервер отверг, не добавлен.
  session.client.track(FunnelStage.partnerAdded);
  return saved;
}

/// Находки города всплывающей панелью — как в макете (s11): ночная плашка с
/// золотым кантом и тенью, строки через волосяную линию.
///
/// Голым списком под полем они читались продолжением формы, а не ответом на
/// набранное. Первая находка светлее остальных — это подсказка, а не
/// предвыбор: нажать всё равно нужно.
class PlaceSuggestions extends StatelessWidget {
  const PlaceSuggestions({super.key, required this.found, required this.onPick});

  final List<Place> found;
  final ValueChanged<Place> onPick;

  @override
  Widget build(BuildContext context) {
    if (found.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.only(top: 6),
      decoration: BoxDecoration(
        color: AlmaPalette.night700,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.35)),
        boxShadow: const [
          BoxShadow(
              color: Color(0x8C000000), blurRadius: 34, offset: Offset(0, 14)),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          for (final (i, place) in found.indexed)
            GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () => onPick(place),
              child: Container(
                width: double.infinity,
                padding:
                    const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                decoration: BoxDecoration(
                  border: i == found.length - 1
                      ? null
                      : Border(
                          bottom: BorderSide(
                              color: AlmaPalette.body.withValues(alpha: 0.08))),
                ),
                child: Text(
                  place.label,
                  style: AlmaType.body.copyWith(
                    fontSize: 15,
                    color: i == 0
                        ? AlmaPalette.goldBright
                        : AlmaPalette.body.withValues(alpha: 0.85),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
