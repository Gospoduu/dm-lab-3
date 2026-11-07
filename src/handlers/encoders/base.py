from abc import ABC, abstractmethod

class BaseEncoder(ABC):
    @abstractmethod
    def encode(self, stats: dict[str, float]):
        pass
    def average_length(self, stats: dict[str, float]) -> float:
        codes = self.encode(stats)
        return sum(stats[s] * len(codes[s]) for s in stats)