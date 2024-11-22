import os
from .stdcell_library import StdcellLibrary

class Nangate45Library(StdcellLibrary):
    """
        Nangate45 open-sourced PDK
        https://github.com/The-OpenROAD-Project/OpenROAD
    """

    def __init__(self, 
        pdk_dir: str,
        syn_tool: str = 'yosys',
        pnr_tool: str = 'openroad',
    ) -> None:
        super().__init__(pdk_dir, syn_tool, pnr_tool)
        assert syn_tool == 'yosys', "We cannot support Genus for now"
        assert pnr_tool == 'openroad', "We cannot support Innovus for now"

    @property
    def name(self) -> str:
        return "Nangate45"

    @property
    def db_files(self) -> list:
        db_files = [os.path.join(self.pdk_dir, 'NangateOpenCellLibrary.db')]
        return db_files

    @property
    def lib_files(self) -> list:
        lib_files = [os.path.join(self.pdk_dir, "Nangate45_typ.lib")]
        return lib_files
    
    @property
    def setup_lib_files(self) -> list:
        lib_files = [os.path.join(self.pdk_dir, "Nangate45_slow.lib")]
        return lib_files
    
    @property
    def hold_lib_files(self) -> list:
        lib_files = [os.path.join(self.pdk_dir, "Nangate45_fast.lib")]
        return lib_files

    @property
    def lef_files(self) -> list:
        lef_files = [
            os.path.join(self.pdk_dir, 'Nangate45_tech.lef'),
            os.path.join(self.pdk_dir, 'Nangate45_stdcell.lef'),
        ]
        return lef_files