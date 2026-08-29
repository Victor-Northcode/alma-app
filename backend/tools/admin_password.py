"""Сгенерировать `ALMA_ADMIN_PASSWORD_HASH` из пароля админки.

    python -m tools.admin_password

Спросит пароль (не показывая его и не пуская в историю оболочки), напечатает
готовую строку для `.env`:

    ALMA_ADMIN_PASSWORD_HASH=scrypt$32768$8$1$<соль>$<хэш>

Пароль сюда вводит владелец сам — как и все прочие секреты (закон продукта). В
непривычном окружении без tty можно передать пароль первым аргументом, но тогда
он попадёт в историю: getpass надёжнее.
"""

from __future__ import annotations

import getpass
import sys

from alma.auth.admin_password import hash_password


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        password = argv[1]
    else:
        password = getpass.getpass("admin password: ")
        again = getpass.getpass("repeat: ")
        if password != again:
            print("passwords do not match", file=sys.stderr)
            return 1
    if not password:
        print("password must not be empty", file=sys.stderr)
        return 1
    print(f"ALMA_ADMIN_PASSWORD_HASH={hash_password(password)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
