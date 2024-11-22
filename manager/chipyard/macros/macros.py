import abc

class Macros(abc.ABC):
    """
        Generate chisel configuration for macros.
    """
    def __init__(self, configs: dict) -> None:
        super().__init__()
        self.chipyard_root = configs["chipyard_root"]
        self.macros = {}

    @abc.abstractmethod
    def run(self):
        raise NotImplementedError    
