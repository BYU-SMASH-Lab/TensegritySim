# Tensegrity Sim

This repo contains code to create a simulation for tensegrity structures. It allows for continuous cables and 2D, 2.5D and 3D structures. 

## Getting started

To get started with development, clone the repo and install the dependencies.

I reccommend using a venv to keep the libraries for this project separate from the main python interpreter. To create a venv, from the project's main directory run `python3 -m venv ./venv`. Now everytime you want to use this venv run `source venv/bin/activate`. To deactivate simply use the `deactivate` command. 

This project uses Python3, in order to run it you will need some dependencies. To get them you can run `pip install -r requirements.txt` (with the venv active)

To run the project:
```bash
python3 main.py <path/to/yaml/config>
```
Sample yaml config files are provided in the `yaml` directory. To understand how to change the simulation to your needs, see the [simulation setup](docs/setup.md) documentation. 

## Installation

If instead of helping develop the project you want to use it as a library, you can install it using pip. To install the project, to use as a library, run `pip install .` from the project's main directory. This will install the `TensegritySim` module and allow you to import it in your own projects.

If you want to install from a different directory, you can run `pip install <path/to/project>` or `pip install -e <path/to/project>` to install in editable mode. Or without cloning the repo, you can run `pip install git+<git-repo-url>`.

## Definitions and Conventions (as used in this project)
Strings - Strings are connection types that only carry tension, they lengthen as force is applied  
Bar - A bar can carry either tension or compression, but does not change length  
Forces - Tensions are positive values and compression forces in connections are negative.

## Organization
`main.py` is the primary file to run the project. It take as an input a yaml file an allows the user to change the length of control strings

### TensegritySim Module
The `TensegritySim` directory contains all the code TensegritySim python module.
* `data_structures.py` contains the `Node`, `Connection`, `Control`, and `Tensegrity` classes
* `yaml_parser.py` reads the yaml file and returns the Tensegrity object. See [YAML Reference](docs/yaml.md) for how to format the yaml file
* `visualization.py` shows the tensegrity structure using matplotlib
* `tensegrity_solver.py` uses an optimizer to solve for an updated structure

### yaml
The `yaml` directory contains sample yaml files for running the sim