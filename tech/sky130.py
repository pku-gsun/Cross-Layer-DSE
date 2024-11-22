import os
from typing import Callable

from .stdcell_library import StdcellLibrary

class Sky130Library(StdcellLibrary):
    """
        sky130 PDK
    """

    def __init__(
        self, 
        pdk_dir: str, 
        syn_tool: str = 'dc',
        pnr_tool: str = 'innovus',
    ) -> None:
        super().__init__(pdk_dir, syn_tool, pnr_tool)

    @property
    def name(self) -> str:
        return "Sky130"

    @property
    def db_files(self) -> list:
        db_files = [os.path.join(self.pdk_dir, 'sky130_fd_sc_hd__tt_025C_1v80.db')]
        return db_files
