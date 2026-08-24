#!/usr/bin/env python3
"""Локализации восьми товаров на семь языков — в оба стора одним прогоном.

Тексты не переводились дословно: имена систем взяты из словаря самого
приложения (lib/l10n/app_*.arb — «Тема natale», «Соляр», «Partnerschaft»…),
описания переписаны так, как это говорят на каждом языке, и уложены в лимиты
App Store Connect (имя ≤30, описание ≤45) и Play. Владелец 24.08.2026
делегировал тексты («сделай перевод максимально умный и грамотный, не
дословный»).

ASC: ключ App Store Connect API (env ASC_KEY_ID / ASC_ISSUER_ID /
ASC_PRIVATE_KEY). Play: сервис-аккаунт (env PLAY_SA_JSON).

    python store_l10n.py            # dry-run: показать план по обоим сторам
    python store_l10n.py --apply    # записать
    python store_l10n.py --only asc|play
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time

try:
    import jwt
    import requests
except ImportError:
    sys.exit("pip install pyjwt cryptography requests google-auth")

ASC_API = "https://api.appstoreconnect.apple.com"
APP_ID = "6803672050"
PLAY_BASE = "https://androidpublisher.googleapis.com/androidpublisher/v3"
PACKAGE = "ai.pazl.alma"

# ── тексты ────────────────────────────────────────────────────────────────
# (name ≤30, description ≤45 — лимиты ASC, самые тесные из двух сторов)

L10N: dict[str, dict[str, tuple[str, str]]] = {
    "ai.pazl.alma.door.natal": {
        "en": ("Natal chart", "All 15 paid chapters. Yours forever."),
        "ru": ("Натальная карта", "Все 15 платных глав. Твои навсегда."),
        "es": ("Carta natal", "Los 15 capítulos de pago. Tuyos para siempre."),
        "de": ("Geburtshoroskop", "Alle 15 Kapitel. Für immer deins."),
        "it": ("Tema natale", "Tutti i 15 capitoli. Tuoi per sempre."),
        "fr": ("Thème natal", "Les 15 chapitres. À toi pour toujours."),
        "pt": ("Mapa natal", "Os 15 capítulos pagos. Seus para sempre."),
    },
    "ai.pazl.alma.door.numerology": {
        "en": ("Numerology", "All 4 paid chapters. Yours forever."),
        "ru": ("Нумерология", "Все 4 платные главы. Твои навсегда."),
        "es": ("Numerología", "Los 4 capítulos de pago. Tuyos para siempre."),
        "de": ("Numerologie", "Alle 4 Kapitel. Für immer deins."),
        "it": ("Numerologia", "Tutti e 4 i capitoli. Tuoi per sempre."),
        "fr": ("Numérologie", "Les 4 chapitres. À toi pour toujours."),
        "pt": ("Numerologia", "Os 4 capítulos pagos. Seus para sempre."),
    },
    "ai.pazl.alma.door.birth_card": {
        "en": ("Birth Card", "Both paid chapters. Yours forever."),
        "ru": ("Карта рождения", "Обе платные главы. Твои навсегда."),
        "es": ("Carta de nacimiento", "Ambos capítulos. Tuyos para siempre."),
        "de": ("Geburtskarte", "Beide Kapitel. Für immer deins."),
        "it": ("Carta di nascita", "Entrambi i capitoli. Tuoi per sempre."),
        "fr": ("Carte de naissance", "Les deux chapitres. À toi pour toujours."),
        "pt": ("Carta de nascimento", "Os dois capítulos. Seus para sempre."),
    },
    "ai.pazl.alma.door.astrocartography": {
        "en": ("Astrocartography", "Both paid chapters. Yours forever."),
        "ru": ("Астрокартография", "Обе платные главы. Твои навсегда."),
        "es": ("Astrocartografía", "Ambos capítulos. Tuyos para siempre."),
        "de": ("Astrokartografie", "Beide Kapitel. Für immer deins."),
        "it": ("Astrocartografia", "Entrambi i capitoli. Tuoi per sempre."),
        "fr": ("Astrocartographie", "Les deux chapitres. À toi pour toujours."),
        "pt": ("Astrocartografia", "Os dois capítulos. Seus para sempre."),
    },
    "ai.pazl.alma.door.synthesis": {
        "en": ("Cross-synthesis", "All 3 paid chapters. Yours forever."),
        "ru": ("Перекрёстный синтез", "Все 3 платные главы. Твои навсегда."),
        "es": ("Síntesis cruzada", "Los 3 capítulos de pago. Tuyos para siempre."),
        "de": ("Quersynthese", "Alle 3 Kapitel. Für immer deins."),
        "it": ("Sintesi incrociata", "Tutti e 3 i capitoli. Tuoi per sempre."),
        "fr": ("Synthèse croisée", "Les 3 chapitres. À toi pour toujours."),
        "pt": ("Síntese cruzada", "Os 3 capítulos pagos. Seus para sempre."),
    },
    "ai.pazl.alma.pair.check": {
        "en": ("Compatibility report", "The 4 chapters about you two. Forever."),
        "ru": ("Отчёт о совместимости", "4 главы о вас двоих. Навсегда."),
        "es": ("Informe de compatibilidad", "Los 4 capítulos sobre los dos. Para siempre."),
        "de": ("Partnerschaftsbericht", "Die 4 Kapitel über euch zwei. Für immer."),
        "it": ("Report di affinità", "I 4 capitoli su voi due. Per sempre."),
        "fr": ("Rapport de compatibilité", "Les 4 chapitres sur vous deux. Pour toujours."),
        "pt": ("Relatório de compatibilidade", "Os 4 capítulos sobre vocês dois. Para sempre."),
    },
    "ai.pazl.alma.bundle.static": {
        "en": ("All five readings", "Every reading that never changes. Once."),
        "ru": ("Все пять чтений", "Всё, что не меняется. Одной покупкой."),
        "es": ("Las cinco lecturas", "Todo lo que no cambia. Un solo pago."),
        "de": ("Alle fünf Lesungen", "Alles, was sich nie ändert. Einmalig."),
        "it": ("Le cinque letture", "Tutto ciò che non cambia. Una volta sola."),
        "fr": ("Les cinq lectures", "Tout ce qui ne change pas. Un seul achat."),
        "pt": ("As cinco leituras", "Tudo o que nunca muda. Uma única vez."),
    },
    "ai.pazl.alma.sub.monthly": {
        "en": ("Everything, monthly", "Readings, transits, solar, 1 pair, 30 asks."),
        "ru": ("Всё сразу, помесячно", "Чтения, транзиты, соляр, пара, 30 вопросов."),
        "es": ("Todo, cada mes", "Todo: tránsitos, solar, pareja, 30 preguntas."),
        "de": ("Alles, monatlich", "Lesungen, Transite, Solar, Paar, 30 Fragen."),
        "it": ("Tutto, ogni mese", "Tutto: transiti, solare, coppia, 30 domande."),
        # Без «:» и «?» — французская типографика требует к ним U+202F,
        # а в 45 знаков с ним не уложиться; фраза перестроена без них.
        "fr": ("Tout, chaque mois", "Transits, solaire, couple et 30 questions."),
        "pt": ("Tudo, todo mês", "Tudo: trânsitos, solar, casal, 30 perguntas."),
    },
}

#: Benefits подписки Play (у Apple такого поля нет): до 4 строк по ≤40 знаков.
BENEFITS: dict[str, list[str]] = {
    "en": ["All readings open while active", "Live transits and solar return",
           "One compatibility check monthly", "30 questions to Alma monthly"],
    "ru": ["Все чтения открыты, пока план жив", "Живые транзиты и соляр",
           "1 проверка совместимости в месяц", "30 вопросов Alma в месяц"],
    "es": ["Todas las lecturas abiertas", "Tránsitos y solar en vivo",
           "1 informe de pareja al mes", "30 preguntas a Alma al mes"],
    "de": ["Alle Lesungen offen", "Live-Transite und Solar",
           "1 Paar-Bericht pro Monat", "30 Fragen an Alma pro Monat"],
    "it": ["Tutte le letture aperte", "Transiti e solare dal vivo",
           "1 report di coppia al mese", "30 domande ad Alma al mese"],
    "fr": ["Toutes les lectures ouvertes", "Transits et solaire en direct",
           "1 rapport de couple par mois", "30 questions à Alma par mois"],
    "pt": ["Todas as leituras abertas", "Trânsitos e solar ao vivo",
           "1 relatório de casal por mês", "30 perguntas à Alma por mês"],
}

ASC_LOCALES = {"ru": "ru", "es": "es-ES", "de": "de-DE", "it": "it",
               "fr": "fr-FR", "pt": "pt-BR"}
PLAY_LOCALES = {"ru": "ru-RU", "es": "es-ES", "de": "de-DE", "it": "it-IT",
                "fr": "fr-FR", "pt": "pt-BR", "en": "en-US"}
SUBSCRIPTION = "ai.pazl.alma.sub.monthly"


def _check_limits() -> None:
    for pid, langs in L10N.items():
        for lang, (name, desc) in langs.items():
            assert len(name) <= 30, (pid, lang, "name>30", name)
            assert len(desc) <= 45, (pid, lang, "desc>45", desc)
    for lang, rows in BENEFITS.items():
        assert len(rows) <= 4, lang
        for row in rows:
            assert len(row) <= 40, (lang, row)


# ── ASC ───────────────────────────────────────────────────────────────────

def asc_token() -> str:
    with open(os.environ["ASC_PRIVATE_KEY"]) as fh:
        key = fh.read()
    now = int(time.time())
    return jwt.encode(
        {"iss": os.environ["ASC_ISSUER_ID"], "iat": now, "exp": now + 1200,
         "aud": "appstoreconnect-v1"},
        key, algorithm="ES256",
        headers={"kid": os.environ["ASC_KEY_ID"], "typ": "JWT"})


def asc_run(apply: bool) -> None:
    s = requests.Session()
    s.headers["Authorization"] = "Bearer " + asc_token()

    def get(path, **params):
        r = s.get(ASC_API + path, params=params, timeout=60)
        r.raise_for_status()
        return r.json()

    def send(method, path, payload):
        r = getattr(s, method)(ASC_API + path, json=payload, timeout=60)
        if r.status_code >= 400:
            sys.exit(f"ASC {r.status_code} {method} {path}\n{r.text[:600]}")

    iaps = {d["attributes"]["productId"]: d["id"]
            for d in get(f"/v1/apps/{APP_ID}/inAppPurchasesV2", limit=200)["data"]}
    subs = {}
    for g in get(f"/v1/apps/{APP_ID}/subscriptionGroups", limit=200)["data"]:
        for d in get(f"/v1/subscriptionGroups/{g['id']}/subscriptions", limit=200)["data"]:
            subs[d["attributes"]["productId"]] = d["id"]

    for pid, langs in L10N.items():
        is_sub = pid == SUBSCRIPTION
        internal = subs.get(pid) if is_sub else iaps.get(pid)
        if not internal:
            print(f"ASC !! {pid}: не найден")
            continue
        kind = "subscriptionLocalizations" if is_sub else "inAppPurchaseLocalizations"
        listing_path = (f"/v1/subscriptions/{internal}/subscriptionLocalizations"
                        if is_sub else
                        f"/v2/inAppPurchases/{internal}/inAppPurchaseLocalizations")
        have = {d["attributes"]["locale"]: d["id"]
                for d in get(listing_path, limit=200)["data"]}
        print(f"\nASC {pid}: есть локали {sorted(have)}")
        for lang, (name, desc) in langs.items():
            if lang == "en":
                continue  # en-US заведён руками агента и не трогается
            locale = ASC_LOCALES[lang]
            attrs = {"name": name, "description": desc}
            if locale in have:
                print(f"  ~ {locale}: обновить -> {name} / {desc}")
                if apply:
                    send("patch", f"/v1/{kind}/{have[locale]}", {"data": {
                        "type": kind, "id": have[locale],
                        "attributes": attrs}})
            else:
                print(f"  + {locale}: создать -> {name} / {desc}")
                if apply:
                    rel_name = "subscription" if is_sub else "inAppPurchaseV2"
                    rel_type = "subscriptions" if is_sub else "inAppPurchases"
                    send("post", f"/v1/{kind}", {"data": {
                        "type": kind,
                        "attributes": {**attrs, "locale": locale},
                        "relationships": {rel_name: {"data": {
                            "type": rel_type, "id": internal}}}}})


# ── Play ──────────────────────────────────────────────────────────────────

def play_session():
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    creds = service_account.Credentials.from_service_account_file(
        os.environ["PLAY_SA_JSON"],
        scopes=["https://www.googleapis.com/auth/androidpublisher"])
    return AuthorizedSession(creds)


def play_run(apply: bool) -> None:
    s = play_session()

    def check(r):
        if r.status_code >= 400:
            sys.exit(f"Play {r.status_code} {r.request.method} {r.url}\n{r.text[:600]}")
        return r.json() if r.text else {}

    for pid, langs in L10N.items():
        is_sub = pid == SUBSCRIPTION
        get_url = (f"{PLAY_BASE}/applications/{PACKAGE}/subscriptions/{pid}"
                   if is_sub else
                   f"{PLAY_BASE}/applications/{PACKAGE}/oneTimeProducts/{pid}")
        # PATCH один и тот же путь у подписки; у one-time — строчный (см.
        # play_prices.py, снято с discovery 24.08).
        patch_url = (get_url if is_sub else
                     f"{PLAY_BASE}/applications/{PACKAGE}/onetimeproducts/{pid}")
        before = check(s.get(get_url))
        after = copy.deepcopy(before)
        listings = {l["languageCode"]: l for l in after.get("listings", [])}
        print(f"\nPlay {pid}: есть языки {sorted(listings)}")
        for lang, (name, desc) in langs.items():
            code = PLAY_LOCALES[lang]
            row = listings.get(code, {"languageCode": code})
            row["title"] = name
            if is_sub:
                row["benefits"] = BENEFITS[lang]
            else:
                row["description"] = desc
            listings[code] = row
            print(f"  = {code}: {name}" + ("" if is_sub else f" / {desc}"))
        after["listings"] = list(listings.values())
        if not apply:
            continue
        params = {"updateMask": "listings",
                  "regionsVersion.version": before.get("regionsVersion", {})
                  .get("version", "2025/03")}
        check(s.patch(patch_url, params=params, json=after))
        print(f"  записано: {len(after['listings'])} языков")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", choices=["asc", "play"])
    args = ap.parse_args()
    _check_limits()
    print("режим:", "ЗАПИСЬ" if args.apply else "dry-run")
    if args.only != "play":
        asc_run(args.apply)
    if args.only != "asc":
        play_run(args.apply)


if __name__ == "__main__":
    main()
