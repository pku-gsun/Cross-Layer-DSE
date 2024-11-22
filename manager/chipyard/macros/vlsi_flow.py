import os
from .macros import Macros
from utils import info, warn, dump_yaml, read_yaml, assert_error, mkdir, if_exist

class VlsiFlow(Macros):
    def __init__(self, configs: dict) -> None:
        super().__init__(configs)
        self.macros = configs['vlsi_configs']
        self._obj_dir = configs['rundir']

    @property
    def obj_dir(self) -> str:
        return self._obj_dir
    
    @property
    def input_conf_dir(self) -> str:
        return os.path.join(self.obj_dir, 'vlsi_input_confs')
    
    @property
    def env_yml_path(self) -> str:
        return os.path.join(self.input_conf_dir, 'env.yml')
    
    @property
    def tech_conf_path(self) -> str:
        return os.path.join(self.input_conf_dir, 'tech_conf.yml')
    
    @property
    def tools_conf_path(self) -> str:
        return os.path.join(self.input_conf_dir, 'tools_conf.yml')

    def generate_env_yml(self):
        cds_lic_file = os.environ.get('CDS_LIC_FILE')
        assert cds_lic_file, assert_error('CDS_LIC_FILE missing in environment variables!')
        snpslmd_license_file = os.environ.get('SNPSLMD_LICENSE_FILE')
        assert snpslmd_license_file, assert_error('SNPSLMD_LICENSE_FILE missing in environment variables!')

        env_yml = {
            'cadence.CDS_LIC_FILE': cds_lic_file,
            'synopsys.SNPSLMD_LICENSE_FILE': snpslmd_license_file,
        }
        dump_yaml(env_yml, self.env_yml_path)

    def generate_tech_conf(self):
        # by default we use asap7
        example_tech_conf = os.path.join(self.chipyard_root, 'vlsi', 'example-asap7.yml')
        assert if_exist(example_tech_conf), assert_error('Example tech conf not found!')
        tech_conf = read_yaml(example_tech_conf)

        asap7_dir = self.macros['asap7_root']
        assert if_exist(asap7_dir), assert_error('ASAP7 directory not found!')
        pdk_install_dir = os.path.join(asap7_dir, 'asap7_pdk_r1p7')
        assert if_exist(pdk_install_dir), assert_error('ASAP7 PDK not found!')
        stdcell_install_dir = os.path.join(asap7_dir, 'asap7sc7p5t_27')
        assert if_exist(stdcell_install_dir), assert_error('ASAP7 standard cell library not found!')

        tech_conf['technology.asap7.tarball_dir'] = asap7_dir
        tech_conf['technology.asap7.pdk_install_dir'] = pdk_install_dir
        tech_conf['technology.asap7.stdcell_install_dir'] = stdcell_install_dir

        dump_yaml(tech_conf, self.tech_conf_path)


    def generate_tools_conf(self):
        warn("Skip generating tools_conf, We don't use Chipyard to run backend flow for now.")

        dump_yaml({}, self.tools_conf_path)

    def run(self):
        info("Generating input configurations for VLSI flow")

        mkdir(self.input_conf_dir)
        self.generate_env_yml()
        self.generate_tech_conf()
        self.generate_tools_conf()