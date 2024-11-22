from .parser import *

class InnovusAreaReportParser(InnovusReportParser):
    """
        Analyze power report in text.    
    """

    def __init__(self, report_path: str) -> None:
        super().__init__(report_path)
    
    def analyze_module(self, line: str, top_module: str) -> list:
        data = line.split()
        if not top_module:  # we don't have top module yet
            hinst_name,              inst_count, total_area, buffer, inverter, combinational, flop, latch, clock_gate, macro, physical = data
            module_name = None
        else:
            hinst_name, module_name, inst_count, total_area, buffer, inverter, combinational, flop, latch, clock_gate, macro, physical = data
        if top_module != "":
            hinst_name = top_module + "/" + hinst_name
        return {
            'instance': hinst_name,
            'module_name': module_name,
            'inst_count': int(inst_count),
            'total_area': float(total_area),
            'buffer': float(buffer),
            'inverter': float(inverter),
            'combinational': float(combinational),
            'flop': float(flop),
            'latch': float(latch),
            'clock_gate': float(clock_gate),
            'macro': float(macro),
            'physical': float(physical),
        }
    
    def run_impl(self) -> list:
        area_reports = []
        top_module = ""

        with open(self.report_path, 'r') as f:
            self.read_until_match(f, r'^-+$')

            while True:
                try:
                    line = f.readline()
                    if not line:
                        break
                    area = self.analyze_module(line.strip(' '), top_module)
                    if not top_module:
                        top_module = area['instance']
                    area_reports.append(area)
                except EOFError:
                    break

        return area_reports

    def run(self) -> list:
        return self.run_impl()
        
        
        