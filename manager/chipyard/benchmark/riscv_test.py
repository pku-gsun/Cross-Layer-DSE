import os
from .benchmark import Benchmark
from utils import if_exist

class RiscvTestBenchmark(Benchmark):
    """
        Riscv test benchmark suite.
    """
    def __init__(self, benchmark_root: str = None, chipyard_root: str = None) -> None:
        """
            benchmark root should be in: 
            $chipyard_root/.conda-env/riscv-tools/riscv64-unknown-elf/share/riscv-tests/benchmarks
        """
        super().__init__()
        self._benchmark_root = benchmark_root
        self._chipyard_root = chipyard_root

        self._benchmark_suite = [
            "dhrystone",
            "median",
            'mm',
            'mt-matmul',
            'mt-vvadd',
            "multiply",
            'pmp',
            "qsort",
            "rsort",
            "spmv",
            "towers",
            "vvadd"
        ]
        self._macros = {k: {
            'name': k,
            'elf': os.path.join(self.benchmark_root, f'{k}.riscv'),
            'inputs': None,
            'options': None,
        } for k in self._benchmark_suite}
        self.validate()

    @property
    def benchmark_root(self):
        if self._benchmark_root is not None:
            return self._benchmark_root
        if self._chipyard_root is not None:
            return os.path.join(self._chipyard_root, '.conda-env/riscv-tools/riscv64-unknown-elf/share/riscv-tests/benchmarks')
        raise ValueError('benchmark root not found!')

    @property
    def name(self):
        return 'riscv_test'

    def __len__(self):
        return len(self._benchmark_suite)

    def __iter__(self):
        for k, v in self._macros.items():
            yield k, v

    def __getitem__(self, item):
        return self._macros[item]
        
    def validate(self):
        for k, v in self._macros.items():
            if_exist(v['elf'], strict=True)