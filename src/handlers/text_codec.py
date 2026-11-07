from collections import deque
from dataclasses import dataclass
from pathlib import Path
import json

from src.handlers import TextHandler


@dataclass
class EncodingResult:
    name: str
    algorithm: str
    source_path: str
    folder: Path

    original_bytes: int
    original_symbols: int
    bits_len: int
    payload_bytes: int
    meta_bytes: int
    escaped_count: int = 0

    @property
    def total_bytes(self) -> int:
        return self.payload_bytes + self.meta_bytes

    @property
    def avg_len_bits(self) -> float:
        return self.bits_len / self.original_symbols if self.original_symbols else 0.0

    @property
    def ratio_payload(self) -> float:
        return self.payload_bytes / self.original_bytes if self.original_bytes else 0.0

    @property
    def ratio_total(self) -> float:
        return self.total_bytes / self.original_bytes if self.original_bytes else 0.0


def _find_free_code(codes: dict[str, str]) -> str:
    """Найти кратчайший код, свободный от конфликтов: не совпадает ни с одним
    существующим кодом и не является его префиксом или надстрокой.

    Для полного дерева (типичный Хаффман) свободного кода не существует —
    тогда бросает RuntimeError, и вызывающий код расширяет длиннейший лист.
    """
    code_set = set(codes.values())
    prefix_set: set[str] = set()
    for c in code_set:
        for i in range(1, len(c)):
            prefix_set.add(c[:i])

    queue = deque(["0", "1"])
    while queue:
        cand = queue.popleft()
        if cand in code_set:
            # это чей-то код — дети не годятся (нарушат префиксность)
            continue
        if cand in prefix_set:
            # это префикс чужого кода — сам кодом быть не может, но дети могут
            queue.append(cand + "0")
            queue.append(cand + "1")
            continue
        return cand
    raise RuntimeError("нет свободного кода: дерево полное")


def add_escape_to_codes(
    codes: dict[str, str],
    escape: str,
) -> tuple[dict[str, str], str]:
    """Добавить escape-символ в коды.

    Стратегия:
      1. Если есть свободный код (дерево неполное, типично для ШФ) — берём его.
      2. Иначе (полное дерево, типично для Хаффмана) — расширяем самый длинный
         лист: victim → victim_code + "0", escape → victim_code + "1".
    Возвращает (новые_коды, код_escape). Исходные коды не мутируются.
    """
    if escape in codes:
        raise ValueError(f"escape-символ {escape!r} уже присутствует в кодах")

    if not codes:
        return {escape: "0"}, "0"

    try:
        free = _find_free_code(codes)
        result = dict(codes)
        result[escape] = free
        return result, free
    except RuntimeError:
        pass

    victim = max(codes, key=lambda s: len(codes[s]))
    victim_code = codes[victim]
    result = dict(codes)
    result[victim] = victim_code + "0"
    result[escape] = victim_code + "1"
    return result, victim_code + "1"


class TextCodec:
    def __init__(self, handler: TextHandler):
        self.handler = handler

    @staticmethod
    def _encode_chunk(
        text: str,
        codes: dict[str, str],
        escape: str | None,
        unknown_bits: int,
    ) -> tuple[str, int]:
        if escape is None:
            missing = {ch for ch in text if ch not in codes}
            if missing:
                raise ValueError(f"Нет кодов для символов: {sorted(missing)}")
            return "".join(codes[ch] for ch in text), 0

        esc_code = codes[escape]
        parts: list[str] = []
        escaped = 0
        for ch in text:
            if ch in codes and ch != escape:
                parts.append(codes[ch])
            else:
                parts.append(esc_code + format(ord(ch), f"0{unknown_bits}b"))
                escaped += 1
        return "".join(parts), escaped

    def encode(
            self,
            path: str,
            codes: dict[str, str],
            name: str | None = None,
            algorithm: str = "custom",
            escape: str | None = None,
            unknown_bits: int | None = None,
            stats: dict[str, float] | None = None,
    ) -> EncodingResult:
        folder_name = name if name is not None else Path(path).stem
        out_dir = Path("codes") / folder_name
        out_dir.mkdir(parents=True, exist_ok=True)

        escape_code: str | None = None
        if escape is not None:
            if escape not in codes:
                raise ValueError(
                    f"escape-символ {escape!r} отсутствует в codes. "
                    f"Добавьте его через with_escape(stats, {escape!r}) "
                    f"перед построением кодов."
                )
            escape_code = codes[escape]

            if unknown_bits is None:
                if stats is not None:
                    missing = set(stats) - set(codes)
                else:
                    all_chars: set[str] = set()
                    for chunk in self.handler.get_text_chunk(path):
                        all_chars.update(chunk)
                    missing = all_chars - set(codes)
                max_ord = max((ord(c) for c in missing), default=0)
                unknown_bits = max(8, max_ord.bit_length())

        bits_buf = ""
        bits_len = 0
        symbols = 0
        escaped_count = 0

        with open(out_dir / "payload.bin", "wb") as f:
            for chunk in self.handler.get_text_chunk(path):
                parts: list[str] = []
                for ch in chunk:
                    if ch in codes and ch != escape:
                        parts.append(codes[ch])
                    elif escape_code is not None:
                        parts.append(
                            escape_code + format(ord(ch), f"0{unknown_bits}b")
                        )
                        escaped_count += 1
                    else:
                        raise ValueError(
                            f"Нет кода для символа {ch!r} (escape не задан)"
                        )
                enc = "".join(parts)
                bits_len += len(enc)
                symbols += len(chunk)
                bits_buf += enc

                n = (len(bits_buf) // 8) * 8
                if n:
                    f.write(bytes(
                        int(bits_buf[i:i + 8], 2) for i in range(0, n, 8)
                    ))
                    bits_buf = bits_buf[n:]

            if bits_buf:
                bits_buf += "0" * (8 - len(bits_buf))
                f.write(bytes([int(bits_buf, 2)]))

        meta: dict = {"codes": codes, "bits_len": bits_len}
        if escape is not None:
            meta["escape"] = escape
            meta["unknown_bits"] = unknown_bits

        with open(out_dir / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return EncodingResult(
            name=folder_name,
            algorithm=algorithm,
            source_path=path,
            folder=out_dir,
            original_bytes=Path(path).stat().st_size,
            original_symbols=symbols,
            bits_len=bits_len,
            payload_bytes=(out_dir / "payload.bin").stat().st_size,
            meta_bytes=(out_dir / "meta.json").stat().st_size,
            escaped_count=escaped_count,
        )

    def decode(self, folder: str | Path) -> str:
        folder = Path(folder)

        with open(folder / "meta.json", encoding="utf-8") as f:
            meta = json.load(f)

        codes: dict[str, str] = meta["codes"]
        bits_len: int = meta["bits_len"]
        escape: str | None = meta.get("escape")
        unknown_bits: int | None = meta.get("unknown_bits")

        if bits_len == 0:
            return ""

        if escape is not None and unknown_bits is None:
            raise ValueError("meta.json: escape задан, но unknown_bits отсутствует")

        escape_code: str | None = codes[escape] if escape is not None else None

        # escape исключаем из обычной таблицы — он обрабатывается отдельно
        reverse = {
            code: symbol
            for symbol, code in codes.items()
            if symbol != escape
        }
        max_len = max((len(c) for c in reverse), default=0)

        result: list[str] = []
        buf = ""
        remaining = bits_len

        with open(folder / "payload.bin", "rb") as f:
            while remaining > 0:
                chunk = f.read(65536)
                if not chunk:
                    raise ValueError(
                        f"payload.bin короче, чем {bits_len} бит из meta.json"
                    )
                bits = "".join(format(b, "08b") for b in chunk)
                if len(bits) > remaining:
                    bits = bits[:remaining]
                remaining -= len(bits)
                buf += bits

                while buf:
                    # 1. escape-ветвь: escape — лист, значит если buf начинается
                    #    с escape_code, это гарантированно escape-последовательность
                    if escape_code is not None and buf.startswith(escape_code):
                        need = len(escape_code) + unknown_bits
                        if len(buf) < need:
                            break  # ждём ещё бит
                        ord_bits = buf[len(escape_code):need]
                        result.append(chr(int(ord_bits, 2)))
                        buf = buf[need:]
                        continue

                    # 2. обычный код
                    matched = False
                    for length in range(1, min(len(buf), max_len) + 1):
                        if buf[:length] in reverse:
                            result.append(reverse[buf[:length]])
                            buf = buf[length:]
                            matched = True
                            break
                    if not matched:
                        break  # недособранный код, ждём ещё бит

        if buf:
            raise ValueError(f"остались неразобранные биты: {buf!r}")

        return "".join(result)