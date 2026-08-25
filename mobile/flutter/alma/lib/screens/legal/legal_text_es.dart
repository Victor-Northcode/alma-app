import 'legal_text.dart';

/// Spanish texts of the five documents. The structure mirrors [LegalText]
/// exactly — guarded by legal_catalog_test.dart.
class LegalTextEs {
  const LegalTextEs._();

  static const updated = '7 de agosto de 2026';

  static const preamble = 'Este es un relato en lenguaje llano de cómo funciona Alma en realidad. Está escrito para leerse, no para pasarlo por encima, y nada en él contradice lo que hace la app. No es asesoramiento legal.';

  static const footer = 'Si una frase de esta página no queda clara, la culpa es nuestra, no tuya. Escribe a hello@pazl.ai y arreglaremos la frase.';

  static LegalDoc of(LegalDocument which) => switch (which) {
        LegalDocument.terms => terms,
        LegalDocument.privacy => privacy,
        LegalDocument.refunds => refunds,
        LegalDocument.subscriptionTerms => subscriptionTerms,
        LegalDocument.imprint => imprint,
      };

  static const terms = LegalDoc(
    lead: 'Lo que recibes, lo que Alma no hará, y las pocas cosas que te pedimos. Nada aquí es una trampa, y no hay ninguna cláusula abajo que contradiga una frase de arriba.',
    sections: [
      LegalSection('Qué es Alma', [
        LegalBlock.para('Alma calcula una carta a partir de tu fecha, hora y lugar de nacimiento, y escribe lecturas basadas en ella. El cálculo es aritmética y es igual para todo el mundo. Las lecturas las escribe un modelo de lenguaje que recibe tu carta y solo tiene permitido citar lo que está en ella.'),
        LegalBlock.para('Pazl LLC opera Alma. Dentro de esta app, la vende Apple — mira los términos de suscripción.'),
      ]),
      LegalSection('Qué no es Alma', [
        LegalBlock.para('Alma no es asesoramiento médico, legal ni financiero, y no predice acontecimientos. No te dirá si aceptar el trabajo, dejar a la persona o someterte a la operación.'),
        LegalBlock.para('Esto no es un descargo de responsabilidad atornillado al final de una página. Es una regla que se aplica allí donde se generan las lecturas: Alma tiene instrucciones de no diagnosticar nunca, no aconsejar nunca sobre dinero ni leyes, y no afirmar nunca que algo va a suceder. Una lectura que haga cualquiera de esas cosas es un fallo de nuestro sistema, no letra pequeña que no leíste. Cuéntanoslo en hello@pazl.ai y lo arreglaremos.'),
        LegalBlock.para('Si no te encuentras bien, estás en peligro o vas a tomar una decisión con dinero o leyes de por medio, habla con alguien calificado. Alma es para el autoconocimiento, y el autoconocimiento no es una segunda opinión.'),
      ]),
      LegalSection('Quién puede usarla', [
        LegalBlock.para('Cualquier persona de 16 años o más. Puedes leer tu carta, e incluso comprar, sin darnos una dirección: un visitante sin sesión iniciada ya es una cuenta con un id, y lo que añade iniciar sesión es durabilidad, no permiso.'),
        LegalBlock.para('Pero una cuenta sin identidad es una cuenta a la que nadie puede volver a entrar. En este teléfono tu cuenta vive en el llavero, así que sobrevive a que se cierre la app — no sobrevive a que se borre la app ni a que cambies de teléfono. Inicia sesión con Apple, o con un enlace a un buzón de correo, y la cuenta te sigue.'),
        LegalBlock.para('Esto importa sobre todo con algo que has pagado. Una compra pertenece a la cuenta de Alma que la reclamó primero, así que iniciar sesión antes de reinstalar es lo que hace que «restaurar compras» las encuentre.'),
      ]),
      LegalSection('Qué te pedimos', [
        LegalBlock.points([
          'Introduce tus propios datos de nacimiento con honestidad. Una hora de nacimiento adivinada produce una carta enteramente plausible y completamente equivocada, y Alma no puede notar la diferencia.',
          'Si introduces los datos de nacimiento de otra persona para una lectura de compatibilidad, pídele permiso primero. Son sus datos de nacimiento, no los tuyos.',
          'No extraigas datos de Alma de forma automatizada, no revendas sus lecturas ni las presentes como un producto tuyo. Lo que Alma escribe para ti es tuyo: puedes guardarlo, imprimirlo, citarlo y compartirlo.',
          'No ataques el servicio ni intentes llegar a las cartas de otras personas.',
        ]),
      ]),
      LegalSection('Qué te debemos', [
        LegalBlock.para('Las lecturas que compraste de forma definitiva, disponibles mientras exista tu cuenta. Las compras únicas son permanentes; no caducan cuando caduca una suscripción.'),
        LegalBlock.para('Un plan es el otro caso, y vale la pena ser exactos: las lecturas escritas para ti mientras un plan está activo se quedan en tu cuenta cuando el plan termina, pero dejan de abrirse, porque lo que un plan vende es el periodo, no el texto. Esa es la razón misma de que el archivo se venda por separado.'),
        LegalBlock.para('Alma no estará en línea cada segundo de cada año. Ningún servicio lo está. Si está caída cuando la quieres, volverá — y si una caída nuestra te costó un mes que pagaste, apoyaremos tu solicitud de reembolso ante Apple, porque son ellos quienes tienen el dinero.'),
        LegalBlock.para('Si cambiamos estos términos, recibes un correo antes de que el cambio entre en vigor, no una fecha actualizada en silencio al principio de una página. Esa carta se escribe a mano y se envía a la dirección de tu cuenta, porque Alma no tiene lista de correo ni nada automático que pudiera enviarla.'),
        LegalBlock.para('Lo que significa: si nunca nos has dado una dirección, no hay canal que te alcance, y la fecha al principio de esta página es el único aviso que existe. Eso es una razón para iniciar sesión, no un resquicio que nos agrade.'),
      ]),
      LegalSection('Si algo sale mal', [
        LegalBlock.para('Si te causamos una pérdida, nuestra responsabilidad se limita a lo que pagaste por la cosa que salió mal. Alma es una lectura, no un servicio profesional, y no debe tratarse como tal — que es la misma frase de la sección anterior, en el idioma de la responsabilidad.'),
        LegalBlock.para('Nada aquí elimina un derecho que te dé tu propio país. Donde los dos discrepen, gana tu país.'),
      ]),
      LegalSection('Terminar', [
        LegalBlock.para('Si has iniciado sesión, puedes eliminar tu cuenta en Ajustes, en cualquier momento, sin pedírnoslo y sin dar explicaciones. Surte efecto de inmediato y se lleva tus datos con ella — mira la página de privacidad.'),
        LegalBlock.para('Si no lo has hecho — leer sin cuenta está permitido, y comprar sin cuenta también —, el botón de Ajustes no tiene cuenta a la que asociar la solicitud, así que te pide iniciar sesión primero. Inicia sesión con la identidad con la que pagaste y funciona. Si no puedes, escribe a hello@pazl.ai y lo hacemos a mano. Eso es una persona y un día hábil en lugar de un botón, y decirlo es mejor que una frase que prometa otra cosa en una pantalla donde el botón está desactivado.'),
        LegalBlock.para('Eliminar tu cuenta de Alma no cancela una suscripción comprada a través del App Store. Esa la tiene Apple, y se cancela en la propia pantalla de suscripciones de Apple — hay un botón en Ajustes que la abre.'),
        LegalBlock.para('Podemos cerrar una cuenta que esté atacando el servicio o usándolo contra otras personas. Si lo hacemos, recibes el correo y el motivo — o, si la cuenta no tiene dirección, el motivo a petición en hello@pazl.ai.'),
      ]),
      LegalSection('Ley', [
        LegalBlock.para('Estos términos se rigen por la ley de Wyoming, United States — el estado en el que está constituida Pazl LLC —, y las disputas se resuelven en los tribunales de Wyoming.'),
        LegalBlock.para('Nada en esa frase elimina un derecho que te dé tu propio país: donde una ley de consumo de tu país y esta cláusula discrepen, gana tu país, como ya dice la sección anterior.'),
      ]),
    ],
  );

  static const privacy = LegalDoc(
    lead: 'Lo que Alma guarda sobre ti, por qué guarda cada cosa, y qué haría falta para deshacerse de todo. Cada punto de abajo es una columna que existe en una tabla real, no una categoría que nos pareció tranquilizadora.',
    sections: [
      LegalSection('Qué se recoge', [
        LegalBlock.points([
          'Tu fecha, hora y lugar de nacimiento, y el nombre que diste. Eso es la carta. Sin ella no hay producto; con ella, todo lo demás que hace Alma es aritmética sobre esos cinco números.',
          'Tu dirección de correo, si iniciaste sesión. Sin contraseña — el buzón es la cuenta. Iniciar sesión con Apple puede darnos en su lugar una dirección de reenvío, y no pasa nada: nunca necesitamos conocer la real.',
          'Las lecturas escritas para ti, para que un capítulo que pagaste diga lo mismo mañana, y para que no se escriba dos veces a costo nuestro.',
          'Tus preguntas a Alma y sus respuestas, para que una conversación tenga memoria.',
          'Lo que has comprado, como una lista de concesiones — qué sistema, cuándo, por cuánto tiempo. No un número de tarjeta: nunca hemos tenido uno y no podríamos almacenarlo aunque quisiéramos.',
          'Un puñado de eventos de embudo — que se empezó un cuestionario, que se vio un retrato — sin ningún contenido dentro. Se cuentan, nunca se leen.',
        ]),
      ]),
      LegalSection('Qué no se recoge', [
        LegalBlock.para('Ningún dato de pago. Apple cobra el pago en esta app y guarda la tarjeta; lo único que nos llega es una declaración firmada de que hubo una compra, que verificamos contra el propio certificado de Apple antes de actuar sobre ella.'),
        LegalBlock.para('Ningún identificador publicitario, ninguna analítica de terceros, ningún rastreo por otras apps o sitios web, ninguna ubicación más allá del lugar de nacimiento que escribiste. No hay nada de lo que darse de baja porque no hay nada funcionando.'),
        LegalBlock.para('No vendemos ni compartimos información personal, en el sentido que cualquiera de esas dos palabras tiene bajo la California Consumer Privacy Act o cualquier otra ley. No existe acuerdo con nadie que nos lo permitiera.'),
      ]),
      LegalSection('Quién más lo ve', [
        LegalBlock.points([
          'Anthropic, que opera el modelo que escribe las lecturas. Se envían tu fecha de nacimiento, tu hora de nacimiento, el nombre de tu lugar de nacimiento y tu nombre si lo diste, tal como están almacenados — son aquello a partir de lo cual se escribe la lectura. También la carta calculada, la pregunta que hiciste y los datos breves que Alma recuerda. Una pregunta que haces lleva consigo los últimos doce mensajes de esa conversación para que tenga sentido en contexto. Tu dirección de correo no se envía y no hace falta. Las coordenadas de tu lugar de nacimiento tampoco se envían: la carta se calcula aquí y solo viaja el resultado.',
          'Apple o Google, según la tienda de la que obtuviste Alma, para cualquier cosa comprada en esta app. Ven la compra, no la carta.',
          'Nuestro proveedor de correo, para las dos cartas que Alma envía: un enlace de inicio de sesión y — para un plan comprado fuera de las tiendas de apps — un aviso antes de una renovación.',
          'Nuestro proveedor de hosting, que opera la máquina donde está la base de datos.',
        ]),
        LegalBlock.para('Esa es la lista completa. Si algún día se alarga, esta página cambia antes de que empiece el acuerdo, no después.'),
      ]),
      LegalSection('Dónde vive, y por cuánto tiempo', [
        LegalBlock.para('En servidores de la Unión Europea. Las lecturas y las cartas se conservan mientras exista tu cuenta, porque ese es su sentido. Los eventos de embudo se conservan como recuentos.'),
        LegalBlock.para('En este teléfono, el token de tu cuenta está en el llavero — cifrado por el sistema, excluido de las copias de seguridad, y nunca escrito en ningún lugar que una copia de seguridad u otra app pueda leer.'),
      ]),
      LegalSection('Qué puedes hacer al respecto', [
        LegalBlock.points([
          'Exportarlo todo, como un solo archivo, desde Ajustes. Son las filas reales de la base de datos, no un resumen.',
          'Eliminarlo todo, desde Ajustes. Es inmediato y es real: las filas se eliminan, no se marcan. Las lecturas que pagaste no pueden escribirse otra vez palabra por palabra, y por eso el botón te pide escribir tu dirección primero.',
          'Preguntarnos lo que sea en hello@pazl.ai. Responde una persona.',
        ]),
        LegalBlock.para('Bajo el GDPR también tienes derecho a corregir lo que guardamos, a oponerte al tratamiento y a reclamar ante tu autoridad de control nacional. Los dos primeros son los dos botones de arriba; el tercero no necesita nada de nosotros.'),
      ]),
      LegalSection('Menores', [
        LegalBlock.para('Alma es para personas de 16 años o más y así está clasificada en el App Store. No guardamos a sabiendas datos de nadie menor. Si crees que sí lo hacemos, escribe a hello@pazl.ai y se eliminarán el día que lo leamos.'),
      ]),
      LegalSection('A quién escribir', [
        LegalBlock.para('Pazl LLC es el responsable del tratamiento. hello@pazl.ai llega a una persona, no a una cola de tickets.'),
        LegalBlock.para('Pazl LLC no tiene establecimiento en la UE y todavía no ha designado un representante conforme al Art. 27 del GDPR. Hasta que se nombre uno en esta página, cada derecho que esta página enumera se ejerce de la misma manera: escribiendo a hello@pazl.ai, donde responde una persona.'),
      ]),
    ],
  );

  static const refunds = LegalDoc(
    lead: 'Alma no es el vendedor de nada de lo que se compra en esta app. Lo es Apple. Ese único hecho decide la mayor parte de lo que sigue, así que va primero y no en una nota al pie.',
    sections: [
      LegalSection('Apple es el vendedor de registro', [
        LegalBlock.para('Cuando compras algo dentro de esta app, tu contrato de compraventa es con Apple. Ellos cobran el pago, ellos emiten el recibo, ellos calculan y remiten el impuesto, y ellos guardan el dinero. Los datos de tu tarjeta nunca nos llegan.'),
        LegalBlock.para('Así que un reembolso no es un botón que podamos pulsar. Sale de su cuenta, no de la nuestra, y por eso las solicitudes de reembolso van a ellos. Podemos apoyar tu solicitud, y lo hacemos, pero la decisión y la transferencia son suyas.'),
      ]),
      LegalSection('Cómo pedirlo', [
        LegalBlock.points([
          'reportaproblem.apple.com, con la sesión iniciada con la cuenta de Apple con la que compraste. Es la vía más rápida y va directo a la gente que tiene el dinero. El mismo formulario está accesible desde el recibo que Apple te envió por correo.',
          'O escribe a hello@pazl.ai con la cuenta de Apple con la que compraste. No podemos emitir el reembolso, pero sí podemos confirmarle a Apple lo que pasó de nuestro lado, y te diremos lo que respondieron incluso cuando la respuesta sea no.',
        ]),
      ]),
      LegalSection('En qué casos apoyamos la solicitud sin discutir', [
        LegalBlock.para('Estos son fallos nuestros, o un derecho tuyo, y ninguno requiere un juicio de valor:'),
        LegalBlock.points([
          'La lectura nunca se generó, o se generó y no se abría.',
          'La carta estaba equivocada por un error de nuestro lado y no por una hora de nacimiento de la que no tenías certeza.',
          'Se te cobró dos veces por lo mismo.',
          'Se te cobró después de cancelar.',
          'Una caída nuestra te costó un mes de suscripción que habías pagado.',
          'Cambiaste de opinión dentro de los catorce días — mira el derecho de desistimiento más abajo, que no damos por renunciado.',
        ]),
        LegalBlock.para('No tienes que demostrarnos nada de esto. Si el registro lo muestra, se lo decimos a Apple, y te decimos que lo hemos hecho.'),
      ]),
      LegalSection('Nada se escribe hasta que lo abres', [
        LegalBlock.para('Un capítulo se genera la primera vez que lo abres, no en el momento en que pagas. El archivo son cuarenta y un capítulos repartidos en ocho sistemas, ocho de los cuales son las muestras gratuitas que cualquiera puede leer; comprarlo abre los otros treinta y tres, y abrirlos no es lo mismo que escribirlos. Cada uno se escribe cuando llegas a él, a partir de tu carta tal como está en ese momento, y se almacena para que diga lo mismo todas las veces siguientes.'),
        LegalBlock.para('Esa es la razón de que esta página pueda decir lo que dice a continuación. En el segundo en que se cobra tu tarjeta, nada ha sido entregado — y una promesa de que has renunciado a un derecho sobre un texto que nadie ha escrito todavía no es una promesa que se le deba pedir cumplir a nadie.'),
      ]),
      LegalSection('El derecho de desistimiento de 14 días, que no damos por renunciado', [
        LegalBlock.para('En la UE y el Reino Unido tienes catorce días para cambiar de opinión sobre algo comprado en línea. El contenido digital puede ser una excepción a eso, pero solo cuando han ocurrido tres cosas: aceptaste expresamente que empezáramos de inmediato, reconociste que empezar de inmediato te cuesta el derecho, y se te envió confirmación de ambas cosas en un soporte duradero.'),
        LegalBlock.para('A través del App Store, Apple gestiona la hoja de compra y Apple envía el recibo — no controlamos ninguna de las tres cosas, y no vamos a ampararnos en una renuncia que no obtuvimos. Si nos dices dentro de los catorce días siguientes a la compra que has cambiado de opinión, apoyamos un reembolso completo ante Apple y no te preguntamos por qué.'),
        LegalBlock.para('Cuando vuelve el precio entero, lo que compró se cierra: el archivo deja de abrirse, o el sistema que compraste deja de abrirse. Dinero devuelto con la lectura conservada no es un reembolso, es un descuento del cien por ciento, y preferimos rechazar lo segundo antes que fingir que es lo primero.'),
        LegalBlock.para('No descontamos por los capítulos ya escritos para ti, y no dividimos la compra en la parte que se ejecutó y la parte que no. Podríamos — sabemos exactamente qué capítulos existen —, pero cualquier cifra que fijáramos sobre cuánto de un libro has leído sería un número inventado por nosotros, y un número inventado es peor para este documento que una política que de vez en cuando nos cuesta una venta.'),
        LegalBlock.para('Pasados los catorce días, la lista de arriba es la política: nuestros fallos, sin discusión, y en lo demás una solicitud que decide Apple.'),
      ]),
      LegalSection('Un año no se entrega el primer día', [
        LegalBlock.para('El plan anual es un caso distinto en el derecho y en los hechos. No es una cosa entregada de una vez — son doce meses de acceso a todo, incluidos sistemas que se reescriben a medida que el cielo se mueve, y en su día diez nada parecido al todo ha sido ejecutado. Ningún consentimiento en una pantalla de pago acaba con tu derecho a desistir de un servicio que apenas ha empezado.'),
        LegalBlock.para('Así que: desiste de un plan dentro de los catorce días y lo que debe volver es la parte del periodo que no has usado, calculada sobre los días transcurridos, y el plan termina ahí en lugar de seguir corriendo. Le pedimos a Apple exactamente eso y cerramos el acceso de nuestro lado estén o no de acuerdo, porque la segunda mitad nos toca hacerla a nosotros.'),
      ]),
      LegalSection('El formulario modelo de desistimiento', [
        LegalBlock.para('No tienes que usar un formulario — basta un correo diciendo que has cambiado de opinión —, pero la ley exige ofrecer uno, así que aquí está:'),
        LegalBlock.para('A Pazl LLC, hello@pazl.ai — Por la presente comunico que desisto de mi contrato de suministro del siguiente contenido digital: [lo que compraste]. Pedido el [fecha]. Nombre del consumidor: [tu nombre]. Dirección de correo utilizada: [tu dirección]. Fecha: [hoy].'),
        LegalBlock.para('Dirigido a nosotros y no a Apple a propósito: el contrato por el contenido es con nosotros, el dinero lo tienen ellos, y no deberías tener que averiguar a cuál de los dos escribir. Nosotros lo reenviamos.'),
      ]),
    ],
  );

  static const subscriptionTerms = LegalDoc(
    lead: 'Qué se renueva, qué cuesta y cómo detenerlo — lo cual, para un plan comprado en esta app, ocurre en la propia pantalla de suscripciones de Apple y no en la nuestra. Donde algo es menos ordenado que eso, está escrito en lugar de omitido.',
    sections: [
      LegalSection('Qué se renueva', [
        LegalBlock.para('La lista de precios lleva dos planes recurrentes. El anual abre todo lo que Alma ha escrito para ti — cada sistema, cada capítulo — durante un año. El mensual abre solo los tres sistemas que se mueven con la fecha: los tránsitos, la revolución solar y la compatibilidad. Alquilar una carta natal sería cobrar renta por números que no han cambiado desde que naciste, así que el archivo no forma parte de él.'),
        LegalBlock.para('Cualquiera de los dos planes se renueva automáticamente en su propio ciclo hasta que lo detienes. El pago se carga a tu cuenta de Apple al confirmar la compra. Se renueva a menos que la renovación automática se desactive al menos 24 horas antes del final del periodo en curso, y la renovación se carga a tu cuenta dentro de las 24 horas previas al final de ese periodo.'),
        LegalBlock.para('Un pago abre un poco más que el periodo al que corresponde — treinta y un días para un mes, trescientos sesenta y cinco para un año, contados desde lo que ocurra más tarde: el día en que pagas o el día en que termina tu acceso actual. Los días extra no se acumulan; existen para que una renovación cobrada unas horas tarde nunca pueda dejarte fuera de un periodo que ya pagaste.'),
        LegalBlock.para('El precio es el que se muestra en la hoja de compra. No está impreso en esta página a propósito: Apple fija y cobra el precio para tu tienda en tu propia moneda con tu propio impuesto, y su número es el que es verdad.'),
      ]),
      LegalSection('Un plan se alquila, no se compra', [
        LegalBlock.para('El plan anual abre todo durante un año. No es una compra del archivo. Cuando el año termina y no has renovado, las lecturas que se escribieron para ti durante él se quedan en tu cuenta — nada se elimina —, pero dejan de abrirse, igual que cualquier capítulo que no has pagado.'),
        LegalBlock.para('Si lo que quieres es texto que sea tuyo pase lo que pase después, eso es el archivo, comprado una sola vez. Todo lo comprado de forma definitiva es permanente y no lo toca que un plan empiece, termine o se cancele.'),
      ]),
      LegalSection('Quién te avisa antes de que te cobren', [
        LegalBlock.para('Para un plan comprado en esta app, Apple. Apple envía el recibo y Apple envía el aviso de renovación, porque Apple es el vendedor y guarda el método de pago. Nosotros no enviamos ninguno de los dos, y una página nuestra que prometiera lo contrario sería una promesa que no podemos cumplir.'),
        LegalBlock.para('Para un plan comprado en nuestro sitio web con tarjeta, nosotros: tres días antes de una renovación sale un correo diciendo qué se va a cobrar, en la moneda en que se cobrará, y en qué fecha. No es un correo de marketing y no tiene enlace para darse de baja, porque una suscripción que has olvidado es el truco más viejo de esta industria y preferimos no estar en ese negocio.'),
      ]),
      LegalSection('El precio que aceptaste es el precio que se renueva', [
        LegalBlock.para('Nada en Alma puede cambiar lo que cuesta un plan existente. Un precio nuevo en la lista de precios se aplica a compras nuevas; tu plan sigue facturando al precio con el que se abrió. Apple además te pide confirmar cualquier subida de precio antes de que entre en vigor, y cancelará la suscripción antes que cobrarte el precio nuevo si no lo confirmas.'),
      ]),
      LegalSection('Cancelar', [
        LegalBlock.para('Una suscripción comprada en esta app se cancela en la pantalla de suscripciones de Apple: Ajustes → Plan → Gestionar esta suscripción en el App Store, que la abre directamente. O, fuera de Alma: la app Ajustes → tu nombre → Suscripciones.'),
        LegalBlock.para('No podemos cancelarla por ti, y no vamos a fingir que sí. Apple guarda el método de pago; una marca de nuestro lado que diga «cancelada» no impide que se cobre una tarjeta, y quien se lo creyera se enteraría en un extracto. Si nos pides cancelar, la app dice exactamente esto y te lleva a la pantalla correcta en lugar de escribir nada.'),
        LegalBlock.para('Un plan comprado en nuestro sitio web con tarjeta es distinto, y ahí los dos toques son reales: Ajustes → Plan → Cancelar suscripción → Confirmar. Sin correo que escribir, sin motivo que dar, sin llamada, y sin ninguna oferta interponiéndose entre ti y el segundo toque.'),
        LegalBlock.para('Cancelar no es un reembolso del periodo en el que estás, y nada se te quita en el momento en que cancelas. Qué es y qué no es reembolsable — incluidos los catorce días en los que puedes desistir de un plan por completo — está en la página de reembolsos.'),
      ]),
      LegalSection('Qué conservas después', [
        LegalBlock.para('Todo lo que compraste de forma definitiva. Un sistema, o el archivo entero, comprado como compra única es permanente y no se ve afectado por el fin de una suscripción.'),
        LegalBlock.para('Tu cuenta, tu carta y tus conversaciones se quedan como están. Terminar una suscripción no es eliminar una cuenta — eso es un acto aparte y deliberado en Ajustes.'),
      ]),
      LegalSection('Primero una lectura, el resto después', [
        LegalBlock.para('Si compras un solo sistema y luego decides, dentro de los treinta días, que quieres el resto, el resto del archivo se te ofrece a su precio menos lo que ya pagaste por esa lectura. Nada que reclamar, nada que reembolsar primero — el precio reducido es simplemente lo que se te cobra.'),
        LegalBlock.para('Se ofrece mientras tienes un solo sistema y nada más amplio. Pasados los treinta días la oferta desaparece y la lectura que compraste sigue siendo tuya. La reducción se aplica al archivo; un plan tiene su precio propio.'),
      ]),
      LegalSection('Si un pago falla', [
        LegalBlock.para('No se te quita nada. Una tarjeta rechazada suele ser una tarjeta que funciona al reintentar, y Apple reintenta durante un tiempo — la persona a la que le falló el pago es la última que debería quedarse fuera mientras se resuelve.'),
        LegalBlock.para('Si los reintentos nunca tienen éxito, el plan simplemente no se extiende: tu acceso corre hasta el final del periodo que ya pagaste y se detiene ahí. Todo lo que compraste de forma definitiva queda intacto ante todo esto. Suscribirte de nuevo inicia un periodo nuevo desde el día en que se paga.'),
      ]),
      LegalSection('Facturas e impuestos', [
        LegalBlock.para('Apple es el vendedor de registro de todo lo comprado en esta app. Ellos emiten el recibo, ellos gestionan el IVA, el GST y el impuesto sobre las ventas donde aplican, y su recibo es el documento que quiere tu contador. Está en reportaproblem.apple.com y en el correo que Apple te envió.'),
      ]),
    ],
  );

  static const imprint = LegalDoc(
    lead: 'Quién está detrás de Alma, en la forma que piden el Telemediengesetz §5 de Alemania y sus equivalentes de Italia y Francia. Todo lo que aún no se ha facilitado está marcado como pendiente en lugar de rellenado con algo plausible.',
    sections: [
      LegalSection('Operador', [
        LegalBlock.fact('Empresa', 'Pazl LLC'),
        LegalBlock.fact('Forma', 'Limited liability company'),
        LegalBlock.fact('Jurisdicción', 'Wyoming, United States'),
        LegalBlock.fact('Dirección registrada', '30 N Gould St Ste R, Sheridan, Wyoming 82801'),
        LegalBlock.fact('Número de registro', '2026-002034771'),
        LegalBlock.fact('Representada por', 'Anatolii Mikhailov'),
      ]),
      LegalSection('Contacto', [
        LegalBlock.fact('Correo electrónico', 'hello@pazl.ai'),
        LegalBlock.para('Lo lee una persona. No hay número de teléfono, y antes que imprimir uno que llegue a un contestador, esta página lo dice.'),
      ]),
      LegalSection('Ventas en esta app', [
        LegalBlock.fact('Vendedor de registro', 'Apple'),
        LegalBlock.para('Todo lo comprado dentro de esta app lo vende Apple, que cobra el pago, emite el recibo y remite el impuesto. La entidad en tu extracto depende de tu tienda — Apple Inc., Apple Distribution International Ltd. o iTunes K.K. — y el recibo que Apple te envía nombra a la que te cobró.'),
      ]),
      LegalSection('Impuesto sobre el valor añadido', [
        LegalBlock.factBlank('Identificación de IVA', 'VAT ID'),
        LegalBlock.para('Alma se vende a través de Apple, que responde del IVA y el GST donde aplican. Un número de IVA propio está en trámite de registro.'),
      ]),
      LegalSection('Resolución de disputas en línea', [
        LegalBlock.para('La plataforma ODR de la Comisión Europea cerró en julio de 2025 y no se enlaza aquí, porque un enlace a una plataforma que ya no existe es peor que ningún enlace. No estamos obligados a usar, ni nos comprometemos a usar, un organismo alternativo de resolución de disputas. Escribe a hello@pazl.ai y responderá una persona.'),
      ]),
      LegalSection('Responsable del contenido', [
        LegalBlock.fact('Según el §18 (2) MStV', 'Anatolii Mikhailov · 30 N Gould St Ste R, Sheridan, Wyoming 82801'),
      ]),
    ],
  );
}
