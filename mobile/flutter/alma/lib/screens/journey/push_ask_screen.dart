import 'package:flutter/material.dart';

import '../../design/arrival.dart';
import '../../design/buttons.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/sky/night_sky.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../notify/push_devices.dart';
import '../../state/session.dart';

/// Пред-вопрос про уведомления — `s39`, «Push pre-ask — before the system
/// dialog».
///
/// **Зачем нужен отдельный экран перед системным окном.** iOS даёт на просьбу о
/// разрешении ровно одну попытку за установку: человек, нажавший «Не разрешать»,
/// вернуть окно из приложения уже не может — только через «Настройки», куда он
/// не пойдёт. Значит системный диалог нельзя показывать вслепую, посреди
/// прихода, когда человек ещё не понимает, о чём его спрашивают. Этот экран
/// покупает попытке контекст: он говорит, **что именно** придёт (одно
/// уведомление в день, когда в карте что-то точно), **как часто** (примерно раз
/// в неделю), **когда не придёт** (ночью — никогда) и **как выключить**. Тот,
/// кто после этого нажимает «Yes, tell me», нажимает «Разрешить» и в системном
/// окне; тот, кто выбирает «Not now», уходит, не потратив единственную попытку,
/// — и его можно спросить снова.
///
/// **Дальше — системное окно и токен.** Нажатие на «Yes, tell me» зовёт
/// [AlmaPush.ask]: разрешение у системы, токен устройства у APNs, устройство на
/// сервер. Порядок именно такой и переставить его нельзя — вся причина
/// существования этого экрана в том, что наш вопрос повторяемый, а системный
/// нет.
class PushAskScreen extends StatefulWidget {
  const PushAskScreen({super.key});

  @override
  State<PushAskScreen> createState() => _PushAskScreenState();
}

class _PushAskScreenState extends State<PushAskScreen> {
  /// Идёт разговор с системой. Кнопка на это время гаснет: второе нажатие
  /// показало бы второе системное окно поверх первого.
  bool _asking = false;

  /// Согласие получено — теперь его надо потратить.
  ///
  /// **Экран закрывается при любом ответе, и это не безразличие.** Guideline
  /// 5.1.2(i) требует, чтобы отказ ничего не менял в продукте: «Сегодня»
  /// покажет то же чтение, а уведомление было указателем на него. Сообщение об
  /// отказе посреди прихода было бы уговариванием, которого §5.5 прямо просит
  /// не устраивать; своё место у этой строки есть — «Каждое утро» в настройках,
  /// и там же лежит `daily.status.denied`.
  Future<void> _yes() async {
    if (_asking) return;
    setState(() => _asking = true);
    // Клиент берётся до `await`: после него `context` может уже не
    // принадлежать дереву.
    final client = SessionScope.of(context).client;
    final navigator = Navigator.of(context);
    try {
      await AlmaPush.instance.ask(client);
    } finally {
      if (mounted) {
        setState(() => _asking = false);
        navigator.maybePop();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Scaffold(
      backgroundColor: AlmaPalette.night,
      body: NightSky(
        // Хвост путешествия — всё ещё путешествие: небо здесь содержание, а не
        // фон под текстом.
        mood: SkyMood.ceremony,
        seed: 0x50555348,
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(
                AlmaMetrics.pad, 44, AlmaMetrics.pad, 24),
            child: Column(children: [
              const Spacer(),
              // Луна, а не знак Alma: разговор идёт про утро, в которое что-то
              // сойдётся на небе, и медальон луны — то же обещание, что стоит
              // на «Сегодня».
              const Breathing(child: _Moon(size: 68)),
              const SizedBox(height: 26),
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 300),
                child: Text(
                  l.dailyAskTitle,
                  textAlign: TextAlign.center,
                  style: AlmaType.displayL.copyWith(fontSize: 27, height: 1.15),
                ),
              ),
              const SizedBox(height: 14),
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 310),
                child: Text(
                  l.dailyAskBody,
                  textAlign: TextAlign.center,
                  style: AlmaType.meta.copyWith(height: 1.55),
                ),
              ),
              const Spacer(),
              AlmaButton(label: l.dailyAskYes, onTap: _asking ? null : _yes),
              const SizedBox(height: 12),
              // «Не сейчас» слышно, и это существенно: тихий отказ здесь стоит
              // дешевле, чем «Не разрешать» в системном окне, — второе
              // необратимо, первое нет. Системного окна этот путь **не
              // показывает вовсе**: единственная попытка остаётся неистраченной,
              // и спросить снова можно будет из настроек.
              GestureDetector(
                onTap: _asking ? null : () => Navigator.of(context).maybePop(),
                behavior: HitTestBehavior.opaque,
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(vertical: 12, horizontal: 20),
                  child: Text(
                    l.paywallNotNow,
                    style: AlmaType.button.copyWith(
                      fontSize: 15,
                      color: AlmaPalette.body.withValues(alpha: 0.85),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ]),
          ),
        ),
      ),
    );
  }
}

/// Медальон луны эталона: кольцо, ночная сторона, свет поверх неё.
///
/// Числа `s39`: поле 68, кольцо волосом `rgba(201,174,107,.35)` с отступом 2,
/// диск 40 в середине, ночная сторона `rgba(16,22,54,.9)` с обводкой 0.7
/// `rgba(201,174,107,.3)`, свет `rgba(246,231,188,.92)`, срезанный эллипсом
/// `74% 100% at 74% 50%`.
///
/// **Свет ложится поверх ночной стороны, а не наоборот** — то же правило, что у
/// медальона на «Сегодня»: рисуя тень поверх света, в новолуние получаешь
/// чёрный кружок без края вместо тёмного диска в золотой обводке.
class _Moon extends StatelessWidget {
  const _Moon({required this.size});

  final double size;

  @override
  Widget build(BuildContext context) => CustomPaint(
        size: Size.square(size),
        painter: const _MoonPainter(),
      );
}

class _MoonPainter extends CustomPainter {
  const _MoonPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final k = size.width / 68;
    final centre = Offset(34 * k, 34 * k);

    canvas.drawCircle(
      centre,
      32 * k,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = AlmaPalette.gold.withValues(alpha: 0.35),
    );

    final disc = 20 * k;
    canvas.drawCircle(
      centre,
      disc,
      Paint()..color = AlmaPalette.night700.withValues(alpha: 0.9),
    );
    canvas.drawCircle(
      centre,
      disc,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 0.7
        ..color = AlmaPalette.gold.withValues(alpha: 0.3),
    );

    canvas.save();
    // Эллипс отсчитывается от квадрата диска 40×40, как в эталоне: центр на
    // 74% ширины, полуоси 74% ширины и 100% высоты.
    final box = Rect.fromCircle(center: centre, radius: disc);
    canvas.clipPath(Path()
      ..addOval(Rect.fromCenter(
        center: Offset(box.left + box.width * 0.74, centre.dy),
        width: box.width * 1.48,
        height: box.height * 2,
      )));
    canvas.drawCircle(
      centre,
      disc,
      Paint()..color = AlmaPalette.starFill.withValues(alpha: 0.92),
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(_MoonPainter oldDelegate) => false;
}
