
import re
import abc
from utils import if_exist

def read_until(f, pattern, return_match=True):
    while True:
        line = f.readline()
        if not line:
            raise EOFError
        
        match = re.match(pattern, line)
        if match:
            if return_match:
                return match
            else:
                return line

class GenusReportParser(abc.ABC):
    def __init__(self, report_path: str) -> None:
        super().__init__()
        self.report_path = report_path
        assert if_exist(report_path), f"Report file {report_path} does not exist."

    @abc.abstractmethod
    def run():
        raise NotImplementedError