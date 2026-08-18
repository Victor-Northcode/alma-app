import 'dart:convert';

import 'package:alma/net/alma_client.dart';
import 'package:alma/net/models.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Разбор стрима беседы — договор `/v1/chat/stream`, прочитанный клиентом.
///
/// Четыре обещания `askStream`, по тесту на каждое: стадии выходят в поток до
/// ответа и в порядке прихода; `done` разбирается ровно как ответ `/v1/chat`,
/// включая главу-источник; `error` внутри потока и HTTP-отказ до него — те же
/// [AlmaError], что у `ask`, чтобы экран обрабатывал оба пути одним `catch`;
/// оборванный без `done` поток — сеть, а не тихий успех, потому что «тихий
/// успех» здесь значил бы потерянный вопрос.
AlmaClient _client(String body,
    {int status = 200, String contentType = 'text/event-stream; charset=utf-8'}) {
  final transport = MockClient((request) async {
    expect(request.url.path, '/v1/chat/stream');
    expect(request.headers['Accept'], 'text/event-stream');
    return http.Response(body, status, headers: {'content-type': contentType});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    // Связка в пробирке: без неё первый же `read()` не отвечает никогда.
    FlutterSecureStorage.setMockInitialValues({});
  });

  test('стадии приходят до ответа, ответ несёт главу-источник', () async {
    final done = jsonEncode({
      'thread_id': 'th1',
      'message': {
        'body': 'Your sun lives in the fourth house.',
        'turn_kind': 'reading',
        'cited_factors': ['sun 17°46′ ♓︎ · house 4'],
      },
      'questions_left': 2,
      'source_chapter': {
        'system': 'numerology',
        'slug': 'life-path',
        'title': 'Life path',
      },
    });
    final events = await _client(
      'event: stage\ndata: {"stage":"house","name":"4"}\n\n'
      'event: stage\ndata: {"stage":"body","name":"saturn"}\n\n'
      'event: done\ndata: $done\n\n',
    ).askStream('why?', locale: 'en').toList();

    expect(events, hasLength(3));
    expect(events[0], isA<ChatStage>());
    expect((events[0] as ChatStage).stage, 'house');
    expect((events[0] as ChatStage).name, '4');
    expect((events[1] as ChatStage).stage, 'body');
    expect((events[1] as ChatStage).name, 'saturn');

    final reply = (events[2] as ChatDone).reply;
    expect(reply.threadId, 'th1');
    expect(reply.kind, ChatTurnKind.reading);
    expect(reply.citedFactors, ['sun 17°46′ ♓︎ · house 4']);
    expect(reply.questionsLeft, 2);
    expect(reply.sourceChapter?.system, 'numerology');
    expect(reply.sourceChapter?.slug, 'life-path');
    expect(reply.sourceChapter?.title, 'Life path');
  });

  test('ответ без главы-источника — обычное состояние, а не сбой', () async {
    final done = jsonEncode({
      'thread_id': 'th1',
      'message': {'body': 'Hello.', 'turn_kind': 'conversation', 'cited_factors': []},
      'source_chapter': null,
    });
    final events = await _client('event: done\ndata: $done\n\n')
        .askStream('hi', locale: 'en')
        .toList();
    expect((events.single as ChatDone).reply.sourceChapter, isNull);
  });

  test('error внутри потока — тот же ServerRefused, что у ask', () async {
    final stream = _client(
      'event: stage\ndata: {"stage":"house","name":"4"}\n\n'
      'event: error\ndata: {"status":503,"detail":{"error":"budget_exceeded",'
      '"message":"Сегодня я уже наговорилась."}}\n\n',
    ).askStream('why?', locale: 'ru');

    await expectLater(
      stream.toList(),
      throwsA(isA<ServerRefused>()
          .having((e) => e.status, 'status', 503)
          .having((e) => e.code, 'code', 'budget_exceeded')
          // Код из списка заведомо переведённых: фраза сервера доходит до
          // экрана дословно, 5xx её не стирает.
          .having((e) => e.message, 'message', 'Сегодня я уже наговорилась.')),
    );
  });

  test('отказ квоты до первого байта — обычный 429, как у /v1/chat', () async {
    final body = jsonEncode({
      'detail': {
        'error': 'question_limit',
        'message': 'Это 3 вопроса на сегодня.',
      }
    });
    final stream = _client(body, status: 429, contentType: 'application/json')
        .askStream('ещё один', locale: 'ru');

    await expectLater(
      stream.toList(),
      throwsA(isA<ServerRefused>()
          .having((e) => e.status, 'status', 429)
          .having((e) => e.code, 'code', 'question_limit')
          .having((e) => e.message, 'message', 'Это 3 вопроса на сегодня.')),
    );
  });

  test('поток, оборванный до done, — сеть, и вопрос не считается ушедшим',
      () async {
    final stream = _client(
      'event: stage\ndata: {"stage":"house","name":"4"}\n\n',
    ).askStream('why?', locale: 'en');

    await expectLater(stream.toList(), throwsA(isA<NetworkDown>()));
  });
}
