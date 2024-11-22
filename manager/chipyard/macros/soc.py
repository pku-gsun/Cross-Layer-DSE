import os
from .macros import Macros
from utils import info, warn

class SocMacros(Macros):
    def __init__(self, configs: dict) -> None:
        super().__init__(configs)
        self.macros = configs['soc_configs']

    @property
    def chisel_config_path(self) -> str:
        return os.path.join(
            self.chipyard_root,
            "generators",
            "chipyard",
            "src",
            "main",
            "scala",
            "config",
            "%s.scala" % self.get_config_name()  # support compiling in parallel
        )
    
    def get_config_name(self) -> str:
        return self.macros.get("config_name")
    
    def get_system_bus_width(self) -> int:
        if 'accelerator_configs' in self.macros:
            system_bus_width = self.macros.get("system_bus_width", 64)
            if system_bus_width < 128:
                warn("Set system bus width from %d to 128 to fit accelerators" % system_bus_width)
                system_bus_width = 128
            return system_bus_width
        else:
            return self.macros.get("system_bus_width", None)
    
    def generate_l2cache_config_codes(self):
        """
            Config codes for L2 cache
        """
        codes = ""
        if self.macros.get('l2cache_tlbs', None):
            codes += "  new chipyard.config.WithL2TLBs(%d) ++\n" % self.macros.get('l2cache_tlbs')
        
        if  self.macros.get('l2cache_ways', None) or \
            self.macros.get('l2cache_capacity', None):
            codes += "  new freechips.rocketchip.subsystem.WithInclusiveCache(\n"
            if self.macros.get('l2cache_ways', None):
                codes += "    nWays = %d,\n" % self.macros.get('l2cache_ways')
            if self.macros.get('l2cache_capacity', None):
                codes += "    capacityKB = %d,\n" % self.macros.get('l2cache_capacity')
            codes += "  ) ++\n"
        
        return codes
    
    def generate_accelerator_config_codes(self):
        """
            Config codes for RoCC accelerators
        """
        type_to_prefix = {
            'gemmini': 'gemmini',
            'hwacha': 'hwacha',
        }

        codes = ""

        for acc_config in self.macros.get('accelerator_configs', []):
            prefix = type_to_prefix[acc_config['config_type']]
            codes += "  new %s.%s ++\n" % (
                prefix,
                acc_config['config_name'],
            )

        return codes
    
    def generate_cpu_config_codes(self):
        """
            Config codes for CPUs
        """
        type_to_prefix = {
            'rocket': 'freechips.rocketchip.subsystem',
            'boom': 'boom.common',
        }

        codes = ""

        for cpu_config in self.macros.get('cpu_configs', []):
            prefix = type_to_prefix[cpu_config['config_type']]
            codes += "  new %s.%s(%d) ++\n" % (
                prefix,
                cpu_config['config_name'],
                cpu_config.get('ncpus', 1),
            )

        return codes
    
    def generate_system_bus_config_codes(self):
        """
            Config codes for system bus
        """
        codes = ""

        system_bus_width = self.get_system_bus_width()
        if system_bus_width:
            codes += "  new chipyard.config.WithSystemBusWidth(%d) ++\n" % system_bus_width
        
        return codes
    
    def generate_chisel_config_codes(self):
        codes = """
package chipyard

import org.chipsalliance.cde.config.{Config}
import boom.common._
import freechips.rocketchip.subsystem._
import gemmini._

class %s extends Config(
""" % self.get_config_name()

        # add L2 cache config
        codes += self.generate_l2cache_config_codes()

        # add RoCC accelerator configs
        codes += self.generate_accelerator_config_codes()

        # add CPU configs
        codes += self.generate_cpu_config_codes()

        # add System Bus Width
        codes += self.generate_system_bus_config_codes()

        # default config
        codes += "  new chipyard.config.AbstractConfig)\n"
        
        return codes
    
    def write_chisel_config_codes(self, codes: str):
        with open(self.chisel_config_path, 'w') as f:
            f.write(codes)

    def run(self):
        info("Generating Chisel codes for SOC Config %s" % (self.get_config_name()))
        codes = self.generate_chisel_config_codes()
        self.write_chisel_config_codes(codes)