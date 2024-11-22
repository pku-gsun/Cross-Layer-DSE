import os
from typing import Callable

from manager.common import BaseManager
from utils import mkdir, if_exist


class InnovusManager(BaseManager):
    """
        Cadence Innovus Manager implement netlist into GDSII
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
        return 'innovus_manager'

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
    def mmmc_script_path(self) -> str:
        return os.path.join(self.script_dir, 'mmmc.tcl')

    @property
    def top_module(self) -> str:
        return self.configs.get('top_module')
    
    @property
    def innovus_bin(self) -> str:
        return self.configs.get('innovus_bin')

    def get_file_list(self, key: str, sep: str = " ") -> str:
        """
            Get the string of a file list from configs.
        """
        files = self.configs.get(key, [])
        return sep.join(files)
    
    def generate_code(self, name: str) -> str:
        """
            Generate code for specific script
        """
        if name == 'mmmc':
            return self.generate_mmmc_code()
        elif name == 'init':
            return self.generate_init_code()
        elif name == 'floorplan':
            return self.generate_floorplan_code()
        elif name == 'powerplan':
            return self.generate_powerplan_code()
        elif name == 'placement':
            return self.generate_placement_code()
        elif name == 'cts':
            return self.generate_cts_code()
        elif name == 'routing':
            return self.generate_routing_code()
        else:
            raise NotImplementedError("Script %s is not implemented" % name)

    def write_to_file(self, codes: str, filepath: str, is_tcl: bool, prev_checkpoint: str = None, cur_checkpoint: str = None) -> None:
        """
            Write the code to the file, with necessary checkpoints.
        """
        mkdir(os.path.dirname(filepath))

        with open(filepath, 'w') as f:
            if prev_checkpoint:
                load_codes = """
# -------------------------------------------------------------
# Read previous checkpoint
# -------------------------------------------------------------
source %s
""" % (os.path.join(self.data_dir, f'{prev_checkpoint}.enc'))
                f.write(load_codes)

            f.write(codes)

            if cur_checkpoint:
                save_codes = """
# -------------------------------------------------------------
# Save Design
# -------------------------------------------------------------
saveDesign %s
""" % os.path.join(self.data_dir, f'{cur_checkpoint}.enc')
                f.write(save_codes)

            if is_tcl:
                f.write("exit 0\n")

    def run_tcl_script(self, step_name: str, timeout: int, condition: Callable) -> None:
        cmd = "cd {} && source ~/.bashrc && " \
                "{} -no_gui -abort_on_error -overwrite " \
                "-file {} " \
                "-log {} ".format(
                self.rundir,
                self.innovus_bin,
                os.path.join(self.script_dir, f'{step_name}.tcl'),
                os.path.join(self.log_dir, step_name),
            )
        self.routine_check(timeout, cmd, condition)
    
    def run_impl(self) -> None:
        """
            Generate scripts and run innovus
        """
        default_steps = [
            'init',
            'floorplan',
            'powerplan',
            'placement',
            'cts',
            'routing',
        ]
        steps = self.configs.get('steps', default_steps)

        runmode = self.configs.get('runmode', 'normal')

        if runmode == 'fast':
            self.write_to_file(self.generate_mmmc_code(), self.mmmc_script_path, is_tcl=False)
            
            fused_code = "\n\n".join([self.generate_code(step) for step in steps])
            self.write_to_file(fused_code, os.path.join(self.script_dir, 'fused_pnr.tcl'), 
                               is_tcl=True, cur_checkpoint='routing')
            
            self.run_tcl_script(
                step_name='fused_pnr',
                timeout=24 * 3600,
                condition=lambda: if_exist(os.path.join(self.data_dir, 'routing.enc'))
            )
        
        elif runmode == 'normal':
            self.write_to_file(self.generate_mmmc_code(), self.mmmc_script_path, is_tcl=False)

            prev_step = None
            for step in steps:
                # Possibly you don't need a clock tree for combinational module
                # So you have to make sure you can run through the flow!
                self.write_to_file(self.generate_code(step),
                                   os.path.join(self.script_dir,  f'{step}.tcl'),
                                   is_tcl=True, prev_checkpoint=prev_step, cur_checkpoint=step)
                prev_step = step

            for step in steps:
                self.run_tcl_script(
                    step_name=step,
                    timeout=10 * 3600,
                    condition=lambda: if_exist(os.path.join(self.data_dir, f'{step}.enc'))
                )

        else:
            raise NotImplementedError("runmode %s is not supported" % runmode)

    def generate_output_impl(self) -> dict:
        return dict()

    def generate_mmmc_code(self) -> str:
        """
            Generate mmmc script
        """
        qrc_techfiles = self.get_file_list('qrc_techfiles')
        qrc_tech_suffix = ('-qrc_tech [list %s]' % qrc_techfiles) if qrc_techfiles else ''

        codes = """
# -------------------------------------------------------------
# Set the SDC FILE
# -------------------------------------------------------------
create_constraint_mode -name setup_constraint -sdc_files %s
create_constraint_mode -name hold_constraint -sdc_files %s

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
create_analysis_view -name setup_view -delay_corner setup_delay -constraint_mode setup_constraint
create_analysis_view -name hold_view -delay_corner hold_delay -constraint_mode hold_constraint

# -------------------------------------------------------------
# Set the analysis view for setup & hold
# -------------------------------------------------------------
set_analysis_view -setup { setup_view } -hold { hold_view }
""" % (
    self.configs.get('setup_sdc_file'),
    self.configs.get('hold_sdc_file'),
    self.get_file_list('setup_lib_files'),
    self.get_file_list('hold_lib_files'),
    qrc_tech_suffix,
)
        return codes
        
    def generate_init_code(self) -> str:
        """
            Generate init script
        """
        codes = """
# ---------------------------------------------
# Read input files
# ---------------------------------------------
set defHierChar {/}
set init_gnd_net {VSS}
set init_pwr_net {VDD}
set init_verilog {%s}
set init_lef_file {%s}
set init_mmmc_version 2
set init_mmmc_file {%s}
set init_top_cell %s

# -------------------------------------------------------------
# Set global configs
# -------------------------------------------------------------
setMultiCpuUsage -localCpu %d

init_design

# -------------------------------------------------------------
# Check design after init
# -------------------------------------------------------------
checkDesign -netList -noHtml -outfile %s
""" % (
    self.configs.get('verilog_file'),
    self.get_file_list('lef_files'),
    self.mmmc_script_path,
    self.top_module,
    self.configs.get('max_threads', 8),
    os.path.join(self.report_dir, 'check_netlist_upon_init.rpt'),
)
        codes += self.generate_timing_report_code(stage='prePlace')

        return codes
        
    def generate_floorplan_code(self) -> str:
        """
            Generate floorplan script.
        """
        codes = ""
        """
            Define a rectangular block die
            The area is placement density times total cell area
        """
        codes += """
# -------------------------------------------------------------
# Define the block die area
# -------------------------------------------------------------
floorPlan -site %s -su 1 %f 1 1 1 1
""" % (
    self.configs.get('place_site'),
    self.configs.get('place_utilization', 0.4),
)
        """
            Place the IO pins.
            For simplicity, we place these pins during placement, and do layer assignment.
        """
        codes += """
# -------------------------------------------------------------
# Place the block port
# -------------------------------------------------------------
setPlaceMode -place_global_place_io_pins true
"""
        """
            Place large macros and hierarchical modules.
            TODO: We'll fix this part later.
        """
        codes += """
# -------------------------------------------------------------
# Generate floorplan
# -------------------------------------------------------------
defOut -floorplan -noStdCells %s
""" % (
    os.path.join(self.data_dir, 'floorplan.def')
)
        return codes

    def generate_powerplan_code(self) -> str:
        """
            Generate powerplan script
        """
        codes = ""
        """
            Connect pins to PDN
        """
        codes += """
# -------------------------------------------------------------
# Global PG net connect
# -------------------------------------------------------------
set pwr_port %s
set gnd_port %s
globalNetConnect VDD -type pgpin -pin $pwr_port -inst *
globalNetConnect VDD -type tiehi -pin $pwr_port -inst *
globalNetConnect VDD -type net -net VDD
globalNetConnect VSS -type pgpin -pin $gnd_port -inst *
globalNetConnect VSS -type tielo -pin $gnd_port -inst *
globalNetConnect VSS -type net -net VSS
""" % (
    self.configs.get('pwr_port'),
    self.configs.get('gnd_port'),
)
        """
            Add power stripes between lower-level power rails and higher-level power net.
            Here we just add one horizontal layer and one vertical layer.
            (Double check asap7 lef for correct layer direction)
            TODO: potentially adding more stripes will benefit IR drop
        """
        codes += """
# -------------------------------------------------------------
# Add power stripes
# -------------------------------------------------------------
set stripe_width %f
set stripe_spacing %f
set stripe_distance %f

addStripe -nets {VSS VDD} \
    -layer {%s} \
    -direction vertical \
    -width $stripe_width \
    -spacing $stripe_spacing \
    -set_to_set_distance $stripe_distance \
    -start_from left \
    -uda power_stripe_v

addStripe -nets {VSS VDD} \
    -layer {%s} \
    -direction horizontal \
    -width $stripe_width \
    -spacing $stripe_spacing \
    -set_to_set_distance $stripe_distance \
    -start_from bottom \
    -uda power_stripe_h
""" % (
    self.configs.get('stripe_width'),
    self.configs.get('stripe_spacing'),
    self.configs.get('stripe_distance'),
    self.configs.get('stripe_v_layer'),
    self.configs.get('stripe_h_layer'),
)
        """
            Add power rails
            
        """
        codes += """
# -------------------------------------------------------------
# Add power rails
# -------------------------------------------------------------
set sroute_min_layer %s
set sroute_max_layer %s
sroute -connect { corePin } \
    -layerChangeRange " $sroute_min_layer $sroute_max_layer " \
    -corePinTarget { None } \
    -allowJogging 1 \
    -crossoverViaLayerRange " $sroute_min_layer $sroute_max_layer " \
    -nets { VDD VSS } \
    -allowLayerChange 1 \
    -targetViaLayerRange " $sroute_min_layer $sroute_max_layer " \
    -uda power_rail
""" % (
    self.configs.get('sroute_min_layer'),
    self.configs.get('sroute_max_layer'),
)
        """
            Verify connect violation
        """        
        codes += """
verifyConnectivity -type special \
    -noAntenna \
    -noWeakConnect \
    -noUnroutedNet \
    -error 1000 \
    -warning 50 \
    -report %s
verify_PG_short -no_routing_blkg -report %s
""" % (
    os.path.join(self.report_dir, 'powerplan_connectivity.rpt'),
    os.path.join(self.report_dir, 'powerplan_PG_short.rpt'),
)
        return codes

    def generate_placement_code(self) -> str:
        """
            Generate placement script
        """
        codes = ""
        
        codes += """
# -------------------------------------------------------------
# Default path group settings
# -------------------------------------------------------------
reset_path_group -all

set input [all_inputs]
set output [all_outputs]
set reg [filter_collection [all_registers] "is_integrated_clock_gating_cell != true"]
set ckgating [filter_collection [all_registers] "is_integrated_clock_gating_cell == true"]
set ignore_path_groups [list inp2reg reg2out reg2out feedthr]

# default path group definition
group_path -name reg2reg -from $reg -to $reg
group_path -name reg2cg -from $reg -to $ckgating
group_path -name in2reg -from $input
group_path -name reg2out -to $output
group_path -name feedthr -from $input -to $output

# default path group effort level
setPathGroupOptions reg2reg -effortLevel high
setPathGroupOptions reg2cg -effortLevel high
setPathGroupOptions in2reg -effortLevel low
setPathGroupOptions reg2out -effortLevel low
setPathGroupOptions feedthr -effortLevel low
setOptMode -ignorePathGroupsForHold $ignore_path_groups
"""

        # TODO: there're options eliminating IR Drop
        codes += """
# -------------------------------------------------------------
# Placement Mode settings
# -------------------------------------------------------------        
setPlaceMode -reset
setPlaceMode -place_global_ignore_scan true
setDesignMode -topRoutingLayer %s
setDesignMode -bottomRoutingLayer %s

# customized detailed placement options
setPlaceMode -place_detail_eco_max_distance %.1f
setPlaceMode -place_detail_eco_priority_insts %s
setPlaceMode -place_detail_activity_power_driven %s
setPlaceMode -place_detail_wire_length_opt_effort %s
setPlaceMode -place_detail_legalization_inst_gap %d

# customized global placement options
setPlaceMode -place_global_auto_blockage_in_channel %s
setPlaceMode -place_global_activity_power_driven %s
setPlaceMode -place_global_activity_power_driven_effort %s
setPlaceMode -place_global_clock_power_driven %s
setPlaceMode -place_global_clock_power_driven_effort %s
setPlaceMode -place_global_timing_effort %s
setPlaceMode -place_global_cong_effort %s
setPlaceMode -place_global_max_density %.3f
setPlaceMode -place_global_clock_gate_aware %s
setPlaceMode -place_global_uniform_density %s
""" % (
    self.configs.get('route_max_layer'),  # early global routing use same layer as detailed routing
    self.configs.get('route_min_layer'),
    # self.configs.get('process_node', ''),

    self.configs.get('place_detail_eco_max_distance', 10.0),            # 0 ~ 999, unit: micron
    self.configs.get('place_detail_eco_priority_insts', 'placed'),      # { placed | fixed | eco }
    self.configs.get('place_detail_activity_power_driven', 'false'),    # { true | false }
    self.configs.get('place_detail_wire_length_opt_effort', 'medium'),  # { none | medium | high }
    self.configs.get('place_detail_legalization_inst_gap', 0),          # 0 ~ 999, unit: micron

    self.configs.get('place_global_auto_blockage_in_channel', 'none'),  # { none | soft | partial }
    self.configs.get('place_global_activity_power_driven', 'false'),    # { true | false }
    self.configs.get('place_global_activity_power_driven_effort', 'standard'),  # { none | standard | high }
    self.configs.get('place_global_clock_power_driven', 'true'),        # { true | false }
    self.configs.get('place_global_clock_power_driven_effort', 'low'),  # { low | standard | high }
    self.configs.get('place_global_timing_effort', 'medium'),           # { medium | high }
    self.configs.get('place_global_cong_effort', 'auto'),               # { low | medium | high | auto }
    self.configs.get('place_global_max_density', -1.000),               # 0 ~ 1
    self.configs.get('place_global_clock_gate_aware', 'true'),          # { true | false }
    self.configs.get('place_global_uniform_density', 'false'),          # { true | false }
)

        codes += """
# -------------------------------------------------------------
# place the design & report congestion
# -------------------------------------------------------------
place_opt_design
reportCongestion -overflow
""" 
        codes += self.generate_timing_report_code(stage='preCTS')
        codes += self.generate_area_report_code(stage='preCTS')
        codes += self.generate_power_report_code(stage='preCTS')
        
        return codes

    def generate_cts_code(self) -> str:
        """
            Generate CTS script
        """
        codes = ""

        cts_inv_cells = map(lambda x: ('*/' + x) if not x.startswith('*/') else x, self.configs.get('cts_inv_cells', []))
        cts_inv_cells = ' '.join(cts_inv_cells)

        codes += """
# -------------------------------------------------------------
# set cts opt use cells
# -------------------------------------------------------------
set_ccopt_property use_inverters true
# FIXME: get_lib_cells have strange return values
# set cts_inv_cells [list %s]
# foreach lib_cell $cts_inv_cells {
#     setDontUse $lib_cell false
# }
# set_ccopt_property inverter_cells [get_db lib_cells $cts_inv_cells]
""" % cts_inv_cells
        
        codes += """
# -------------------------------------------------------------
# clk net routing non-default rule setting
# -------------------------------------------------------------
set mul %.2f
set ndr_cts_min_layer %s
set ndr_cts_max_layer %s
add_ndr -name cts_1 \
    -width_multiplier "$ndr_cts_min_layer:$ndr_cts_max_layer $mul" \
    -spacing_multiplier "$ndr_cts_min_layer:$ndr_cts_max_layer $mul"
create_route_type -name clk_net_rule \
    -non_default_rule cts_1 \
    -top_preferred_layer $ndr_cts_min_layer \
    -bottom_preferred_layer $ndr_cts_max_layer
set_ccopt_property -route_type clk_net_rule -net_type trunk
""" % (
    self.configs.get('cts_routing_mul', 2),
    self.configs.get('ndr_cts_min_layer'),
    self.configs.get('ndr_cts_max_layer'),
)

        codes += """
# -------------------------------------------------------------
# create cts
# -------------------------------------------------------------
create_ccopt_clock_tree_spec -file %s
source %s
""" % (
    os.path.join(self.data_dir, 'clk.spec'),
    os.path.join(self.data_dir, 'clk.spec'),
)
        
        codes += """
# -------------------------------------------------------------
# run ccopt
# -------------------------------------------------------------
ccopt_design -cts
report_ccopt_skew_groups
"""
        
        codes += """
# -------------------------------------------------------------
# post cts opt
# -------------------------------------------------------------
set_interactive_constraint_modes [all_constraint_modes -active]
set_propagated_clock [all_clocks]
setOptMode -fixDrc true -fixFanoutLoad true

optDesign -postCTS
optDesign -postCTS -hold
"""
        codes += self.generate_timing_report_code(stage='postCTS')

        return codes

    def generate_routing_code(self) -> str:
        """
            Generate routing script
        """
        codes = ""

        codes += """
# -------------------------------------------------------------
# NanoRoute Mode setting
# -------------------------------------------------------------
setAnalysisMode -analysisType onChipVariation

# FIXME: many routing configuration still missing!
#        They are now just copied from the example script
setNanoRouteMode -quiet -drouteEndIteration 70
setNanoRouteMode -quiet -drouteFixAntenna true
setNanoRouteMode -quiet -drouteUseMultiCutViaEffort medium
setNanoRouteMode -quiet -drouteMinSlackForWireOptimization 0.1
setDelayCalMode -engine default -siAware true
"""

        codes += """
# -------------------------------------------------------------
# Route Design
# -------------------------------------------------------------
routeDesign -globalDetail
"""
        
        codes += """
# -------------------------------------------------------------
# post routing opt
# -------------------------------------------------------------
optDesign -postRoute -setup
"""
        codes += self.generate_timing_report_code(stage='postRoute')
        codes += self.generate_area_report_code(stage='postRoute')
        codes += self.generate_power_report_code(stage='postRoute')

        return codes

    def generate_timing_report_code(self, stage: str) -> str:
        """
            Timing report code, reused in multiple stages ()
        """
        assert stage in ('prePlace', 'preCTS', 'postCTS', 'postRoute')

        timing_report_dir = os.path.join(self.report_dir, f'{stage}_timing')

        codes = """
# -------------------------------------------------------------
# Report design timing
# -------------------------------------------------------------
set report_dir %s

timeDesign -%s \
  -pathReports \
  -drvReports \
  -slackReports \
  -numPaths 50 \
  -prefix %s \
  -outDir ${report_dir}     

report_timing -nworst 1 -machine_readable > ${report_dir}/timing.rpt   
""" % (
    timing_report_dir,
    stage,
    stage,
)
        codes += """
# -------------------------------------------------------------
# Report path group timing
# -------------------------------------------------------------
"""
        for path_group in self.configs.get('path_groups', []):
                if path_group.get('report', False):
                    codes += """
report_timing -from %s -to %s -nworst 1 -machine_readable > ${report_dir}/group_timing_%s.rpt
""" % (
    path_group.get('from'),
    path_group.get('to'),
    path_group.get('name'),
)
        return codes
    
    def generate_area_report_code(self, stage: str) -> str:
        """
            Area report code
        """

        area_report_path = os.path.join(self.report_dir, f'{stage}_area.rpt')
        
        codes = """
# -------------------------------------------------------------
# Report area
# -------------------------------------------------------------
report_area -detail > %s
""" % area_report_path
        return codes

    def generate_power_report_code(self, stage: str) -> str:
        power_report_path = os.path.join(self.report_dir, f'{stage}_power.rpt')

        codes = """

# -------------------------------------------------------------
# Report area
# -------------------------------------------------------------
report_power -hierarchy all > %s
""" % power_report_path

        return codes