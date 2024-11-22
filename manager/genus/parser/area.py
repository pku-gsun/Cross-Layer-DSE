from .parser import *

def update_dfs(dfs, label, level):
    """
        Maintain a DFS stack to reconstruct module hierarchy
    """
    for i in reversed(range(len(dfs))):
        top_level, top_label = dfs[i]
        if top_level >= level:
            dfs.pop()
    dfs.append((level, label))

class GenusAreaReportParser(GenusReportParser):

    def __init__(self, report_path: str) -> None:
        super().__init__(report_path)

    def analyze_child_module(self, line) -> dict:
        data = line.split()
        instance, module, cell_count, cell_area, net_area, total_area = data
        return {
            'instance': instance,
            'module': module,
            'cell_count': int(cell_count),
            'cell_area': float(cell_area),
            'net_area': float(net_area),
            'total_area': float(total_area),
        }
    
    def analyze_root_module(self, line) -> str:
        data = line.split()
        instance, cell_count, cell_area, net_area, total_area = data
        return {
            'instance': instance,
            'module': instance,
            'cell_count': int(cell_count),
            'cell_area': float(cell_area),
            'net_area': float(net_area),
            'total_area': float(total_area),
        }
    
    def run_impl(self):
        area_reports = []
        parent_instance = None
        dfs = []

        with open(self.report_path, 'r') as f:
            read_until(f, r'^-+$')

            while True:
                try:
                    line = f.readline()
                    if not line:
                        break
                    
                    if parent_instance is None:
                        area_report = self.analyze_root_module(line)
                        parent_instance = area_report['instance']
                    else:
                        leading_spaces = len(line) - len(line.lstrip(' '))
                        area_report = self.analyze_child_module(line.strip(' '))
                        instance = area_report['instance']
                        update_dfs(dfs, instance, leading_spaces)
                        hier_instance = "%s/" % parent_instance + "/".join([label for _, label in dfs])
                        area_report['instance'] = hier_instance
                    area_reports.append(area_report)
                except EOFError:
                    break

        return area_reports
    
    def run(self):
        return self.run_impl()