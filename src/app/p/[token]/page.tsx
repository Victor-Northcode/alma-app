"use client";

/**
 * «/p/{token}» — приглашение «проверь нас»: страница, на которую приходит
 * второй человек по ссылке из приложения (друзья, владелец 31.08.2026).
 *
 * Один экран, одна форма: имя, дата, время по желанию, город — та же анкета,
 * что в журнее, теми же словами словаря. Отправка принимает приглашение
 * (`POST /v1/friends/invites/{token}/claim`): у обоих рождается профиль
 * второго, совместимость посчитана. Хвост честный: «она живёт в приложении»
 * плюс собственное небо принявшего (Солнце и число пути — то, что даёт одна
 * дата, посчитанное здесь же, бесплатно) и кнопки магазинов.
 *
 * Просмотр страницы аккаунт не минтит (`Visitor` на сервере); минтит его
 * отправка формы — акт, а не заход по ссылке.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Star } from "@/components/brand/Star";
import { Starfield } from "@/components/sky/Sky";
import { GetTheApp } from "@/components/handoff/GetTheApp";
import { api, isOk, type Place } from "@/lib/api";
import { insightFor } from "@/lib/data";
import { useT } from "@/lib/i18n/provider";
import { usePlaceSearch } from "@/lib/use-alma";

const DAYS = Array.from({ length: 31 }, (_, i) => String(i + 1));
const YEARS = Array.from({ length: 100 }, (_, i) => String(new Date().getFullYear() - i));
const HOURS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, "0"));
const MINUTES = Array.from({ length: 60 }, (_, i) => String(i).padStart(2, "0"));

type Stage = "loading" | "form" | "done" | "dead";

export default function InvitePage() {
  const t = useT();
  const { token } = useParams<{ token: string }>();

  const [stage, setStage] = useState<Stage>("loading");
  const [deadText, setDeadText] = useState("");
  const [inviter, setInviter] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [day, setDay] = useState("");
  const [monthIndex, setMonthIndex] = useState(-1);
  const [year, setYear] = useState("");
  const [hour, setHour] = useState("");
  const [minute, setMinute] = useState("");
  const [query, setQuery] = useState("");
  const [place, setPlace] = useState<Place | null>(null);
  const { places, searching, failed } = usePlaceSearch(query);

  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    void api.inviteInfo(token).then((r) => {
      if (isOk(r)) {
        if (r.data.claimed) {
          setDeadText(t.invite.claimed);
          setStage("dead");
        } else {
          setInviter(r.data.inviter_name);
          setStage("form");
        }
      } else {
        setDeadText(t.invite.unknown);
        setStage("dead");
      }
    });
    // Словарь меняется вместе с локалью, но приглашение перечитывать незачем.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  /** Дата, если три поля складываются в существующий день. */
  const date = useMemo(() => {
    if (!day || monthIndex < 0 || !year) return null;
    const d = Number(day);
    const parsed = new Date(Date.UTC(Number(year), monthIndex, d));
    if (parsed.getUTCDate() !== d || parsed.getUTCMonth() !== monthIndex) return null;
    return { day: d, month: monthIndex + 1, year: Number(year) };
  }, [day, monthIndex, year]);

  const complete = date !== null && place !== null;

  const submit = useCallback(async () => {
    if (!date || !place || busy) return;
    setBusy(true);
    setNotice(null);
    const iso = `${date.year}-${String(date.month).padStart(2, "0")}-${String(date.day).padStart(2, "0")}`;
    const r = await api.claimInvite(token, {
      name: name.trim() || null,
      birth_date: iso,
      // Час без минут — это «в семь», а не «времени не знаю»: пустые минуты
      // складываются в :00, а не роняют время целиком.
      birth_time: hour ? `${hour}:${minute || "00"}` : null,
      latitude: place.latitude,
      longitude: place.longitude,
      timezone: place.timezone,
      place_label: place.label,
      place_id: place.id,
    });
    setBusy(false);
    if (isOk(r)) {
      setInviter(r.data.inviter_name ?? inviter);
      setStage("done");
      return;
    }
    if (r.kind === "error" && r.code === "invite_claimed") {
      setDeadText(t.invite.claimed);
      setStage("dead");
    } else if (r.kind === "error" && r.code === "own_invite") {
      setNotice(t.invite.own);
    } else if (r.kind === "error" && r.code === "invite_unknown") {
      setDeadText(t.invite.unknown);
      setStage("dead");
    } else if (r.kind === "invalid") {
      setNotice(t.capture.impossibleDate);
    } else {
      setNotice(t.invite.failed);
    }
  }, [date, place, busy, token, name, hour, minute, inviter, t]);

  const insight = stage === "done" ? insightFor(date) : null;

  return (
    <main className="signin-page">
      <Starfield />
      <div className="signin-inner" style={{ maxWidth: 430 }}>
        <Star size={44} />

        {stage === "loading" && <p className="signin-sent">…</p>}

        {stage === "dead" && (
          <>
            <h1 className="signin-title">{t.invite.title("")}</h1>
            <p className="signin-lead">{deadText}</p>
            <GetTheApp />
          </>
        )}

        {stage === "form" && (
          <>
            <h1 className="signin-title">{t.invite.title(inviter ?? "")}</h1>
            <p className="signin-lead">{t.invite.lead}</p>

            <div className="pay-form" style={{ maxWidth: 430 }}>
              <input
                className="text-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t.journey.namePlaceholder}
                aria-label={t.journey.nameAria}
                autoComplete="given-name"
              />

              <div style={{ display: "flex", gap: 9 }}>
                <select
                  className="text-input"
                  style={{ flex: 1 }}
                  aria-label={t.capture.day}
                  value={day}
                  onChange={(e) => setDay(e.target.value)}
                >
                  <option value="" disabled>{t.capture.dayShort}</option>
                  {DAYS.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
                <select
                  className="text-input"
                  style={{ flex: 1.7 }}
                  aria-label={t.capture.month}
                  value={monthIndex < 0 ? "" : String(monthIndex)}
                  onChange={(e) => setMonthIndex(Number(e.target.value))}
                >
                  <option value="" disabled>{t.capture.monthShort}</option>
                  {t.months.map((m, i) => <option key={m} value={i}>{m}</option>)}
                </select>
                <select
                  className="text-input"
                  style={{ flex: 1.2 }}
                  aria-label={t.capture.year}
                  value={year}
                  onChange={(e) => setYear(e.target.value)}
                >
                  <option value="" disabled>{t.capture.yearShort}</option>
                  {YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
                </select>
              </div>

              {/* Время — по желанию: совместимость честно считается и без
                  него, недостающее сервер помечает недоступным, а не
                  выдумывает. */}
              <div style={{ display: "flex", gap: 9 }}>
                <select
                  className="text-input"
                  style={{ flex: 1 }}
                  aria-label={t.journey.hourLabel}
                  value={hour}
                  onChange={(e) => setHour(e.target.value)}
                >
                  <option value="">{t.journey.hourLabel}</option>
                  {HOURS.map((h) => <option key={h} value={h}>{h}</option>)}
                </select>
                <select
                  className="text-input"
                  style={{ flex: 1 }}
                  aria-label={t.journey.minuteLabel}
                  value={minute}
                  onChange={(e) => setMinute(e.target.value)}
                >
                  <option value="">{t.journey.minuteLabel}</option>
                  {MINUTES.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              {(!hour || !minute) && (
                <p className="signin-note" style={{ textAlign: "left" }}>
                  {t.journey.lockedWithoutTime}
                </p>
              )}

              <input
                className="text-input"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setPlace(null);
                }}
                placeholder={t.journey.placePlaceholder}
                aria-label={t.capture.searchPlace}
              />
              {place === null && (
                <div className="suggestions">
                  {places.map((option) => (
                    <button
                      key={option.id}
                      type="button"
                      className="suggestion"
                      onClick={() => {
                        setPlace(option);
                        setQuery(option.label);
                      }}
                    >
                      <span>{option.label}</span>
                      <span className="suggestion-tz">
                        {option.timezone.split("/").pop()?.replace(/_/g, " ")}
                      </span>
                    </button>
                  ))}
                  {!places.length && query.trim().length >= 2 && !searching && !failed && (
                    <p className="suggestion-empty">{t.capture.noPlaces}</p>
                  )}
                  {failed && !places.length && (
                    <p className="suggestion-empty">{t.journey.placeOffline}</p>
                  )}
                </div>
              )}

              <button
                type="button"
                className="btn btn-gold btn-block"
                disabled={!complete || busy}
                onClick={() => void submit()}
              >
                {busy ? t.invite.working : t.invite.submit}
              </button>
              {notice && (
                <p className="signin-error" role="alert">{notice}</p>
              )}
            </div>
          </>
        )}

        {stage === "done" && (
          <>
            <h1 className="signin-title">{t.invite.doneTitle(inviter ?? "")}</h1>
            <p className="signin-lead">{t.invite.doneLead}</p>
            {insight && (
              <p className="signin-sent">
                {t.hero.yourSky} · {insight.sign.glyph}{" "}
                {t.insight.sun(t.signs[insight.sign.name as keyof typeof t.signs] ?? insight.sign.name)}
                {" · "}
                {t.insight.lifePath(insight.path)}
              </p>
            )}
            <GetTheApp />
          </>
        )}
      </div>
    </main>
  );
}
