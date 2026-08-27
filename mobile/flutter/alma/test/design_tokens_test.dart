import 'package:alma/design/palette.dart';
import 'package:flutter_test/flutter_test.dart';

/// **Числа ночной продающей поверхности закреплены, а не пересказаны.**
///
/// Карточка оффера и лист покупки обязаны быть одной семьёй; пока их числа
/// жили в двух файлах, они уже разъехались незамеченными — комментарии
/// продолжали утверждать родство (ревью 27.08.2026). Теперь оба берут
/// `nightCardTop/Bottom/Edge` из палитры, а здесь стерегутся сами значения:
/// правка токена — осознанная правка обеих вещей, а не дрейф одной.
void main() {
  test('тона ночной карточки — те самые числа листа покупки', () {
    expect(AlmaPalette.nightCardTop.a, closeTo(0.88, 1e-9),
        reason: 'верх: ночь на 0.88');
    expect(AlmaPalette.nightCardTop.withValues(alpha: 1), AlmaPalette.night);
    expect(AlmaPalette.nightCardBottom.a, closeTo(0.97, 1e-9),
        reason: 'низ: глубокая ночь на 0.97');
    expect(AlmaPalette.nightCardBottom.withValues(alpha: 1),
        AlmaPalette.night900);
    expect(AlmaPalette.nightCardEdge.a, closeTo(0.30, 1e-9),
        reason: 'кант: золото на 0.30, число холста V2');
    expect(AlmaPalette.nightCardEdge.withValues(alpha: 1), AlmaPalette.gold);
    expect(AlmaGradient.nightCard.colors,
        [AlmaPalette.nightCardTop, AlmaPalette.nightCardBottom]);
  });
}
