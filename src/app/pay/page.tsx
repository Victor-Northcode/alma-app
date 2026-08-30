"use client";

/**
 * «/pay» — русская страница оплаты через Т-Банк: СБП и российская карта.
 *
 * Существует по ТЗ владельца от 29.08.2026 («оплата как у Twinby»): русский
 * покупатель с российской картой не может заплатить в App Store, поэтому
 * платит здесь — входит той же почтой, что в приложении, выбирает продукт,
 * уходит на платёжную форму Т-Банка, и доступ привязывает к аккаунту
 * подписанный вебхук. Приложению остаётся «Обновить доступ».
 *
 * Страница нарочно **отдельная и целиком русская** («сделай русский
 * отдельно» — слово владельца): у сайта нет русской локали, и заводить её
 * ради одной страницы значило бы переводить весь лендинг. Заголовок и
 * подзаголовок — формулировки владельца из ТЗ, дословно.
 *
 * Ни одного числа страница не знает: витрину присылает
 * `/v1/billing/catalogue?country=RU` (рублёвая полоса), сумму называет `Init`
 * на сервере, а доступ выдаёт только вебхук. Русские имена товаров ниже — не
 * «выдуманные строки» продукта: продукт живёт в приложении на семи языках, а
 * это витрина той же полки для страницы, у которой нет словаря. Карточка
 * товара, чьего slug здесь нет, не прячется, а рисуется с серверным именем —
 * витрина не смеет скрывать то, что продаёт каталог.
 */

import { useCallback, useEffect, useState } from "react";
import { Star } from "@/components/brand/Star";
import { Starfield } from "@/components/sky/Sky";
import { API_BASE, api, isOk, readToken, writeToken } from "@/lib/api";
import { looksLikeEmail } from "@/lib/email";

/** Вклейки — те же файлы, что видит приложение, с того же сервера. */
const PLATES = `${API_BASE}/static/plates`;

type ShelfItem = {
  slug: string;
  name: string;
  kind: string;
  interval: string | null;
  display: string;
};

type Shelf = {
  provider?: string;
  merchant?: string;
  unlocked?: string[];
  items?: ShelfItem[];
};

/**
 * Русская витрина по slug'у каталога. Slug — единственный контракт: имена и
 * подписи серверный каталог держит по-английски, а вклейка — вообще знание
 * приложения. Порядок здесь же: подписка первой, как в приложении.
 */
const SHOWCASE: Record<string, { name: string; blurb: string; plate: string }> = {
  "sub.monthly": {
    name: "Вся Alma — на месяц",
    blurb:
      "Все восемь систем, живой прогноз каждый день и вопросы к Alma. " +
      "Продлевается само, отменяется в пару нажатий — доступ дожидается конца оплаченного месяца.",
    plate: "plate-sky",
  },
  "bundle.static": {
    name: "Пять разборов — навсегда",
    blurb:
      "Все пять постоянных систем одной покупкой. Остаются твоими без всякой подписки.",
    plate: "plate-seal",
  },
  "door.natal": {
    name: "Натальная карта",
    blurb: "Полный разбор твоего неба — навсегда.",
    plate: "plate-face",
  },
  "door.numerology": {
    name: "Нумерология",
    blurb: "Все числа твоего имени и даты — навсегда.",
    plate: "plate-eleven",
  },
  "door.birth-card": {
    name: "Карта рождения",
    blurb: "Твоя карта в колоде и её год — навсегда.",
    plate: "plate-soulcard",
  },
  "door.astrocartography": {
    name: "Астрокартография",
    blurb: "Твои линии на карте мира — навсегда.",
    plate: "plate-here",
  },
  "door.synthesis": {
    name: "Перекрёстный синтез",
    blurb: "Что все системы говорят хором — навсегда.",
    plate: "plate-synthesis",
  },
  "pair.check": {
    name: "Проверка пары",
    blurb: "Один разбор совместимости для вас двоих.",
    plate: "plate-love",
  },
};

const ORDER = Object.keys(SHOWCASE);

export default function PayPage() {
  const [shelf, setShelf] = useState<Shelf | null>(null);
  const [stage, setStage] = useState<"email" | "code" | "shop">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [held, setHeld] = useState<string[] | null>(null);

  useEffect(() => {
    // Страна названа явно: страница русская, и витрина обязана быть рублёвой
    // независимо от того, из какой сети её открыли.
    void api.catalogue("RU").then((r) => {
      if (isOk(r)) setShelf(r.data as Shelf);
    });
    if (readToken()) setStage("shop");
  }, []);

  const sendCode = useCallback(async () => {
    const address = email.trim().toLowerCase();
    if (!looksLikeEmail(address)) {
      setNotice("Проверь адрес почты.");
      return;
    }
    setBusy("send");
    setNotice(null);
    const r = await api.requestMagicLink(address, "ru");
    setBusy(null);
    if (!isOk(r)) {
      setNotice(
        r.kind === "offline"
          ? "Нет связи. Попробуй ещё раз."
          : "Письмо не отправилось. Попробуй через минуту.",
      );
      return;
    }
    setStage("code");
    setNotice(null);
    // Локальная песочница без почтового провайдера возвращает код прямо в
    // ответе — поле заполняется само, и вход проходится глазами. В проде
    // ветка недостижима (см. `_may_show_debug_token` на бекенде).
    if (r.data.debug_code) setCode(r.data.debug_code);
  }, [email]);

  const consume = useCallback(async () => {
    setBusy("code");
    setNotice(null);
    const r = await api.consumeEmailCode(email.trim().toLowerCase(), code.trim());
    setBusy(null);
    if (isOk(r)) {
      writeToken(r.data.token);
      setStage("shop");
      return;
    }
    if (r.kind === "error" && r.code === "link_expired") {
      setNotice("Код истёк — запроси новый.");
    } else if (r.kind === "error" && r.code === "link_used") {
      setNotice("Этот код уже использован — запроси новый.");
    } else {
      setNotice("Код не подошёл. Проверь цифры из письма.");
    }
  }, [email, code]);

  const buy = useCallback(async (product: string) => {
    setBusy(product);
    setNotice(null);
    const r = await api.checkout(product, { country: "RU" });
    setBusy(null);
    if (isOk(r) && r.data.checkout_url) {
      // Уход на форму Т-Банка. Возврат — `/pay/done` или `/pay/fail`
      // (SuccessURL/FailURL адаптера); доступ выдаст вебхук, не возврат.
      window.location.href = r.data.checkout_url;
      return;
    }
    if (!isOk(r) && r.kind === "error" && r.code === "already_owned") {
      setNotice("Это уже открыто на твоём аккаунте — второй раз платить не надо.");
    } else if (!isOk(r) && r.kind === "error" && r.code === "email_required") {
      setNotice("Для чека нужна почта — войди по коду из письма и повтори.");
    } else if (!isOk(r) && r.kind === "unavailable") {
      setNotice("Оплата пока не подключена. Загляни чуть позже.");
    } else if (!isOk(r) && r.kind === "unauthenticated") {
      setStage("email");
      setNotice("Сначала войди — той же почтой, что в приложении.");
    } else {
      setNotice("Платёжная форма не открылась. Попробуй ещё раз.");
    }
  }, []);

  const refresh = useCallback(async () => {
    setBusy("refresh");
    setNotice(null);
    const r = await api.entitlements();
    setBusy(null);
    if (isOk(r)) {
      setHeld(r.data.unlocked ?? []);
    } else if (r.kind === "unauthenticated") {
      setStage("email");
      setNotice("Сначала войди — той же почтой, что в приложении.");
    } else {
      setNotice("Не получилось проверить. Попробуй ещё раз.");
    }
  }, []);

  const items = [...(shelf?.items ?? [])].sort(
    (a, b) =>
      (ORDER.indexOf(a.slug) + 1 || ORDER.length + 1) -
      (ORDER.indexOf(b.slug) + 1 || ORDER.length + 1),
  );

  return (
    <main className="signin-page" lang="ru">
      <Starfield />
      <div className="signin-inner pay-inner">
        <Star size={44} />
        {/* Заголовок и лид — текст владельца из ТЗ, дословно (кроме «ты»). */}
        <h1 className="signin-title">Оплата российской картой или через СБП</h1>
        <p className="signin-lead">
          Войди тем же способом, которым входишь в приложении. После оплаты
          доступ автоматически появится на всех твоих устройствах.
        </p>

        {stage === "email" && (
          <div className="pay-form">
            <input
              className="text-input"
              type="email"
              inputMode="email"
              autoComplete="email"
              placeholder="Твоя почта"
              aria-label="Твоя почта"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void sendCode()}
            />
            <button
              type="button"
              className="btn btn-gold btn-block"
              disabled={busy !== null}
              onClick={() => void sendCode()}
            >
              {busy === "send" ? "Отправляю…" : "Войти и оплатить"}
            </button>
            <p className="signin-note">
              Почта нужна для входа и чека об оплате. Никаких рассылок.
            </p>
          </div>
        )}

        {stage === "code" && (
          <div className="pay-form">
            <p className="signin-sent">
              Код из шести цифр уже летит на почту. Он работает один раз и
              живёт 20 минут.
            </p>
            <input
              className="text-input"
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="Код из письма"
              aria-label="Код из письма"
              value={code}
              maxLength={6}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              onKeyDown={(e) => e.key === "Enter" && code.length === 6 && void consume()}
            />
            <button
              type="button"
              className="btn btn-gold btn-block"
              disabled={busy !== null || code.length !== 6}
              onClick={() => void consume()}
            >
              {busy === "code" ? "Проверяю…" : "Войти"}
            </button>
            <button
              type="button"
              className="btn btn-outline btn-block"
              onClick={() => {
                setStage("email");
                setCode("");
                setNotice(null);
              }}
            >
              Другая почта
            </button>
          </div>
        )}

        {stage === "shop" && (
          <div className="pay-shop">
            {items.length === 0 && (
              <p className="signin-sent">Витрина загружается…</p>
            )}
            {items.map((item) => {
              const face = SHOWCASE[item.slug];
              // Никакого «Уже открыто» по списку `unlocked`: подписка
              // открывает все восемь систем, и такая пометка запирала бы
              // подписчику законную покупку двери навсегда («купить дверь
              // про запас, будучи подписчиком, законно» —
              // `entitlements.already_owned`, BUG-007). Что дубль, а что
              // нет, решает сервер: его 409 показывается запиской ниже.
              return (
                <div className="pay-card" key={item.slug}>
                  {face && (
                    <img
                      className="pay-plate"
                      src={`${PLATES}/${face.plate}.webp`}
                      alt=""
                      width={64}
                      height={84}
                      loading="lazy"
                    />
                  )}
                  <div className="pay-card-words">
                    <strong>{face?.name ?? item.name}</strong>
                    {face && <p className="signin-note pay-blurb">{face.blurb}</p>}
                  </div>
                  <div className="pay-card-side">
                    <span className="pay-price">{item.display}</span>
                    <button
                      type="button"
                      className="btn btn-gold"
                      disabled={busy !== null}
                      onClick={() => void buy(item.slug)}
                    >
                      {busy === item.slug
                        ? "Открываю…"
                        : item.interval
                          ? "Оформить"
                          : "Купить"}
                    </button>
                  </div>
                </div>
              );
            })}

            <button
              type="button"
              className="btn btn-outline btn-block"
              disabled={busy !== null}
              onClick={() => void refresh()}
            >
              {busy === "refresh" ? "Проверяю…" : "Уже оплатили? Обновить доступ"}
            </button>
            {held !== null && (
              <p className="signin-sent" role="status">
                {held.length
                  ? "Доступ на месте. Открой приложение — всё уже там."
                  : "Оплаченного пока не видно. Если платил только что — подожди минуту и проверь ещё раз."}
              </p>
            )}
          </div>
        )}

        {notice && (
          <p className="signin-error" role="alert">
            {notice}
          </p>
        )}

        <div className="pay-legal">
          <p className="signin-note">
            Приложение Alma — в App Store и Google Play. После оплаты открой
            его и войди той же почтой: доступ подтянется сам.
          </p>
          <p className="signin-note">
            {/* Имя продавца — только когда витриной правит сам Т-Банк: пока
                глобальный процессор другой (Paddle до включения ключей),
                каталог называет ЕГО merchant, и строка «Продавец:
                Paddle.com Market Ltd» рядом с «оплату принимает Т-Банк»
                была неправдой — поймано на проде 30.08.2026. */}
            {shelf?.provider === "tbank" && shelf.merchant
              ? `Продавец: ${shelf.merchant}. `
              : ""}
            Оплату принимает Т-Банк. Цена и период списания видны до оплаты.
            Подписка продлевается автоматически, пока не отменишь; после
            отмены доступ сохраняется до конца оплаченного периода, разовые
            покупки остаются навсегда.
          </p>
          <p className="signin-note">
            Alma носит ознакомительный и развлекательный характер и не
            является медицинской, психологической, юридической или финансовой
            консультацией. <a href="/terms">Условия</a> ·{" "}
            <a href="/privacy">Конфиденциальность</a> ·{" "}
            <a href="/refunds">Возвраты</a>
          </p>
        </div>
      </div>
    </main>
  );
}
