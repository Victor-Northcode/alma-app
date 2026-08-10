import 'package:flutter/material.dart';

import '../../design/palette.dart';
import '../../design/screen_scaffold.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/session.dart';
import '../cabinet_words.dart';
import 'natal_wheel.dart';

/// Одна система: её оглавление, дверь и бесплатные расчёты.
///
/// Порт `mobile/ios/Alma/Screens/Systems/SystemScreen.swift`, пока без колеса
/// натальной карты и рисунков систем — они приедут отдельным заходом, это
/// самостоятельные полотна. Оглавление здесь главное: это дорога к главе.
class SystemScreen extends StatefulWidget {
  const SystemScreen({super.key, required this.system, required this.onOpenChapter});

  final SystemSlug system;
  final void Function(SystemSlug system, String chapter) onOpenChapter;

  @override
  State<SystemScreen> createState() => _SystemScreenState();
}

class _SystemScreenState extends State<SystemScreen> {
  ChapterList? _chapters;
  CalcResult? _result;
  AlmaError? _failure;
  bool _loading = true;

  bool _started = false;

  // Не initState: `SessionScope.of` зависит от наследуемого виджета, а
  // зависеть от него в initState нельзя — исключение уходит в невозвращённое
  // будущее, и экран молча стоит на «Секунду» вечно. Найдено в браузере:
  // запрос глав просто не уходил в сеть.
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_started) {
      _started = true;
      _load();
    }
  }

  Future<void> _load() async {
    final session = SessionScope.of(context);
    setState(() {
      _loading = true;
      _failure = null;
    });
    try {
      // Расчёт и оглавление одновременно: рисунок системы и её главы — две
      // независимые вещи, и ждать их по очереди значит удвоить пустой экран.
      final both = await Future.wait([
        session.client.chapters(widget.system, locale: session.locale),
        session.client.compute(widget.system),
      ]);
      if (mounted) {
        setState(() {
          _chapters = both[0] as ChapterList;
          _result = both[1] as CalcResult;
        });
      }
    } on AlmaError catch (error) {
      if (mounted) setState(() => _failure = error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return ScreenScaffold(
      seed: 0x53595300 + widget.system.index,
      title: CabinetWordsMore.system(l, widget.system),
      onRefresh: _load,
      children: [
        // Рисунок системы, чертящий себя. Натальная и соляр — настоящее
        // колесо; у остальных свои полотна, они приедут следующими.
        if (_wheelData case final chart?)
          Padding(
            padding: const EdgeInsets.only(top: 6, bottom: 10),
            child: NatalWheel(data: chart),
          ),
        const SizedBox(height: 10),
        _section(
          l.cabChapters,
          trailing: _chapters?.total.toString(),
          children: [
            if (_loading)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 40),
                child: Center(
                    child: Text(l.stateLoadingShort, style: AlmaType.meta)),
              )
            else if (_failure != null)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 24),
                child: Text(
                  _failure is ServerRefused &&
                          (_failure! as ServerRefused).message.isNotEmpty
                      ? (_failure! as ServerRefused).message
                      : l.stateUnavailable,
                  style: AlmaType.meta,
                ),
              )
            else if (_chapters != null)
              for (final entry in _chapters!.chapters) _row(l, entry),
          ],
        ),
      ],
    );
  }

  /// Данные для колеса. Натальная карта — она сама; соляр — карта возвращения:
  /// то же колесо, небо этого года.
  Map<String, dynamic>? get _wheelData {
    final data = _result?.data;
    if (data == null) return null;
    if (widget.system == SystemSlug.natal) return data;
    if (widget.system == SystemSlug.solarReturn) {
      final chart = data['chart'];
      return chart is Map ? chart.cast<String, dynamic>() : null;
    }
    return null;
  }

  Widget _section(String label, {String? trailing, required List<Widget> children}) {
    return Column(
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
          if (trailing != null) ...[
            const SizedBox(width: 12),
            Text(trailing, style: AlmaType.numeral),
          ],
        ]),
        ...children,
      ],
    );
  }

  /// Одна глава: римская цифра засечным, заголовок, вопрос — и ничего про
  /// замок. Закрытая глава честно скажет это внутри, показав заголовок, вопрос
  /// и дверь; прятать её из списка значило бы прятать сам продукт.
  Widget _row(L l, ChapterEntry entry) {
    return InkWell(
      onTap: () => widget.onOpenChapter(widget.system, entry.slug),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          border: Border(bottom: BorderSide(color: AlmaPalette.hairline)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 44,
              child: Padding(
                padding: const EdgeInsets.only(top: 3),
                child: Text(entry.numeral, style: AlmaType.numeral),
              ),
            ),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(entry.title, style: AlmaType.headingM),
                  if (entry.question.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(entry.question, style: AlmaType.meta),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
