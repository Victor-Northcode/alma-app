#!/usr/bin/env python3
"""Set exact per-country prices in Google Play for the eight Alma products.

Черновик стор-агента 24.08 + мои правки после прогона по живому API.
Диалог Play Console «Bulk edit pricing» прибавляет НДС сверху введённой суммы
(проверено агентом: 5,49 EUR по еврозоне сохранились как 6,49/6,99/6,48);
ровную сумму пишет только ручной ввод по стране — и API, которым пишет этот
скрипт. По умолчанию dry-run; запись — с --apply.
"""

from __future__ import annotations

import argparse
import copy
import os
import sys
from decimal import Decimal

try:
    import requests
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
except ImportError:
    sys.exit("pip install google-auth requests")

PACKAGE = "ai.pazl.alma"
BASE = "https://androidpublisher.googleapis.com/androidpublisher/v3"
SCOPE = "https://www.googleapis.com/auth/androidpublisher"

PRICES: dict[str, dict[str, str]] = {
    "USD": {"door": "4.99", "bundle": "19.99", "monthly": "9.99"},
    "EUR": {"door": "5.49", "bundle": "20.99", "monthly": "10.49"},
    "GBP": {"door": "4.99", "bundle": "19.99", "monthly": "9.99"},
    "CHF": {"door": "5.90", "bundle": "23.90", "monthly": "11.90"},
    "AUD": {"door": "7.99", "bundle": "31.99", "monthly": "15.99"},
    "CAD": {"door": "7.49", "bundle": "27.99", "monthly": "13.99"},
    "NOK": {"door": "59", "bundle": "219", "monthly": "109"},
    "DKK": {"door": "39", "bundle": "159", "monthly": "79"},
    "BRL": {"door": "12.90", "bundle": "51.90", "monthly": "25.90"},
    "MXN": {"door": "59.00", "bundle": "219.00", "monthly": "109.00"},
    "PLN": {"door": "10.99", "bundle": "43.99", "monthly": "21.99"},
    "TRY": {"door": "69.00", "bundle": "259.00", "monthly": "129.00"},
    "INR": {"door": "109.00", "bundle": "439.00", "monthly": "219.00"},
}

# COUNTRY_CURRENCY из catalogue.py + GA/GW: у Play это EUR-витрины (снято
# агентом с консоли), каталог приведён тем же коммитом.
COUNTRY_CURRENCY: dict[str, str] = {
    "BR": "BRL", "MX": "MXN",
    "DE": "EUR", "FR": "EUR", "IT": "EUR", "ES": "EUR", "NL": "EUR",
    "PT": "EUR", "IE": "EUR", "AT": "EUR", "BE": "EUR", "FI": "EUR",
    "GR": "EUR", "SK": "EUR", "SI": "EUR", "LT": "EUR", "LV": "EUR",
    "EE": "EUR", "LU": "EUR", "CY": "EUR", "MT": "EUR", "HR": "EUR",
    "GA": "EUR", "GW": "EUR",
    "GB": "GBP", "CH": "CHF", "AU": "AUD", "CA": "CAD",
    "NO": "NOK", "DK": "DKK", "PL": "PLN", "TR": "TRY", "IN": "INR",
}

ONETIME: dict[str, str] = {
    "ai.pazl.alma.door.natal": "door",
    "ai.pazl.alma.door.numerology": "door",
    "ai.pazl.alma.door.birth_card": "door",
    "ai.pazl.alma.door.astrocartography": "door",
    "ai.pazl.alma.door.synthesis": "door",
    "ai.pazl.alma.pair.check": "door",
    "ai.pazl.alma.bundle.static": "bundle",
}
SUBSCRIPTION = "ai.pazl.alma.sub.monthly"
SUB_TIER = "monthly"


def money(currency: str, amount: str) -> dict:
    d = Decimal(amount)
    units = int(d)
    nanos = int((d - units) * 1_000_000_000)
    out = {"currencyCode": currency, "units": str(units)}
    if nanos:
        out["nanos"] = nanos
    return out


def same(a: dict | None, b: dict) -> bool:
    if not a:
        return False
    return (a.get("currencyCode") == b.get("currencyCode")
            and str(a.get("units", "0")) == str(b.get("units", "0"))
            and int(a.get("nanos", 0)) == int(b.get("nanos", 0)))


def show(m: dict | None) -> str:
    if not m:
        return "-"
    v = Decimal(str(m.get("units", 0))) + Decimal(m.get("nanos", 0)) / 1_000_000_000
    return f"{m.get('currencyCode', '???')} {v:.2f}"


def session() -> AuthorizedSession:
    path = os.environ.get("PLAY_SA_JSON")
    if not path:
        sys.exit("PLAY_SA_JSON не задан")
    creds = service_account.Credentials.from_service_account_file(path, scopes=[SCOPE])
    return AuthorizedSession(creds)


def check(resp: requests.Response) -> dict:
    if resp.status_code >= 400:
        sys.exit(f"HTTP {resp.status_code} {resp.request.method} {resp.url}\n{resp.text[:800]}")
    return resp.json() if resp.text else {}


def do_onetime(s: AuthorizedSession, product_id: str, tier: str, apply: bool) -> None:
    # GET маршрутизирован на camelCase-пути, PATCH — на строчном: это не
    # опечатка, а факт discovery-документа androidpublisher v3 (снято 24.08:
    # PATCH на oneTimeProducts отвечает голым 404-HTML).
    url = f"{BASE}/applications/{PACKAGE}/oneTimeProducts/{product_id}"
    patch_url = f"{BASE}/applications/{PACKAGE}/onetimeproducts/{product_id}"
    before = check(s.get(url))
    after = copy.deepcopy(before)

    changes: list[str] = []
    for option in after.get("purchaseOptions", []):
        for cfg in option.get("regionalPricingAndAvailabilityConfigs", []):
            region = cfg.get("regionCode")
            currency = COUNTRY_CURRENCY.get(region)
            if not currency:
                continue
            want = money(currency, PRICES[currency][tier])
            have = cfg.get("price")
            if same(have, want):
                continue
            changes.append(f"    {region}: {show(have)} -> {show(want)}")
            cfg["price"] = want

    print(f"\n{product_id}  ({tier})")
    if not changes:
        print("    всё уже совпадает")
        return
    print("\n".join(changes))
    if not apply:
        return
    params = {
        "updateMask": "purchaseOptions",
        "regionsVersion.version": before.get("regionsVersion", {}).get("version", "2022/02"),
        "latencyTolerance": "PRODUCT_UPDATE_LATENCY_TOLERANCE_LATENCY_TOLERANT",
    }
    check(s.patch(patch_url, params=params, json=after))
    print(f"    записано: {len(changes)} стран")


def do_subscription(s: AuthorizedSession, apply: bool) -> None:
    url = f"{BASE}/applications/{PACKAGE}/subscriptions/{SUBSCRIPTION}"
    before = check(s.get(url))
    after = copy.deepcopy(before)

    changes: list[str] = []
    for plan in after.get("basePlans", []):
        for cfg in plan.get("regionalConfigs", []):
            region = cfg.get("regionCode")
            currency = COUNTRY_CURRENCY.get(region)
            if not currency:
                continue
            want = money(currency, PRICES[currency][SUB_TIER])
            have = cfg.get("price")
            if same(have, want):
                continue
            changes.append(f"    {region}: {show(have)} -> {show(want)}")
            cfg["price"] = want

    print(f"\n{SUBSCRIPTION}  ({SUB_TIER})")
    if not changes:
        print("    всё уже совпадает")
        return
    print("\n".join(changes))
    if not apply:
        return
    params = {
        "updateMask": "basePlans",
        "regionsVersion.version": before.get("regionsVersion", {}).get("version", "2022/02"),
    }
    check(s.patch(url, params=params, json=after))
    print(f"    записано: {len(changes)} стран")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", choices=["onetime", "sub"])
    args = ap.parse_args()

    s = session()
    print("режим:", "ЗАПИСЬ" if args.apply else "dry-run")
    if args.only != "sub":
        for pid, tier in ONETIME.items():
            do_onetime(s, pid, tier, args.apply)
    if args.only != "onetime":
        do_subscription(s, args.apply)


if __name__ == "__main__":
    main()
