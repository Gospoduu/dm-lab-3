import collections
from typing import Any

from src.handlers.encoders.base import BaseEncoder

class TreeNode:
    def __init__(
            self,
            symbols: list[str],
            weight: float,
            lch: Any | None = None,
            rch: Any | None = None
    ):
        self.symbols = symbols
        self.weight = weight
        self.lch = lch
        self.rch = rch

class HuffmanEncoder(BaseEncoder):
    def encode(self, stats: dict[str, float]):
        if not stats:
            return {}

        if len(stats) == 1:
            symbol = next(iter(stats))
            return {symbol: "0"}
        queue = [
            TreeNode([symbol], stats[symbol])
                for symbol in sorted(
                    stats.keys(),
                    key=lambda x: stats[x],
                    reverse=True
            )
        ]

        while len(queue) > 1:
            node1 = queue.pop()
            node2 = queue.pop()
            new_node = TreeNode(
                node1.symbols + node2.symbols,
                node1.weight + node2.weight,
                node1,
                node2,
                )

            pos = len(queue)
            while pos > 0 and queue[pos - 1].weight < new_node.weight:
                pos -= 1
            queue.insert(pos, new_node)

        codes = collections.defaultdict(str)
        start = queue[0]
        def step(node: TreeNode, side: str):
            if node is None:
                return
            for symbol in node.symbols:
                codes[symbol] += side
            if node.lch is not None:
                step(node.lch, "0")
            if node.rch is not None:
                step(node.rch, "1")
        step(start.lch, "0")
        step(start.rch, "1")
        return codes











