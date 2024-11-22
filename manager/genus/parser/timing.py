from .parser import *

class GenusTimingReportParser(GenusReportParser):
    """
        Analyze timing report in text.    
    """

    def __init__(self, report_path: str, max_timing_paths: int = 1) -> None:
        super().__init__(report_path)
        self.max_timing_paths = max_timing_paths
    
    def analyze_single_path(self, f) -> dict:
        """
            Analyze timing report for a single path.
        """
        path_info = dict()
        
        path_title_match = read_until(f, r'^Path (\d+):')
        path_info['path_index'] = int(path_title_match.group(1))

        start_match = read_until(f, r'^\s+Startpoint:\s+\([A-Z]\)\s+([^\s]+)$')
        path_info['begin_point'] = start_match.group(1)

        end_match = read_until(f, r'^\s+Endpoint:\s+\([A-Z]\)\s+([^\s]+)$')
        path_info['end_point'] = end_match.group(1)

        datapath_match = read_until(f, r'^\s+Data Path:-\s+(\d+)')
        path_info['arrival_time'] = int(datapath_match.group(1))

        slack_match = read_until(f, r'^\s+Slack:=\s+(-?\d+)')
        path_info['slack_time'] = int(slack_match.group(1))

        read_until(f, r'^#-+$')
        read_until(f, r'^#-+$')
        read_until(f, r'^#-+$')

        return path_info

    def run(self) -> list:
        """
            Analyze timing report for all paths.
        """

        timing_paths = []
        cnt_path = 0

        with open(self.report_path, 'r') as f:
            while cnt_path < self.max_timing_paths:
                try:
                    path_info = self.analyze_single_path(f)
                    timing_paths.append(path_info)
                except EOFError:
                    break
                cnt_path += 1 

        return timing_paths
        
        
        