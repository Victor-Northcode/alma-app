import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';

import '../../design/palette.dart';
import '../../design/close_button.dart';
import '../../design/screen_scaffold.dart';
import '../../design/sky/night_sky.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/session.dart';
import '../systems/chapter_screen.dart';
import 'chat_turn.dart';

/// Одна прошлая беседа, целиком.
///
/// Порт `mobile/ios/Alma/Screens/Alma/ThreadScreen.swift`. Открывается только
/// из меню «раньше» на вкладке Alma.
///
/// **Только для чтения, и это решение.** Композер живёт ровно на одном экране:
/// второе место, откуда можно отправить вопрос, — это второе место, где можно
/// потратить чужую квоту и перепутать идентификатор беседы.
///
/// Реплики рисует **та же** [ChatTurnView], что и живая лента. На нативе здесь
/// когда-то стояла своя копия, и она молча разошлась: одно и то же сообщение
/// показывало «ответила не из карты» в живом чате и не показывало в
/// переоткрытой беседе.
class ThreadScreen extends StatefulWidget {
  const ThreadScreen({super.key, required this.id, this.title});

  final String id;
  final String? title;

  @override
  State<ThreadScreen> createState() => _ThreadScreenState();
}

class _ThreadScreenState extends State<ThreadScreen> {
  List<ChatTurn>? _turns;
  AlmaError? _failure;
  bool _started = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    _load();
  }

  Future<void> _load() async {
    setState(() => _failure = null);
    try {
      final turns = await SessionScope.of(context).client.thread(widget.id);
      if (mounted) setState(() => _turns = turns);
    } on AlmaError catch (error) {
      if (mounted) setState(() => _failure = error);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final turns = _turns;
    return Scaffold(
      backgroundColor: AlmaPalette.night,
      body: Stack(children: [
        ScreenScaffold(
        eyebrow: l.tabAlma,
        mood: SkyMood.reading,
        seed: 0x54485244,
        children: [
          Text(widget.title?.isNotEmpty == true ? widget.title! : l.scrChatUntitled,
              style: AlmaType.displayL),
          const SizedBox(height: 8),
          if (_failure != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 20),
              child: Text(l.stateUnavailable, style: AlmaType.meta),
            )
          else if (turns == null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 20),
              child: Text(l.stateLoadingShort, style: AlmaType.meta),
            )
          else
            // **Расстояние между репликами принадлежит реплике, а не экрану.**
            //
            // Здесь поверх [ChatTurnView] лежал ещё `gapLarge` снизу, и та же
            // переписка в архиве шла с шагом 42–48 точек вместо 14–20 живой
            // ленты (s7): разговор, разложенный вдвое реже, читается не тем же
            // разговором. Виджет один — пусть и ритм будет один.
            for (final turn in turns)
              ChatTurnView(
                mine: turn.mine,
                body: turn.body,
                citedFactors: turn.citedFactors,
                // Вид реплики приезжает и в сохранённой беседе — сервер отдаёт
                // `turn_kind` и здесь. Не передать его тут значило бы вернуть
                // ровно то расхождение, ради снятия которого вью общая: одно и
                // то же сообщение с тихой строкой в живой ленте и без неё после
                // перезапуска.
                kind: turn.kind,
                // И глава-источник — по тому же правилу и ровно по той же
                // причине. Сервер хранит её в сообщении; не прочитать её здесь
                // значило бы оставить в архиве ответ, который словами
                // ссылается на главу, и дверь в неё только в живой ленте.
                sourceChapter: turn.sourceChapter,
                onOpenSource: _open,
              ),
        ],
        ),
        // У экрана прошлой беседы выхода не было ВОВСЕ — только системный
        // свайп. Единый крестик справа (правило 24 авг, см. AlmaClose), поверх
        // прокрутки и в безопасной зоне.
        Positioned(
          right: 8,
          top: MediaQuery.paddingOf(context).top + 4,
          child: AlmaClose(onTap: () => Navigator.of(context).maybePop()),
        ),
      ]),
    );
  }

  /// Открыть главу-источник — тем же маршрутом, что и живая лента.
  ///
  /// Копия из `AlmaScreen._openSourceChapter`, и копия намеренная: экран
  /// прошлой беседы открыт из корневого навигатора, стек вкладки систем отсюда
  /// так же недостижим, а заводить общий вход в него ради одной карточки
  /// значило бы связать две вкладки навсегда.
  void _open(SourceChapter source) {
    final system = SystemSlug.from(source.system);
    // Система с сервера свежее сборки: вести некуда, и молчание честнее экрана
    // с ошибкой под карточкой, которая выглядит как приглашение.
    if (system == null) return;
    Navigator.of(context, rootNavigator: true).push(CupertinoPageRoute(
      builder: (context) => ChapterScreen(system: system, chapter: source.slug),
    ));
  }
}
