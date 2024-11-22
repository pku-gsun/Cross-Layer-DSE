import abc
from utils import if_exist

class StdcellLibrary(abc.ABC):

    def __init__(self, 
        pdk_dir: str, 
        syn_tool: str,
        pnr_tool: str,
        use_typical_corner: bool = True
    ) -> None:
        super().__init__()
        self.pdk_dir = pdk_dir
        self.syn_tool = syn_tool
        self.pnr_tool = pnr_tool
        self.use_typical_corner = use_typical_corner

    # properties of PDK

    @property
    def db_files(self) -> list:
        return []

    @property
    def lib_files(self) -> list:
        return []
    
    @property
    def setup_lib_files(self) -> list:
        return []
    
    @property
    def hold_lib_files(self) -> list:
        return []

    @property
    def lef_files(self) -> list:
        return []
    
    @property
    def qrc_techfiles(self) -> list:
        return []

    @property
    def dont_use_cells(self) -> list:
        return []
    
    @property
    def name(self) -> str:
        return "PDK"

    # helper functions

    def if_exist_files(self, files: list) -> None:
        for file in files:
            if_exist(file, strict=True)

    def to_dict(self) -> dict:
        d = {
            "pdk_name": self.name,
            "db_files": self.db_files,
            "lib_files": self.lib_files,
            "lef_files": self.lef_files,
            "qrc_techfiles": self.qrc_techfiles,
            "dont_use_cells": self.dont_use_cells,
        }

        if self.use_typical_corner:
            d.update({
                "setup_lib_files": self.lib_files,
                "hold_lib_files": self.lib_files,
            })
        else:
            d.update({
                "setup_lib_files": self.setup_lib_files,
                "hold_lib_files": self.hold_lib_files,
            })

        for var_name, file_list in d.items():
            if 'files' in var_name:
                self.if_exist_files(file_list)

        return d