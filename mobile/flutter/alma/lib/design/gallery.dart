import 'package:flutter/material.dart';

import '../net/models.dart' show SystemSlug;
import 'art.dart';
import 'buttons.dart';
import 'emblem.dart';
import 'layout.dart';
import 'metrics.dart';
import 'palette.dart';
import 'plates.dart';
import 'screen_scaffold.dart';
import 'section_label.dart';
import 'typography.dart';

/// Витрина базовых виджетов — то, с чем сверяют эталон.
///
/// **Нужна потому, что базовый виджет негде увидеть.** Кнопка живёт на витрине
/// покупки, поле — в анкете, арка — внутри платной главы: чтобы посмотреть на
/// все восемь разом, приходилось проходить приложение насквозь и в трёх местах
/// иметь подписку. Здесь они стоят рядом, в тех же размерах и на том же небе.
///
/// Открывается сборкой с `--dart-define=ALMA_GALLERY=1` и в обычную сборку не
/// попадает: экран не локализован и не должен, он не для читателя.
class DesignGallery extends StatefulWidget {
  const DesignGallery({super.key, this.plates});

  final PlateStore? plates;

  static bool get requested =>
      const String.fromEnvironment('ALMA_GALLERY') == '1';

  @override
  State<DesignGallery> createState() => _DesignGalleryState();
}

class _DesignGalleryState extends State<DesignGallery> {
  final _field = TextEditingController();
  final _filled = TextEditingController(text: 'Анна');

  @override
  void dispose() {
    _field.dispose();
    _filled.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AlmaLayout.of(context);
    // Витрина открывается вместо приложения и оболочки под собой не имеет.
    // Без `Material` Flutter рисует текст своим умолчанием — жёлтым с двойным
    // подчёркиванием; в приложении это скрыто оболочкой, здесь видно сразу.
    return Material(
      type: MaterialType.transparency,
      child: ScreenScaffold(
      eyebrow: 'design system',
      title: 'Базовые виджеты',
      children: [
        _Note('полоса ${l.band.name} · поле ${l.pad} · титул ${l.title} · '
            'бар ${l.tabBar} · рейл ${l.railWidth}'),

        const SectionLabel('Кнопки', trailing: '4'),
        const SizedBox(height: 14),
        AlmaButton(label: 'Unlock the Natal chart', onTap: () {}),
        const SizedBox(height: 12),
        AlmaButton(
          label: 'See the plans',
          kind: AlmaButtonKind.outline,
          onTap: () {},
        ),
        const SizedBox(height: 12),
        AlmaButton(
          label: 'Restore purchases',
          kind: AlmaButtonKind.veil,
          onTap: () {},
        ),
        const SizedBox(height: 12),
        AlmaButton(
          label: 'Delete account',
          kind: AlmaButtonKind.danger,
          fills: false,
          onTap: () {},
        ),
        const SizedBox(height: 12),
        const AlmaButton(label: 'Continue', onTap: null),

        const SizedBox(height: AlmaMetrics.gapSection),
        const SectionLabel('Поле'),
        const SizedBox(height: 14),
        CeremonialField(controller: _field, hint: 'What should I call you?'),
        const SizedBox(height: 12),
        CeremonialField(controller: _filled),

        const SizedBox(height: AlmaMetrics.gapSection),
        const SectionLabel('Знак'),
        const SizedBox(height: 8),
        // Знак с кольцами занимает вдвое больше своей стороны, поэтому три
        // размера рядом не помещаются в ширину телефона — ряд прокручивается.
        SizedBox(
          height: 240,
          child: ListView(
            scrollDirection: Axis.horizontal,
            children: const [
              Center(child: AlmaEmblem(size: 24, rings: false)),
              SizedBox(width: 20),
              Center(child: AlmaEmblem(size: 64)),
              SizedBox(width: 12),
              Center(child: AlmaEmblem(size: 110)),
            ],
          ),
        ),

        const SizedBox(height: AlmaMetrics.gapSection),
        const SectionLabel('Строка главы', trailing: 'III'),
        const SizedBox(height: 6),
        const _ChapterRow(
          numeral: 'I',
          title: 'Core',
          question: 'What am I really like underneath?',
        ),
        const _ChapterRow(
          numeral: 'II',
          title: 'Portrait',
          question: 'How do I come across before I speak?',
        ),

        const SizedBox(height: AlmaMetrics.gapSection),
        const SectionLabel('Арка-вклейка', trailing: '3'),
        const SizedBox(height: 14),
        Row(
          children: [
            PlateArch(
              store: widget.plates,
              plate: AlmaPlates.name(SystemSlug.natal, 'love'),
              numeral: 'III',
            ),
            const SizedBox(width: 14),
            // Глава без арта — так выглядят четыре дыры, пока их не нарисуют.
            const PlateArch(store: null, plate: null, numeral: 'II'),
          ],
        ),

        const SizedBox(height: AlmaMetrics.gapSection),
        const SectionLabel('Карты систем', trailing: '8'),
        const SizedBox(height: 14),
        SizedBox(
          height: 210,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: SystemSlug.values.length,
            separatorBuilder: (_, _) => const SizedBox(width: 12),
            itemBuilder: (context, i) => _Card(system: SystemSlug.values[i]),
          ),
        ),
        const SizedBox(height: AlmaMetrics.gapSection),
      ],
      ),
    );
  }
}

class _Note extends StatelessWidget {
  const _Note(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 24),
        child: Text(text,
            style: AlmaType.meta.copyWith(color: AlmaPalette.gold)),
      );
}

/// Строка главы: римская цифра в колонке 44, титул засечным, вопрос под ним.
class _ChapterRow extends StatelessWidget {
  const _ChapterRow({
    required this.numeral,
    required this.title,
    required this.question,
  });

  final String numeral;
  final String title;
  final String question;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 15),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: AlmaPalette.hairline)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: 44, child: Text(numeral, style: AlmaType.numeral)),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: AlmaType.headingM),
                const SizedBox(height: 3),
                Text(question, style: AlmaType.meta),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Card extends StatelessWidget {
  const _Card({required this.system});

  final SystemSlug system;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(13),
      child: SizedBox(
        width: 140,
        child: Stack(
          fit: StackFit.expand,
          children: [
            Image.asset(AlmaArt.card(system), fit: BoxFit.cover),
            DecoratedBox(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(13),
                border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.5)),
                gradient: const LinearGradient(
                  begin: Alignment.center,
                  end: Alignment.bottomCenter,
                  colors: [Color(0x00070A16), Color(0xD9070A16)],
                ),
              ),
            ),
            Align(
              alignment: Alignment.bottomLeft,
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: Text(
                  system.slug,
                  style: AlmaType.headingM
                      .copyWith(fontSize: 15, color: AlmaPalette.starFill),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
