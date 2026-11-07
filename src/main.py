"""Точка входа для лабораторной работы №3: коды Шеннона-Фано и Хаффмана."""

from dataclasses import dataclass, field
from pathlib import Path

from src.handlers import TextHandler
from src.handlers.encoders.uniform import UniformEncoder
from src.handlers.encoders import ShanonFanoEncoder
from src.handlers.encoders.huffman import HuffmanEncoder
from src.handlers import TextCodec, EncodingResult

# _add_escape_to_codes живёт в модуле codec; если она не экспортируется
# через __init__.py — поправьте путь импорта под свою структуру пакета.
from src.handlers import add_escape_to_codes


ESCAPE = "¤"


# ============================================================================
# Модели данных
# ============================================================================

@dataclass
class TextData:
    name: str
    path: str
    stats: dict[str, float]
    entropy: float
    codes: dict[str, dict[str, str]]                              # algo -> {symbol -> code}
    results: list[EncodingResult]                                 # свои результаты
    foreign_codes: dict[tuple[str, str], dict[str, str]] = field(default_factory=dict)
    # ключ: (имя_чужого_текста, algo) -> коды с escape
    foreign: dict[tuple[str, str], "EncodingResult | str"] = field(default_factory=dict)
    # ключ: (имя_чужого_текста, algo) -> результат или текст ошибки


# ============================================================================
# Форматирование
# ============================================================================

def fmt_table(headers, rows, aligns=None):
    aligns = aligns or "l" * len(headers)
    widths = [len(str(h)) for h in headers]
    for r in rows:
        for i, v in enumerate(r):
            widths[i] = max(widths[i], len(str(v)))

    def render(row):
        return "  ".join(
            str(v).ljust(w) if a == "l" else str(v).rjust(w)
            for v, w, a in zip(row, widths, aligns)
        )

    sep = "  ".join("-" * w for w in widths)
    return "\n".join([render(headers), sep] + [render(r) for r in rows])


def print_code_table(title, stats, codes_by_algo, algos, escape=None):
    """Таблица кодов: строка — символ, столбец — код в данной кодировке."""
    print(f"\n  {title}")
    print(f"  {'─' * len(title)}")

    rows = []
    any_missing = False
    for symbol in sorted(stats, key=lambda s: (-stats[s], s)):
        cells = []
        for algo in algos:
            code = codes_by_algo.get(algo, {}).get(symbol)
            if code is None:
                cells.append("—")
                any_missing = True
            else:
                cells.append(code)
        rows.append([repr(symbol), f"{stats[symbol]:.4f}", *cells])

    # строка для escape-символа (если он присутствует в кодах)
    if escape is not None:
        esc_cells = [codes_by_algo.get(algo, {}).get(escape, "—") for algo in algos]
        if any(c != "—" for c in esc_cells):
            rows.append([f"[esc] {escape}", "—", *esc_cells])

    headers = ["символ", "частота", *algos]
    table = fmt_table(headers, rows, "l" + "r" * (len(headers) - 1))
    for line in table.splitlines():
        print(f"  {line}")
    if any_missing:
        if escape is not None:
            print(f"     — : символ отсутствует в чужом коде → "
                  f"будет закодирован через escape-маркер {escape!r}")
        else:
            print("     — : символ отсутствует в этой кодировке → закодировать нельзя")


def print_analytics(data: TextData):
    """Аналитика по одному тексту — все пункты задания."""
    r0 = data.results[0]

    print(f"\n Аналитика:")
    print(f"    Исходный текст ────────────────────────────────────────────")
    print(f"    файл:                  {data.path}")
    print(f"    количество символов:   {r0.original_symbols}")
    print(f"    размер файла (UTF-8):  {r0.original_bytes} Б")
    print(f"    энтропия H:            {data.entropy:.4f} бит/символ")
    print(f"    ───────────────────────────────────────────────────────────")

    # Свои коды
    print(f"\n  Свои коды:")
    headers = ["код", "L, бит/симв", "L-H", "bits", "payload", "meta",
               "total", "pl/orig", "tot/orig"]
    rows = []
    for r in data.results:
        rows.append([
            r.algorithm,
            f"{r.avg_len_bits:.4f}",
            f"{r.avg_len_bits - data.entropy:+.4f}",
            r.bits_len,
            f"{r.payload_bytes} Б",
            f"{r.meta_bytes} Б",
            f"{r.total_bytes} Б",
            f"{r.ratio_payload:.3f}",
            f"{r.ratio_total:.3f}",
        ])
    for line in fmt_table(headers, rows, "l" + "r" * (len(headers) - 1)).splitlines():
        print(f"  {line}")
    print("  (bits = символов в закодированном тексте; каждый бит — отдельный символ)")
    print("  (payload — чистый поток без метаданных; total = payload + meta)")

    # Чужие коды
    if not data.foreign:
        return

    print(f"\n  Чужие коды (lossless через escape-маркер {ESCAPE!r}):")
    by_other: dict[str, list] = {}
    for (other_name, algo), val in data.foreign.items():
        own = next(r for r in data.results if r.algorithm == algo)
        if isinstance(val, EncodingResult):
            delta = val.bits_len - own.bits_len
            pct = (val.bits_len / own.bits_len - 1) * 100 if own.bits_len else 0.0
            by_other.setdefault(other_name, []).append([
                algo,
                f"{own.avg_len_bits:.4f}", own.bits_len,
                f"{val.avg_len_bits:.4f}", val.bits_len,
                f"{delta:+d}", f"{pct:+.1f}%",
                str(val.escaped_count),
            ])
        else:
            by_other.setdefault(other_name, []).append([
                algo,
                f"{own.avg_len_bits:.4f}", own.bits_len,
                "—", "—", "—", "—",
                f"ошибка: {val}",
            ])

    for other_name, rows in by_other.items():
        print(f"\n    коды построены по тексту {other_name}:")
        headers = ["код", "L (свой)", "bits (свой)", "L (чужой)",
                   "bits (чужой)", "Δ bits", "Δ %", "escaped"]
        for line in fmt_table(headers, rows).splitlines():
            print(f"    {line}")


def print_summary(data: dict[str, TextData]):
    print(f"\n{'═' * 80}")
    print("ИТОГИ")
    print(f"{'═' * 80}")
    for td in data.values():
        r0 = td.results[0]
        print(f"\n▸ {td.name}: H = {td.entropy:.4f} бит/симв, "
              f"{r0.original_symbols} символов, {r0.original_bytes} Б")

        best = min(td.results, key=lambda r: r.bits_len)
        worst = max(td.results, key=lambda r: r.bits_len)
        print(f"  Лучший:  {best.algorithm:12} "
              f"({best.bits_len} bits, L={best.avg_len_bits:.4f})")
        print(f"  Худший:  {worst.algorithm:12} "
              f"({worst.bits_len} bits, L={worst.avg_len_bits:.4f})")
        print(f"  Выигрыш: {worst.bits_len - best.bits_len} bits "
              f"({(1 - best.bits_len / worst.bits_len) * 100:.1f}%)")

        for (other_name, algo), val in td.foreign.items():
            if isinstance(val, EncodingResult):
                own = next(r for r in td.results if r.algorithm == algo)
                delta = val.bits_len - own.bits_len
                if delta > 0:
                    print(f"  Чужой {algo} (по {other_name}) хуже своего на "
                          f"{delta} bits (+{delta / own.bits_len * 100:.1f}%), "
                          f"escaped: {val.escaped_count}")


# =================================================
# main
# =================================================

def main() -> None:
    # === 1. Инициализация ===
    handler = TextHandler()
    codec = TextCodec(handler)
    encoders = {
        "Uniform":     UniformEncoder(),
        "ShannonFano": ShanonFanoEncoder(),
        "Huffman":     HuffmanEncoder(),
    }
    text_paths = ["data/voina_i_mir.txt", "data/hamlet.txt"]

    # === 2. Свои коды и результаты ===
    data: dict[str, TextData] = {}
    for path in text_paths:
        stem = Path(path).stem
        stats, H = handler.get_symbols_prob(path)
        codes = {algo: enc.encode(stats) for algo, enc in encoders.items()}

        results = [
            codec.encode(path, c, algorithm=algo, name=f"{stem}_{algo}")
            for algo, c in codes.items()
        ]

        data[stem] = TextData(
            name=stem, path=path, stats=stats, entropy=H,
            codes=codes, results=results,
        )

    # === 3. Чужие коды (lossless через escape) ===
    for own in data.values():
        for other in data.values():
            if own.name == other.name:
                continue

            for algo in encoders.keys():
                try:
                    foreign_codes_esc, _ = add_escape_to_codes(
                        other.codes[algo], ESCAPE
                    )
                except ValueError as e:
                    own.foreign[(other.name, algo)] = str(e)
                    continue

                own.foreign_codes[(other.name, algo)] = foreign_codes_esc

                try:
                    r = codec.encode(
                        own.path,
                        foreign_codes_esc,
                        algorithm=algo,
                        name=f"{own.name}_foreign_{other.name}_{algo}",
                        escape=ESCAPE,
                        stats=own.stats,   # для авто-вычисления unknown_bits
                    )
                    own.foreign[(other.name, algo)] = r
                except ValueError as e:
                    own.foreign[(other.name, algo)] = str(e)

    # === 4. Вывод ===
    algos = list(encoders.keys())

    print("=" * 80)
    print("ЛАБОРАТОРНАЯ РАБОТА №3: КОДЫ ШЕННОНА-ФАНО И ХАФФМАНА")
    print("=" * 80)

    for td in data.values():
        print(f"\n{'═' * 80}")
        print(f"ТЕКСТ: {td.name}  ({td.path})")
        print(f"{'═' * 80}")

        # 4.1: таблица своих кодов
        print_code_table(
            "Таблица кодов (свои — построены по этому тексту)",
            td.stats, td.codes, algos,
        )

        # 4.2: таблицы чужих кодов
        for other in data.values():
            if other.name == td.name:
                continue
            foreign_codes_for_display = {
                algo: td.foreign_codes.get((other.name, algo), {})
                for algo in algos
            }
            print_code_table(
                f"Таблица кодов (чужие — построены по тексту {other.name}, "
                f"применены к {td.name})",
                td.stats, foreign_codes_for_display, algos, escape=ESCAPE,
            )

        # 4.3: аналитика
        print_analytics(td)

    # 4.4: сводка
    print_summary(data)


if __name__ == "__main__":
    main()