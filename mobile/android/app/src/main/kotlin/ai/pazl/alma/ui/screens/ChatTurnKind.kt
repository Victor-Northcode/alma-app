package ai.pazl.alma.ui.screens

import ai.pazl.alma.data.dto.ChatMessageDto

/**
 * What Alma just did, as opposed to what she found.
 *
 * ## The bug this type exists to make impossible
 *
 * A reply used to carry one boolean, `answered_from_chart`, and both clients
 * drew "Not from your chart" whenever it was false. The field turned out to
 * carry two unrelated meanings — *"I looked at your chart and it does not speak
 * to this"* and *"this reply does not assert anything about you at all"* — so a
 * greeting, which is the second, was labelled as though it were the first. A
 * person who typed "hello" was told, under their own hello, that it was not in
 * their chart. `docs/CONVERSATION.md` §5.4 has the four measured turns where
 * the flag and the citations flatly contradict one another.
 *
 * `turn_kind` names the **shape of the turn** rather than the outcome of a
 * search. The rules agent owns the values; this enum owns what each looks like.
 *
 * ## Unknown values are not an error
 *
 * A branch of the taxonomy arriving from a newer backend must degrade to "a
 * reply", never to a crash in the middle of a conversation. That is why the
 * wire field is a `String?` on [ChatMessageDto] and why [of] never throws.
 */
internal enum class ChatTurnKind {

    /**
     * A claim about this person, read from their placements. The one kind that
     * must show its citations — that is the whole difference between Alma and a
     * chatbot wearing an astrologer's hat.
     */
    Reading,

    /**
     * She read the chart and it genuinely has nothing to say about this. She has
     * already said so in words; the screen adds one quiet sentence so a general
     * answer is not mistaken for a reading.
     */
    ChartSilent,

    /**
     * A turn that asserts nothing about anybody: a greeting, a thank-you, a
     * question about what she can do, a message in a language we do not write
     * yet. Taxonomy group A and most of E. **Never labelled**, because there is
     * no claim here to qualify.
     */
    Conversation,

    /**
     * Distress, a medical question — anything in taxonomy group D. Drawn as
     * prose with nothing decorating it: somebody who has just said they feel
     * awful should not be handed a row of metadata.
     */
    Care,

    ;

    /**
     * Whether the "read from" line belongs under this answer. Citations show
     * wherever they exist — a [Care] reply that cited a placement still made a
     * claim — with one exception: [Conversation] asserts nothing, so anything it
     * happened to cite is decoration.
     */
    val showsCitations: Boolean get() = this != Conversation

    val showsChartSilentNote: Boolean get() = this == ChartSilent

    internal companion object {

        /**
         * What to draw, from whatever the server actually sent.
         *
         * **The legacy branch is the interesting one**, because the old payload
         * cannot tell a greeting from a silent chart — that is exactly the
         * ambiguity `turn_kind` was added to remove. With citations it is a
         * reading. Without them the two candidates are "she greeted you", where
         * the label is a lie, and "the chart is silent", where `CHAT_RULES`
         * already requires her to have said so in her own sentence, so the label
         * is a duplicate. Choosing [Conversation] trades a redundancy for a
         * falsehood, which is the right way round; keeping [ChartSilent] as the
         * fallback is what shipped the screenshot in the bug report.
         *
         * So: **the honest footnote renders only when the server names the
         * kind.** Silence on the wire buys silence on the screen.
         */
        fun of(message: ChatMessageDto): ChatTurnKind = when (message.turnKind) {
            "reading" -> Reading
            "chart_silent" -> ChartSilent
            "conversation" -> Conversation
            "care" -> Care
            // `answeredFromChart` is deliberately not consulted here.
            else -> if (message.citedFactors.isNotEmpty()) Reading else Conversation
        }
    }
}
