/// Португальский (Бразилия) перевод пяти юридических документов.
///
/// Зеркало `legal_text.dart` один в один: те же документы, те же разделы в том
/// же порядке, те же виды блоков и то же число пунктов в каждом списке —
/// расхождение по структуре означало бы, что чей-то абзац потерялся при
/// переводе, а не что перевод «вольный». Считать блоки и пункты, а не только
/// разделы: список остаётся одним блоком, из скольких бы пунктов он ни состоял.
///
/// «Você» всюду — так во всём продукте. Право четырнадцати дней в возвратах
/// названо «direito de arrependimento» (термин CDC ст. 49): бразильский
/// читатель узнаёт его под этим именем, а упоминание ЕС/Великобритании
/// остаётся упоминанием ЕС/Великобритании — ничего не добавлено и не убрано.
///
/// Имена собственные и значения фактов не переводятся: Pazl LLC, Apple,
/// hello@pazl.ai, reportaproblem.apple.com, Wyoming, United States, GDPR.
/// В [LegalFactBlank] переведена подпись, слаг остаётся английским: дыра
/// должна совпадать с дырой в английском документе, чтобы её заполнили один
/// раз в обоих.
library;

import 'legal_text.dart';

class LegalTextPt {
  const LegalTextPt._();

  /// Дата та же, что в английском документе: их проверяли вместе.
  static const updated = '7 de agosto de 2026';

  static const operatorName = 'Pazl LLC';

  static const merchant = 'Apple';

  static const contact = 'hello@pazl.ai';

  static const preamble = 'Este é um relato em linguagem simples de como a Alma realmente funciona. Foi escrito para ser lido, não para ser pulado, e nada aqui contradiz o que o aplicativo faz. Não é aconselhamento jurídico.';

  static const footer = 'Se uma frase desta página estiver confusa, a culpa é nossa, não sua. Escreva para hello@pazl.ai e nós corrigiremos a frase.';

  static LegalDoc of(LegalDocument which) => switch (which) {
        LegalDocument.terms => terms,
        LegalDocument.privacy => privacy,
        LegalDocument.refunds => refunds,
        LegalDocument.subscriptionTerms => subscriptionTerms,
        LegalDocument.imprint => imprint,
      };

  static const terms = LegalDoc(
    lead: 'O que você recebe, o que a Alma não fará e as poucas coisas que pedimos de você. Nada aqui é um truque, e não existe cláusula abaixo que contradiga uma frase acima dela.',
    sections: [
      LegalSection('O que a Alma é', [
        LegalBlock.para('A Alma calcula um mapa a partir da sua data, hora e local de nascimento, e escreve leituras a partir dele. O cálculo é aritmética e é o mesmo para todo mundo. As leituras são escritas por um modelo de linguagem que recebe o seu mapa e só pode citar o que está nele.'),
        LegalBlock.para('A Pazl LLC opera a Alma. Dentro deste aplicativo, quem a vende é a Apple — veja os termos de assinatura.'),
      ]),
      LegalSection('O que a Alma não é', [
        LegalBlock.para('A Alma não é aconselhamento médico, jurídico ou financeiro, e não prevê acontecimentos. Ela não vai dizer a você se deve aceitar o emprego, deixar a pessoa ou fazer a operação.'),
        LegalBlock.para('Isto não é um aviso pregado no fim de uma página. É uma regra aplicada no lugar onde as leituras são geradas: a Alma é instruída a nunca diagnosticar, nunca aconselhar sobre dinheiro ou lei e nunca afirmar que algo vai acontecer. Uma leitura que faça qualquer uma dessas coisas é uma falha do nosso sistema, não letra miúda que você deixou de ler. Conte para a gente em hello@pazl.ai e nós corrigiremos.'),
        LegalBlock.para('Se você está doente, em perigo ou tomando uma decisão que envolve dinheiro ou lei, converse com alguém qualificado. A Alma é para autoconhecimento, e autoconhecimento não é uma segunda opinião.'),
      ]),
      LegalSection('Quem pode usar', [
        LegalBlock.para('Qualquer pessoa com 16 anos ou mais. Você pode ler o seu mapa, e até comprar, sem nos dar um endereço: um visitante que não entrou na conta já é uma conta com um id, e o que entrar acrescenta é durabilidade, não permissão.'),
        LegalBlock.para('Mas uma conta sem identidade é uma conta em que ninguém consegue entrar de novo. Neste telefone, a sua conta vive no chaveiro do sistema, então ela sobrevive ao fechamento do aplicativo — não sobrevive à exclusão do aplicativo, nem à troca do telefone. Entre com a Apple, ou com um link enviado para uma caixa de entrada, e a conta acompanha você.'),
        LegalBlock.para('Isso importa mais para algo que você pagou. Uma compra pertence à conta da Alma que a reivindicou primeiro, então entrar na conta antes de reinstalar é o que faz "restaurar compras" encontrá-las.'),
      ]),
      LegalSection('O que pedimos de você', [
        LegalBlock.points([
          'Informe os seus próprios dados de nascimento com honestidade. Uma hora de nascimento chutada produz um mapa inteiramente plausível e completamente errado, e a Alma não consegue perceber a diferença.',
          'Se você informar os dados de nascimento de outra pessoa para uma leitura de compatibilidade, pergunte a ela antes. São os dados de nascimento dela, não os seus.',
          'Não raspe a Alma, não revenda as leituras dela e não as apresente como um produto seu. O que a Alma escreve para você é seu para guardar, imprimir, citar e compartilhar.',
          'Não ataque o serviço nem tente alcançar os mapas de outras pessoas.',
        ]),
      ]),
      LegalSection('O que devemos a você', [
        LegalBlock.para('As leituras que você comprou de vez, mantidas disponíveis enquanto a sua conta existir. Compras avulsas são permanentes; elas não expiram quando uma assinatura expira.'),
        LegalBlock.para('Um plano é o outro caso, e vale ser exato: leituras escritas para você enquanto um plano está ativo permanecem na sua conta quando o plano termina, mas param de abrir, porque o que um plano vende é o período, não o texto. É por essa razão que o arquivo é vendido separadamente.'),
        LegalBlock.para('A Alma não vai estar no ar cada segundo de cada ano. O serviço de ninguém está. Se ela estiver fora do ar quando você quiser usá-la, ela voltará — e se uma queda nossa custou a você um mês que você pagou, apoiaremos o seu pedido de reembolso junto à Apple, porque é ela quem segura o dinheiro.'),
        LegalBlock.para('Se mudarmos estes termos, você recebe um e-mail antes de a mudança entrar em vigor, não uma data silenciosamente atualizada no topo de uma página. Essa carta é escrita à mão e enviada para o endereço da sua conta, porque a Alma não tem lista de e-mails nem nada automático que pudesse enviá-la.'),
        LegalBlock.para('O que significa: se você nunca nos deu um endereço, não existe canal que chegue até você, e a data no topo desta página é o único aviso que há. Isso é um motivo para entrar na conta, não uma brecha da qual nos orgulhamos.'),
      ]),
      LegalSection('Se algo der errado', [
        LegalBlock.para('Se causarmos prejuízo a você, a nossa responsabilidade se limita ao que você pagou pela coisa que deu errado. A Alma é uma leitura, não um serviço profissional, e não deve ser tratada como um — que é a mesma frase da seção acima, na linguagem da responsabilidade civil.'),
        LegalBlock.para('Nada aqui remove um direito que o seu próprio país dá a você. Onde os dois divergirem, o seu país prevalece.'),
      ]),
      LegalSection('Encerrando', [
        LegalBlock.para('Se você entrou na conta, pode excluí-la em Ajustes, a qualquer momento, sem nos pedir e sem explicar. Tem efeito imediato e leva os seus dados junto — veja a página de privacidade.'),
        LegalBlock.para('Se não entrou — ler sem conta é permitido, e comprar sem conta também —, o botão em Ajustes não tem conta à qual anexar o pedido, então ele pede que você entre primeiro. Entre com a identidade com a qual você pagou e ele funciona. Se não conseguir, escreva para hello@pazl.ai e nós fazemos à mão. Isso é uma pessoa e um dia útil em vez de um botão, e dizer isso é melhor do que uma frase prometendo o contrário numa tela em que o botão está acinzentado.'),
        LegalBlock.para('Excluir a sua conta da Alma não cancela uma assinatura comprada pela App Store. Quem a segura é a Apple, e ela é cancelada na própria tela de assinaturas da Apple — há um botão em Ajustes que a abre.'),
        LegalBlock.para('Podemos encerrar uma conta que esteja atacando o serviço ou usando-o contra outras pessoas. Se o fizermos, você recebe o e-mail e o motivo — ou, quando não houver endereço na conta, o motivo mediante pedido em hello@pazl.ai.'),
      ]),
      LegalSection('Lei aplicável', [
        LegalBlock.para('Estes termos são regidos pela lei do Wyoming, United States — o estado em que a Pazl LLC está constituída —, e as disputas são julgadas nos tribunais do Wyoming.'),
        LegalBlock.para('Nada nessa frase remove um direito que o seu próprio país dá a você: onde uma lei de consumo do seu país e esta cláusula divergirem, o seu país prevalece, como a seção acima já diz.'),
      ]),
    ],
  );

  static const privacy = LegalDoc(
    lead: 'O que a Alma guarda sobre você, por que cada coisa é guardada e o que seria preciso para se livrar de tudo. Cada item abaixo é uma coluna que existe numa tabela real, não uma categoria que achamos que soaria tranquilizadora.',
    sections: [
      LegalSection('O que é coletado', [
        LegalBlock.points([
          'A sua data, hora e local de nascimento, e o nome que você deu. Isso é o mapa. Sem ele não há produto; com ele, tudo o mais que a Alma faz é aritmética sobre esses cinco números.',
          'O seu endereço de e-mail, se você entrou na conta. Sem senha — a caixa de entrada é a conta. Entrar com a Apple pode nos dar um endereço de retransmissão no lugar do seu, e tudo bem: nunca precisamos saber o real.',
          'As leituras escritas para você, para que um capítulo que você pagou diga a mesma coisa amanhã, e para que não seja escrito duas vezes ao nosso custo.',
          'As suas perguntas à Alma e as respostas dela, para que uma conversa tenha memória.',
          'O que você comprou, como uma lista de concessões — qual sistema, quando, por quanto tempo. Não um número de cartão: nunca tivemos um e não poderíamos armazená-lo nem se quiséssemos.',
          'Um punhado de eventos de funil — que um quiz foi iniciado, que um retrato foi visto — sem nenhum conteúdo dentro. Eles são contados, nunca lidos.',
        ]),
      ]),
      LegalSection('O que não é coletado', [
        LegalBlock.para('Nenhum dado de pagamento. A Apple recebe o pagamento neste aplicativo e guarda o cartão; a única coisa que chega até nós é uma declaração assinada de que uma compra aconteceu, que verificamos contra o próprio certificado da Apple antes de agir com base nela.'),
        LegalBlock.para('Nenhum identificador de publicidade, nenhuma análise de terceiros, nenhum rastreamento por outros aplicativos ou sites, nenhuma localização além do local de nascimento que você digitou. Não há do que se descadastrar porque não há nada rodando.'),
        LegalBlock.para('Não vendemos nem compartilhamos informações pessoais, em nenhum dos sentidos que essas palavras têm sob a California Consumer Privacy Act ou qualquer outra lei. Não existe acordo com ninguém que nos permitisse isso.'),
      ]),
      LegalSection('Quem mais vê', [
        LegalBlock.points([
          'A Anthropic, que opera o modelo que escreve as leituras. A sua data de nascimento, a sua hora de nascimento, o nome do seu local de nascimento e o seu nome, se você deu um, são enviados tal como são armazenados — é a partir deles que a leitura é escrita. O mesmo vale para o mapa calculado, a pergunta que você fez e os fatos curtos de que a Alma se lembra. Uma pergunta que você faz carrega as últimas doze mensagens daquela conversa, para que faça sentido em contexto. O seu endereço de e-mail não é enviado e não é necessário. As coordenadas do seu local de nascimento também não são enviadas: o mapa é calculado aqui e só o resultado viaja.',
          'A Apple ou o Google, conforme a loja em que você obteve a Alma, para qualquer coisa comprada neste aplicativo. Eles veem a compra, não o mapa.',
          'O nosso provedor de e-mail, para as duas cartas que a Alma envia: um link de entrada na conta e — para um plano comprado fora das lojas de aplicativos — um aviso antes de uma renovação.',
          'O nosso provedor de hospedagem, que opera a máquina em que o banco de dados está.',
        ]),
        LegalBlock.para('Essa é a lista inteira. Se ela algum dia ficar mais longa, esta página muda antes de o acordo começar, não depois.'),
      ]),
      LegalSection('Onde vive, e por quanto tempo', [
        LegalBlock.para('Em servidores na União Europeia. Leituras e mapas são mantidos enquanto a sua conta existir, porque esse é o propósito deles. Eventos de funil são mantidos como contagens.'),
        LegalBlock.para('Neste telefone, o token da sua conta está no chaveiro do sistema — criptografado pelo sistema, excluído dos backups e nunca gravado em lugar algum que um backup ou outro aplicativo consiga ler.'),
      ]),
      LegalSection('O que você pode fazer a respeito', [
        LegalBlock.points([
          'Exportar tudo, como um único arquivo, em Ajustes. São as linhas reais do banco de dados, não um resumo.',
          'Excluir tudo, em Ajustes. É imediato e é de verdade: as linhas são apagadas, não marcadas. Leituras que você pagou não podem ser escritas de novo palavra por palavra, e é por isso que o botão pede que você digite o seu endereço antes.',
          'Perguntar qualquer coisa em hello@pazl.ai. Uma pessoa responde.',
        ]),
        LegalBlock.para('Sob o GDPR você também tem o direito de corrigir o que guardamos, de se opor ao tratamento e de reclamar à autoridade supervisora do seu país. Os dois primeiros são os dois botões acima; o terceiro não precisa de nada de nós.'),
      ]),
      LegalSection('Crianças', [
        LegalBlock.para('A Alma é para pessoas com 16 anos ou mais e é classificada de acordo com isso na App Store. Não guardamos, conscientemente, dados sobre ninguém mais jovem. Se você acredita que guardamos, escreva para hello@pazl.ai e eles serão excluídos no dia em que lermos a mensagem.'),
      ]),
      LegalSection('Para quem escrever', [
        LegalBlock.para('A Pazl LLC é a controladora. hello@pazl.ai chega a uma pessoa, não a uma fila de tíquetes.'),
        LegalBlock.para('A Pazl LLC não tem estabelecimento na UE e ainda não nomeou um representante nos termos do Art. 27 do GDPR. Até que um seja nomeado nesta página, todo direito que esta página lista se exerce da mesma forma: escrevendo para hello@pazl.ai, onde uma pessoa responde.'),
      ]),
    ],
  );

  static const refunds = LegalDoc(
    lead: 'A Alma não é a vendedora de nada comprado neste aplicativo. A Apple é. Esse único fato decide a maior parte do que vem a seguir, por isso ele vem primeiro, e não numa nota de rodapé.',
    sections: [
      LegalSection('A Apple é a vendedora registrada', [
        LegalBlock.para('Quando você compra algo dentro deste aplicativo, o seu contrato de venda é com a Apple. Ela recebe o pagamento, emite o recibo, calcula e recolhe o imposto e segura o dinheiro. Os dados do seu cartão nunca chegam até nós.'),
        LegalBlock.para('Então um reembolso não é um botão que podemos apertar. Ele sai da conta deles, não da nossa, e é por isso que os pedidos de reembolso vão para eles. Podemos apoiar o seu pedido, e apoiamos, mas a decisão e a transferência são deles.'),
      ]),
      LegalSection('Como pedir', [
        LegalBlock.points([
          'reportaproblem.apple.com, com a Apple Account com que você comprou. Essa é a rota mais rápida e vai direto às pessoas que seguram o dinheiro. O mesmo formulário é acessível a partir do recibo que a Apple enviou a você por e-mail.',
          'Ou escreva para hello@pazl.ai informando a Apple Account com que você comprou. Não podemos emitir o reembolso, mas podemos confirmar à Apple o que aconteceu do nosso lado, e diremos a você o que eles responderam mesmo quando a resposta for não.',
        ]),
      ]),
      LegalSection('Quando apoiamos o pedido sem discutir', [
        LegalBlock.para('Estes são erros nossos, ou um direito seu, e nenhum deles é questão de julgamento:'),
        LegalBlock.points([
          'A leitura nunca foi gerada, ou foi gerada e não abria.',
          'O mapa estava errado por um erro do nosso lado, e não por uma hora de nascimento de que você não tinha certeza.',
          'Você foi cobrado duas vezes pela mesma coisa.',
          'Você foi cobrado depois de cancelar.',
          'Uma queda nossa custou a você um mês de assinatura que você tinha pago.',
          'Você mudou de ideia dentro de quatorze dias — veja o direito de arrependimento abaixo, que não tratamos como renunciado.',
        ]),
        LegalBlock.para('Você não precisa provar nada disso para nós. Se o registro mostrar, dizemos isso à Apple, e avisamos você de que dissemos.'),
      ]),
      LegalSection('Nada é escrito até você abrir', [
        LegalBlock.para('Um capítulo é gerado na primeira vez que você o abre, não no momento em que você paga. O arquivo são quarenta e um capítulos em oito sistemas, dos quais oito são as amostras gratuitas que qualquer pessoa pode ler; comprá-lo abre os outros trinta e três, e abri-los não é o mesmo que escrevê-los. Cada um é escrito quando você chega até ele, a partir do seu mapa tal como está naquele momento, e armazenado para que diga a mesma coisa todas as vezes depois.'),
        LegalBlock.para('É por isso que esta página pode dizer o que diz a seguir. No segundo em que o seu cartão é cobrado, nada foi entregue — e uma promessa de que você abriu mão de um direito sobre um texto que ninguém escreveu ainda não é uma promessa que se deva pedir a alguém que cumpra.'),
      ]),
      LegalSection('O direito de arrependimento de 14 dias, que não tratamos como renunciado', [
        LegalBlock.para('Na UE e no Reino Unido você tem quatorze dias para mudar de ideia sobre algo comprado on-line. Conteúdo digital pode ser uma exceção a isso, mas só quando três coisas aconteceram: você concordou expressamente que começássemos imediatamente, você reconheceu que começar imediatamente custa a você esse direito, e uma confirmação de ambas as coisas foi enviada a você em um suporte durável.'),
        LegalBlock.para('Pela App Store, é a Apple que opera a tela de compra e é a Apple que envia o recibo — não controlamos nenhuma das três coisas, e não vamos nos apoiar numa renúncia que não obtivemos. Se você nos disser, dentro de quatorze dias da compra, que mudou de ideia, apoiamos um reembolso integral junto à Apple e não perguntamos por quê.'),
        LegalBlock.para('Quando o preço inteiro volta, o que ele comprou se fecha: o arquivo para de abrir, ou o sistema que você comprou para de abrir. Dinheiro de volta com a leitura mantida não é reembolso, é um desconto de cem por cento, e preferimos recusar o segundo a fingir que ele é o primeiro.'),
        LegalBlock.para('Não descontamos pelos capítulos já escritos para você, e não dividimos a compra na parte que foi executada e na parte que não foi. Poderíamos — sabemos exatamente quais capítulos existem —, mas qualquer número que fixássemos para quanto de um livro você já leu seria um número inventado por nós, e um número inventado é pior para este documento do que uma política que de vez em quando nos custa uma venda.'),
        LegalBlock.para('Depois dos quatorze dias, a lista acima é a política: erros nossos, sem discussão, e no restante um pedido que a Apple decide.'),
      ]),
      LegalSection('Um ano não é entregue no primeiro dia', [
        LegalBlock.para('O plano anual é um caso diferente no direito e nos fatos. Ele não é uma coisa entregue de uma vez — são doze meses de acesso a tudo, incluindo sistemas que são reescritos conforme o céu se move, e no décimo dia dele nada parecido com o todo foi executado. Nenhum consentimento numa tela de compra encerra o seu direito de se arrepender de um serviço que mal começou.'),
        LegalBlock.para('Então: arrependa-se de um plano dentro de quatorze dias e o que deve voltar é a parte do período que você não usou, calculada sobre os dias decorridos, e o plano termina ali em vez de continuar correndo. Pedimos exatamente isso à Apple e fechamos o acesso do nosso lado, concordem eles ou não, porque a segunda metade cabe a nós.'),
      ]),
      LegalSection('O formulário-modelo de arrependimento', [
        LegalBlock.para('Você não precisa usar um formulário — um e-mail dizendo que mudou de ideia basta —, mas a lei exige que um seja oferecido, então aqui está:'),
        LegalBlock.para('À Pazl LLC, hello@pazl.ai — Comunico, por meio desta, que exerço o meu direito de arrependimento quanto ao meu contrato de fornecimento do seguinte conteúdo digital: [o que você comprou]. Pedido em [data]. Nome do consumidor: [seu nome]. Endereço de e-mail usado: [seu endereço]. Data: [hoje].'),
        LegalBlock.para('Endereçado a nós, e não à Apple, de propósito: o contrato pelo conteúdo é conosco, o dinheiro está com eles, e você não deveria ter de descobrir a qual dos dois escrever. Nós o encaminhamos.'),
      ]),
    ],
  );

  static const subscriptionTerms = LegalDoc(
    lead: 'O que renova, quanto custa e como parar — o que, para um plano comprado neste aplicativo, acontece na própria tela de assinaturas da Apple, não na nossa. Onde algo é menos arrumado do que isso, está escrito, em vez de omitido.',
    sections: [
      LegalSection('O que renova', [
        LegalBlock.para('A lista de preços tem dois planos recorrentes. O anual abre tudo o que a Alma escreveu para você — cada sistema, cada capítulo — por um ano. O mensal abre só os três sistemas que se movem com a data: os trânsitos, a revolução solar e a compatibilidade. Alugar um mapa natal seria cobrar aluguel sobre números que não mudaram desde que você nasceu, então o arquivo não faz parte dele.'),
        LegalBlock.para('Qualquer dos dois planos renova automaticamente no seu próprio ciclo até você pará-lo. O pagamento é cobrado da sua Apple Account na confirmação da compra. Ele renova a menos que a renovação automática seja desligada pelo menos 24 horas antes do fim do período atual, e a sua conta é cobrada pela renovação dentro das 24 horas que antecedem o fim desse período.'),
        LegalBlock.para('Um pagamento abre um pouco mais do que o período a que se refere — trinta e um dias para um mês, trezentos e sessenta e cinco para um ano, contados a partir do que for mais tarde: o dia em que você paga ou o dia em que o seu acesso atual termina. Os dias extras não se acumulam; eles existem para que uma renovação cobrada com algumas horas de atraso nunca possa deixar você fora de um período que você já pagou.'),
        LegalBlock.para('O preço é o mostrado na tela de compra. Ele não está impresso nesta página de propósito: a Apple define e cobra o preço para a sua loja, na sua moeda e com o seu imposto, e o número dela é o verdadeiro.'),
      ]),
      LegalSection('Um plano é alugado, não comprado', [
        LegalBlock.para('O plano anual abre tudo por um ano. Ele não é uma compra do arquivo. Quando o ano termina e você não renovou, as leituras que foram escritas para você durante ele permanecem na sua conta — nada é apagado —, mas param de abrir, como qualquer capítulo que você não pagou.'),
        LegalBlock.para('Se o que você quer é um texto que seja seu aconteça o que acontecer, isso é o arquivo, comprado uma única vez. Qualquer coisa comprada de vez é permanente e não é tocada por um plano que começa, termina ou é cancelado.'),
      ]),
      LegalSection('Quem avisa você antes da cobrança', [
        LegalBlock.para('Para um plano comprado neste aplicativo, a Apple avisa. A Apple envia o recibo e a Apple envia o aviso de renovação, porque a Apple é a vendedora e guarda o meio de pagamento. Nós não enviamos nenhum dos dois, e uma página nossa prometendo o contrário seria uma promessa que não podemos cumprir.'),
        LegalBlock.para('Para um plano comprado no nosso site com cartão, nós avisamos: três dias antes de uma renovação, sai um e-mail dizendo o que está prestes a ser cobrado, na moeda em que será cobrado e em que data. Não é um e-mail de marketing e não há descadastro nele, porque uma assinatura da qual você se esqueceu é o truque mais velho desta indústria e preferimos não estar nesse negócio.'),
      ]),
      LegalSection('O preço que você aceitou é o preço que renova', [
        LegalBlock.para('Nada na Alma pode mudar o que um plano existente custa. Um preço novo na lista de preços vale para compras novas; o seu plano continua cobrando o valor com que foi aberto. A Apple, além disso, pede que você confirme qualquer aumento de preço antes que ele entre em vigor, e cancela a assinatura em vez de cobrar o preço novo se você não confirmar.'),
      ]),
      LegalSection('Cancelando', [
        LegalBlock.para('Uma assinatura comprada neste aplicativo é cancelada na tela de assinaturas da Apple: Ajustes → Plano → Gerenciar esta assinatura na App Store, que a abre diretamente. Ou, fora da Alma: o app Ajustes → seu nome → Assinaturas.'),
        LegalBlock.para('Não podemos cancelá-la por você, e não vamos fingir que podemos. A Apple guarda o meio de pagamento; uma marcação do nosso lado dizendo "cancelado" não impede um cartão de ser cobrado, e quem acreditasse nela descobriria isso na fatura. Se você nos pedir para cancelar, o aplicativo diz exatamente isto e leva você à tela certa, em vez de gravar qualquer coisa.'),
        LegalBlock.para('Um plano comprado no nosso site com cartão é diferente, e lá os dois toques são reais: Ajustes → Plano → Cancelar assinatura → Confirmar. Nenhum e-mail para escrever, nenhum motivo para dar, nenhuma ligação e nenhuma oferta entre você e o segundo toque.'),
        LegalBlock.para('Cancelar não é um reembolso do período em que você está, e nada é retirado no momento em que você cancela. O que é e o que não é reembolsável — incluindo os quatorze dias em que você pode se arrepender de um plano por inteiro — está na página de reembolsos.'),
      ]),
      LegalSection('O que você mantém depois', [
        LegalBlock.para('Tudo o que você comprou de vez. Um sistema, ou o arquivo inteiro, comprado como compra avulsa é permanente e não é afetado pelo fim de uma assinatura.'),
        LegalBlock.para('A sua conta, o seu mapa e as suas conversas permanecem como estão. Encerrar uma assinatura não é excluir uma conta — isso é um ato separado e deliberado em Ajustes.'),
      ]),
      LegalSection('Uma leitura primeiro, o resto depois', [
        LegalBlock.para('Se você comprar um único sistema e então decidir, dentro de trinta dias, que quer o resto, o restante do arquivo é oferecido pelo preço dele menos o que você já pagou por aquela leitura. Nada a reivindicar, nada a reembolsar antes — o preço reduzido é simplesmente o que é cobrado de você.'),
        LegalBlock.para('A oferta vale enquanto você tem um único sistema e nada mais amplo. Depois de trinta dias a oferta desaparece e a leitura que você comprou continua sua. A redução se aplica ao arquivo; um plano tem preço próprio.'),
      ]),
      LegalSection('Se um pagamento falhar', [
        LegalBlock.para('Nada é retirado. Um cartão que falha costuma ser um cartão que funciona na nova tentativa, e a Apple tenta de novo por um tempo — a pessoa cujo pagamento falhou é a última que deveria ficar trancada do lado de fora enquanto isso se resolve.'),
        LegalBlock.para('Se as tentativas nunca derem certo, o plano simplesmente não é estendido: o seu acesso corre até o fim do período que você já pagou e para ali. Qualquer coisa comprada de vez fica intocada por tudo isso. Assinar de novo começa um período novo a partir do dia em que for pago.'),
      ]),
      LegalSection('Faturas e impostos', [
        LegalBlock.para('A Apple é a vendedora registrada de tudo o que é comprado neste aplicativo. Ela emite o recibo, ela cuida de VAT, GST e imposto sobre vendas onde se aplicam, e o recibo dela é o documento que o seu contador quer. Ele está em reportaproblem.apple.com e no e-mail que a Apple enviou a você.'),
      ]),
    ],
  );

  static const imprint = LegalDoc(
    lead: 'Quem está por trás da Alma, na forma que o §5 do Telemediengesetz da Alemanha e os equivalentes da Itália e da França pedem. Tudo o que ainda não foi fornecido está marcado como faltante, em vez de preenchido com algo plausível.',
    sections: [
      LegalSection('Operadora', [
        LegalBlock.fact('Empresa', 'Pazl LLC'),
        LegalBlock.fact('Forma', 'Sociedade de responsabilidade limitada'),
        LegalBlock.fact('Jurisdição', 'Wyoming, United States'),
        LegalBlock.factBlank('Endereço registrado', 'registered address'),
        LegalBlock.factBlank('Número de registro', 'filing ID'),
        LegalBlock.factBlank('Representada por', 'managing member'),
      ]),
      LegalSection('Contato', [
        LegalBlock.fact('E-mail', 'hello@pazl.ai'),
        LegalBlock.para('Uma pessoa lê. Não há número de telefone, e em vez de imprimir um que leve a uma secretária eletrônica, esta página diz isso.'),
      ]),
      LegalSection('Vendas neste aplicativo', [
        LegalBlock.fact('Vendedora registrada', 'Apple'),
        LegalBlock.para('Tudo o que é comprado dentro deste aplicativo é vendido pela Apple, que recebe o pagamento, emite o recibo e recolhe o imposto. A entidade na sua fatura depende da sua loja — Apple Inc., Apple Distribution International Ltd. ou iTunes K.K. — e o recibo que a Apple envia a você nomeia a que cobrou.'),
      ]),
      LegalSection('Imposto sobre valor agregado', [
        LegalBlock.factBlank('Identificação de VAT', 'VAT ID'),
        LegalBlock.para('A Alma é vendida por meio da Apple, que responde pelo VAT e pelo GST onde se aplicam. Um número de VAT próprio está sendo registrado.'),
      ]),
      LegalSection('Resolução de disputas on-line', [
        LegalBlock.para('A plataforma de ODR da Comissão Europeia fechou em julho de 2025 e não está vinculada aqui, porque um link para uma plataforma que não existe mais é pior do que nenhum link. Não somos obrigados a usar, e não nos comprometemos a usar, um órgão alternativo de resolução de disputas. Escreva para hello@pazl.ai e uma pessoa responderá.'),
      ]),
      LegalSection('Responsável pelo conteúdo', [
        LegalBlock.factBlank('Nos termos do §18 (2) MStV', 'name and address'),
      ]),
    ],
  );
}
