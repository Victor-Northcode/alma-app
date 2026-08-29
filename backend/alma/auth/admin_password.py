"""Хэш пароля админки — солёный и медленный, а не голый SHA-256.

**Зачем отдельный медленный KDF, если хэш и так не в сети.** До 29.08.2026
пароль хранился как `sha256(password)` — несолёный и быстрый. Тайминг закрывал
`hmac.compare_digest`, но сам хэш не сопротивлялся перебору: SHA-256 считается
миллиардами в секунду на GPU, а пароль «не-высокой энтропии» (а именно такой
владелец наберёт с телефона) перебирается по словарю за минуты, стоит хэшу
утечь — дамп `.env`, бэкап, тикет. В связке с обходом троттла (BUG-003) это был
и реальный онлайн-перебор. Найдено аудитом 29.08.2026 (BUG-005).

`hashlib.scrypt` из stdlib: соль на каждый хэш (две одинаковые пароли — разные
строки), и настраиваемая цена, из-за которой одна проверка стоит десятки
миллисекунд, а перебор — годы. Никакой сторонней зависимости — argon2/bcrypt
пришлось бы тянуть колесом, а scrypt уже в стандартной библиотеке.

**Формат строки — самоописывающийся:** `scrypt$<n>$<r>$<p>$<salt_hex>$<dk_hex>`.
Параметры лежат рядом с хэшем, поэтому их можно поднять завтра, не трогая уже
розданные строки: проверка читает цену из самой строки, а не из константы в
коде. Старый голый 64-символьный SHA-256 сюда не подходит намеренно —
`verify` его отвергает, а не принимает по-тихому: принять его значило бы
оставить дыру, ради которой всё это и написано. Деплой с таким значением
получает честный отказ входа и строку в лог «перегенерируй `tools.admin_password`».
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os

log = logging.getLogger("alma.auth.admin_password")

#: Параметры scrypt. `n` — работа (степень двойки), `r`/`p` — блок и
#: параллелизм. 2**15 = 32768 держит одну проверку около 30–60 мс на сервере —
#: неощутимо для входа раз в сутки и дорого для перебора. Записываются в строку,
#: так что поднять их можно не ломая существующие хэши.
_N = 1 << 15
_R = 8
_P = 1
#: Длина соли и выводимого ключа в байтах.
_SALT_BYTES = 16
_DK_BYTES = 32
#: `scrypt` требует `maxmem` ≥ ~128*n*r; по умолчанию 0 = 32 МБ, чего при n=2**15
#: не хватает и вызов падает. Считаем с запасом.
_MAXMEM = 128 * _N * _R * 2


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Собрать самоописывающуюся строку хэша для `ALMA_ADMIN_PASSWORD_HASH`.

    `salt=` — только для тестов, которым нужен воспроизводимый вывод; в проде
    соль всегда случайная.
    """
    if salt is None:
        salt = os.urandom(_SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_N,
        r=_R,
        p=_P,
        dklen=_DK_BYTES,
        maxmem=_MAXMEM,
    )
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${derived.hex()}"


def verify(password: str, stored: str) -> bool:
    """Верен ли пароль. Сравнение постоянного времени, параметры — из строки.

    `False` на любой невнятной строке, а не исключение: старый SHA-256 в конфиге
    — не крэш, а «этот деплой надо перенастроить», и login отвечает на него
    обычным отказом, залогировав причину один раз выше по стеку.
    """
    parts = stored.strip().split("$")
    if len(parts) != 6 or parts[0] != "scrypt":
        return False
    try:
        n, r, p = int(parts[1]), int(parts[2]), int(parts[3])
        salt = bytes.fromhex(parts[4])
        expected = bytes.fromhex(parts[5])
    except (ValueError, TypeError):
        return False
    try:
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(expected),
            maxmem=128 * n * r * 2,
        )
    except ValueError:
        return False
    return hmac.compare_digest(derived, expected)


def looks_like_scrypt(stored: str) -> bool:
    """Строка в новом формате? Чтобы login мог отличить старый SHA-256 и сказать."""
    return stored.strip().startswith("scrypt$") and stored.count("$") == 5
