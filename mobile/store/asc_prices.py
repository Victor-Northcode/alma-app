#!/usr/bin/env python3
"""Ручные цены всех восьми покупок Alma в App Store Connect — одним прогоном.

ЗАЧЕМ. В консоли цена ставится по одной витрине за раз: 36 витрин × 8 товаров ≈
290 выпадающих списков по четыре клика (стор-агент прошёл путь руками на
door.natal 24.08.2026 и остановился на Австрии). Через API это один прогон.

ЧЕМ ОТЛИЧАЕТСЯ ОТ ЧЕРНОВИКА АГЕНТА. Его версия постила
`inAppPurchasePriceSchedules` внутри цикла по витринам — а этот эндпоинт
ЗАМЕНЯЕТ расписание целиком, так что после прогона у товара осталась бы одна
ручная цена (последняя витрина цикла, Индия), а 35 остальных тихо упали бы в
авто. Здесь расписание собирается одно на товар: базовая витрина USA плюс все
ручные точки одним POST, с временными id `${p0}…${pN}` — так их сшивает сам
формат Apple. Подписка — другой механизм (`subscriptionPrices` — по витрине за
раз, и это у Apple штатно), там цикл остался.

КЛЮЧ. App Store Connect API (не APNs!): .p8 читается с диска, никуда кроме
api.appstoreconnect.apple.com не уходит и в вывод не печатается.

    set ASC_KEY_ID=UUM98VV283
    set ASC_ISSUER_ID=<UUID со страницы Users and Access → Integrations>
    set ASC_PRIVATE_KEY=C:\\Users\\user\\Downloads\\AuthKey_UUM98VV283.p8
    pip install pyjwt cryptography requests

СНАЧАЛА СУХОЙ ПРОГОН (по умолчанию, ничего не меняет):
    python asc_prices.py
Печатает, какая точка сетки Apple будет выбрана для каждой витрины, и отдельным
списком — где точной суммы в сетке нет и взята ближайшая. Эти отклонения
вписываются в REGIONAL_CENTS тем же коммитом: показанная цена обязана равняться
списанной.

Применить: python asc_prices.py --apply
"""

import argparse
import json
import os
import sys
import time
from decimal import Decimal

try:
    import jwt
    import requests
except ImportError:
    sys.exit("pip install pyjwt cryptography requests")

API = "https://api.appstoreconnect.apple.com"
APP_ID = "6803672050"

# Цены — mobile/store/PRODUCTS.md §4 / backend catalogue.py REGIONAL_CENTS.
# валюта -> (дверь/пара, бандл, подписка)
PRICES = {
    # USA обязана быть в списке ручных цен: расписание с baseTerritory USA без
    # ручной цены для неё Apple отклоняет 409 BASE_TERRITORY_INTERVAL_REQUIRED
    # (поймано на живом API 24.08). Суммы — базовые из PRODUCTS.md §1.
    "USD": ("4.99", "19.99", "9.99"),
    "EUR": ("5.49", "20.99", "10.49"),
    "GBP": ("4.99", "19.99", "9.99"),
    "CHF": ("5.90", "23.90", "11.90"),
    "AUD": ("7.99", "31.99", "15.99"),
    "CAD": ("7.49", "27.99", "13.99"),
    "NOK": ("59", "219", "109"),
    "DKK": ("39", "159", "79"),
    "BRL": ("12.90", "51.90", "25.90"),
    "MXN": ("59", "219", "109"),
    "PLN": ("10.99", "43.99", "21.99"),
    "TRY": ("69", "259", "129"),
    "INR": ("109", "439", "219"),
}

# Витрины Apple по валютам. Список EUR снят с консоли 24.08.2026: он шире
# еврозоны — Болгария, Босния, Косово, Сербия и Черногория тоже торгуют в EUR
# (каталог бэкенда приведён к этому тем же коммитом).
TERRITORIES = {
    "USD": ["USA"],
    # XKX (Косово) убран после сухого прогона 24.08: в консоли оно стоит в
    # списке EUR-витрин, а в API у него нет НИ ОДНОЙ точки цены ни у одного
    # товара — витрины как таковой не существует, прайсить нечего.
    "EUR": ["AUT", "BEL", "BGR", "BIH", "DEU", "GRC", "IRL", "ESP", "ITA",
            "CYP", "LVA", "LTU", "LUX", "MLT", "NLD", "PRT", "SRB",
            "SVK", "SVN", "FIN", "FRA", "HRV", "MNE", "EST"],
    "GBP": ["GBR"], "CHF": ["CHE"], "AUD": ["AUS"], "CAD": ["CAN"],
    "NOK": ["NOR"], "DKK": ["DNK"], "BRL": ["BRA"], "MXN": ["MEX"],
    "PLN": ["POL"], "TRY": ["TUR"], "INR": ["IND"],
}

# product id -> колонка PRICES
PRODUCTS = {
    "ai.pazl.alma.door.natal": 0,
    "ai.pazl.alma.door.numerology": 0,
    "ai.pazl.alma.door.birth_card": 0,
    "ai.pazl.alma.door.astrocartography": 0,
    "ai.pazl.alma.door.synthesis": 0,
    "ai.pazl.alma.pair.check": 0,
    "ai.pazl.alma.bundle.static": 1,
    "ai.pazl.alma.sub.monthly": 2,
}
SUBSCRIPTION_ID = "ai.pazl.alma.sub.monthly"
BASE_TERRITORY = "USA"


def token() -> str:
    with open(os.environ["ASC_PRIVATE_KEY"]) as fh:
        private_key = fh.read()
    now = int(time.time())
    return jwt.encode(
        {"iss": os.environ["ASC_ISSUER_ID"], "iat": now, "exp": now + 20 * 60,
         "aud": "appstoreconnect-v1"},
        private_key, algorithm="ES256",
        headers={"kid": os.environ["ASC_KEY_ID"], "typ": "JWT"},
    )


class Client:
    def __init__(self) -> None:
        self.s = requests.Session()
        self.s.headers["Authorization"] = "Bearer " + token()

    def get_all(self, path: str, **params):
        out, url, first = [], API + path, True
        while url:
            # Apple изредка отвечает 500 на ровном месте (поймано на NLD после
            # ~150 запросов подряд, 24.08) — три попытки с паузой.
            for attempt in range(3):
                r = self.s.get(url, params=params if first else None, timeout=60)
                if r.status_code < 500:
                    break
                time.sleep(3 * (attempt + 1))
            first = False
            r.raise_for_status()
            body = r.json()
            out.append(body)
            url = body.get("links", {}).get("next")
        return out

    def post(self, path: str, payload: dict):
        r = self.s.post(API + path, json=payload, timeout=120)
        if r.status_code >= 400:
            raise SystemExit(
                f"{r.status_code} {path}\n"
                + json.dumps(r.json(), indent=2, ensure_ascii=False))
        return r.json()


def nearest(points, target: Decimal):
    best = min(points, key=lambda p: abs(p[1] - target))
    return best, best[1] != target


def price_points(c: Client, base: str, terr: str):
    pts = []
    for page in c.get_all(base, **{"filter[territory]": terr, "limit": 200}):
        for d in page["data"]:
            pts.append((d["id"], Decimal(d["attributes"]["customerPrice"])))
    return pts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="реально записать цены")
    args = ap.parse_args()
    c = Client()

    iaps: dict[str, str] = {}
    for page in c.get_all(f"/v1/apps/{APP_ID}/inAppPurchasesV2", limit=200):
        for d in page["data"]:
            iaps[d["attributes"]["productId"]] = d["id"]
    subs: dict[str, str] = {}
    for page in c.get_all(f"/v1/apps/{APP_ID}/subscriptionGroups", limit=200):
        for g in page["data"]:
            for sp in c.get_all(
                    f"/v1/subscriptionGroups/{g['id']}/subscriptions", limit=200):
                for d in sp["data"]:
                    subs[d["attributes"]["productId"]] = d["id"]

    deviations = []

    for product_id, column in PRODUCTS.items():
        is_sub = product_id == SUBSCRIPTION_ID
        internal = subs.get(product_id) if is_sub else iaps.get(product_id)
        if not internal:
            print(f"!! {product_id}: не найден в App Store Connect")
            continue
        print(f"\n=== {product_id} ({'подписка' if is_sub else 'покупка'}) ===")
        base = (f"/v1/subscriptions/{internal}/pricePoints" if is_sub
                else f"/v2/inAppPurchases/{internal}/pricePoints")

        chosen = []  # (territory, point_id, target, actual)
        for currency, terrs in TERRITORIES.items():
            target = Decimal(PRICES[currency][column])
            for terr in terrs:
                pts = price_points(c, base, terr)
                if not pts:
                    print(f"  {terr} {currency}: точек цены нет")
                    continue
                (pp_id, actual), off = nearest(pts, target)
                print(f"  {terr} {currency}: {target} -> {actual}"
                      + ("  ~ ОТКЛОНЕНИЕ" if off else ""))
                if off:
                    deviations.append(
                        (product_id, terr, currency, str(target), str(actual)))
                chosen.append((terr, pp_id))

        if not args.apply or not chosen:
            continue

        if is_sub:
            # Подписка: по витрине за раз — так устроен сам эндпоинт.
            for terr, pp_id in chosen:
                c.post("/v1/subscriptionPrices", {"data": {
                    "type": "subscriptionPrices",
                    "attributes": {"preserveCurrentPrice": False},
                    "relationships": {
                        "subscription": {"data": {
                            "type": "subscriptions", "id": internal}},
                        "subscriptionPricePoint": {"data": {
                            "type": "subscriptionPricePoints", "id": pp_id}},
                        "territory": {"data": {
                            "type": "territories", "id": terr}}}}})
                print(f"  applied sub price {terr}")
        else:
            # Покупка: ОДНО расписание со всеми ручными ценами. POST по одной
            # витрине заменял бы расписание целиком — см. шапку файла.
            manual = [{"type": "inAppPurchasePrices", "id": f"${{p{i}}}"}
                      for i in range(len(chosen))]
            included = [
                {"type": "inAppPurchasePrices", "id": f"${{p{i}}}",
                 "attributes": {"startDate": None},
                 "relationships": {
                     "inAppPurchasePricePoint": {"data": {
                         "type": "inAppPurchasePricePoints", "id": pp_id}}}}
                for i, (_, pp_id) in enumerate(chosen)]
            c.post("/v1/inAppPurchasePriceSchedules", {
                "data": {
                    "type": "inAppPurchasePriceSchedules",
                    "relationships": {
                        "inAppPurchase": {"data": {
                            "type": "inAppPurchases", "id": internal}},
                        "baseTerritory": {"data": {
                            "type": "territories", "id": BASE_TERRITORY}},
                        "manualPrices": {"data": manual}}},
                "included": included})
            print(f"  applied schedule: {len(chosen)} витрин одним расписанием")

    if deviations:
        print("\n\nТОЧНОЙ ТОЧКИ У APPLE НЕТ — взята ближайшая. "
              "Впиши в REGIONAL_CENTS тем же коммитом:\n")
        for row in deviations:
            print("  " + " | ".join(row))
    else:
        print("\n\nВсе суммы легли в сетку Apple точка в точку.")
    if not args.apply:
        print("\n(сухой прогон — ничего не записано; повтори с --apply)")


if __name__ == "__main__":
    main()
