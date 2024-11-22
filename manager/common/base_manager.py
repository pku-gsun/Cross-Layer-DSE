import abc
from time import sleep
from typing import Callable
from utils import timestamp, execute, dump_yaml, mkdir, get_dir, RoutineCheckError

class BaseManager(abc.ABC):
    """
        Base class for all the managers handling certain tools 
        (e.g. RTL generation, EDA tools, PDK generation)

        For each manager, define the steps that it should run.
    """

    def __init__(self, configs: dict) -> None:
        super(BaseManager, self).__init__()
        self.configs = configs
        mkdir(self.rundir)

    @property
    def name(self) -> str:
        """
            Name of the manager, to avoid manager input/output yaml file confusion.
        """
        raise NotImplementedError

    @property
    def rundir(self) -> str:
        """
            Directory to store intermediate files.
        """
        return self.configs.get('rundir')

    @property
    def input_path(self) -> str:
        default_input_path = f'{self.rundir}/{self.name}-input.yml'
        return self.configs.get('input_path', default_input_path)

    @property
    def output_path(self) -> str:
        default_output_path = f'{self.rundir}/{self.name}-output.yml'
        return self.configs.get('output_path', default_output_path)

    def routine_check(
        self,
        period: int,
        cmd: str,
        condition: Callable,
        wait: int = 1,
    ):
        """
        Perform a routine check by executing a command and checking a condition periodically.

        Args:
            period (int): The total duration in seconds for the routine check.
            cmd (str): The command to execute.
            condition (Callable): A callable object that represents the condition to be checked.
            wait (int, optional): The duration in seconds to wait between each check. Defaults to 1.

        Raises:
            RoutineCheckError: If the condition is not satisfied within the specified period.

        """
        # early exit if condition is already satisfied
        if condition():
            return
        
        # run cmd async, return on finish or timeout
        start = timestamp()
        process = execute(cmd, verbose=True, wait=False)
        while (timestamp() - start) < period:
            if process.poll() is not None:
                if not condition():
                    raise RoutineCheckError
                else:
                    return
            sleep(wait)

        # timeout, terminate the process and raise error
        process.terminate()
        raise RoutineCheckError    

    @abc.abstractmethod
    def run_impl(self) -> None:
        raise NotImplementedError
    

    @abc.abstractmethod
    def generate_output_impl(self) -> dict:
        raise NotImplementedError
    

    def run(self) -> dict:
        if self.input_path:
            mkdir(get_dir(self.input_path))
            dump_yaml(self.configs, self.input_path)
        self.run_impl()

        return self.generate_output()

    def generate_output(self) -> dict:
        output = self.generate_output_impl()
        if self.output_path:
            mkdir(get_dir(self.output_path))
            dump_yaml(output, self.output_path)

        return output