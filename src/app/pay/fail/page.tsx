"use client";

/**
 * Возврат с платёжной формы Т-Банка после неудачи (`FailURL` адаптера).
 * Деньги не списаны — форма не довела платёж; страница говорит это прямо
 * и ведёт назад к витрине, где можно попробовать снова или выбрать СБП
 * вместо карты.
 */

import { Star } from "@/components/brand/Star";
import { Starfield } from "@/components/sky/Sky";

export default function PayFailPage() {
  return (
    <main className="signin-page" lang="ru">
      <Starfield />
      <div className="signin-inner pay-inner">
        <Star size={44} />
        <h1 className="signin-title">Оплата не прошла</h1>
        <p className="signin-lead">
          Деньги не списаны. Так бывает — банк отклонил операцию или платёж
          отменили. Попробуй ещё раз: на форме можно выбрать СБП вместо карты.
        </p>
        <div className="pay-form">
          <a className="btn btn-gold btn-block" href="/pay">
            Попробовать ещё раз
          </a>
        </div>
      </div>
    </main>
  );
}
