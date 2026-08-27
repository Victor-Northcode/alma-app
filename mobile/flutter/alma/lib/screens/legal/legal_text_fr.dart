/// Французские тела пяти юридических документов.
///
/// Структура зеркалит [LegalText] один в один: те же 37 разделов, те же виды
/// блоков в том же порядке, то же число пунктов в каждом списке — сверка
/// считает пункты отдельно от блоков ровно по той причине, что записана в
/// `legal_text.dart`. Продукт целиком на «tu», включая эти страницы: платный
/// чек уже говорит «tu», и юридический текст на «vous» выпадал бы из голоса.
///
/// Типографика — закон продукта: узкий неразрывный пробел U+202F перед
/// `? ! ; :` и внутри кавычек-ёлочек, апострофы только типографские (U+2019).
/// Имена собственные и технические значения (Pazl LLC, Apple, адреса, RGPD,
/// CCPA, Anthropic) не переводятся; в [LegalFactBlank] переведена подпись,
/// слаг остаётся английским — дыра должна остаться узнаваемой дырой.
library;

import 'legal_text.dart';

class LegalTextFr {
  const LegalTextFr._();

  /// Дата в шапке каждого документа — та же, что в [LegalText.updated],
  /// по той же причине: пять документов проверялись вместе.
  static const updated = '7 août 2026';

  static const preamble =
      'Voici, en langage clair, comment Alma fonctionne réellement. Ce texte est écrit pour être lu, pas survolé, et rien ici ne contredit ce que l’app fait. Ce n’est pas un conseil juridique.';

  static const footer =
      'Si une phrase de cette page n’est pas claire, c’est notre faute, pas la tienne. Écris à hello@pazl.ai et nous corrigerons la phrase.';

  static LegalDoc of(LegalDocument which) => switch (which) {
        LegalDocument.terms => terms,
        LegalDocument.privacy => privacy,
        LegalDocument.refunds => refunds,
        LegalDocument.subscriptionTerms => subscriptionTerms,
        LegalDocument.imprint => imprint,
      };

  static const terms = LegalDoc(
    lead:
        'Ce que tu obtiens, ce qu’Alma ne fera pas, et les quelques choses que nous te demandons. Rien ici n’est un piège, et aucune clause ci-dessous ne contredit une phrase au-dessus d’elle.',
    sections: [
      LegalSection('Ce qu’Alma est', [
        LegalBlock.para(
            'Alma calcule un thème à partir de ta date, ton heure et ton lieu de naissance, puis en écrit des lectures. Le calcul est arithmétique et le même pour tout le monde. Les lectures sont écrites par un modèle de langage qui reçoit ton thème et n’a le droit de citer que ce qui s’y trouve.'),
        LegalBlock.para(
            'Pazl LLC exploite Alma. Dans cette app, c’est Apple qui la vend — voir les conditions d’abonnement.'),
      ]),
      LegalSection('Ce qu’Alma n’est pas', [
        LegalBlock.para(
            'Alma n’est pas un conseil médical, juridique ou financier, et elle ne prédit pas les événements. Elle ne te dira pas s’il faut accepter le poste, quitter la personne ou subir l’opération.'),
        LegalBlock.para(
            'Ce n’est pas un avertissement collé au bas d’une page. C’est une règle appliquée là où les lectures sont générées : Alma a pour instruction de ne jamais diagnostiquer, de ne jamais conseiller sur l’argent ou le droit, et de ne jamais affirmer qu’une chose arrivera. Une lecture qui fait l’une de ces choses est un défaut de notre système, pas une clause en petits caractères que tu aurais manquée. Signale-la à hello@pazl.ai et nous la corrigerons.'),
        LegalBlock.para(
            'Si tu vas mal, si tu es en danger, ou si tu prends une décision où il y a de l’argent ou du droit, parle à quelqu’un de qualifié. Alma sert à la connaissance de soi, et la connaissance de soi n’est pas un second avis.'),
      ]),
      LegalSection('Qui peut l’utiliser', [
        LegalBlock.para(
            'Toute personne de 16 ans ou plus. Tu peux lire ton thème, et même acheter, sans nous donner d’adresse : un visiteur non connecté est déjà un compte avec un identifiant, et ce que la connexion ajoute, c’est de la durabilité, pas une permission.'),
        LegalBlock.para(
            'Mais un compte sans identité est un compte dans lequel personne ne peut revenir. Sur ce téléphone, ton compte vit dans le trousseau, donc il survit à la fermeture de l’app — il ne survit pas à sa suppression, ni au remplacement du téléphone. Connecte-toi avec Apple, ou avec un lien envoyé vers une boîte mail, et le compte te suit.'),
        LegalBlock.para(
            'C’est surtout important pour ce que tu as payé. Un achat appartient au compte Alma qui l’a réclamé en premier, donc te connecter avant de réinstaller est ce qui permet à « restaurer les achats » de les retrouver.'),
      ]),
      LegalSection('Ce que nous te demandons', [
        LegalBlock.points([
          'Saisis tes propres données de naissance honnêtement. Une heure de naissance devinée produit un thème entièrement plausible et complètement faux, et Alma ne peut pas faire la différence.',
          'Si tu saisis les données de naissance de quelqu’un d’autre pour une lecture de compatibilité, demande-lui d’abord. Ce sont ses données de naissance, pas les tiennes.',
          'N’aspire pas Alma, ne revends pas ses lectures et ne les présente pas comme un produit à toi. Ce qu’Alma écrit pour toi est à toi : garde-le, imprime-le, cite-le, partage-le.',
          'N’attaque pas le service et n’essaie pas d’atteindre les thèmes d’autres personnes.',
        ]),
      ]),
      LegalSection('Ce que nous te devons', [
        LegalBlock.para(
            'Les lectures achetées une fois pour toutes, disponibles tant que ton compte existe. Les achats uniques sont permanents ; ils n’expirent pas quand un abonnement expire.'),
        LegalBlock.para(
            'Un forfait est l’autre cas, et il vaut la peine d’être précis : les lectures écrites pour toi pendant qu’un forfait court restent dans ton compte quand le forfait se termine, mais elles cessent de s’ouvrir, parce qu’un forfait vend la période, pas le texte. C’est précisément pour cela que l’archive se vend à part.'),
        LegalBlock.para(
            'Alma ne sera pas en ligne chaque seconde de chaque année. Aucun service ne l’est. Si elle est indisponible au moment où tu la veux, elle reviendra — et si une panne de notre côté t’a coûté un mois que tu avais payé, nous appuierons ta demande de remboursement auprès d’Apple, parce que c’est Apple qui détient l’argent.'),
        LegalBlock.para(
            'Si nous changeons ces conditions, tu reçois un e-mail avant que le changement prenne effet, pas une date discrètement mise à jour en haut d’une page. Cette lettre est écrite à la main et envoyée à l’adresse de ton compte, parce qu’Alma n’a pas de liste de diffusion ni rien d’automatique qui pourrait l’envoyer.'),
        LegalBlock.para(
            'Ce qui veut dire : si tu ne nous as jamais donné d’adresse, aucun canal ne t’atteint, et la date en haut de cette page est le seul avis qui existe. C’est une raison de te connecter, pas une échappatoire dont nous serions fiers.'),
      ]),
      LegalSection('Si quelque chose tourne mal', [
        LegalBlock.para(
            'Si nous te causons une perte, notre responsabilité est limitée à ce que tu as payé pour la chose qui a mal tourné. Alma est une lecture, pas un service professionnel, et il ne faut pas s’y fier comme à un service professionnel — c’est la même phrase que la section plus haut, dans la langue de la responsabilité.'),
        LegalBlock.para(
            'Rien ici ne retire un droit que ton propre pays te donne. Là où les deux se contredisent, ton pays gagne.'),
      ]),
      LegalSection('Y mettre fin', [
        LegalBlock.para(
            'Si tu t’es connecté, tu peux supprimer ton compte dans les Réglages, à tout moment, sans nous demander et sans te justifier. C’est immédiat et tes données partent avec — voir la page de confidentialité.'),
        LegalBlock.para(
            'Si tu ne l’as pas fait — lire sans compte est permis, acheter sans compte aussi — le bouton des Réglages n’a aucun compte auquel rattacher la demande, alors il te demande d’abord de te connecter. Connecte-toi avec l’identité avec laquelle tu as payé et ça marche. Si tu ne peux pas, écris à hello@pazl.ai et nous le faisons à la main. C’est une personne et un jour ouvré plutôt qu’un bouton, et le dire vaut mieux qu’une phrase promettant le contraire sur un écran où le bouton est grisé.'),
        LegalBlock.para(
            'Supprimer ton compte Alma n’annule pas un abonnement acheté via l’App Store. C’est Apple qui le détient, et il s’annule sur l’écran d’abonnements d’Apple — un bouton dans les Réglages l’ouvre.'),
        LegalBlock.para(
            'Nous pouvons fermer un compte qui attaque le service ou l’utilise contre d’autres personnes. Si nous le faisons, tu reçois l’e-mail et la raison — ou, s’il n’y a pas d’adresse sur le compte, la raison sur demande à hello@pazl.ai.'),
      ]),
      LegalSection('Droit applicable', [
        LegalBlock.para(
            'Ces conditions sont régies par le droit du Wyoming, aux États-Unis — l’État où Pazl LLC est constituée — et les litiges sont portés devant les tribunaux du Wyoming.'),
        LegalBlock.para(
            'Rien dans cette phrase ne retire un droit que ton propre pays te donne : là où une loi de protection des consommateurs de ton pays et cette clause se contredisent, ton pays gagne, comme la section plus haut le dit déjà.'),
      ]),
    ],
  );

  static const privacy = LegalDoc(
    lead:
        'Ce qu’Alma détient sur toi, pourquoi chaque chose est détenue, et ce qu’il faudrait pour tout effacer. Chaque élément ci-dessous est une colonne qui existe dans une vraie table, pas une catégorie qui nous semblait rassurante.',
    sections: [
      LegalSection('Ce qui est collecté', [
        LegalBlock.points([
          'Ta date, ton heure et ton lieu de naissance, et le prénom que tu as donné. C’est le thème. Sans lui il n’y a pas de produit ; avec lui, tout le reste de ce qu’Alma fait est de l’arithmétique sur ces cinq nombres.',
          'Ton adresse e-mail, si tu t’es connecté. Sans mot de passe — la boîte mail est le compte. Se connecter avec Apple peut nous fournir une adresse relais à la place, et c’est très bien : nous n’avons jamais besoin de connaître ta vraie adresse.',
          'Les lectures écrites pour toi, pour qu’un chapitre que tu as payé dise la même chose demain, et pour qu’il ne soit pas écrit deux fois à nos frais.',
          'Tes questions à Alma et ses réponses, pour qu’une conversation ait une mémoire.',
          'Ce que tu as acheté, sous forme de liste de droits — quel système, quand, pour combien de temps. Pas un numéro de carte : nous n’en avons jamais eu et ne pourrions pas en stocker un même si nous le voulions.',
          'Une poignée d’événements de parcours — qu’un quiz a été commencé, qu’un portrait a été vu — sans aucun contenu dedans. Ils sont comptés, jamais lus.',
        ]),
      ]),
      LegalSection('Ce qui n’est pas collecté', [
        LegalBlock.para(
            'Aucune donnée de paiement. Apple prend le paiement dans cette app et garde la carte ; la seule chose qui nous parvient est une déclaration signée qu’un achat a eu lieu, que nous vérifions contre le propre certificat d’Apple avant d’agir dessus.'),
        LegalBlock.para(
            'Pas d’identifiants publicitaires, pas d’analytique tierce, pas de pistage à travers d’autres apps ou sites, pas de localisation au-delà du lieu de naissance que tu as tapé. Il n’y a rien à refuser parce qu’il n’y a rien qui tourne.'),
        LegalBlock.para(
            'Nous ne vendons ni ne partageons d’informations personnelles, au sens que chacun de ces mots a dans le California Consumer Privacy Act ou dans toute autre loi. Il n’existe aucun accord avec qui que ce soit qui nous le permettrait.'),
      ]),
      LegalSection('Qui d’autre les voit', [
        LegalBlock.points([
          'Anthropic, qui fait tourner le modèle qui écrit les lectures. Ta date de naissance, ton heure de naissance, le nom de ton lieu de naissance et ton prénom si tu l’as donné sont envoyés, tels qu’ils sont stockés — c’est à partir d’eux que la lecture s’écrit. Le thème calculé aussi, la question que tu as posée, et les faits courts qu’Alma retient. Une question que tu poses emporte les douze derniers messages de cette conversation pour garder son sens en contexte. Ton adresse e-mail n’est pas envoyée et n’est pas nécessaire. Les coordonnées de ton lieu de naissance non plus : le thème est calculé ici et seul le résultat voyage.',
          'Apple ou Google, selon la boutique où tu as pris Alma, pour tout achat dans cette app. Ils voient l’achat, pas le thème.',
          'Notre fournisseur d’e-mail, pour les deux lettres qu’Alma envoie : un lien de connexion, et — pour un forfait acheté hors des boutiques d’apps — un avis avant un renouvellement.',
          'Notre hébergeur, qui fait tourner la machine où se trouve la base de données.',
        ]),
        LegalBlock.para(
            'C’est la liste entière. Si elle s’allonge un jour, cette page change avant que l’accord commence, pas après.'),
      ]),
      LegalSection('Où ça vit, et pour combien de temps', [
        LegalBlock.para(
            'Sur des serveurs dans l’Union européenne. Les lectures et les thèmes sont conservés tant que ton compte existe, parce que c’est leur raison d’être. Les événements de parcours sont conservés sous forme de comptages.'),
        LegalBlock.para(
            'Sur ce téléphone, ton jeton de compte est dans le trousseau — chiffré par le système, exclu des sauvegardes, et jamais écrit là où une sauvegarde ou une autre app pourrait le lire.'),
      ]),
      LegalSection('Ce que tu peux y faire', [
        LegalBlock.points([
          'Tout exporter, en un seul fichier, depuis les Réglages. Ce sont les vraies lignes de la base de données, pas un résumé.',
          'Tout supprimer, depuis les Réglages. C’est immédiat et c’est réel : les lignes sont supprimées, pas marquées. Les lectures que tu as payées ne peuvent pas être réécrites mot pour mot, et c’est pour cela que le bouton te demande d’abord de taper ton adresse.',
          'Nous demander n’importe quoi à hello@pazl.ai. Une personne répond.',
        ]),
        LegalBlock.para(
            'Au titre du RGPD, tu as aussi le droit de rectifier ce que nous détenons, de t’opposer au traitement, et de porter plainte auprès de ton autorité de contrôle nationale. Les deux premiers sont les deux boutons ci-dessus ; le troisième n’a besoin de rien de notre part.'),
      ]),
      LegalSection('Enfants', [
        LegalBlock.para(
            'Alma est pour les personnes de 16 ans et plus et est classée en conséquence sur l’App Store. Nous ne détenons sciemment aucune donnée sur quelqu’un de plus jeune. Si tu penses que c’est le cas, écris à hello@pazl.ai et ces données seront supprimées le jour même où nous lisons ton message.'),
      ]),
      LegalSection('À qui écrire', [
        LegalBlock.para(
            'Pazl LLC est le responsable du traitement. hello@pazl.ai arrive chez une personne, pas dans une file de tickets.'),
        LegalBlock.para(
            'Pazl LLC n’a pas d’établissement dans l’UE et n’a pas encore désigné de représentant au titre de l’art. 27 du RGPD. Tant qu’un nom n’est pas donné sur cette page, chaque droit que cette page liste s’exerce de la même façon : en écrivant à hello@pazl.ai, où une personne répond.'),
      ]),
    ],
  );

  static const refunds = LegalDoc(
    lead:
        'Alma n’est le vendeur de rien de ce qui s’achète dans cette app. C’est Apple. Ce seul fait décide de presque tout ce qui suit, alors il vient en premier plutôt qu’en note de bas de page.',
    sections: [
      LegalSection('Apple est le vendeur officiel', [
        LegalBlock.para(
            'Quand tu achètes quelque chose dans cette app, ton contrat de vente est avec Apple. Ils prennent le paiement, ils émettent le reçu, ils calculent et reversent la taxe, et ils détiennent l’argent. Les données de ta carte ne nous parviennent jamais.'),
        LegalBlock.para(
            'Un remboursement n’est donc pas un bouton que nous pouvons presser. Il sort de leur compte, pas du nôtre, et c’est pourquoi les demandes de remboursement leur sont adressées. Nous pouvons appuyer ta demande, et nous le faisons, mais la décision et le virement leur appartiennent.'),
      ]),
      LegalSection('Comment demander', [
        LegalBlock.points([
          'reportaproblem.apple.com, connecté avec le compte Apple avec lequel tu as acheté. C’est la voie la plus rapide et elle va droit aux gens qui détiennent l’argent. Le même formulaire est accessible depuis le reçu qu’Apple t’a envoyé par e-mail.',
          'Ou écris à hello@pazl.ai avec le compte Apple avec lequel tu as acheté. Nous ne pouvons pas émettre le remboursement, mais nous pouvons confirmer à Apple ce qui s’est passé de notre côté, et nous te dirons ce qu’ils ont répondu, même quand la réponse est non.',
        ]),
      ]),
      LegalSection('Les cas où nous appuyons la demande sans discuter', [
        LegalBlock.para(
            'Ce sont nos fautes, ou ton droit, et ni l’un ni l’autre n’est une affaire d’appréciation :'),
        LegalBlock.points([
          'La lecture ne s’est jamais générée, ou s’est générée et ne s’ouvrait pas.',
          'Le thème était faux à cause d’une erreur de notre côté, pas d’une heure de naissance dont tu n’étais pas sûr.',
          'Tu as été débité deux fois pour la même chose.',
          'Tu as été débité après avoir annulé.',
          'Une panne de notre côté t’a coûté un mois d’abonnement que tu avais payé.',
          'Tu as changé d’avis dans les quatorze jours — voir le droit de rétractation ci-dessous, que nous ne considérons pas comme perdu.',
        ]),
        LegalBlock.para(
            'Tu n’as rien de tout cela à nous prouver. Si le registre le montre, nous le disons à Apple, et nous te disons que nous l’avons fait.'),
      ]),
      LegalSection('Rien n’est écrit avant que tu l’ouvres', [
        LegalBlock.para(
            'Un chapitre est généré la première fois que tu l’ouvres, pas au moment où tu paies. L’archive, c’est quarante et un chapitres répartis sur huit systèmes, dont huit sont les extraits gratuits que tout le monde peut lire ; l’acheter ouvre les trente-trois autres, et les ouvrir n’est pas la même chose que les écrire. Chacun s’écrit quand tu y vas, à partir de ton thème tel qu’il est alors, puis est stocké pour dire la même chose à chaque fois ensuite.'),
        LegalBlock.para(
            'C’est la raison pour laquelle cette page peut dire ce qu’elle dit ensuite. À la seconde où ta carte est débitée, rien n’a été livré — et une promesse selon laquelle tu aurais renoncé à un droit sur un texte que personne n’a encore écrit n’est pas une promesse qu’on devrait te demander de tenir.'),
      ]),
      LegalSection('Le droit de rétractation de 14 jours, que nous ne considérons pas comme perdu', [
        LegalBlock.para(
            'Dans l’UE et au Royaume-Uni, tu as quatorze jours pour changer d’avis sur un achat en ligne. Le contenu numérique peut faire exception, mais seulement quand trois choses ont eu lieu : tu as expressément accepté que nous commencions immédiatement, tu as reconnu que commencer immédiatement te coûte le droit, et une confirmation des deux t’a été envoyée sur un support durable.'),
        LegalBlock.para(
            'Via l’App Store, c’est Apple qui affiche la feuille d’achat et Apple qui envoie le reçu — nous ne contrôlons aucune des trois conditions, et nous n’allons pas nous prévaloir d’une renonciation que nous n’avons pas obtenue. Si tu nous dis dans les quatorze jours suivant l’achat que tu as changé d’avis, nous appuyons un remboursement intégral auprès d’Apple et nous ne te demandons pas pourquoi.'),
        LegalBlock.para(
            'Quand tout le prix revient, ce qu’il avait acheté se ferme : l’archive cesse de s’ouvrir, ou le système que tu as acheté cesse de s’ouvrir. L’argent rendu avec la lecture gardée n’est pas un remboursement, c’est une remise de cent pour cent, et nous préférons refuser la seconde plutôt que la faire passer pour le premier.'),
        LegalBlock.para(
            'Nous ne déduisons rien pour les chapitres déjà écrits pour toi, et nous ne découpons pas l’achat en une part exécutée et une part qui ne l’est pas. Nous pourrions — nous savons exactement quels chapitres existent — mais tout chiffre que nous fixerions pour dire quelle part d’un livre tu as lue serait un nombre inventé, et un seul nombre inventé est pire pour ce document qu’une politique qui nous coûte parfois une vente.'),
        LegalBlock.para(
            'Passé les quatorze jours, la liste ci-dessus est la politique : nos fautes, sans discuter, et sinon une demande qu’Apple tranche.'),
      ]),
      LegalSection('Une année n’est pas livrée le premier jour', [
        LegalBlock.para(
            'Le forfait annuel est un cas différent, en droit comme en fait. Ce n’est pas une chose remise d’un coup — ce sont douze mois d’accès à tout, y compris des systèmes réécrits à mesure que le ciel bouge, et au dixième jour rien qui ressemble au tout n’a été exécuté. Aucun consentement à une caisse ne met fin à ton droit de te rétracter d’un service qui a à peine commencé.'),
        LegalBlock.para(
            'Donc : rétracte-toi d’un forfait dans les quatorze jours et ce qui doit revenir, c’est la part de la période que tu n’as pas utilisée, calculée sur les jours écoulés, et le forfait s’arrête là au lieu de continuer. Nous demandons à Apple exactement cela et nous fermons l’accès de notre côté, qu’ils soient d’accord ou non, parce que cette seconde moitié dépend de nous.'),
      ]),
      LegalSection('Le formulaire type de rétractation', [
        LegalBlock.para(
            'Tu n’as pas besoin d’utiliser un formulaire — un e-mail disant que tu as changé d’avis suffit — mais la loi exige qu’il en soit proposé un, alors le voici :'),
        LegalBlock.para(
            'À Pazl LLC, hello@pazl.ai — Je notifie par la présente ma rétractation du contrat portant sur la fourniture du contenu numérique suivant : [ce que tu as acheté]. Commandé le [date]. Nom du consommateur : [ton nom]. Adresse e-mail utilisée : [ton adresse]. Date : [aujourd’hui].'),
        LegalBlock.para(
            'Adressé à nous plutôt qu’à Apple, exprès : le contrat sur le contenu est avec nous, l’argent est détenu par eux, et tu ne devrais pas avoir à deviner auquel des deux écrire. Nous transmettons.'),
      ]),
    ],
  );

  static const subscriptionTerms = LegalDoc(
    lead:
        'Ce qui se renouvelle, ce que ça coûte, et comment l’arrêter — ce qui, pour un forfait acheté dans cette app, se passe sur l’écran d’abonnements d’Apple plutôt que sur le nôtre. Là où quelque chose est moins net que cela, c’est écrit plutôt qu’omis.',
    sections: [
      LegalSection('Ce qui se renouvelle', [
        LegalBlock.para(
            'La liste de prix porte deux forfaits récurrents. L’annuel ouvre tout ce qu’Alma a écrit pour toi — chaque système, chaque chapitre — pendant un an. Le mensuel n’ouvre que les trois systèmes qui bougent avec la date : les transits, la révolution solaire et la compatibilité. Louer un thème natal serait un loyer sur des nombres qui n’ont pas changé depuis ta naissance, alors l’archive n’en fait pas partie.'),
        LegalBlock.para(
            'Chaque forfait se renouvelle automatiquement selon son propre cycle jusqu’à ce que tu l’arrêtes. Le paiement est débité sur ton compte Apple à la confirmation de l’achat. Il se renouvelle sauf si le renouvellement automatique est désactivé au moins 24 heures avant la fin de la période en cours, et ton compte est débité pour le renouvellement dans les 24 heures précédant la fin de cette période.'),
        LegalBlock.para(
            'Un paiement ouvre un peu plus que la période qu’il couvre — trente et un jours pour un mois, trois cent soixante-cinq pour une année, comptés à partir du plus tardif des deux : le jour où tu paies ou le jour où ton accès actuel se termine. Les jours en plus ne s’accumulent pas ; ils existent pour qu’un renouvellement débité avec quelques heures de retard ne puisse jamais te fermer une période que tu as déjà payée.'),
        LegalBlock.para(
            'Le prix est celui affiché sur la feuille d’achat. Il n’est pas imprimé sur cette page, exprès : Apple fixe et débite le prix pour ta boutique, dans ta monnaie, avec ta taxe, et c’est leur chiffre qui est le vrai.'),
      ]),
      LegalSection('Un forfait se loue, il ne s’achète pas', [
        LegalBlock.para(
            'Le forfait annuel ouvre tout pendant un an. Ce n’est pas un achat de l’archive. Quand l’année se termine et que tu n’as pas renouvelé, les lectures écrites pour toi pendant l’année restent dans ton compte — rien n’est supprimé — mais elles cessent de s’ouvrir, comme n’importe quel chapitre que tu n’as pas payé.'),
        LegalBlock.para(
            'Si ce que tu veux, c’est un texte qui reste à toi quoi qu’il arrive ensuite, c’est l’archive, achetée une fois. Tout ce qui est acheté une fois pour toutes est permanent et n’est pas touché par un forfait qui commence, se termine ou s’annule.'),
      ]),
      LegalSection('Qui te prévient avant un débit', [
        LegalBlock.para(
            'Pour un forfait acheté dans cette app, c’est Apple. Apple envoie le reçu et Apple envoie l’avis de renouvellement, parce qu’Apple est le vendeur et détient le moyen de paiement. Nous n’envoyons ni l’un ni l’autre, et une page de notre part promettant le contraire serait une promesse que nous ne pouvons pas tenir.'),
        LegalBlock.para(
            'Pour un forfait acheté sur notre site avec une carte, c’est nous : trois jours avant un renouvellement, un e-mail part disant ce qui va être prélevé, dans la monnaie où ce sera prélevé, et à quelle date. Ce n’est pas un e-mail marketing et il n’a pas de lien de désinscription, parce qu’un abonnement oublié est le plus vieux tour de cette industrie et que nous préférons ne pas être de ce commerce.'),
      ]),
      LegalSection('Le prix que tu as accepté est le prix qui se renouvelle', [
        LegalBlock.para(
            'Rien dans Alma ne peut changer ce que coûte un forfait existant. Un nouveau prix sur la liste s’applique aux nouveaux achats ; ton forfait continue d’être facturé au prix auquel il a été ouvert. Apple te demande en plus de confirmer toute hausse de prix avant qu’elle prenne effet, et annulera l’abonnement plutôt que de te débiter le nouveau prix si tu ne le fais pas.'),
      ]),
      LegalSection('Annuler', [
        LegalBlock.para(
            'Un abonnement acheté dans cette app s’annule sur l’écran d’abonnements d’Apple : Réglages → Formule → Gérer cet abonnement dans l’App Store, qui l’ouvre directement. Ou, hors d’Alma : l’app Réglages → ton nom → Abonnements.'),
        LegalBlock.para(
            'Nous ne pouvons pas l’annuler pour toi, et nous ne ferons pas semblant de le pouvoir. Apple détient le moyen de paiement ; un drapeau de notre côté disant « annulé » n’empêche pas une carte d’être débitée, et la personne qui y aurait cru l’apprendrait sur un relevé. Si tu nous demandes d’annuler, l’app dit exactement cela et t’envoie vers le bon écran au lieu d’écrire quoi que ce soit.'),
        LegalBlock.para(
            'Un forfait acheté sur notre site avec une carte est différent, et là les deux touches sont réelles : Réglages → Formule → Résilier l’abonnement → Confirmer. Aucun e-mail à écrire, aucune raison à donner, aucun appel, et aucune offre entre toi et la seconde touche.'),
        LegalBlock.para(
            'Annuler n’est pas un remboursement de la période en cours, et rien ne t’est retiré au moment où tu annules. Ce qui est remboursable et ce qui ne l’est pas — y compris les quatorze jours pendant lesquels tu peux te rétracter d’un forfait purement et simplement — est sur la page des remboursements.'),
      ]),
      LegalSection('Ce que tu gardes après', [
        LegalBlock.para(
            'Tout ce que tu as acheté une fois pour toutes. Un système, ou l’archive entière, acheté en achat unique est permanent et n’est pas affecté par la fin d’un abonnement.'),
        LegalBlock.para(
            'Ton compte, ton thème et tes conversations restent tels quels. Mettre fin à un abonnement n’est pas supprimer un compte — c’est un acte séparé et délibéré, dans les Réglages.'),
      ]),
      LegalSection('Une lecture d’abord, le reste ensuite', [
        LegalBlock.para(
            'Si tu achètes un seul système puis décides dans les trente jours que tu veux le reste, le reste de l’archive t’est proposé à son prix moins ce que tu as déjà payé pour cette lecture. Rien à réclamer, rien à rembourser d’abord — le prix réduit est simplement ce qui t’est débité.'),
        LegalBlock.para(
            'L’offre vaut tant que tu détiens un système et rien de plus large. Passé trente jours, l’offre disparaît et la lecture que tu as achetée reste à toi. La réduction s’applique à l’archive ; un forfait a son propre prix.'),
      ]),
      LegalSection('Si un paiement échoue', [
        LegalBlock.para(
            'Rien ne t’est retiré. Une carte qui rebondit est le plus souvent une carte qui marche à la nouvelle tentative, et Apple réessaie pendant un moment — la personne dont le paiement a échoué est la dernière qui devrait être mise dehors pendant que ça se règle.'),
        LegalBlock.para(
            'Si les tentatives n’aboutissent jamais, le forfait n’est simplement pas prolongé : ton accès court jusqu’à la fin de la période déjà payée et s’arrête là. Tout ce que tu as acheté une fois pour toutes n’est touché par rien de tout cela. Te réabonner ouvre une nouvelle période à partir du jour où elle est payée.'),
      ]),
      LegalSection('Factures et taxes', [
        LegalBlock.para(
            'Apple est le vendeur officiel de tout ce qui s’achète dans cette app. Ils émettent le reçu, ils gèrent la TVA, la GST et la taxe de vente là où elles s’appliquent, et leur reçu est le document que veut ton comptable. Il est sur reportaproblem.apple.com et dans l’e-mail qu’Apple t’a envoyé.'),
      ]),
    ],
  );

  static const imprint = LegalDoc(
    lead:
        'Qui est derrière Alma, dans la forme que demandent le §5 du Telemediengesetz allemand et ses équivalents italien et français. Tout ce qui n’a pas encore été fourni est marqué comme manquant plutôt que rempli avec quelque chose de plausible.',
    sections: [
      LegalSection('Exploitant', [
        LegalBlock.fact('Société', 'Pazl LLC'),
        LegalBlock.fact('Forme', 'Limited liability company'),
        LegalBlock.fact('Juridiction', 'Wyoming, United States'),
        LegalBlock.fact('Adresse du siège', '30 N Gould St Ste R, Sheridan, Wyoming 82801'),
        LegalBlock.fact('Numéro d’immatriculation', '2026-002034771'),
        LegalBlock.fact('Représentée par', 'Anatolii Mikhailov'),
      ]),
      LegalSection('Contact', [
        LegalBlock.fact('E-mail', 'hello@pazl.ai'),
        LegalBlock.para(
            'Une personne le lit. Il n’y a pas de numéro de téléphone, et plutôt que d’en imprimer un qui aboutit à un répondeur, cette page le dit.'),
      ]),
      LegalSection('La vente dans cette app', [
        LegalBlock.fact('Vendeur officiel', 'Apple'),
        LegalBlock.para(
            'Tout ce qui s’achète dans cette app est vendu par Apple, qui prend le paiement, émet le reçu et reverse la taxe. L’entité sur ton relevé dépend de ta boutique — Apple Inc., Apple Distribution International Ltd. ou iTunes K.K. — et le reçu qu’Apple t’envoie nomme celle qui t’a débité.'),
      ]),
      LegalSection('Taxe sur la valeur ajoutée', [
        LegalBlock.factBlank('Numéro de TVA', 'VAT ID'),
        LegalBlock.para(
            'Alma est vendue via Apple, qui déclare la TVA et la GST là où elles s’appliquent. Un numéro de TVA à nous est en cours d’enregistrement.'),
      ]),
      LegalSection('Règlement des litiges en ligne', [
        LegalBlock.para(
            'La plateforme de RLL de la Commission européenne a fermé en juillet 2025 et n’est pas liée ici, parce qu’un lien vers une plateforme qui n’existe plus est pire que pas de lien. Nous ne sommes pas tenus de recourir à un organisme de règlement extrajudiciaire des litiges, et nous ne nous y engageons pas. Écris à hello@pazl.ai et une personne répondra.'),
      ]),
      LegalSection('Responsable du contenu', [
        LegalBlock.fact('Au titre du §18 (2) MStV', 'Anatolii Mikhailov · 30 N Gould St Ste R, Sheridan, Wyoming 82801'),
      ]),
    ],
  );
}
