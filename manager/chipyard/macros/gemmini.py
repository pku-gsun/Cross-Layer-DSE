import os
from .macros import Macros
from utils import info

class GemminiMacros(Macros):
    """
        Generate chisel configuration for Gemmini.
    """
    def __init__(self, configs: dict) -> None:
        super().__init__(configs)
        self.macros = configs['gemmini_configs']

    @property
    def chisel_config_path(self) -> str:
        return os.path.join(
            self.chipyard_root,
            "generators",
            "gemmini",
            "src",
            "main",
            "scala",
            "gemmini",
            "%s.scala" % self.get_config_name()  # support compiling in parallel
        )
    
    def get_config_name(self):
        return self.macros.get("config_name")
    
    def generate_config_codes(self):
        codes = """
package gemmini

import org.chipsalliance.cde.config.{Config, Parameters}
import chisel3._
import freechips.rocketchip.diplomacy.LazyModule
import freechips.rocketchip.subsystem.SystemBusKey
import freechips.rocketchip.tile.BuildRoCC


object %sArrayConfig {
    val defaultConfig = GemminiConfigs.defaultConfig

    val customConfig = defaultConfig.copy(
        // Data types
        inputType = SInt(%d.W),
        accType = SInt(%d.W),
        spatialArrayOutputType = SInt(%d.W),

        // Spatial array PE options
        tileRows = %d,
        tileColumns = %d,
        meshRows = %d,
        meshColumns = %d,

        // Dataflow
        dataflow = Dataflow.%s,

        // Scratchpad and accumulator
        sp_capacity = CapacityInKilobytes(%d),
        acc_capacity = CapacityInKilobytes(%d),
        sp_banks = %d,
        acc_banks = %d,

        // Ld/Ex/St instruction queue lengths
        ld_queue_length = %d,
        st_queue_length = %d,
        ex_queue_length = %d,

        // Reservation station entries
        reservation_station_entries_ld = %d,
        reservation_station_entries_st = %d,
        reservation_station_entries_ex = %d,

        // DMA options
        max_in_flight_mem_reqs = %d,
        dma_maxbytes = %d,
        dma_buswidth = %d,

        // TLB options
        tlb_size = %d,
    )
}

class %s[T <: Data : Arithmetic, U <: Data, V <: Data](
  gemminiConfig: GemminiArrayConfig[T,U,V] = %sArrayConfig.customConfig
) extends Config((site, here, up) => {
  case BuildRoCC => up(BuildRoCC) ++ Seq(
    (p: Parameters) => {
      implicit val q = p
      val gemmini = LazyModule(new Gemmini(gemminiConfig))
      gemmini
    }
  )
})

""" % (
            self.get_config_name(),
            self.macros.get('input_type'),
            self.macros.get('acc_type'),
            self.macros.get('output_type'),
            self.macros.get('tile_rows'),
            self.macros.get('tile_columns'),
            self.macros.get('mesh_rows'),
            self.macros.get('mesh_columns'),
            self.macros.get('dataflow'),  # WS, OS, BOTH
            self.macros.get('sp_capacity'),
            self.macros.get('acc_capacity'),
            self.macros.get('sp_banks'),
            self.macros.get('acc_banks'),
            self.macros.get('ld_queue_length'),
            self.macros.get('st_queue_length'),
            self.macros.get('ex_queue_length'),
            self.macros.get('ld_res_entries'),
            self.macros.get('st_res_entries'),
            self.macros.get('ex_res_entries'),
            self.macros.get('max_in_flight_mem_reqs'),
            self.macros.get('dma_maxbytes'),
            self.macros.get('dma_buswidth'),
            self.macros.get('tlb_sizes'),
            self.get_config_name(),
            self.get_config_name(),
        )
        return codes
    
    def write_config_codes(self, codes: str):
        with open(self.chisel_config_path, 'w') as f:
            f.write(codes)

    def run(self):
        info("Generating Chisel codes for Gemmini Config %s" % self.get_config_name())
        codes = self.generate_config_codes()
        self.write_config_codes(codes)