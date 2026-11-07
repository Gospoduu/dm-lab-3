import os
import collections
from typing import Generator
from contextlib import contextmanager
import codecs
import math

@contextmanager
def open_file(file: str):
    fd = os.open(file, os.O_RDONLY)
    try:
        yield fd
    finally:
        os.close(fd)



class TextHandler:
    def __init__(self, chunk_size = 1024 * 1024):
        self.chunk_size = chunk_size
        pass

    def get_symbols_prob(self, file: str):
        symbol_counts, ln = self.get_symbols_stats_from_txt(file)
        return self.get_probability_of_symbols_from_stats(symbol_counts, ln)

    def get_text_chunk(self, file: str) -> Generator[str]:
        if not os.path.exists(file):
            raise FileNotFoundError
        if not file.endswith(".txt"):
            raise ValueError(f"File {file} must be .txt format.")

        decoder = codecs.getincrementaldecoder("utf-8")()
        with open_file(file) as fd:
            while chunk := os.read(fd, self.chunk_size):
                yield decoder.decode(chunk)
        tail = decoder.decode(b"", final=True)
        if tail:
            yield tail


    def get_symbols_stats_from_txt(self, file: str) -> tuple[dict[str, int], int]:
        global_counter = collections.defaultdict(int)
        symbols_cnt = 0
        for chunk in self.get_text_chunk(file):
            chunk_counter = collections.Counter(chunk)
            for symbol, count in chunk_counter.items():
                global_counter[symbol] += count
            symbols_cnt += len(chunk)
        return global_counter, symbols_cnt

    def get_probability_of_symbols_from_stats(self, stats: dict[str, int], ln: int) -> tuple[dict[str, float], float]:
        imperial_prob = {}
        h = 0
        for symbol, count in stats.items():
            pi = count / ln
            imperial_prob[symbol] = pi
            h -= pi * math.log(pi, 2)
        return imperial_prob, h





