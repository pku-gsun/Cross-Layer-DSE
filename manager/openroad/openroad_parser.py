import re
from utils import if_exist

class OpenroadParser():

    def __init__(self, report_path: str) -> None:
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
            
    def run(self):

        results = dict()

        with open(self.report_path, 'r') as f:
            while True:
                try:
                    line = self.read_until_match(f, r'^result:')
                    data_match = re.match(r'^result:\s+([\w\_]+)\s+=\s+(-?\d+\.\d*)', line)
                    results[data_match.group(1)] = float(data_match.group(2))

                except EOFError:
                    break

        print(results)

        return results