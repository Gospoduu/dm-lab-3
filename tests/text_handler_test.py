import pytest
import os
from collections import Counter

from src.handlers import TextHandler

def test_check_chunk_reading():
    test_file = "data/test.txt"
    handler = TextHandler()
    all_text = ""
    for chunk in handler.get_text_chunk(test_file):
        all_text += chunk
    text_from_file = open(test_file, "r").read()
    assert text_from_file == all_text

def test_check_stats():
    test_file = "data/test.txt"
    handler = TextHandler()
    text_from_file = open(test_file, "r", encoding="utf-8").read()
    count_symbols = Counter(text_from_file)
    handler_counter, ln = handler.get_symbols_stats_from_txt(test_file)

    all_symb_cnt = 0
    all_symb_from_stats_count = 0
    for symbol, count in handler_counter.items():
        all_symb_from_stats_count += count
        assert count == count_symbols[symbol]
    for symbol, count in count_symbols.items():
        all_symb_cnt += count
        assert count == handler_counter[symbol]

    assert all_symb_from_stats_count == all_symb_cnt
    assert all_symb_cnt == ln
    assert all_symb_from_stats_count == ln





