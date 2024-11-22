import os
from typing import Callable

from .stdcell_library import StdcellLibrary

def collect_filtered_files(root: str, filter_func: Callable) -> list:
    """
        Collect files from root directory using filter_func and output_func.
    """
    files = os.listdir(root)
    files = list(filter(filter_func, files))
    files = [os.path.join(root, f) for f in files]
    return files

class Asap7Library(StdcellLibrary):
    """
        Asap7 open-sourced PDK
        https://github.com/The-OpenROAD-Project/asap7
    """

    def __init__(
        self, 
        pdk_dir: str, 
        syn_tool: str = 'genus',
        pnr_tool: str = 'innovus',
        version: str = 'asap7sc7p5t_27',
    ) -> None:
        super().__init__(pdk_dir, syn_tool, pnr_tool)
        self.version = version
        assert version in (
            'asap7sc6t_26',
            'asap7sc7p5t_27',
            'asap7sc7p5t_28',
        )
        assert syn_tool == 'genus', "We cannot support Yosys for now"
        assert pnr_tool == 'innovus', "We cannot support OpenROAD for now"

    @property
    def name(self) -> str:
        return "Asap7"

    @property
    def lib_files(self) -> list:
        lib_dir = os.path.join(self.pdk_dir, self.version, 'LIB/NLDM')
        lib_files = collect_filtered_files(lib_dir, lambda x: x.endswith('TT_nldm_201020.lib.gz'))
        return lib_files
    
    @property
    def db_files(self) -> list:
        db_files = [os.path.join(self.pdk_dir, 'asap7sc7p5t_AO_LVT_FF_nldm_211120.db')]
        return db_files
    
    @property
    def setup_lib_files(self) -> list:
        lib_dir = os.path.join(self.pdk_dir, self.version, 'LIB/NLDM')
        lib_files = collect_filtered_files(lib_dir, lambda x: x.endswith('SS_nldm_201020.lib.gz'))
        return lib_files
    
    @property
    def hold_lib_files(self) -> list:
        lib_dir = os.path.join(self.pdk_dir, self.version, 'LIB/NLDM')
        lib_files = collect_filtered_files(lib_dir, lambda x: x.endswith('FF_nldm_201020.lib.gz'))
        return lib_files

    @property
    def lef_files(self) -> list:
        # techlef
        lef_files = [os.path.join(self.pdk_dir, self.version, 'techlef_misc', 'asap7_tech_4x_201209.lef')]
        # stdcell lef
        lef_dir = os.path.join(self.pdk_dir, self.version, 'LEF', 'scaled')
        lef_files += collect_filtered_files(lef_dir, lambda x: x.endswith('.lef'))
        return lef_files
    
    @property
    def qrc_techfiles(self) -> list:
        return [os.path.join(self.pdk_dir, self.version, 'qrc', 'qrcTechFile_typ03_scaled4xV06')]
    
    @property
    def dont_use_cells(self) -> list:
        return [
            "ICGx*DC*",
            "AND4x1*",
            "SDFLx2*",
            "AO21x1*",
            "XOR2x2*",
            "OAI31xp33*",
            "OAI221xp5*",
            "SDFLx3*",
            "SDFLx1*",
            "AOI211xp5*",
            "OAI322xp33*",
            "OR2x6*",
            "A2O1A1O1Ixp25*",
            "XNOR2x1*",
            "OAI32xp33*",
            "FAx1*",
            "OAI21x1*",
            "OAI31xp67*",
            "OAI33xp33*",
            "AO21x2*",
            "AOI32xp33*"
        ]
    
    @property
    def innovus_vars(self) -> list:
        return {
        # floorplan
        'place_site': 'asap7sc7p5t',

        # powerplan
        'pwr_port': 'VDD',
        'gnd_port': 'VSS',
        'stripe_width': 6,
        'stripe_spacing': 4,
        'stripe_distance': 30,
        'stripe_v_layer': 'M8',
        'stripe_h_layer': 'M9',
        'sroute_min_layer': 'M1',
        'sroute_max_layer': 'M8',

        # placement
        'route_min_layer': 'M1',
        'route_max_layer': 'M8',

        # cts
        'cts_routing_mul': 2,
        'ndr_cts_min_layer': 'M1',
        'ndr_cts_max_layer': 'M8',
        'cts_inv_cells': [],
        'cts_buf_cells': [],
    }

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update(self.innovus_vars)
        return d