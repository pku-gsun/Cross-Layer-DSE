import os
import abc

class Benchmark(abc.ABC):
    """
        Base class for benchmark suite.
        The benchmark suite is essentially a dictionary
        Each item is also a dict containing:
        - elf: executable file
        - inputs: list of input arguments
        - options: list of options
    """

    def __init__(self) -> None:
        super().__init__()

    @property
    def name(self):
        raise NotImplementedError
    
    @abc.abstractmethod
    def __len__(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def __iter__(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def __getitem__(self, item):
        raise NotImplementedError()
    
