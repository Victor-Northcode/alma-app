import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/net/models.dart';
import 'package:alma/screens/alma/chat_turn.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Четыре вида реплики — и порт рисует все четыре.
///
/// Порт `ChatTurnKindTest.kt` и превью «turn kinds» из `ChatPieces.swift`:
/// случаи те же, потому что беда была не в вёрстке. Реплика несла один булев
/// `answered_from_chart`, а он отвечал сразу на два вопроса — «карта об этом
/// молчит» и «я вообще ничего о тебе не утверждаю», — и приветствие получало
/// пометку «не из твоей карты». Порт же не читал `turn_kind` вовсе: тихого
/// ответа `care` и честной приписки молчащей карты в нём не существовало.
void main() {
  group('разбор', () {
    test('приветствие, названное сервером, не подписывается ничем', () {
      const kind = ChatTurnKind.conversation;
      expect(ChatTurnKind.of('conversation', citedFactors: const []), kind);
      expect(kind.showsChartSilentNote, isFalse);
      expect(kind.showsCitations, isFalse);
    });

    test('ответ без цитат и без поля — беседа, а не молчащая карта', () {
      // Тот самый кадр из отчёта: `turn_kind` нет, цитат нет. Кандидатов два —
      // «она поздоровалась», где подпись ложь, и «карта молчит», где подпись
      // повтор её же слов. Запасной путь берёт повтор.
      final kind = ChatTurnKind.of(null, citedFactors: const []);
      expect(kind, ChatTurnKind.conversation);
      expect(kind.showsChartSilentNote, isFalse);
    });

    test('цитаты перевешивают отсутствие поля', () {
      final kind = ChatTurnKind.of(null,
          citedFactors: const ['moon 28°36′ ♒︎ · house 7', 'mercury in Virgo']);
      expect(kind, ChatTurnKind.reading);
      expect(kind.showsCitations, isTrue);
      expect(kind.showsChartSilentNote, isFalse);
    });

    test('молчащая карта — единственный вид с припиской', () {
      final kind = ChatTurnKind.of('chart_silent', citedFactors: const []);
      expect(kind, ChatTurnKind.chartSilent);
      expect(kind.showsChartSilentNote, isTrue);
    });

    test('забота приписки не получает, а названное — показывает', () {
      final kind = ChatTurnKind.of('care', citedFactors: const ['moon in Virgo']);
      expect(kind, ChatTurnKind.care);
      expect(kind.showsCitations, isTrue);
      expect(kind.showsChartSilentNote, isFalse);
    });

    test('беседа не украшает то, что случайно процитировала', () {
      final kind = ChatTurnKind.of('conversation', citedFactors: const ['life path 7']);
      expect(kind.showsCitations, isFalse);
    });

    test('незнакомый вид вырождается в обычную реплику, а не в сбой', () {
      // Сервер свежее сборки. Ветка таксономии, о которой эта сборка не знает,
      // обязана нарисоваться, а не оборвать чужой разговор.
      expect(ChatTurnKind.of('elegy', citedFactors: const ['sun in Pisces']),
          ChatTurnKind.reading);
      expect(ChatTurnKind.of('elegy', citedFactors: const []),
          ChatTurnKind.conversation);
    });

    test('вид приезжает и в живом ответе, и в перечитанной беседе', () {
      // Формы сняты с сервера: `/v1/chat` кладёт вид в `message`, а
      // `/v1/chat/threads/{id}` — в каждую строку `messages` (`readings.py`).
      final reply = ChatReply.fromJson(const {
        'thread_id': 'th1',
        'message': {
          'id': 'm1',
          'role': 'alma',
          'body': 'Ничто в твоей карте про это не говорит.',
          'cited_factors': <String>[],
          'turn_kind': 'chart_silent',
        },
      });
      expect(reply.kind, ChatTurnKind.chartSilent);

      final turn = ChatTurn.fromJson(const {
        'id': 'm1',
        'role': 'alma',
        'body': 'Ничто в твоей карте про это не говорит.',
        'cited_factors': <String>[],
        'turn_kind': 'chart_silent',
      });
      expect(turn.kind, ChatTurnKind.chartSilent,
          reason: 'иначе то же сообщение после перезапуска рисуется иначе');

      // Строка беседы, написанная до появления колонки: `turn_kind` там null.
      final old = ChatTurn.fromJson(const {
        'id': 'm0',
        'role': 'alma',
        'body': '…',
        'cited_factors': ['sun in Pisces'],
        'turn_kind': null,
      });
      expect(old.kind, ChatTurnKind.reading);
    });
  });

  group('что из этого нарисовано', () {
    Widget host(ChatTurnKind kind, {List<String> cited = const []}) => MaterialApp(
          locale: const Locale('en'),
          localizationsDelegates: L.localizationsDelegates,
          supportedLocales: L.supportedLocales,
          home: Scaffold(
            body: SingleChildScrollView(
              child: ChatTurnView(
                mine: false,
                body: 'Одна реплика.',
                citedFactors: cited,
                kind: kind,
              ),
            ),
          ),
        );

    // Свет Alma дышит вечно — `pumpAndSettle` не вернётся; кадры руками.
    Future<void> settle(WidgetTester tester) async {
      for (var i = 0; i < 8; i++) {
        await tester.pump(const Duration(milliseconds: 80));
      }
    }

    const silentLine =
        'I answered that one from what I know, not from your chart.';

    testWidgets('у молчащей карты стоит фраза, а не бирка прописными',
        (tester) async {
      await tester.pumpWidget(host(ChatTurnKind.chartSilent));
      await settle(tester);
      expect(find.text(silentLine), findsOneWidget);
    });

    testWidgets('заботливый ответ остаётся тихим', (tester) async {
      // Группа D таксономии: человеку, который только что написал, что ему
      // плохо, не выдают ни приписки, ни строки пометок сверх сказанного.
      await tester.pumpWidget(host(ChatTurnKind.care));
      await settle(tester);
      expect(find.text(silentLine), findsNothing);
      expect(find.text('READ FROM'), findsNothing);
    });

    testWidgets('беседа не показывает цитат, чтение — показывает',
        (tester) async {
      await tester.pumpWidget(
          host(ChatTurnKind.conversation, cited: const ['life path 7']));
      await settle(tester);
      expect(find.text('READ FROM'), findsNothing);

      await tester.pumpWidget(
          host(ChatTurnKind.reading, cited: const ['life path 7']));
      await settle(tester);
      expect(find.text('READ FROM'), findsOneWidget);
    });
  });
}
