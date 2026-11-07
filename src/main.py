from src.handlers import TextHandler
from src.handlers.encoders import ShanonFanoEncoder, HuffmanEncoder

if __name__ == '__main__':
    test_file = "data/test.txt"
    handler = TextHandler(1024)

    for idx, chunk in enumerate(handler.get_text_chunk(test_file)):
        print("="*5,"chunk", idx,"="*5)
        print(chunk)
    print()
    stats, inf = handler.get_symbols_prob(test_file)

    print(stats)
    print(inf)
    print()
    encoder = HuffmanEncoder()
    print("HuffmanEncoder")
    print(encoder.encode(stats))
    print()
    encoder = ShanonFanoEncoder()
    print("ShanonFanoEncoder")
    print(encoder.encode(stats))