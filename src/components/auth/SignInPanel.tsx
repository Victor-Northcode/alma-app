"use client";

/**
 * Signing in, for real.
 *
 * Until now every one of these buttons called `onNext()` — the journey
 * advanced and nobody was signed in. What it looked like and what it did were
 * different things, which is the one failure this product cannot afford
 * anywhere near the moment a person decides to trust it with their birth
 * data.
 *
 * Three routes in, and only one of them is always available:
 *
 * **The link in an email** works with no configuration beyond a mail
 * provider, and it is the honest default. There is no password anywhere in
 * Alma — nothing to leak, nothing to reset, nothing to get wrong.
 *
 * **Google and Apple** are shown only when a client id is actually
 * configured. A provider button that cannot work is worse than no button:
 * it is the most reassuring thing on the panel and it fails after the tap.
 *
 * The guest's work survives all three. The token in the browser already
 * identifies an account with a chart in it; signing in attaches an identity
 * to that same row, or folds it into one the person already had. Nothing is
 * copied and nothing is lost — see `accounts.sign_in` on the backend.
 */

import Script from "next/script";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, isOk, writeToken, type Failure } from "@/lib/api";
import { looksLikeEmail } from "@/lib/email";
import { useLocale } from "@/lib/i18n/provider";
import type { Locale } from "@/lib/i18n";

/**
 * Set only when the deployment has the provider configured.
 *
 * Apple is not here, and the button that used to be was worse than its
 * absence: its handler was `() => {}`, so on any deployment that set
 * `NEXT_PUBLIC_APPLE_CLIENT_ID` the most reassuring control on the panel did
 * nothing at all when tapped. Sign in with Apple is a real route in both
 * mobile apps, which mint the identity token natively and post it to
 * `/v1/auth/apple`; the browser has no such token, and the web flow needed to
 * get one is work nobody has done. The endpoint stays on the backend for the
 * apps. Nothing on the web pretends to be it.
 */
const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";

/**
 * Copy lives here rather than in the dictionary only because two other
 * changes were editing the locale files at the same time. It belongs in
 * `src/lib/i18n/` and should move there — the shape is identical.
 */
const COPY: Record<Locale, Record<string, string>> = {
  en: {
    email: "Your email",
    send: "Email me a link",
    sending: "Sending…",
    sent: "Check your inbox — the link works once and expires in 20 minutes.",
    google: "Continue with Google",
    or: "or",
    bad: "That does not look like an email address.",
    failed: "The link could not be sent. Try again in a moment.",
    keeps: "Your chart, your readings and your questions stay exactly as they are.",
  },
  es: {
    email: "Tu correo",
    send: "Envíame un enlace",
    sending: "Enviando…",
    sent: "Mira tu bandeja — el enlace funciona una vez y caduca en 20 minutos.",
    google: "Continuar con Google",
    or: "o",
    bad: "Eso no parece un correo electrónico.",
    failed: "No se ha podido enviar el enlace. Inténtalo en un momento.",
    keeps: "Tu carta, tus lecturas y tus preguntas se quedan tal como están.",
  },
  de: {
    email: "Deine E-Mail",
    send: "Schick mir einen Link",
    sending: "Wird gesendet…",
    sent: "Sieh in dein Postfach — der Link funktioniert einmal und läuft in 20 Minuten ab.",
    google: "Weiter mit Google",
    or: "oder",
    bad: "Das sieht nicht nach einer E-Mail-Adresse aus.",
    failed: "Der Link konnte nicht gesendet werden. Versuch es gleich noch einmal.",
    keeps: "Dein Horoskop, deine Lesungen und deine Fragen bleiben genau so, wie sie sind.",
  },
  it: {
    email: "La tua email",
    send: "Mandami un link",
    sending: "Invio…",
    sent: "Guarda la posta — il link funziona una volta e scade tra 20 minuti.",
    google: "Continua con Google",
    or: "oppure",
    bad: "Questo non sembra un indirizzo email.",
    failed: "Non è stato possibile inviare il link. Riprova fra un momento.",
    keeps: "Il tuo tema, le tue letture e le tue domande restano esattamente come sono.",
  },
  fr: {
    email: "Ton e-mail",
    send: "Envoie-moi un lien",
    sending: "Envoi…",
    sent: "Regarde ta boîte — le lien fonctionne une fois et expire dans 20 minutes.",
    google: "Continuer avec Google",
    or: "ou",
    bad: "Cela ne ressemble pas à une adresse e-mail.",
    failed: "Le lien n'a pas pu être envoyé. Réessaie dans un instant.",
    keeps: "Ton thème, tes lectures et tes questions restent exactement tels quels.",
  },
  "pt-BR": {
    email: "Seu e-mail",
    send: "Me manda um link",
    sending: "Enviando…",
    sent: "Olhe sua caixa de entrada — o link funciona uma vez e expira em 20 minutos.",
    google: "Continuar com Google",
    or: "ou",
    bad: "Isso não parece um endereço de e-mail.",
    failed: "Não foi possível enviar o link. Tente de novo daqui a pouco.",
    keeps: "Seu mapa, suas leituras e suas perguntas ficam exatamente como estão.",
  },
};

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: { client_id: string; callback: (r: { credential: string }) => void }) => void;
          renderButton: (el: HTMLElement, opts: Record<string, unknown>) => void;
        };
      };
    };
  }
}

/**
 * `onLinkSent` is not a duplicate of `onSignedIn`, and the difference is the
 * whole reason it exists: in production there is no debug token, so the common
 * ending of this panel is *a letter is in flight and nobody is signed in yet*.
 * The handoff at the end of the journey has a different, truer thing to say to
 * that person than to a guest who skipped the step — the link they have not
 * clicked yet is exactly what will carry their chart onto an account — and it
 * cannot know unless this tells it.
 */
export function SignInPanel({
  onSignedIn,
  onLinkSent,
}: {
  onSignedIn?: () => void;
  onLinkSent?: (email: string) => void;
}) {
  const { locale } = useLocale();
  const copy = COPY[locale] ?? COPY.en;

  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [message, setMessage] = useState("");
  // Whether the Google Identity script has finished loading. The init effect
  // below used to depend only on `withGoogle` and bail if `window.google` was
  // not there yet — but `<Script afterInteractive>` resolves *after* mount, so
  // on the common ordering the effect ran once, found no `window.google`, and
  // never ran again: the button simply never appeared. Flipping this from the
  // script's own `onReady` re-runs the effect at the moment the API exists.
  const [gsiReady, setGsiReady] = useState(false);
  // Синхронный замок от двойной отправки. `disabled={state==="sending"}` на
  // кнопке применяется только после ре-рендера React, а три клика в один тик
  // успевают вызвать `submit` до него — замерено аудитом 20.08.2026: три
  // синхронных клика дали три запроса magic-link. Проверять `state` в замыкании
  // не помогло бы: для тех же синхронных вызовов оно ещё "idle". Ref ставится
  // до первого `await` и потому виден следующему вызову в том же такте.
  const sendingRef = useRef(false);

  const submit = useCallback(async () => {
    if (sendingRef.current) return;
    const address = email.trim().toLowerCase();
    // One shared rule, in `lib/email.ts` — a second copy of "what looks like
    // an email address" is a copy that drifts, and it drifts towards being
    // stricter, which costs a sign-in.
    if (!looksLikeEmail(address)) {
      setState("error");
      setMessage(copy.bad);
      return;
    }

    sendingRef.current = true;
    setState("sending");
    try {
      const result = await api.requestMagicLink(address, locale);
      if (!isOk(result)) {
        setState("error");
        setMessage(copy.failed);
        return;
      }

      // In development there is no mail provider, so the backend hands the link
      // back instead of pretending it sent one. Production never reaches this.
      if (result.data.debug_token) {
        const consumed = await api.consumeMagicLink(result.data.debug_token);
        if (isOk(consumed)) {
          writeToken(consumed.data.token);
          onSignedIn?.();
          return;
        }
      }

      setState("sent");
      setMessage(copy.sent);
      onLinkSent?.(address);
    } finally {
      // Снять замок в любом исходе, кроме уже случившегося входа: ошибка и
      // «письмо отправлено» — оба состояния, из которых человек вправе
      // повторить, а вход размонтирует панель и повтор невозможен.
      sendingRef.current = false;
    }
  }, [copy, email, locale, onSignedIn, onLinkSent]);

  const withGoogle = useCallback(
    async (credential: string) => {
      const result = await api.googleSignIn(credential);
      if (isOk(result)) {
        writeToken(result.data.token);
        onSignedIn?.();
      } else {
        setState("error");
        setMessage(describe(result, copy));
      }
    },
    [copy, onSignedIn],
  );

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !gsiReady || !window.google) return;
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: (r) => void withGoogle(r.credential),
    });
    const host = document.getElementById("alma-google-button");
    if (host) {
      window.google.accounts.id.renderButton(host, {
        theme: "outline",
        size: "large",
        width: 320,
        text: "continue_with",
      });
    }
  }, [withGoogle, gsiReady]);

  if (state === "sent") {
    return (
      <div className="signin">
        <p className="signin-sent">{message}</p>
      </div>
    );
  }

  return (
    <div className="signin">
      {GOOGLE_CLIENT_ID && (
        <>
          <Script
            src="https://accounts.google.com/gsi/client"
            strategy="afterInteractive"
            onReady={() => setGsiReady(true)}
          />
          <div id="alma-google-button" className="signin-provider" />
        </>
      )}
      {GOOGLE_CLIENT_ID && <div className="signin-or">{copy.or}</div>}

      <input
        className="text-input"
        type="email"
        inputMode="email"
        autoComplete="email"
        value={email}
        onChange={(e) => {
          setEmail(e.target.value);
          if (state === "error") setState("idle");
        }}
        onKeyDown={(e) => e.key === "Enter" && void submit()}
        placeholder={copy.email}
        aria-label={copy.email}
      />

      <button
        type="button"
        className="btn btn-gold btn-block"
        onClick={() => void submit()}
        disabled={state === "sending"}
      >
        {state === "sending" ? copy.sending : copy.send}
      </button>

      {state === "error" && (
        <p className="signin-error" role="alert">
          {message}
        </p>
      )}
      <p className="signin-note">{copy.keeps}</p>
    </div>
  );
}

function describe(failure: Failure, copy: Record<string, string>): string {
  return failure.kind === "offline" ? copy.failed : failure.message || copy.failed;
}
