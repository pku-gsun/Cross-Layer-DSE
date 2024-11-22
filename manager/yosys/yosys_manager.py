import os
from typing import Callable

from manager.common import BaseManager
from .yosys_parser import YosysParser
from utils import mkdir, if_exist

class YosysManager(BaseManager):
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
        return 'yosys_manager'

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
    def top_module(self) -> str:
        return self.configs.get('top_module')
    
    @property
    def yosys_bin(self) -> str:
        return self.configs.get('yosys_bin')
    
    @property
    def openroad_bin(self) -> str:
        return self.configs.get('openroad_bin')
    
    def get_file_list(self, key: str, sep: str = " ") -> str:
        """
            Get the string of a file list from configs.
        """
        files = self.configs.get(key, [])
        return sep.join(files)

    def generate_syn_code(self) -> str:
        """
            Generate synthesis codes for yosys
        """
        codes = ""

        codes += "read -sv %s\n" % self.get_file_list('verilog_files')

        codes += "hierarchy -top %s\n" % self.top_module
        codes += "flatten\n"
        codes += "proc; techmap; opt;\n"

        # map the register files
        codes += "dfflibmap -liberty %s\n" % self.get_file_list('lib_files')

        #  -constr %s
        codes += "abc -fast -liberty %s -D %.1f \n" % (
            self.get_file_list('lib_files'),
            # os.path.join(self.script_dir, 'abc_constr'),
            self.configs.get('clk_period_ns') * 1000,
        )

        codes += "write_verilog %s\n" % self.hdl_mapped_path

        return codes
    
    def generate_abc_constr_code(self) -> str:
        """
            Generate abc constraint codes
        """

        codes = """
set_driving_cell BUF_X1
set_load 10.0 [all_outputs] 
"""
        return codes
    
    def generate_report_code(self) -> str:
        """
            Generate report codes for openroad
        """
        codes = ""

        for lef_file in self.configs.get('lef_files'):
            codes += "read_lef %s\n" % lef_file
        for lib_file in self.configs.get('lib_files'):
            codes += "read_lib %s\n" % lib_file
        codes += '''
read_verilog %s
link_design %s
set_max_delay -from [all_inputs] 0
set critical_path [lindex [find_timing_paths -sort_by_slack] 0]
set path_delay [sta::format_time [[$critical_path path] arrival] 4]
puts "result: worst_delay = $path_delay"
report_design_area
exit
''' % (
    self.hdl_mapped_path,
    self.top_module,
)
        return codes

    def run_impl(self):
        """
            Run Yosys
        """
        # generate synthesis script
        yosys_script_path = os.path.join(self.script_dir, 'syn.ys')
        with open(yosys_script_path, 'w') as f:
            f.write(self.generate_syn_code())

        # generate constraint script
        abc_constr_path = os.path.join(self.script_dir, 'abc_constr')
        with open(abc_constr_path, 'w') as f:
            f.write(self.generate_abc_constr_code())

        # run synthesis
        cmd = f'{self.yosys_bin} -s {yosys_script_path} | tee {os.path.join(self.log_dir, "syn.log")}'
        self.routine_check(
            period=3600,
            cmd=cmd,
            condition=lambda: if_exist(self.hdl_mapped_path),
        )

        # report PPA with openroad
        report_script_path = os.path.join(self.script_dir, 'report.tcl')
        with open(report_script_path, 'w') as f:
            f.write(self.generate_report_code())
        
        # run report
        log_path = os.path.join(self.log_dir, 'report.log')
        cmd = f'{self.openroad_bin} {report_script_path} | tee {log_path}'
        self.routine_check(
            period=3600,
            cmd=cmd,
            condition=lambda: if_exist(log_path),
        )

    def generate_output_impl(self) -> dict:
        output = {
            'verilog_file': self.hdl_mapped_path,
        }

        parser = YosysParser(os.path.join(self.log_dir, 'report.log'))
        output.update(parser.run())
    
        return output