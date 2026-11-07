import math

from src.handlers.encoders.base import BaseEncoder

class UniformEncoder(BaseEncoder):
    def encode(self, stats: dict[str, float]) -> dict[str, str]:
        if not stats:
            return {}

        k = len(stats)
        bits = math.ceil(math.log2(k))
        symbols = list(stats)

        codes = {}
        for i, symbol in enumerate(symbols):
            codes[symbol] = bin(i)[2:].zfill(bits)
        return codes
