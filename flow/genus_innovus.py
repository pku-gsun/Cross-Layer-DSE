
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from manager.genus import GenusManager, GenusTimingReportParser, GenusPowerReportParser, GenusAreaReportParser
from manager.innovus import InnovusManager, InnovusAreaReportParser, InnovusPowerReportParser, InnovusTimingReportParser
from utils import mkdir, dump_json, if_exist

class GenusInnovusFlow():
    """
        An Easy-to-use user API to call Cadence design flow
    """

    def __init__(
        self,
        design_config: dict,
        tech_config: dict,
        syn_options: dict,
        pnr_options: dict,
        rundir: str,
    ) -> None:
        self.design_config = design_config
        self.tech_config = tech_config
        self.genus_options = syn_options
        self.innovus_options = pnr_options
        self.rundir = rundir

        self.results = dict()

    @property
    def top_module(self) -> str:
        return self.design_config['top_module']

    def get_genus_configs(self) -> dict:
        configs = {
            'rundir': os.path.join(self.rundir, 'genus-rundir'),
            'steps': ['syn', 'report'],
            'runmode': 'fast',
            'clk_period_ns': 0.0,
        }
        configs.update(self.design_config)
        configs.update(self.tech_config)
        configs.update(self.genus_options)

        return configs

    def get_innovus_configs(self, genus_output: dict) -> dict:
        configs = {
            'rundir': os.path.join(self.rundir, 'innovus-rundir'),
            'steps':[
                'init',
                'floorplan',
                'powerplan',
                'placement',
                'cts',
                'routing',
           ],
            'runmode': 'fast',
        }
        configs.update(genus_output)
        configs.update(self.tech_config)
        configs.update(self.innovus_options)

        return configs

    def run(self):
        """
            Run the design flow
        """
        # run genus
        genus_configs = self.get_genus_configs()
        genus_manager = GenusManager(genus_configs)
        genus_output = genus_manager.run()

        self.results['Post-Syn Timing'] = self.get_timing('postSyn')
        self.results['Post-Syn Power'] = self.get_power('postSyn')
        self.results['Post-Syn Area'] = self.get_area('postSyn')

        # run innovus
        if self.innovus_options.get('runmode') != 'skip':
            innovus_configs = self.get_innovus_configs(genus_output)
            innovus_manager = InnovusManager(innovus_configs)
            innovus_output = innovus_manager.run()

            self.results['Post-Place Timing'] = self.get_timing('postPlace')
            self.results['Post-Route Timing'] = self.get_timing('postRoute')
            self.results['Post-Place Power'] = self.get_power('postPlace')
            self.results['Post-Route Power'] = self.get_power('postRoute')
            self.results['Post-Place Area'] = self.get_area('postPlace')
            self.results['Post-Route Area'] = self.get_area('postRoute')

        else:
            self.results['Post-Place Timing'] = None
            self.results['Post-Route Timing'] = None
            self.results['Post-Place Power'] = None
            self.results['Post-Route Power'] = None
            self.results['Post-Place Area'] = None
            self.results['Post-Route Area'] = None

        return self.results

        
    def get_area(self, stage: str) -> float:
        if stage == 'postSyn':
            report_path = os.path.join(self.rundir, 'genus-rundir', 'reports', 'area.rpt')
            report_parser = GenusAreaReportParser(report_path)

        elif stage == 'postPlace':
            report_path = os.path.join(self.rundir, 'innovus-rundir', 'reports', 'preCTS_area.rpt')
            report_parser = InnovusAreaReportParser(report_path)

        elif stage == 'postRoute':
            report_path = os.path.join(self.rundir, 'innovus-rundir', 'reports', 'postRoute_area.rpt')
            report_parser = InnovusAreaReportParser(report_path)

        else:
            raise NotImplementedError(f"Stage {stage} is not supported in get_area")

        report_list = report_parser.run()
        report_dict = {r['instance']: r for r in report_list}
        key_name = 'total_area' if stage != 'postSyn' else 'cell_area'
        area = report_dict[self.top_module][key_name]

        return area
    
    def get_power(self, stage: str) -> float:
        if stage == 'postSyn':
            report_path = os.path.join(self.rundir, 'genus-rundir', 'reports', 'power.rpt')
            report_parser = GenusPowerReportParser(report_path)
        
        elif stage == 'postPlace':
            report_path = os.path.join(self.rundir, 'innovus-rundir', 'reports', 'preCTS_power.rpt')
            report_parser = InnovusPowerReportParser(report_path)

        elif stage == 'postRoute':
            report_path = os.path.join(self.rundir, 'innovus-rundir', 'reports', 'postRoute_power.rpt')
            report_parser = InnovusPowerReportParser(report_path)

        else:
            raise NotImplementedError(f"Stage {stage} is not supported in get_power")
        
        report_list = report_parser.run()
        report_dict = {r['instance']: r for r in report_list}
        power = report_dict[self.top_module]['total']
        
        return power

    def get_timing(self, stage: str, path_name: str = None) -> float:
        if stage == 'postSyn':
            report_dir = os.path.join(self.rundir, 'genus-rundir', 'reports')
            report_parser_class = GenusTimingReportParser

        elif stage == 'postPlace':
            report_dir = os.path.join(self.rundir, 'innovus-rundir', 'reports', 'preCTS_timing')
            report_parser_class = InnovusTimingReportParser

        elif stage == 'postRoute':
            report_dir = os.path.join(self.rundir, 'innovus-rundir', 'reports', 'postRoute_timing')
            report_parser_class = InnovusTimingReportParser

        else:
            raise NotImplementedError(f"Stage {stage} is not supported in get_timing")
        
        if path_name is not None:
            report_path = os.path.join(report_dir, f'group_timing_{path_name}.rpt')
        else:
            report_path = os.path.join(report_dir, 'timing.rpt')

        report_list = report_parser_class(report_path).run()
        arrival_time = report_list[0]['arrival_time'] if len(report_list) else 0
        return arrival_time
