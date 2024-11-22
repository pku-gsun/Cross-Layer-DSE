from .parser import *

class InnovusPowerReportParser(InnovusReportParser):
    """
        Analyze power report in text.    
    """

    def __init__(self, report_path: str) -> None:
        super().__init__(report_path)
    
    def run_impl(self) -> list:
        power_reports = []
        power_unit = 1e-3  # mW

        with open(self.report_path, 'r') as f:

            design_line = self.read_until_match(f, r'^\*\s+Design:')
            design_name = design_line.split(':')[1].strip()

            self.read_until_match(f, r'^Group')
            self.read_until_match(f, r'^-+$')
            self.read_until_match(f, r'^-+$')

            total_power_line = f.readline()
            total_power_vals = total_power_line.split()

            power_reports.append({
                'instance': design_name,
                'internal': float(total_power_vals[1]) * power_unit,
                'switching': float(total_power_vals[2]) * power_unit,
                'leakage': float(total_power_vals[3]) * power_unit,
                'total': float(total_power_vals[4]) * power_unit,
            })

            self.read_until_match(f, r'^Hierarchy')
            self.read_until_match(f, r'^-+$')

            while True:
                power_line = f.readline()
                power_vals = power_line.split()
                if len(power_vals) < 6:
                    break

                power_reports.append({
                    'instance': design_name + '/' + power_vals[0],
                    'internal': float(power_vals[1]) * power_unit,
                    'switching': float(power_vals[2]) * power_unit,
                    'leakage': float(power_vals[3]) * power_unit,
                    'total': float(power_vals[4]) * power_unit,
                })

            return power_reports

    def run(self) -> list:
        return self.run_impl()
        
        
        