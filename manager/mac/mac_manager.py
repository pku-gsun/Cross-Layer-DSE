import abc
import os
from manager.common import BaseManager
from utils import if_exist, execute, mkdir, info

class MacManager(BaseManager):
    """
        Mac Manager generates verilog codes from EasyMAC chisel codes.
    """
    def __init__(self, configs: dict) -> None:
        super().__init__(configs)

    @property
    def name(self):
        return "mac_manager"
    
    @property
    def easymac_root(self):
        return self.configs['easymac_root']
    
    @property
    def wallace_verilog_file(self):
        return os.path.join(self.rundir, 'wallace', 'PartialProdWallaceTree.v')
    
    @property
    def ppadder_verilog_file(self):
        return os.path.join(self.rundir, 'ppadder', 'PPAdder.v')
    
    @property
    def mac_verilog_file(self):
        return os.path.join(self.rundir, 'mac', 'MAC.v')
    
    def complie_wallace(self):
        """
            Compile the Wallace tree of multipliers
        """
        if 'wallace_configs' not in self.configs: return
        info("Compiling Wallace tree multiplier")

        wallace_file = self.configs['wallace_configs']['wallace_file']
        
        wallace_dir = os.path.dirname(self.wallace_verilog_file)
        cmd = "cd %s && source ~/.bashrc && source env.sh && " \
            "sbt 'Test/runMain wallace.test " \
            "--wallace-file %s " \
            "--target-dir %s'" % (
                self.easymac_root,
                wallace_file,
                wallace_dir,
            )
        
        def condition():
            return if_exist(self.wallace_verilog_file)
        
        self.routine_check(5*60, cmd, condition, 1)

    def compile_ppadder(self):
        """
            Compile the Parallel Prefix Adder
        """
        if 'ppadder_configs' not in self.configs: return
        info('Compiling parallel prefix adder')

        ppadder_file = self.configs['ppadder_configs']['ppadder_file']

        ppadder_dir = os.path.dirname(self.ppadder_verilog_file)
        cmd = "cd %s && source ~/.bashrc && source env.sh && " \
            "sbt 'Test/runMain ppadder.test " \
            "--prefix-adder-file %s " \
            "--target-dir %s'" % (
                self.easymac_root,
                ppadder_file,
                ppadder_dir,
            )
        
        def condition():
            return if_exist(self.ppadder_verilog_file)
        
        self.routine_check(5*60, cmd, condition, 1)

    def compile_mac(self):
        """
            Compile the Parallel Prefix Adder
        """
        if 'mac_configs' not in self.configs: return
        info('Compiling MAC Unit')

        mac_config = self.configs['mac_configs']
        mult_wallace_file = mac_config['mult_wallace_file']
        mult_ppadder_file = mac_config['mult_ppadder_file']
        acc_ppadder_file  = mac_config['acc_ppadder_file']

        mac_dir = os.path.dirname(self.mac_verilog_file)
        cmd = "cd %s && source ~/.bashrc && source env.sh && " \
            "sbt 'Test/runMain mac.test " \
            "--compressor-file %s " \
            "--prefix-adder-file %s " \
            "--accumulator-file %s " \
            "--target-dir %s'" % (
                self.easymac_root,
                mult_wallace_file,
                mult_ppadder_file,
                acc_ppadder_file,
                mac_dir,
            )
        
        def condition():
            return if_exist(self.mac_verilog_file)
        
        self.routine_check(5*60, cmd, condition, 1)

    def run_impl(self):
        self.complie_wallace()
        self.compile_ppadder()
        self.compile_mac()

    def generate_output_impl(self) -> dict:
        output = {
            'wallace_verilog_file': self.wallace_verilog_file if if_exist(self.wallace_verilog_file) else None,
            'ppadder_verilog_file': self.ppadder_verilog_file if if_exist(self.ppadder_verilog_file) else None,
            'mac_verilog_file': self.mac_verilog_file if if_exist(self.mac_verilog_file) else None,
        }

        return output