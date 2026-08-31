"use client";

/**
 * Where the link in the email lands.
 *
 * The one page on this website that another program depends on. `alma/mail.py`
 * builds every sign-in letter as `{web_url}/sign-in?token=…`, and the Android
 * manifest claims that exact path as an app link — so on a phone with the app
 * installed the letter opens the app, and everywhere else it opens this. Both
 * apps ask for their sign-in link through the same endpoint, which means this
 * page answers for people who have never visited the website at all: an
 * unverified app link, a desktop inbox, a mail client that strips the handoff.
 * It is not a leftover of the cabinet and it does not go with it.
 *
 * The whole screen is one decision and it has to be made before anything is
 * drawn: consume the token, or explain why it did not work. There are exactly
 * three ways it fails and each deserves a different sentence — a link that was
 * already used, a link that expired, and a link that was never ours. Saying
 * "something went wrong" to all three would leave someone re-clicking a dead
 * link forever.
 *
 * Consumed exactly once. The backend marks the token used before it touches
 * the account, so a double-tap or a mail client's link prefetch cannot produce
 * two sign-ins — but this guard stops the second request from ever being
 * sent, which is what keeps the *second* attempt from showing "already used"
 * to somebody who only clicked once.
 */

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { Star } from "@/components/brand/Star";
import { Starfield } from "@/components/sky/Sky";
import { SignInPanel } from "@/components/auth/SignInPanel";
import { GetTheApp } from "@/components/handoff/GetTheApp";
import { LanguagePicker } from "@/components/landing/LanguagePicker";
import { api, isOk, writeToken } from "@/lib/api";
import { useLocale } from "@/lib/i18n/provider";
import type { Locale } from "@/lib/i18n";

const COPY: Record<Locale, Record<string, string>> = {
  en: {
    working: "Signing you in…",
    welcome: "You are in.",
    used: "That link has already been used. Ask for a fresh one.",
    expired: "That link has expired. Ask for a fresh one.",
    invalid: "That link is not valid. Ask for a fresh one.",
    title: "Sign in",
    lead: "No password, ever. A link in your inbox is the whole of it.",
  },
  es: {
    working: "Entrando…",
    welcome: "Ya estás dentro.",
    used: "Ese enlace ya se ha usado. Pide uno nuevo.",
    expired: "Ese enlace ha caducado. Pide uno nuevo.",
    invalid: "Ese enlace no es válido. Pide uno nuevo.",
    title: "Entrar",
    lead: "Nunca una contraseña. Un enlace en tu correo y ya está.",
  },
  de: {
    working: "Du wirst angemeldet…",
    welcome: "Du bist drin.",
    used: "Dieser Link wurde bereits benutzt. Fordere einen neuen an.",
    expired: "Dieser Link ist abgelaufen. Fordere einen neuen an.",
    invalid: "Dieser Link ist ungültig. Fordere einen neuen an.",
    title: "Anmelden",
    lead: "Niemals ein Passwort. Ein Link im Postfach, mehr ist es nicht.",
  },
  it: {
    working: "Accesso in corso…",
    welcome: "Sei dentro.",
    used: "Quel link è già stato usato. Chiedine uno nuovo.",
    expired: "Quel link è scaduto. Chiedine uno nuovo.",
    invalid: "Quel link non è valido. Chiedine uno nuovo.",
    title: "Accedi",
    lead: "Mai una password. Un link nella posta, tutto qui.",
  },
  fr: {
    working: "Connexion…",
    welcome: "Tu es connecté.",
    used: "Ce lien a déjà été utilisé. Demandes-en un nouveau.",
    expired: "Ce lien a expiré. Demandes-en un nouveau.",
    invalid: "Ce lien n'est pas valide. Demandes-en un nouveau.",
    title: "Se connecter",
    lead: "Jamais de mot de passe. Un lien dans ta boîte, c'est tout.",
  },
  "pt-BR": {
    working: "Entrando…",
    welcome: "Você entrou.",
    used: "Esse link já foi usado. Peça um novo.",
    expired: "Esse link expirou. Peça um novo.",
    invalid: "Esse link não é válido. Peça um novo.",
    title: "Entrar",
    lead: "Nunca uma senha. Um link no seu e-mail e pronto.",
  },
  ru: {
    working: "Впускаю…",
    welcome: "Вход выполнен.",
    used: "Эта ссылка уже использована. Запроси новую.",
    expired: "Эта ссылка истекла. Запроси новую.",
    invalid: "Эта ссылка не работает. Запроси новую.",
    title: "Войти",
    lead: "Пароля нет и не будет. Ссылка в почте — и всё.",
  },
};

function SignIn() {
  const { locale } = useLocale();
  const copy = COPY[locale] ?? COPY.en;
  const params = useSearchParams();
  const token = params.get("token");

  const [state, setState] = useState<"idle" | "working" | "done" | "failed">(
    token ? "working" : "idle",
  );
  const [problem, setProblem] = useState("");
  const attempted = useRef(false);

  useEffect(() => {
    if (!token || attempted.current) return;
    attempted.current = true;

    api.consumeMagicLink(token).then((result) => {
      // The token is single-use and now spent (or was never ours): strip it
      // from the address bar so it is not left in history or resent on a back
      // navigation. `replaceState` rather than a navigation so nothing
      // re-renders and the just-computed `result` still lands below.
      if (typeof window !== "undefined") {
        window.history.replaceState(null, "", "/sign-in");
      }

      if (isOk(result)) {
        writeToken(result.data.token);
        setState("done");
        return;
      }

      // A network failure is not the server's verdict on the link — the token
      // was never consumed and may be perfectly valid. Calling it "invalid"
      // (the old fall-through) sent people to ask for a fresh link they did
      // not need. Show the sign-in form instead, where they can retry or
      // request one. (No dedicated copy string is invented for this — see the
      // owner's rule on strings.)
      if (result.kind === "offline" || result.kind === "unavailable") {
        setState("idle");
        return;
      }

      // Branch on the backend's typed error code, not on the English text of
      // the message: the three magic-link failures now arrive as
      // `link_used` / `link_expired` / `link_invalid`. The substring check is
      // kept only as a fallback for an older server that still sends a plain
      // string.
      setState("failed");
      const code = result.kind === "error" ? result.code : undefined;
      const said = result.message.toLowerCase();
      const used = code === "link_used" || (!code && said.includes("already"));
      const expired = code === "link_expired" || (!code && said.includes("expired"));
      setProblem(used ? copy.used : expired ? copy.expired : copy.invalid);
    });
  }, [copy, token]);

  return (
    <main className="signin-page">
      <Starfield />
      <div className="signin-inner">
        <Star size={44} />

        {state === "working" && <p className="signin-sent">{copy.working}</p>}

        {/* This used to `router.replace("/today")` the instant the token was
            consumed, and then offer a button to the same place. There is no
            /today on the web any more — the reading happens in the app — so
            what a consumed link produces is the fact that it worked and the
            way onward. The account is what carries: the same address in the
            app opens the same sky. */}
        {state === "done" && (
          <>
            <h1 className="signin-title">{copy.welcome}</h1>
            <GetTheApp />
          </>
        )}

        {(state === "idle" || state === "failed") && (
          <>
            <h1 className="signin-title">{copy.title}</h1>
            <p className="signin-lead">{copy.lead}</p>
            {state === "failed" && (
              <p className="signin-error" role="alert">
                {problem}
              </p>
            )}
            <SignInPanel onSignedIn={() => setState("done")} />
          </>
        )}

        {/* The way out of the wrong language, on the page most likely to be
            opened by somebody who is stuck.

            This route honours the locale cookie like every other — it renders
            under `<html lang="de">` for a German negotiation — and until now it
            was the only thing on the page that could not be argued with: the
            picker lives in the landing's footer and this page does not mount
            the footer. A magic link lands here, from an email, often on a
            different device from the one the choice was made on, where the
            language is negotiated from `Accept-Language` all over again. Being
            unable to read the page you were sent to is a bad place for that to
            happen.

            Below the panel rather than above it: the page has one job and the
            person is usually here to finish it, so the sign-in comes first in
            reading order and in tab order. */}
        <div className="signin-lang">
          <LanguagePicker />
        </div>
      </div>
    </main>
  );
}

export default function SignInPage() {
  // useSearchParams needs a Suspense boundary in the App Router, or the whole
  // route opts out of static rendering.
  return (
    <Suspense fallback={null}>
      <SignIn />
    </Suspense>
  );
}
