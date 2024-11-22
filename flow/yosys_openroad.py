import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from manager.yosys import YosysManager
from manager.openroad import OpenroadManager

class YosysOpenroadFlow():
    """
        An Easy-to-use user API to call Yosys and OpenROAD flow
    """

    def __init__(
        self,
        design_config: dict,
        tech_config: dict,
        syn_options: dict,
        pnr_options: dict,
        rundir: str,
        *,
        remove_netlist: bool = True,
    ) -> None:
        self.design_config = design_config
        self.tech_config = tech_config
        self.syn_options = syn_options
        self.pnr_options = pnr_options
        self.rundir = rundir

        self.remove_netlist = remove_netlist

        self.results = dict()

    @property
    def top_module(self) -> str:
        return self.design_config['top_module']

    def get_syn_configs(self) -> dict:
        configs = {
            'rundir': os.path.join(self.rundir, 'yosys-rundir'),
            'clk_period_ns': 0.0,
        }
        configs.update(self.design_config)
        configs.update(self.tech_config)
        configs.update(self.syn_options)

        return configs

    def get_pnr_configs(self, syn_output: dict) -> dict:
        configs = {
            'rundir': os.path.join(self.rundir, 'openroad-rundir'),
            'runmode': 'default',
        }
        configs['verilog_file'] = syn_output['verilog_file']
        configs.update(self.design_config)
        configs.update(self.tech_config)
        configs.update(self.pnr_options)

        return configs

    def run(self):
        """
            Run the design flow
        """
        syn_configs = self.get_syn_configs()
        syn_manager = YosysManager(syn_configs)
        syn_output = syn_manager.run()
        
        self.results['post_syn_delay'] = syn_output['delay']
        self.results['post_syn_area'] = syn_output['area']

        if self.pnr_options.get('runmode') != 'skip':
            pnr_configs = self.get_pnr_configs(syn_output)
            pnr_manager = OpenroadManager(pnr_configs)
            pnr_output = pnr_manager.run()
            
            self.results['post_pnr_delay'] = pnr_output['worst_delay']
            self.results['post_pnr_area'] = pnr_output['design_area']

        else:
            self.results['post_pnr_delay'] = None
            self.results['post_pnr_area'] = None

        # remove netlist to save disk
        if self.remove_netlist:
            os.remove(syn_output['verilog_file'])

        return self.results