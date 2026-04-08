# philote-examples

[![CI](https://github.com/MDO-Standards/philote-examples/actions/workflows/ci.yml/badge.svg)](https://github.com/MDO-Standards/philote-examples/actions/workflows/ci.yml)

Examples for the AIAA MDO TC Standard Interface Working Group.

## Installation Instructions

These are the instructions to get started with the Philote-Examples

  1a) Install philote examples repository (without tests)  
    - `pip install -e`  
  1b) Install philote examples (with tests)  
    - `pip install -e[dev]`  

## Tests

To run all tests execute all the pytest tests

- Open a command prompt 
- Change directory into `philote-examples` repo
  - `cd <path\to\philote-examples>`  
- Run pytest tests  
  -  `pytest`

**NOTE**: If running xfoil example test, you must download xfoil analysis and set XFOIL_PATH environment variable

## XFOIL Example

The xfoil example showcases how Philote can connect to an 
aerospace-relevant external discipline using its python bindings and
it's open-mdao-like problem formulation.
Openmdao is used as the integration framework to perform the test with 
the philote server communicating the data to and from Xfoil as it performs its analysis.

To set up XFOIL Example you must perform the following steps

1) Download [xfoil software](https://web.mit.edu/drela/Public/web/xfoil/)
2) Set environment variable `XFOIL_PATH=<path/to/xfoil.exe>`

### Run XFOIL tests  

The xfoil example can be executed by running the xfoil tests only (or all tests)

`pytest test_naca_xfoil.py`  
`pytest test_naca_gradients.py`  


