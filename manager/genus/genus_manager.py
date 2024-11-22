import abc
import os
import itertools
from typing import Callable

from manager.common import BaseManager
from utils import info, mkdir, if_exist, read_json


class GenusManager(BaseManager):
    """
        Cadence Genus manager synthesize RTL into netlist.
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
        return 'genus_manager'

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
    def hdl_mapped_path(self) -> str:
        """
            Mapped netlist. Marks the end of synthesis
        """
        return os.path.join(self.data_dir, '%s-mapped.v' % self.top_module)
    
    @property
    def sdf_path(self) -> str:
        return os.path.join(self.data_dir, '%s.sdf' % self.top_module)

    @property
    def timing_report_path(self) -> str:
        """
            Timing report. Marks the end of reporting.
        """
        return os.path.join(self.report_dir, 'timing.rpt')
    
    @property
    def mmmc_script_path(self) -> str:
        return os.path.join(self.script_dir, 'mmmc.tcl')
    
    @property
    def syn_script_path(self) -> str:
        return os.path.join(self.script_dir, 'syn.tcl')
    
    @property
    def sdc_script_path(self) -> str:
        return os.path.join(self.script_dir, 'constraint.sdc')
    
    @property
    def report_script_path(self) -> str:
        return os.path.join(self.script_dir, 'report.tcl')
    
    @property
    def fused_syn_script_path(self) -> str:
        """
            Fast synthesis script without checkpoints
        """
        return os.path.join(self.script_dir, 'fused_syn.tcl')
    
    @property
    def top_module(self) -> str:
        return self.configs.get('top_module')
    
    @property
    def genus_bin(self) -> str:
        return self.configs.get('genus_bin')

    def get_file_list(self, key: str, sep: str = " ") -> str:
        """
            Get the string of a file list from configs.
        """
        files = self.configs.get(key, [])
        return sep.join(files)
    
    def write_to_file(self, codes: str, filepath: str, is_tcl: bool, prev_checkpoint: str = None, cur_checkpoint: str = None) -> None:
        """
            Write the code to the file, with necessary checkpoints.
        """
        mkdir(os.path.dirname(filepath))

        with open(filepath, 'w') as f:
            if prev_checkpoint:
                load_codes = """
# -------------------------------------------------------------
# Read the design
# -------------------------------------------------------------
read_db %s/%s.db
""" % (self.data_dir, prev_checkpoint)
                f.write(load_codes)

            f.write(codes)

            if cur_checkpoint:
                save_codes = """
# -------------------------------------------------------------
# Save the design
# -------------------------------------------------------------
write_db %s/%s.db
""" % (self.data_dir, cur_checkpoint)
                f.write(save_codes)

            if is_tcl:
                f.write("exit 0\n")



    def run_tcl_script(self, script_path: str, step_name: str, timeout: int, condition: Callable) -> None:
        cmd = "cd {} && source ~/.bashrc && " \
                "{} -no_gui -abort_on_error -overwrite " \
                "-file {} " \
                "-log {} ".format(
                self.rundir,
                self.genus_bin,
                script_path,
                os.path.join(self.log_dir, step_name)
            )
        self.routine_check(timeout, cmd, condition)
    
    def run_impl(self) -> None:
        """
            Generate scripts and run genus
        """
        steps = self.configs.get('steps', ['syn', 'report'])

        runmode = self.configs.get('runmode', 'normal')
        
        if runmode == 'fast':
            fused_code = ""
            if 'syn' in steps: fused_code += self.generate_syn_code()
            if 'report' in steps: fused_code += self.generate_report_code()
            
            self.write_to_file(self.generate_sdc_code(), self.sdc_script_path, is_tcl=False)
            self.write_to_file(self.generate_mmmc_code(), self.mmmc_script_path, is_tcl=False)
            self.write_to_file(fused_code, self.fused_syn_script_path, is_tcl=True)

            self.run_tcl_script(
                script_path=self.fused_syn_script_path,
                step_name='fused',
                timeout=10 * 3600,
                condition=lambda: if_exist(self.hdl_mapped_path)
            )

        elif runmode == 'normal':
            self.write_to_file(self.generate_sdc_code(), self.sdc_script_path, is_tcl=False)
            self.write_to_file(self.generate_mmmc_code(), self.mmmc_script_path, is_tcl=False)
            self.write_to_file(self.generate_syn_code(), self.syn_script_path,
                               prev_checkpoint=None, cur_checkpoint='syn', is_tcl=True)
            self.write_to_file(self.generate_report_code(), self.report_script_path,
                               prev_checkpoint='syn', cur_checkpoint='report', is_tcl=True)
            
            # let the users determine which steps to use, we don't check it here
            if 'syn' in steps:
                self.run_tcl_script(
                    script_path=self.syn_script_path,
                    step_name='syn',
                    timeout=10 * 3600,
                    condition=lambda: if_exist(self.hdl_mapped_path)
                )
            if 'report' in steps:
                self.run_tcl_script(
                    script_path=self.report_script_path,
                    step_name='report',
                    timeout=3600,
                    condition=lambda: if_exist(self.timing_report_path)
                )
        else:
            raise NotImplementedError("runmode %s is not supported" % runmode)

    def generate_output_impl(self) -> None:
        output = {
            'verilog_file': self.hdl_mapped_path,  # single netlist file for innovus
            'top_module': self.top_module,
            'setup_lib_files': self.configs.get('setup_lib_files'),
            'hold_lib_files': self.configs.get('hold_lib_files'),
            'lef_files': self.configs.get('lef_files'),
            'qrc_techfiles': self.configs.get('qrc_techfiles'),
            'cts_inv_cells': self.configs.get('cts_inv_cells', []),
            'setup_sdc_file': os.path.join(self.data_dir, 'constraint_setup.sdc'),
            'hold_sdc_file': os.path.join(self.data_dir, 'constraint_hold.sdc'),
            'path_groups': self.configs.get('path_groups', []),
        }
        return output

    def generate_sdc_code(self) -> str:
        """
            Generate SDC constraints for synthesis
        """
        clk_period_ns = self.configs.get('clk_period_ns')
        clk_period_ps = clk_period_ns * 1000.0
        default_input_delay_ns = clk_period_ns * 0.1
        default_output_delay_ns = clk_period_ns * 0.1

        codes = """
current_design %s

set_units -capacitance 1.0fF
set_units -time 1.0ps

set clk_name %s
set clk_port_name %s
set clk_period_ps %.1f
set input_delay_ps %.1f
set output_delay_ps %.1f

create_clock -period ${clk_period_ps} -name $clk_name [get_ports ${clk_port_name}]
set_input_delay $input_delay_ps -clock $clk_name [all_inputs -no_clock]
set_output_delay $output_delay_ps -clock $clk_name [all_outputs]
set_clock_groups -asynchronous  -group ${clk_name}
""" % (
    self.top_module,
    self.configs.get('clk_name', 'clk'),
    self.configs.get('clk_port_name'),
    clk_period_ps,
    self.configs.get('input_delay_ns', default_input_delay_ns) * 1000,
    self.configs.get('output_delay_ns', default_output_delay_ns) * 1000,
)
        codes += """
# -------------------------------------------------------------
# Set global constraints
# -------------------------------------------------------------
"""
        max_transition_ns = self.configs.get('max_transition_ns', None)
        if max_transition_ns:
            codes += """
set_max_transition %.2f
""" % (max_transition_ns * 1000)  # ps
            
        max_capacitance_ff = self.configs.get('max_capacitance_ff', None)
        if max_capacitance_ff:
            codes += """
set_max_capacitance %.2f
""" % max_capacitance_ff
            
        max_fanout = self.configs.get('max_fanout', None)
        if max_fanout:
            codes += """
set_max_fanout %d
""" % max_fanout
            
        max_leakage_power_uw = self.configs.get('max_leakage_power_uw', None)
        if max_leakage_power_uw:
            codes += """
set_max_leakage_power %.2f uW
""" % max_leakage_power_uw
            
        max_dynamic_power_uw = self.configs.get('max_dynamic_power_uw', None)
        if max_dynamic_power_uw:
            codes += """
set_max_dynamic_power %.2f uW
""" % max_dynamic_power_uw
        
        # When both max_leakage and max_dynamic attributes are set, you have to set a weight factor
        # If no weight factor is set, Genus optimizes only for the leakage power
        lp_power_optimization_weight = self.configs.get('lp_power_optimization_weight', None)
        if lp_power_optimization_weight:
            codes += """
set lp_power_optimization_weight %.2f
""" % lp_power_optimization_weight

        return codes

    def generate_mmmc_code(self) -> str:
        """
            Multi-Mode Multi-Corner scripts, used for timing analysis.
            This script has to be separately loaded with read_mmmc command
        """
        qrc_techfiles = self.get_file_list('qrc_techfiles')
        qrc_tech_suffix = ('-qrc_tech [list %s]' % qrc_techfiles) if qrc_techfiles else ''

        codes = """
# -------------------------------------------------------------
# Set the SDC FILE
# -------------------------------------------------------------
create_constraint_mode -name common -sdc_files %s

# -------------------------------------------------------------
# Set the lib
# -------------------------------------------------------------
create_library_set -name setup_set -timing [list %s]
create_library_set -name hold_set -timing [list %s]

# -------------------------------------------------------------
# Create timing condition
# -------------------------------------------------------------
create_timing_condition -name setup_cond -library_sets [list setup_set]
create_timing_condition -name hold_cond -library_sets [list hold_set]

# -------------------------------------------------------------
# Create RC corner
# -------------------------------------------------------------
create_rc_corner -name rc_corner %s

# -------------------------------------------------------------
# Create the delay corner
# -------------------------------------------------------------
create_delay_corner -name setup_delay -timing_condition setup_cond -rc_corner rc_corner
create_delay_corner -name hold_delay -timing_condition hold_cond -rc_corner rc_corner

# -------------------------------------------------------------
# Create the analysis view
# -------------------------------------------------------------
create_analysis_view -name setup_view -delay_corner setup_delay -constraint_mode common
create_analysis_view -name hold_view -delay_corner hold_delay -constraint_mode common

# -------------------------------------------------------------
# Set the analysis view for setup & hold
# -------------------------------------------------------------
set_analysis_view -setup { setup_view } -hold { hold_view }
""" % (
    self.sdc_script_path,
    self.get_file_list('setup_lib_files'),
    self.get_file_list('hold_lib_files'),
    qrc_tech_suffix,
)
        return codes

    def generate_syn_code(self) -> str:
        """
            Generate synthesis TCL script
        """
        codes = """
# -------------------------------------------------------------
# Global synthesis settings
# -------------------------------------------------------------
set_db hdl_error_on_blackbox %s
set_db max_cpus_per_server %d
""" % (
    'true' if self.configs.get('hdl_error_on_blackbox', True) else 'false',
    self.configs.get('max_threads', 8),
)
        
        codes += """
# -------------------------------------------------------------
# Read library files
# -------------------------------------------------------------
read_mmmc %s
read_physical -lef { %s }
""" % (
    self.mmmc_script_path,
    self.get_file_list('lef_files'),
)
        
        codes += """
# -------------------------------------------------------------
# Read verilog design files
# -------------------------------------------------------------
read_hdl -sv { %s }
elaborate %s
init_design -top %s
check_design -unresolved
""" % (
    self.get_file_list('verilog_files'),
    self.top_module,
    self.top_module,
)
        if self.configs.get('auto_ungroup', True) is False:
            codes += """
set_db root: .auto_ungroup none        
"""

        codes += """
# -------------------------------------------------------------
# Set retime modules
# -------------------------------------------------------------
"""
        for retime_module in self.configs.get('retime_modules', []):
            codes += """
set_db module:%s/%s .retime true
""" % (self.top_module, retime_module)

        codes += """
# -------------------------------------------------------------
# Set dont use cells
# -------------------------------------------------------------
"""
        for dont_use_cell in self.configs['dont_use_cells']:
            if not dont_use_cell.startswith("*/"):
                dont_use_cell = "*/" + dont_use_cell
            codes += """
if { [get_db lib_cells %s] ne "" } {
    set_dont_use [get_db lib_cells %s]
} else {
    puts "WARNING: cell %s was not found for set_dont_use"
}
""" % (dont_use_cell, dont_use_cell, dont_use_cell)

    # TODO: physical-aware synthesis requires floorplan (DEF file)        
        codes += """
# -------------------------------------------------------------
# Synthesize the design to target library
# -------------------------------------------------------------
set syn_generic_effort %s
syn_generic %s

set syn_map_effort %s
syn_map %s
""" % (
    self.configs.get('syn_generic_effort', 'medium'),
    '-physical' if self.configs.get('syn_generic_physical', False) else '',
    self.configs.get('syn_map_effort', 'high'),
    '-physical' if self.configs.get('syn_map_physical', False) else '',
)
        if self.configs.get('syn_opt_effort', None):
            codes += """
set syn_opt_effort %s
syn_opt %s
""" % (
    self.configs.get('syn_opt_effort'),
    '-physical' if self.configs.get('syn_opt_physical', False) else '',
)
            
        codes += """
# -------------------------------------------------------------
# Write out data
# -------------------------------------------------------------
write_hdl -mapped > %s
write_sdf > %s
write_sdc -view setup_view > %s/constraint_setup.sdc
write_sdc -view hold_view > %s/constraint_hold.sdc
""" % (
    self.hdl_mapped_path,
    self.sdf_path,
    self.data_dir,
    self.data_dir,
)

        return codes

    def generate_report_code(self) -> str:
        """
            Generate report code
        """
        codes = """
# -------------------------------------------------------------
# Generate reports
# -------------------------------------------------------------
set report_dir %s

report_timing > ${report_dir}/timing.rpt
report_power -by_hierarchy -levels all > ${report_dir}/power.rpt
report_area > ${report_dir}/area.rpt
report_design_rules > ${report_dir}/drc.rpt
report_qor > ${report_dir}/qor.rpt

""" % (
    self.report_dir,
)

        codes += """
# -------------------------------------------------------------
# Report path group timing
# -------------------------------------------------------------
report_timing -from [ all_inputs ] -to [ all_outputs ] -nworst 1 > ${report_dir}/timing_in_to_out.rpt
# report_timing -from [ all_inputs ] -to [ all_registers ] -nworst 1 > ${report_dir}/timing_in_to_reg.rpt
# report_timing -from [ all_registers ] -to [ all_outputs ] -nworst 1 > ${report_dir}/timing_reg_to_out.rpt
"""
        for path_group in self.configs.get('path_groups', []):
            if path_group.get('report', False):
                codes += """
report_timing -from %s -to %s -nworst 1 > ${report_dir}/group_timing_%s.rpt
""" % (
    path_group.get('from'),
    path_group.get('to'),
    path_group.get('name'),
)
            
        return codes