import os
from .benchmark import Benchmark
from utils import if_exist, assert_error

class GemminiBenchmark(Benchmark):
    """
        Gemmini benchmark suite.
    """

    def __init__(self, benchmark_root: str = None, chipyard_root: str = None, mode: str = 'baremetal') -> None:
        """
            benchmark root should be in:
            $chipyard_root/generators/gemmini/software/gemmini-rocc-tests/build.
            Check Gemmini documentation to build executable files of benchmark programs.
        """
        super().__init__()
        super().__init__()
        self._benchmark_root = benchmark_root
        self._chipyard_root = chipyard_root
        self.mode = mode

        self._benchmark_suite = [
            "mobilenet",
            "resnet50",
            "mlp1",
            "mlp2",
            "mlp3",
            "mlp4",
            "transformer",
        ]
        self._macros = self.init_macros()
        self.validate()

    @property
    def name(self):
        return 'gemmini'
    
    @property
    def benchmark_root(self):
        if self._benchmark_root is not None:
            return self._benchmark_root
        if self._chipyard_root is not None:
            return os.path.join(self._chipyard_root, 'generators/gemmini/software/gemmini-rocc-tests/build')
        raise ValueError('benchmark root not found!')
    
    def __len__(self):
        return len(self._benchmark_suite)

    def __iter__(self):
        for k, v in self._macros.items():
            yield k, v

    def __getitem__(self, item):
        return self._macros[item]
    
    def init_macros(self):
        prefix = {
            "mobilenet": "imagenet",
            "resnet50": "imagenet",
            "mlp1": "mlps",
            "mlp2": "mlps",
            "mlp3": "mlps",
            "mlp4": "mlps",
            "transformer": "transformers",
        }
        suffix = self.mode
        return {k: {
            'name': k,
            'elf': os.path.join(self.benchmark_root, prefix[k], f'{k}-{suffix}'),
            'inputs': None,
            'options': None,
        } for k in self._benchmark_suite}

    def validate(self):
        # baremetal or proxy-kernel
        assert self.mode in ['baremetal', 'pk'], assert_error(f'Invalid gemmini benchmark mode: {self.mode}')
        
        for k, v in self._macros.items():
            if_exist(v['elf'], strict=True)