from .parser import *

class InnovusTimingReportParser(InnovusReportParser):
    """
        Analyze timing report in text.    
    """

    def __init__(self, report_path: str) -> None:
        super().__init__(report_path)
    
    def analyze_single_path(self, f) -> dict:
        """
            Analyze timing report for a single path.
        """
        path_info = dict()
        
        self.read_until_match(f, r'^PATH \d+$')

        endpt_line = self.read_until_match(f, r'^\s+ENDPT')
        endpt_vals = self.parse_bracketed_value(endpt_line)
        path_info['end_point'] = endpt_vals[1]

        beginpt_line = self.read_until_match(f, r'^\s+BEGINPT')
        beginpt_vals = self.parse_bracketed_value(beginpt_line)
        path_info['begin_point'] = beginpt_vals[1]

        slc_clc_lines = self.read_between_match(f, r'^\s+SLK_CLC', r'^\s+END_SLK_CLC')
        arrival_time_line = slc_clc_lines[0]
        arrival_time_vals = self.parse_bracketed_value(arrival_time_line)
        path_info['arrival_time'] = float(arrival_time_vals[2])
        slack_time_line = slc_clc_lines[1]
        slack_time_vals = self.parse_bracketed_value(slack_time_line)
        path_info['slack_time'] = float(slack_time_vals[2])

        self.read_until_match(f, r'^END_PATH (\d+)$')

        return path_info

    def run(self) -> list:
        """
            Analyze timing report for all paths.
        """

        timing_paths = []

        with open(self.report_path, 'r') as f:
            while True:
                try:
                    path_info = self.analyze_single_path(f)
                    timing_paths.append(path_info)
                except EOFError:
                    break

        return timing_paths
        
        
        