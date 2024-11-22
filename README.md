# Cross-Layer DSE

Cross-Layer Design Space Exploration Framework

## Requirements

- Python >= 3.12
- Pytorch >= 2.3.1
- yosys >= 0.27
- OpenROAD >= 2.0
- Cadence Genus
- Cadence Innovus

## Installation

- Install yosys and OpenROAD executable binaries
```
conda install -c litex-hub --prefix ~/.conda-yosys yosys=0.27_4_gb58664d44
conda install -c litex-hub --prefix ~/.conda-openroad openroad=2.0_7070_g0264023b6
```

- Clone OpenROAD repository to use PDKs and scripts
```
git clone https://github.com/The-OpenROAD-Project/OpenROAD.git
```
