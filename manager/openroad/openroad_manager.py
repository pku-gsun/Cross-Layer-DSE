import os
from typing import Callable

from manager.common import BaseManager
from utils import mkdir, if_exist
from .openroad_parser import OpenroadParser

class OpenroadManager(BaseManager):
    """
        Manager for Yosys
    """

    def __init__(self, configs: dict) -> None:
        super().__init__(configs)
        mkdir(self.rundir)
        mkdir(self.data_dir)
        mkdir(self.log_dir)
        mkdir(self.report_dir)
        mkdir(self.script_dir)

    @property
    def name(self) -> str:
        return 'openroad_manager'

    @property
    def data_dir(self) -> str:
        return os.path.join(self.rundir, 'data')
    
    @property
    def log_dir(self) -> str:
        return os.path.join(self.rundir, 'log')
    
    @property
    def report_dir(self) -> str:
        return os.path.join(self.rundir, 'reports')
    
    @property
    def script_dir(self) -> str:
        return os.path.join(self.rundir, 'scripts')
    
    @property
    def top_module(self) -> str:
        return self.configs.get('top_module')
    
    @property
    def openroad_bin(self) -> str:
        return self.configs.get('openroad_bin')
    
    @property
    def openroad_dir(self) -> str:
        return self.configs.get('openroad_dir')
    
    def get_file_list(self, key: str, sep: str = " ") -> str:
        """
            Get the string of a file list from configs.
        """
        files = self.configs.get(key, [])
        return sep.join(files)

    def generate_pnr_code(self) -> str:

        codes = ""

        pdk_name = self.configs.get('pdk_name')
        assert pdk_name in ('Nangate45', 'sky130hs', 'sky130hd'), f'PDK {pdk_name} is not supported'

        codes += 'source "%s"\n' % os.path.join(self.openroad_dir, 'test/helpers.tcl')
        codes += 'source "%s"\n' % os.path.join(self.openroad_dir, 'test/flow_helpers.tcl')
        codes += 'source "%s"\n' % os.path.join(os.path.join(self.script_dir, 'pdk.vars'))

        codes += 'set design "%s"\n' % self.top_module
        codes += 'set top_module "%s"\n' % self.top_module
        codes += 'set synth_verilog "%s"\n' % self.configs.get('verilog_file')
        codes += 'set sdc_file "%s"\n' % os.path.join(self.script_dir, 'constraints.sdc')

        codes += 'set die_area {%s}\n' % ' '.join(map(str, self.configs.get('die_area', [0, 0, 0, 0])))
        codes += 'set core_area {%s}\n' % ' '.join(map(str, self.configs.get('core_area', [0, 0, 0, 0])))

        runmode = self.configs.get('runmode', 'default')
        openroad_manager_dir = os.path.dirname(os.path.abspath(__file__))
        if runmode == 'fast':
            codes += 'source -echo "%s"\n' % os.path.join(openroad_manager_dir, 'fast_flow.tcl')
        else:
            codes += 'source -echo "%s"\n' % os.path.join(openroad_manager_dir, 'full_flow.tcl')

        return codes

    def generate_sdc_code(self) -> str:
        codes = """
create_clock [get_ports %s] -name %s -period %.4f
set_all_input_output_delays
""" % (
    self.configs.get('clk_port_name'),
    self.configs.get('clk_name'),
    self.configs.get('clk_period_ns'),
)
        return codes
    
    def generate_var_code(self) -> str:

        assert self.configs.get('pdk_name') == 'Nangate45', 'Only Nangate45 PDK is supported'
        pdk_test_dir = os.path.join(self.openroad_dir, 'test')

        codes = """
set platform "nangate45"
set tech_lef "%s/Nangate45/Nangate45_tech.lef"
set std_cell_lef "%s/Nangate45/Nangate45_stdcell.lef"
set extra_lef {}
set liberty_file "%s/Nangate45/Nangate45_typ.lib"
set extra_liberty {}
set site "FreePDK45_38x28_10R_NP_162NW_34O"
set pdn_cfg "%s/Nangate45/Nangate45.pdn.tcl"
set tracks_file "%s/Nangate45/Nangate45.tracks"
set io_placer_hor_layer metal3
set io_placer_ver_layer metal2
set tapcell_args "-distance 120 \
      -tapcell_master TAPCELL_X1 \
      -endcap_master TAPCELL_X1"
set global_place_density 0.3
# default value
set global_place_density_penalty 8e-5
# placement padding in SITE widths applied to both sides
set global_place_pad 2
set detail_place_pad 1

set macro_place_halo {22.4 15.12}
set macro_place_channel {18.8 19.95}

set layer_rc_file "%s/Nangate45/Nangate45.rc"
# equiv -resistance .0035 -capacitance .052
set wire_rc_layer "metal3"
set wire_rc_layer_clk "metal6"
set tielo_port "LOGIC0_X1/Z"
set tiehi_port "LOGIC1_X1/Z"
set dont_use {CLKBUF_* AOI211_X1 OAI211_X1}
# tie hi/low instance to load separation (microns)
set tie_separation 5
set cts_buffer "BUF_X4"
set cts_cluster_diameter 100
set filler_cells "FILLCELL*"

# global route
set global_routing_layers metal2-metal10
set global_routing_clock_layers metal6-metal10
set global_routing_layer_adjustments {{{metal2-metal10} 0.5}}

# detail route
set min_routing_layer metal2
set max_routing_layer metal10

set rcx_rules_file "%s/Nangate45/Nangate45.rcx_rules"

# Local Variables:
# mode:tcl
# End:
""" % ((pdk_test_dir,) * 7)
        
        return codes

    def run_impl(self) -> None:
        # generate codes
        openroad_script_path = os.path.join(self.script_dir, 'pnr.tcl')
        with open(openroad_script_path, 'w') as f:
            f.write(self.generate_pnr_code())

        sdc_script_path = os.path.join(self.script_dir, 'constraints.sdc')
        with open(sdc_script_path, 'w') as f:
            f.write(self.generate_sdc_code())

        var_script_path = os.path.join(self.script_dir, 'pdk.vars')
        with open(var_script_path, 'w') as f:
            f.write(self.generate_var_code())

        # run pnr
        log_path = os.path.join(self.log_dir, 'report.log')
        cmd = "cd {} && PATH=$PATH:{} " \
                "{} {} | tee {}".format(
                  self.rundir,
                  os.path.join(self.openroad_dir, 'test'),
                  self.openroad_bin,
                  openroad_script_path,
                  log_path,
              )
        self.routine_check(
            period=3600*10,
            cmd=cmd,
            condition=lambda: if_exist(log_path),
        )

    def generate_output_impl(self) -> dict:
        parser = OpenroadParser(os.path.join(self.log_dir, 'report.log'))
        return parser.run()