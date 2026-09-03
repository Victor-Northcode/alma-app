"use client";

/**
 * The end of the web: where a person goes to keep reading, and what happens to
 * the chart they made on the way here.
 *
 * Everything that used to be sold on this site is sold in the app now, through
 * Apple and Google, so the last thing the website does is hand somebody over.
 * Three parts, in the order a person needs them.
 *
 * **The badge, or the plate.** One row per store. When `lib/stores.ts` holds a
 * listing URL the row is that store's own badge artwork, linked; when it does
 * not — which is the truth today, because neither build has been accepted
 * anywhere — the row is a plate that says "coming". The plate is deliberately
 * not a disabled button and not a link to a search page. A dead badge is worse
 * than an honest sentence: it looks like the thing that works, it is tapped,
 * and the person concludes the product is broken rather than unreleased.
 * `<span>` rather than `<button disabled>` for the same reason — a disabled
 * button is a control that could have worked, and there is no control here yet.
 *
 * **The badge is the store's artwork and nothing else.** Both guidelines say
 * the same three things: use the file they supply, do not redraw or recolour or
 * angle it, and leave clear space around it — a quarter of its own height,
 * Apple and Google independently. So the live badge is an `<img>` inside a bare
 * `<a>`: no border, no plate, no gold. The bordered treatment belongs to the
 * "coming" plate, which is our sentence rather than their mark, and the two
 * must not be styled as the same object. Apple is first in the row because
 * Apple's guidelines ask for that where badges for more than one platform
 * appear; when the artwork arrives it must be the black badge, for the same
 * reason.
 *
 * **What travels.** This is the one screen that has to say whether the chart
 * just calculated will be there when the app opens, and the answer genuinely
 * differs per person — the rule is `lib/carry.ts`. It is stated rather than implied,
 * because implying continuity we do not provide is how somebody loses a birth
 * time they will not remember to re-enter.
 */

import { carrySentence } from "@/lib/carry";
import { useT } from "@/lib/i18n/provider";
import {
  APP_STORE_BADGE,
  APP_STORE_URL,
  PLAY_STORE_BADGE,
  PLAY_STORE_URL,
} from "@/lib/stores";
import { useIdentity } from "@/lib/use-alma";

export function GetTheApp({
  linkSentTo,
  carry = true,
}: {
  linkSentTo?: string | null;
  /**
   * Показывать ли строку «выживет ли это небо по дороге в телефон».
   *
   * Она написана для хвоста квиза — человека, только что посчитавшего
   * карту В ЭТОМ браузере. На страницах без карты («/pay» — «оплата
   * готовится») та же строка обещала небо, которого на странице нет,
   * и говорила про повторный ввод даты человеку, пришедшему платить
   * (снято на проде 02.09.2026).
   */
  carry?: boolean;
}) {
  const t = useT();
  const identity = useIdentity();
  const published = Boolean(APP_STORE_URL || PLAY_STORE_URL);

  return (
    <div className="stores">
      <p className="stores-note">{t.app.note}</p>
      <Badge
        url={APP_STORE_URL}
        artwork={APP_STORE_BADGE}
        live={t.app.appStore}
        soon={t.app.appleSoon}
      />
      <Badge
        url={PLAY_STORE_URL}
        artwork={PLAY_STORE_BADGE}
        live={t.app.googlePlay}
        soon={t.app.googleSoon}
      />
      {/* Answered before it is asked. Somebody looking at two plates they
          cannot tap deserves to know why in one line, rather than tapping
          each of them twice to find out. */}
      {!published && <p className="stores-fine">{t.app.notYet}</p>}
      {carry && (
        <p className="stores-carry">
          {carrySentence(t.app, identity, linkSentTo ?? null)}
        </p>
      )}
    </div>
  );
}

function Badge({
  url,
  artwork,
  live,
  soon,
}: {
  url: string;
  artwork: string;
  live: string;
  soon: string;
}) {
  if (!url) {
    return <span className="store-badge-soon">{soon}</span>;
  }
  return (
    <a className="store-badge" href={url} target="_blank" rel="noreferrer">
      {/* The badge already contains the words, in the store's own typeface and
          in its own localisation — so the alt text repeats them for a reader
          who cannot see it rather than describing the image. `<img>` and not
          `next/image`: the optimiser would re-encode artwork that both stores
          require to be used exactly as supplied. */}
      <img src={artwork} alt={live} />
    </a>
  );
}

// Which of the four sentences a person gets is in `lib/carry.ts`, with a test
// over all six dictionaries: it is the one claim on this screen that can be
// false rather than merely badly worded, and it does not belong in a component
// that cannot be run without a DOM.
