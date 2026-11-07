import collections

from src.handlers.encoders.base import BaseEncoder


class ShanonFanoEncoder(BaseEncoder):
    def encode(self, stats: dict[str, float]):
        if not stats:
            return {}

        if len(stats) == 1:
            symbol = next(iter(stats))
            return {symbol: "0"}
        queue = [
            (symbol, stats[symbol])
            for symbol in sorted(
                stats.keys(),
                key=lambda x: stats[x],
            )
        ]
        codes = collections.defaultdict(str)
        def add_code(symbols: list[tuple[str, float]]):
            if len(symbols) == 1:
                return
            if len(symbols) <= 2:
                code = 0
                for symbol in symbols:
                    codes[symbol[0]] += str(code)
                    code += 1
                return
            all_prb = sum(s[1] for s in symbols)

            prb_sum = 0
            last_prb_delta = all_prb
            last_idx = 0

            for idx, symbol in enumerate(symbols):
                new_sm = prb_sum + symbol[1]
                new_prb_delta = abs(all_prb/2 - new_sm)
                if new_prb_delta > last_prb_delta:
                    last_idx = idx
                    break
                prb_sum = new_sm
                last_prb_delta = new_prb_delta
            zeros = []
            for symbol in symbols[:last_idx]:
                zeros.append(symbol)
                codes[symbol[0]] += '0'
            ones = []
            for symbol in symbols[last_idx:]:
                ones.append(symbol)
                codes[symbol[0]] += '1'
            add_code(zeros)
            add_code(ones)
        add_code(queue)
        return dict(codes)







