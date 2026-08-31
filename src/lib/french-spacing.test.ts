import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { dictionaries } from "./i18n";

/**
 * Французская типографика на сайте — тот же закон, что держат
 * `backend/tests/test_french_spacing.py` и `test/french_spacing_test.dart`
 * в приложении: узкий неразрывный пробел U+202F перед `? ! ; :` и внутри
 * «ёлочек». Словарь сайта жил вне обоих сторожей, и до 31.08.2026 в нём
 * было ноль таких пробелов при четырнадцати нужных местах — весь
 * французский лендинг переносил знаки препинания на новую строку.
 *
 * Обходится словарь целиком через объект, а не файл: строка, пришедшая из
 * функции (`sun`, `chapters`…), проверяется на образце вызова.
 */

const NNBSP = " ";

/** Все строковые листья словаря, с путём до каждого. */
function leaves(node: unknown, path: string, found: [string, string][]): void {
  if (typeof node === "string") {
    found.push([path, node]);
  } else if (typeof node === "function") {
    // Образец вызова: числа и имена, безопасные для любой сигнатуры.
    try {
      const sample = (node as (...a: unknown[]) => unknown)("Sofia", 3);
      if (typeof sample === "string") found.push([`${path}()`, sample]);
    } catch {
      /* функции с иной сигнатурой дословно строк не прячут */
    }
  } else if (Array.isArray(node)) {
    node.forEach((item, i) => leaves(item, `${path}[${i}]`, found));
  } else if (node && typeof node === "object") {
    for (const [key, value] of Object.entries(node)) {
      leaves(value, `${path}.${key}`, found);
    }
  }
}

describe("французские пробелы в словаре сайта", () => {
  const found: [string, string][] = [];
  leaves(dictionaries.fr, "fr", found);

  it("видит словарь вообще", () => {
    expect(found.length).toBeGreaterThan(100);
  });

  it("перед ? ! ; : стоит узкий неразрывный пробел, а не обычный", () => {
    const broken = found.filter(([, text]) => / [?!;:]/.test(text));
    expect(
      broken.map(([path]) => path),
      "обычный пробел перед знаком — знак уедет на свою строку",
    ).toEqual([]);
  });

  it("ёлочки несут узкий пробел внутри", () => {
    const broken = found.filter(([, text]) => /« | »/.test(text));
    expect(broken.map(([path]) => path)).toEqual([]);
  });

  it("узкие пробелы в словаре есть — сторож не сторожит пустоту", () => {
    // Упадёт, если французский перепишут без единого U+202F: это не
    // «стало чисто», это значит регрессия вернула обычные пробелы.
    const carrying = found.filter(([, text]) => text.includes(NNBSP));
    expect(carrying.length).toBeGreaterThanOrEqual(10);
  });

  it("и в COPY страницы входа тоже", () => {
    // Два словаря живут в компонентах, не в i18n/ — до переезда их
    // французский проверяется по файлу.
    for (const file of [
      "src/app/sign-in/page.tsx",
      "src/components/auth/SignInPanel.tsx",
    ]) {
      const text = readFileSync(join(process.cwd(), file), "utf8");
      const fr = text.match(/fr:\s*\{([\s\S]*?)\n\s*\},/);
      expect(fr, `${file}: блок fr не найден`).toBeTruthy();
      const bad = (fr![1].match(/"[^"]* [?!;:][^"]*"/g) ?? []).filter(
        (s) => !s.includes("=>"),
      );
      expect(bad, `${file}: обычный пробел перед знаком`).toEqual([]);
    }
  });
});
