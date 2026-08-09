import 'package:flutter/material.dart';

import 'design/metrics.dart';
import 'design/palette.dart';
import 'design/sky/night_sky.dart';
import 'design/tab_bar.dart';
import 'l10n/alma_l10n.dart';

void main() => runApp(const AlmaApp());

/// Корень.
///
/// Порт `mobile/ios/Alma/AlmaApp.swift` и `Navigation/RootView.swift`. Пока
/// здесь только оболочка: небо, бар и четыре пустых места под экраны. Экраны
/// приезжают следующими, по одному, в том порядке, в каком их встречает
/// человек.
class AlmaApp extends StatelessWidget {
  const AlmaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Alma',
      debugShowCheckedModeBanner: false,
      localizationsDelegates: L.localizationsDelegates,
      supportedLocales: L.supportedLocales,
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        scaffoldBackgroundColor: AlmaPalette.night,
        // Продукт целиком на ночи. Единственная светлая поверхность — лист
        // главы — рисуется сама, а не темой.
        colorScheme: const ColorScheme.dark(
          surface: AlmaPalette.night,
          primary: AlmaPalette.gold,
          onPrimary: AlmaPalette.inkOnGold,
        ),
      ),
      home: const CabinetShell(),
    );
  }
}

/// Кабинет: четыре вкладки под одним небом.
class CabinetShell extends StatefulWidget {
  const CabinetShell({super.key});

  @override
  State<CabinetShell> createState() => _CabinetShellState();
}

class _CabinetShellState extends State<CabinetShell> {
  CabinetTab _tab = CabinetTab.today;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AlmaPalette.night,
      extendBody: true,
      body: NightSky(
        mood: SkyMood.cabinet,
        // Своё зерно у каждой вкладки, чтобы переход между ними был видимым
        // переходом, а не теми же звёздами дважды.
        seed: 0x414C4D41 + _tab.index * 7919,
        child: SafeArea(bottom: false, child: _Placeholder(tab: _tab)),
      ),
      bottomNavigationBar: CabinetTabBar(
        current: _tab,
        onSelect: (tab) => setState(() => _tab = tab),
      ),
    );
  }
}

/// Временное место экрана.
///
/// Живёт ровно до того коммита, в котором приезжает настоящий экран, и не
/// разрастается: это заглушка каркаса, а не «пока сойдёт». На Android такой
/// файл однажды пережил все экраны и остался в дереве мёртвым грузом —
/// повторять не будем.
class _Placeholder extends StatelessWidget {
  const _Placeholder({required this.tab});

  final CabinetTab tab;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AlmaMetrics.pad),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: AlmaMetrics.gapLarge),
          Text(
            tab.title(l),
            style: const TextStyle(
              fontSize: 34,
              height: 1.1,
              color: AlmaPalette.inkLight,
              fontWeight: FontWeight.w400,
            ),
          ),
        ],
      ),
    );
  }
}
