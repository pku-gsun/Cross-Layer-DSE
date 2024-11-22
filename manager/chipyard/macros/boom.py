import os
from .macros import Macros
from utils import info

class BoomMacros(Macros):
    """
        Generate chisel configuration for Boom Core.
    """
    def __init__(self, configs: dict) -> None:
        super().__init__(configs)
        self.macros = configs["boom_configs"]

    @property
    def chisel_config_path(self) -> str:
        return os.path.join(
            self.chipyard_root,
            "generators",
            "boom",
            "src",
            "main",
            "scala",
            "common",
            "%s.scala" % self.get_config_name()  # support compiling in parallel
        )

    def get_config_name(self) -> str:
        return self.macros.get("config_name")

    def generate_branch_predictor(self) -> str:
        """
            default branch predictor: TAGEL
        """
        return "new WithTAGELBPD ++"
    
    def generate_fetch_width(self) -> int:
        return self.macros.get("fetch_width")
    
    def generate_decode_width(self) -> int:
        return self.macros.get("decode_width")
    
    def generate_fetch_buffer_entries(self) -> int:
        return self.macros.get("fetch_buffer_entries")
    
    def generate_rob_entries(self) -> int:
        return self.macros.get("rob_entries")
    
    def generate_ras_entries(self) -> int:
        return self.macros.get("ras_entries")
    
    def generate_phy_registers(self) -> str:
        return """numIntPhysRegisters = %d,
                    numFpPhysRegisters = %d""" % (
                self.macros.get("int_phy_registers"),
                self.macros.get("fp_phy_registers")
            )
    
    def generate_lsu(self) -> str:
        return """numLdqEntries = %d,
                    numStqEntries = %d""" % (
                self.macros.get("ldq_entries"),
                self.macros.get("stq_entries")
            )
    
    def generate_max_br_count(self) -> int:
        return self.macros.get("max_br_count")
    
    def generate_issue_parames(self) -> str:
        """
            Reinterpret BoomExplorer's code with my understanding.
        """
        # shared by mem, int and fp
        dispatch_width = self.macros.get("decode_width")
        
        # select IQT_MEM/INT/FP.numEntries
        isu_params = [
            [8, 8, 8],
            [12, 20, 16],
            [16, 32, 24],
            [24, 40, 32],
            [24, 40, 32],
        ]
        iqt_mem_num_entries, iqt_int_num_entries, iqt_fp_num_entries = isu_params[dispatch_width - 1]
        return """Seq(
                        IssueParams(issueWidth=%d, numEntries=%d, iqType=IQT_MEM.litValue, dispatchWidth=%d),
                        IssueParams(issueWidth=%d, numEntries=%d, iqType=IQT_INT.litValue, dispatchWidth=%d),
                        IssueParams(issueWidth=%d, numEntries=%d, iqType=IQT_FP.litValue, dispatchWidth=%d)
                    )""" % (
                self.macros.get("mem_issue_width"), iqt_mem_num_entries, dispatch_width,
                self.macros.get("int_issue_width"), iqt_int_num_entries, dispatch_width,
                self.macros.get("fp_issue_width"),  iqt_fp_num_entries, dispatch_width
            )
    
    def generate_ftq_entries(self) -> int:
        # select ftq entries from decode width
        ftq_entries = [8, 16, 24, 32, 32]
        decode_width = self.macros.get("decode_width")
        return ftq_entries[decode_width - 1]

    def generate_dcache_and_mmu(self) -> str:
        return """Some(
                    DCacheParams(
                        rowBits=site(SystemBusKey).beatBits,
                        nSets=64,
                        nWays=%d,
                        nMSHRs=%d,
                        nTLBSets=1,
                        nTLBWays=%d
                    )
                    )""" % (
                self.macros.get("dcache_ways"),
                self.macros.get("dcache_mshrs"),
                self.macros.get("dcache_tlbs")
            )

    def generate_icache_and_mmu(self):
        return """Some(
                      ICacheParams(
                        rowBits=site(SystemBusKey).beatBits,
                        nSets=64,
                        nWays=%d,
                        nTLBSets=1,
                        nTLBWays=%d,
                        fetchBytes=%d*4
                      )
                    )""" % (
                self.macros.get("icache_ways"),
                self.macros.get("icache_tlbs"),
                self.macros.get("icache_fetch_bytes")
            )
    
    def generate_system_bus_key(self):
        return self.macros.get("fetch_width") << 1

    def generate_chisel_config_codes(self):
        codes = '''
class %s(n: Int = 1, overrideIdOffset: Option[Int] = None) extends Config(
  %s
  new Config((site, here, up) => {
    case TilesLocated(InSubsystem) => {
      val prev = up(TilesLocated(InSubsystem), site)
      val idOffset = overrideIdOffset.getOrElse(prev.size)
      (0 until n).map { i =>
        BoomTileAttachParams(
          tileParams = BoomTileParams(
            core = BoomCoreParams(
              fetchWidth = %d,
              decodeWidth = %d,
              numFetchBufferEntries = %d,
              numRobEntries = %d,
              numRasEntries = %d,
              %s,
              %s,
              maxBrCount = %d,
              issueParams = %s,
              ftq = FtqParameters(nEntries=%d),
              fpu = Some(
                freechips.rocketchip.tile.FPUParams(
                  sfmaLatency=4, dfmaLatency=4, divSqrt=true
                )
              ),
              enablePrefetching = true
            ),
            dcache = %s,
            icache = %s,
            hartId = i + idOffset
          ),
          crossingParams = RocketCrossingParams()
        )
      } ++ prev
    }
    case SystemBusKey => up(SystemBusKey, site).copy(beatBytes = %d)
    case XLen => 64
  })
)
''' % (
    self.get_config_name(),
    self.generate_branch_predictor(),
    self.generate_fetch_width(),
    self.generate_decode_width(),
    self.generate_fetch_buffer_entries(),
    self.generate_rob_entries(),
    self.generate_ras_entries(),
    self.generate_phy_registers(),
    self.generate_lsu(),
    self.generate_max_br_count(),
    self.generate_issue_parames(),
    self.generate_ftq_entries(),
    self.generate_dcache_and_mmu(),
    self.generate_icache_and_mmu(),
    self.generate_system_bus_key()
)
        return codes
        
    def write_chisel_config_codes(self, codes: str):
        prefix = """
package boom.common

import chisel3._
import chisel3.util.{log2Up}

import org.chipsalliance.cde.config.{Parameters, Config, Field}
import freechips.rocketchip.subsystem._
import freechips.rocketchip.devices.tilelink.{BootROMParams}
import freechips.rocketchip.diplomacy.{SynchronousCrossing, AsynchronousCrossing, RationalCrossing}
import freechips.rocketchip.rocket._
import freechips.rocketchip.tile._

import boom.ifu._
import boom.exu._
import boom.lsu._

"""
        with open(self.chisel_config_path, 'w') as f:
            f.write(prefix)
            f.write(codes)

    def run(self):
        info('Generating Chisel codes for Boom Config %s' % (self.get_config_name()))
        codes = self.generate_chisel_config_codes()
        self.write_chisel_config_codes(codes)
