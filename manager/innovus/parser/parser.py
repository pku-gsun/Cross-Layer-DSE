
import re
import abc
from utils import if_exist

class InnovusReportParser(abc.ABC):
    def __init__(self, report_path: str) -> None:
        super().__init__()
        self.report_path = report_path
        assert if_exist(report_path), f"Report file {report_path} does not exist."

    def read_until_match(self, f, pattern) -> str:
        """
            Reads lines from a file until a line matching the given pattern is found.
        """
        while True:
            line = f.readline()
            if not line:
                raise EOFError
            
            match = re.match(pattern, line)
            # print(f"[line {match is not None}]: {line}")

            if match:
                return line

    def read_between_match(self, f, start_pattern, end_pattern) -> list[str]:
        """
            Read lines and return a list of lines between two patterns.
        """
        lines = []

        self.read_until_match(f, start_pattern)
        
        while True:
            line = f.readline()
            if not line:
                raise RuntimeError(f"End pattern {end_pattern} not found.")

            match = re.match(end_pattern, line)
            if match:
                return lines

            lines.append(line)

    def parse_bracketed_value(self, line) -> list:
        """
            Parse all values in the line
        """
        pattern = r'\{(.*?)\}'
        match = re.findall(pattern, line)
        return match

    @abc.abstractmethod
    def run():
        raise NotImplementedError