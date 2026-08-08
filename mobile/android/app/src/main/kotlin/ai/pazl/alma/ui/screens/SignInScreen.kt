package ai.pazl.alma.ui.screens

import ai.pazl.alma.R
import ai.pazl.alma.core.AppContainer
import ai.pazl.alma.core.SessionHolder
import ai.pazl.alma.data.AlmaClient
import ai.pazl.alma.data.ApiResult
import ai.pazl.alma.ui.components.AlmaWordmark
import ai.pazl.alma.ui.components.GoldButton
import ai.pazl.alma.ui.components.Hairline
import ai.pazl.alma.ui.components.QuietButton
import androidx.compose.ui.platform.LocalContext
import ai.pazl.alma.ui.sky.NightSky
import ai.pazl.alma.ui.sky.SkyConfig
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

/**
 * Signing in, which on Alma means attaching an address to an account that
 * already exists.
 *
 * ## What it is not
 *
 * It is not registration and there is no password — there has never been one.
 * The account was created on the first request the app made, before this screen
 * existed, and everything in it (a birth chart, a purchase, a conversation)
 * belongs to it already. `POST /v1/auth/magic-link/consume` is sent *with* the
 * current token, so the identity is attached to this row rather than swapping
 * it for another one. The copy says so, because a person who believes signing
 * in might lose what they have will not do it.
 *
 * ## "Continue with Google", gated on configuration
 *
 * The token comes from the platform's Credential Manager, and the button only
 * exists while `google_web_client_id` is filled in — a sign-in button that
 * opens an error would be worse than no button. The id token is never decoded
 * here; `alma/auth/providers.py` checks the signature and the audience.
 *
 * ## How the link gets back into the app
 *
 * The email carries `https://alma.pazl.ai/sign-in?token=…`, and
 * `AndroidManifest.xml` claims that path as an App Link. `MainActivity` reads
 * the token off the intent and hands it to [SignInViewModel.consume]. Until
 * `assetlinks.json` is published on the domain Android will show a chooser
 * rather than opening the app directly — which still works, and is the honest
 * state to ship in rather than a code the person has to copy by hand.
 */
@Composable
fun SignInScreen(
    container: AppContainer,
    onDone: () -> Unit,
) {
    val vm: SignInViewModel = viewModel { SignInViewModel(container.client, container.session) }
    val state by vm.state.collectAsStateWithLifecycle()

    // Leaves on its own once the identity is attached. Nothing to tap: the
    // person asked to sign in and it happened, and a confirmation screen with
    // one button on it is a step that exists to be dismissed.
    LaunchedEffect(state.signedIn) {
        if (state.signedIn) onDone()
    }

    NightSky(config = SkyConfig(seed = 6, motes = 1, comet = false)) {
        SignInBody(state, vm::send, vm::signInWithGoogle, onDone)
    }
}

@Composable
private fun BoxScope.SignInBody(
    state: SignInState,
    onSend: (String) -> Unit,
    onGoogle: (android.content.Context) -> Unit,
    onClose: () -> Unit,
) {
    var email by remember { mutableStateOf("") }
    val hint = stringResource(R.string.signin_email)

    Column(
        modifier = Modifier
            .fillMaxSize()
            .widthIn(max = 460.dp)
            .align(Alignment.TopCenter)
            .windowInsetsPadding(WindowInsets.safeDrawing)
            .imePadding()
            .padding(horizontal = 22.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp, Alignment.CenterVertically),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        AlmaWordmark()

        Text(
            text = stringResource(R.string.signin_lead),
            style = AlmaTheme.type.almaVoice,
        )

        if (state.sent) {
            Text(text = stringResource(R.string.signin_sent), style = AlmaTheme.type.meta)
        } else {
            GoogleButton(state, onGoogle)

            Column(Modifier.fillMaxWidth()) {
                BasicTextField(
                    value = email,
                    onValueChange = { email = it },
                    singleLine = true,
                    textStyle = AlmaTheme.type.meta.copy(color = AlmaPalette.Body, fontSize = 16.sp),
                    cursorBrush = SolidColor(AlmaPalette.Gold),
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Email,
                        imeAction = ImeAction.Done,
                    ),
                    modifier = Modifier.fillMaxWidth().padding(vertical = 10.dp),
                    decorationBox = { field ->
                        Column {
                            if (email.isEmpty()) {
                                Text(
                                    text = hint,
                                    style = AlmaTheme.type.meta.copy(fontSize = 16.sp),
                                    color = AlmaPalette.Muted3,
                                )
                            }
                            field()
                            Spacer(Modifier.height(8.dp))
                            Hairline()
                        }
                    },
                )
                Spacer(Modifier.height(18.dp))
                GoldButton(
                    text = stringResource(R.string.signin_send),
                    onClick = { onSend(email) },
                    // The check is deliberately the crudest one that catches a
                    // typo: the server does not say whether an address exists —
                    // that would turn this route into an account enumerator —
                    // so the app has to catch "sofia@" before it is sent, and
                    // must not pretend to catch more than that.
                    enabled = email.contains('@') && email.substringAfterLast('@').contains('.') &&
                        !state.working,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }

        if (state.invalidEmail) {
            Text(
                text = stringResource(R.string.signin_invalid_email),
                style = AlmaTheme.type.meta,
                color = AlmaPalette.Disagree,
            )
        }
        if (state.failed) {
            Text(
                text = stringResource(R.string.signin_failed),
                style = AlmaTheme.type.meta,
                color = AlmaPalette.Disagree,
            )
        }

        Text(
            text = stringResource(R.string.signin_no_password),
            style = AlmaTheme.type.meta,
            color = AlmaPalette.Muted3,
        )

        QuietButton(
            text = stringResource(R.string.nav_back),
            onClick = onClose,
            contentColor = AlmaPalette.Muted,
        )
    }
}

/* ── state ─────────────────────────────────────────────────────────────── */

@Immutable
data class SignInState(
    val working: Boolean = false,
    /** The letter went out — or the server declined to say, which is the same screen. */
    val sent: Boolean = false,
    val failed: Boolean = false,
    val invalidEmail: Boolean = false,
    val signedIn: Boolean = false,
)

class SignInViewModel(
    private val client: AlmaClient,
    private val session: SessionHolder,
) : ViewModel() {

    private val _state = MutableStateFlow(SignInState())
    val state: StateFlow<SignInState> = _state.asStateFlow()

    /**
     * Ask for a link.
     *
     * The answer is 202 whether or not the address is known, on purpose — a
     * route that said "no such account" would be an account enumerator — so
     * there is exactly one thing this screen can say afterwards, and it says it.
     */
    /**
     * Sign in with Google, through Credential Manager.
     *
     * The activity context matters: Credential Manager presents its own sheet
     * and needs the window it will sit over. Everything failure-shaped lands
     * on the same `failed` flag the link path uses — a cancellation lands on
     * nothing at all, because it is the most common outcome of the button.
     */
    fun signInWithGoogle(context: android.content.Context) {
        val webClientId = context.getString(R.string.google_web_client_id)
        if (webClientId.isBlank()) return
        viewModelScope.launch {
            _state.value = SignInState(working = true)
            try {
                val manager = androidx.credentials.CredentialManager.create(context)
                val option = com.google.android.libraries.identity.googleid
                    .GetGoogleIdOption.Builder()
                    .setServerClientId(webClientId)
                    .setFilterByAuthorizedAccounts(false)
                    .build()
                val request = androidx.credentials.GetCredentialRequest.Builder()
                    .addCredentialOption(option)
                    .build()
                val result = manager.getCredential(context, request)
                val credential = com.google.android.libraries.identity.googleid
                    .GoogleIdTokenCredential.createFrom(result.credential.data)
                _state.value = when (val answer = client.signInWithGoogle(credential.idToken)) {
                    is ApiResult.Ok -> {
                        session.onSignedIn(answer.data)
                        SignInState(signedIn = true)
                    }
                    is ApiResult.Err -> SignInState(failed = true)
                }
            } catch (cancelled: androidx.credentials.exceptions.GetCredentialCancellationException) {
                _state.value = SignInState()
            } catch (failed: Exception) {
                _state.value = SignInState(failed = true)
            }
        }
    }

    fun send(email: String) {
        val address = email.trim()
        if (!address.contains('@')) {
            _state.value = SignInState(invalidEmail = true)
            return
        }
        viewModelScope.launch {
            _state.value = SignInState(working = true)
            val locale = session.state.first { it.ready }.locale
            _state.value = when (client.requestMagicLink(address, locale)) {
                is ApiResult.Ok -> SignInState(sent = true)
                is ApiResult.Err -> SignInState(failed = true)
            }
        }
    }

    // Redeeming the emailed token is **not** here. It lives on
    // `SessionHolder.signInWithLink`, because `MainActivity` is what receives
    // the App Link intent and the link can arrive with this screen closed —
    // which is the ordinary case, since the person left the app to open their
    // mail. A `consume` on this ViewModel would be a sign-in that works only if
    // you have not navigated away.
}

/**
 * The Google door, only while an OAuth client is configured.
 */
@Composable
private fun GoogleButton(state: SignInState, onGoogle: (android.content.Context) -> Unit) {
    val context = LocalContext.current
    val configured = stringResource(R.string.google_web_client_id).isNotBlank()
    if (!configured) return
    QuietButton(
        text = stringResource(R.string.signin_google),
        onClick = { onGoogle(context) },
        enabled = !state.working,
        contentColor = AlmaPalette.GoldBright,
    )
}
