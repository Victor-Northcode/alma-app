"use client";

/**
 * Возврат с платёжной формы Т-Банка после успешной оплаты (`SuccessURL`
 * адаптера). Страница нарочно не утверждает «доступ открыт»: возврат браузера
 * — не доказательство платежа, доказательство — подписанный вебхук, и он
 * может прийти на несколько секунд позже человека. Поэтому здесь кнопка
 * «Проверить доступ», а не готовый вердикт.
 */

import { useCallback, useState } from "react";
import { Star } from "@/components/brand/Star";
import { Starfield } from "@/components/sky/Sky";
import { api, isOk } from "@/lib/api";

export default function PayDonePage() {
  const [busy, setBusy] = useState(false);
  const [held, setHeld] = useState<string[] | null>(null);
  const [failed, setFailed] = useState(false);

  const check = useCallback(async () => {
    setBusy(true);
    setFailed(false);
    const r = await api.entitlements();
    setBusy(false);
    if (isOk(r)) setHeld(r.data.unlocked ?? []);
    else setFailed(true);
  }, []);

  return (
    <main className="signin-page" lang="ru">
      <Starfield />
      <div className="signin-inner pay-inner">
        <Star size={44} />
        <h1 className="signin-title">Оплата принята</h1>
        <p className="signin-lead">
          Банк подтверждает платёж — обычно это несколько секунд. Как только
          подтверждение придёт, доступ сам появится на всех твоих устройствах.
        </p>
        <div className="pay-form">
          <button
            type="button"
            className="btn btn-gold btn-block"
            disabled={busy}
            onClick={() => void check()}
          >
            {busy ? "Проверяю…" : "Проверить доступ"}
          </button>
          <a className="btn btn-outline btn-block" href="/pay">
            Назад к оплате
          </a>
        </div>
        {held !== null && (
          <p className="signin-sent" role="status">
            {held.length
              ? "Доступ на месте. Открой приложение и войди той же почтой — всё уже там."
              : "Подтверждение ещё в пути. Подожди минуту и проверь ещё раз."}
          </p>
        )}
        {failed && (
          <p className="signin-error" role="alert">
            Не получилось проверить. Попробуй ещё раз.
          </p>
        )}
      </div>
    </main>
  );
}
