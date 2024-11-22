import re
from utils import if_exist

class YosysParser():

    def __init__(self, report_path: str) -> None:
        self.report_path = report_path
        assert if_exist(report_path), f"Report file {report_path} does not exist."
            
    def run(self):

        results = dict()

        with open(self.report_path, 'r') as f:
            for line in f.readlines():
                if 'worst_delay' in line:
                    delay = float(line.strip().split()[-1])
                    results['delay'] = delay
                elif 'Design area' in line:
                    area = float(line.strip().split()[2])
                    results['area'] = area

        print(results)

        return results