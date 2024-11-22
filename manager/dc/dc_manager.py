import os
from typing import Callable

from manager.common import BaseManager
from utils import mkdir, if_exist

class DCManager(BaseManager):
    """
        Synopsys manager synthesize RTL into netlist.
    """
    def __init__(self, configs: dict) -> None:
        super().__init__(configs)
        mkdir(self.data_dir)
        mkdir(self.log_dir)
        mkdir(self.report_dir)
        mkdir(self.script_dir)

    @property
    def name(self) -> str:
        return 'dc_manager'
    
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
    def hdl_mapped_path(self) -> str:
        """
            Mapped netlist. Marks the end of synthesis
        """
        return os.path.join(self.data_dir, '%s-mapped.v' % self.top_module)

    @property
    def script_dir(self) -> str:
        return os.path.join(self.rundir, 'scripts')
    
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
    def fused_syn_script_path(self) -> str:
        """
            Fast synthesis script without checkpoints
        """
        return os.path.join(self.script_dir, 'fused_syn.tcl')

    @property
    def top_module(self) -> str:
        return self.configs.get('top_module')
    
    @property
    def dc_bin(self) -> str:
        return self.configs.get('dc_bin')

    def get_file_list(self, key: str, sep: str = " ") -> str:
        """
            Get the string of a file list from configs.
        """
        files = self.configs.get(key, [])
        return sep.join(files)

    def generate_preprocessing_code(self) -> str:
        lib_files = self.configs.get("lib_files", [])
        code = """
# -------------------------------------------------------------
# Preprocessing
# -------------------------------------------------------------
"""
        for lib_file in lib_files:
            if lib_file.endswith(".lib") or lib_file.endswith(".lib.gz"):
                lib_wo_ext = lib_file.split('/')[-1].split('.')[0]
                code += f"""
read_lib {lib_file}
write_lib {lib_wo_ext} -output {lib_wo_ext}.db
"""
                self.configs["lib_files"].remove(f"{lib_file}")
                self.configs["lib_files"].append(f"{lib_wo_ext}.db")

        return code

    def generate_syn_code(self) -> str:
        """
            Generate synthesis TCL script
        """
        codes = """
# -------------------------------------------------------------
# Set libraries
# -------------------------------------------------------------
set target_library "%s"
set link_library "* %s"

# -------------------------------------------------------------
# Read verilog design files
# -------------------------------------------------------------
read_file -format verilog { %s }
current_design %s

# -------------------------------------------------------------
# Reset constraints and compile
# -------------------------------------------------------------
reset_design
link
uniquify
compile

# -------------------------------------------------------------
# Write out data
# -------------------------------------------------------------
write_sdf %s
write_sdc %s/constraint.sdc
write -f verilog -hier -output %s
""" % (
    self.get_file_list('db_files'), 
    self.get_file_list('db_files'), 
    self.get_file_list('verilog_files'),
    self.top_module,
    self.sdf_path,
    self.data_dir,
    self.hdl_mapped_path
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
report_power -hierarchy > ${report_dir}/power.rpt
report_area > ${report_dir}/area.rpt
report_design > ${report_dir}/drc.rpt
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
                "{} -no_gui " \
                "-f {} " \
                "-output_log_file {} ".format(
                self.rundir,
                self.dc_bin,
                script_path,
                os.path.join(self.log_dir, step_name)
            )
        self.routine_check(timeout, cmd, condition)

    def run_impl(self) -> None:
        """
            Generate scripts and run Design Compiler
        """
        steps = self.configs.get('steps', ['preprocess', 'syn', 'report'])

        fused_code = ""
        if 'preprocess' in steps:
            fused_code += self.generate_preprocessing_code()
        if 'syn' in steps:
            fused_code += self.generate_syn_code()
        if 'report' in steps:
            fused_code += self.generate_report_code()
        
        self.write_to_file(fused_code, self.fused_syn_script_path, is_tcl=True)
        self.run_tcl_script(
            script_path=self.fused_syn_script_path,
            step_name='fused',
            timeout=10 * 3600,
            condition=lambda: if_exist(self.hdl_mapped_path)
        )


    def generate_output_impl(self) -> None:
        output = {
            'verilog_file': self.hdl_mapped_path,  # single netlist file for innovus
            'top_module': self.top_module,
            'lib_files': self.configs.get('lib_files'),
            'lef_files': self.configs.get('lef_files'),
            'qrc_techfiles': self.configs.get('qrc_techfiles'),
            'cts_inv_cells': self.configs.get('cts_inv_cells', []),
            'sdc_file': os.path.join(self.data_dir, 'constraint_setup.sdc'),
            'path_groups': self.configs.get('path_groups', []),
        }
        return output