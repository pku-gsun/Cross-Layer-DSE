from .parser import *

class GenusPowerReportParser(GenusReportParser):

    def __init__(self, report_path: str) -> None:
        super().__init__(report_path)
        self._power_unit = None

    def get_power_unit(self, f) -> str:
        power_unit_match = read_until(f, r'^Power\s+Unit:\s+([^\s]+)$')
        return power_unit_match.group(1)
    
    def analyze_line(self, line) -> dict:
        data = line.split()
        cell_count, pct_cells, leakage, internal, switching, total, lvl, instance = data
        return {
            'instance': instance[1:],
            'cell_count': int(cell_count),
            'leakage': float(leakage),
            'internal': float(internal),
            'switching': float(switching),
            'total': float(total),
        }

    def run_impl(self):
        power_reports = []

        with open(self.report_path, 'r') as f:
            self._power_unit = self.get_power_unit(f)

            read_until(f, r'^-+$')
            read_until(f, r'^-+$')

            while True:
                try:
                    line = f.readline()
                    if re.match(r'^-+$', line):
                        break
                    power_report = self.analyze_line(line)
                    power_reports.append(power_report)
                except EOFError:
                    break

        return power_reports
    
    def run(self):
        return self.run_impl()
    
