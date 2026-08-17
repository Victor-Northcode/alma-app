package ai.pazl.alma.ui.screens

import ai.pazl.alma.ui.components.Hairline
import ai.pazl.alma.ui.sky.NightSky
import ai.pazl.alma.ui.sky.SkyConfig
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

/**
 * One of the five legal documents, read inside the app.
 *
 * Reached from Settings → DATA & LEGAL. Those five rows used to hand the URL to
 * a browser — `https://alma.pazl.ai/terms` and its four siblings — and the host
 * does not resolve, so every one of them opened an error page. Play requires a
 * working privacy policy from an app that creates an account, and this one
 * creates one silently on first launch.
 *
 * The text is in the binary — see [LegalText] for why, and for what is
 * deliberately still missing from it — so this screen has no state, no loading
 * and no failure. It is the only screen in the app that cannot fail to open, and
 * that is the point of it.
 */
@Composable
fun LegalScreen(document: LegalDocument, onBack: () -> Unit) {
    val doc = LegalText.document(document)

    NightSky(config = SkyConfig.Reader) {
        CabinetPage {
            // The arrow belongs in the title row rather than above it, as on
            // every other pushed screen in the cabinet. Settings is the only
            // door to these five, and without a drawn back the edge swipe would
            // be the whole way out.
            ScreenTitle(stringResource(document.title), onBack = onBack)

            Spacer(Modifier.height(10.dp))
            Text(
                // Not translated, and neither is the date. Both belong to the
                // document rather than to the interface, and the document is
                // English until it has been read by a lawyer in each country.
                text = "Last updated ${LegalText.UPDATED}",
                style = AlmaTheme.type.meta,
            )
            // The admission comes before the document, not under it.
            Text(
                text = LegalText.PREAMBLE,
                style = AlmaTheme.type.meta,
                modifier = Modifier.padding(top = 6.dp),
            )

            Spacer(Modifier.height(16.dp))
            Hairline()
            Spacer(Modifier.height(16.dp))

            Text(text = doc.lead, style = AlmaTheme.type.almaVoice)

            doc.sections.forEachIndexed { index, section ->
                Spacer(Modifier.height(28.dp))
                // "1 · WHAT ALMA IS" — numbered, and across the full width
                // rather than through `RuledLabel`.
                //
                // The number is not a translated string: it is the ordinal of
                // the section, and it is what a document is cited by in an
                // email. The rule is dropped because `RuledLabel` gives the
                // hairline the rest of the row, and these headings are
                // sentences — "THE 14-DAY WITHDRAWAL RIGHT, WHICH WE DO NOT
                // TREAT AS WAIVED" leaves the line no room and wraps into four
                // lines against the left edge. The port made the same choice
                // for the same reason.
                Text(
                    text = "${index + 1} · ${section.title}".uppercase(),
                    style = AlmaTheme.type.overline,
                    // TalkBack reads these as headings, so the document can be
                    // navigated by section instead of one paragraph at a time.
                    modifier = Modifier.semantics { heading() },
                )
                Spacer(Modifier.height(6.dp))
                section.blocks.forEach { Block(it) }
            }

            Spacer(Modifier.height(28.dp))
            Hairline()
            Text(
                text = LegalText.FOOTER,
                style = AlmaTheme.type.meta,
                modifier = Modifier.padding(top = 14.dp),
            )
            Text(
                text = "${LegalText.OPERATOR} · Wyoming, United States",
                style = AlmaTheme.type.meta,
                modifier = Modifier.padding(top = 6.dp),
            )
            Spacer(Modifier.height(36.dp))
        }
    }
}

/** A paragraph, a list, a fact, or a gap where a fact will go. */
@Composable
private fun Block(block: LegalBlock) {
    when (block) {
        is LegalBlock.Para -> Text(
            text = block.text,
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.padding(vertical = 6.dp),
        )

        is LegalBlock.Points -> Column(Modifier.padding(vertical = 6.dp)) {
            block.items.forEach { item ->
                Row(
                    modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
                    verticalAlignment = Alignment.Top,
                ) {
                    // The same gold interpunct the paywall's honesty plate uses.
                    // Not a filled disc: a bullet list is what a settings app
                    // does, and nothing else in this product has one.
                    Text(text = "·", style = AlmaTheme.type.positions)
                    Spacer(Modifier.width(10.dp))
                    Text(text = item, style = MaterialTheme.typography.bodyLarge)
                }
            }
        }

        is LegalBlock.Fact -> FactRow(block.label, block.value)

        // Square brackets and the warning colour, on purpose. A registered
        // address nobody has given us has to look unfinished on the screen, or
        // it never gets finished.
        is LegalBlock.FactBlank -> FactRow(block.label, "[${block.value}]", missing = true)

        is LegalBlock.Blank -> Text(
            text = "[${block.what}]",
            style = MaterialTheme.typography.bodyLarge.copy(
                color = AlmaPalette.Disagree.copy(alpha = 0.8f),
            ),
            modifier = Modifier.padding(vertical = 2.dp),
        )
    }
}

@Composable
private fun FactRow(label: String, value: String, missing: Boolean = false) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 7.dp),
        verticalAlignment = Alignment.Top,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        // 4/6 rather than an even split, as everywhere else a label sits beside
        // a value: "Merchant of record" is two words and "Apple Distribution
        // International Ltd." is not.
        Text(
            text = label,
            style = AlmaTheme.type.meta,
            modifier = Modifier.weight(4f),
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyLarge.copy(
                color = if (missing) AlmaPalette.Disagree.copy(alpha = 0.8f) else AlmaPalette.Body,
            ),
            textAlign = TextAlign.End,
            modifier = Modifier.weight(6f),
        )
    }
}
