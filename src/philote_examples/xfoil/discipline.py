"""XFOIL Philote discipline for airfoil analysis."""

import os
import tempfile
from pathlib import Path

import numpy as np
import philote_mdo.general as pmdo

from philote_examples.xfoil.wrapper import (
    parse_output_file,
    run_xfoil,
    write_airfoil_file,
    write_command_file,
)


class XfoilDiscipline(pmdo.ExplicitDiscipline):
    """Philote discipline that wraps XFOIL for airfoil analysis.

    This discipline computes aerodynamic coefficients (Cl, Cd, Cm) for
    a given airfoil geometry at specified flight conditions.

    Parameters
    ----------
    n_points : int
        Number of points defining the airfoil geometry.

    Environment Variables
    ---------------------
    XFOIL_PATH : str
        Path to the XFOIL executable. Must be set before running.
    """

    def __init__(self, n_points: int):
        super().__init__()
        self.n_points = n_points
        self.xfoil_path = None
        self.viscous = True

    def initialize(self):
        """Declare available options."""
        self.add_option("viscous", "bool")

    def set_options(self, options):
        """Set option values from client."""
        if "viscous" in options:
            self.viscous = bool(options["viscous"])

    def setup(self):
        """Define inputs and outputs for the XFOIL discipline."""
        # Read XFOIL path from environment, default to "xfoil" on PATH
        self.xfoil_path = os.environ.get("XFOIL_PATH")
        if self.xfoil_path is None:
            raise ValueError("Environment variable XFOIL_PATH not set. You must set XFOIL_PATH so the program can find xfoil.exe.")

        # Flight condition inputs
        self.add_input("alpha", shape=(1,), units="deg")
        if self.viscous:
            self.add_input("reynolds", shape=(1,), units="")
            self.add_input("mach", shape=(1,), units="")

        # Airfoil geometry inputs
        self.add_input("airfoil_x", shape=(self.n_points,), units="")
        self.add_input("airfoil_y", shape=(self.n_points,), units="")

        # Aerodynamic coefficient outputs
        self.add_output("cl", shape=(1,), units="")
        self.add_output("cd", shape=(1,), units="")
        self.add_output("cm", shape=(1,), units="")

    def compute(self, inputs, outputs):
        """Run XFOIL and compute aerodynamic coefficients.

        Parameters
        ----------
        inputs : dict
            Input dictionary containing:
            - alpha: angle of attack (deg)
            - reynolds: Reynolds number
            - mach: Mach number
            - airfoil_x: airfoil x-coordinates
            - airfoil_y: airfoil y-coordinates

        outputs : dict
            Output dictionary to be populated with:
            - cl: lift coefficient
            - cd: drag coefficient
            - cm: moment coefficient
        """
        # Extract inputs
        alpha = float(inputs["alpha"][0])
        airfoil_x = inputs["airfoil_x"]
        airfoil_y = inputs["airfoil_y"]

        cmd_kwargs = dict(alpha=alpha, viscous=self.viscous)
        if self.viscous:
            cmd_kwargs["reynolds"] = float(inputs["reynolds"][0])
            cmd_kwargs["mach"] = float(inputs["mach"][0])

        # Create temporary directory for XFOIL files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            airfoil_file = tmpdir / "airfoil.dat"
            command_file = tmpdir / "commands.txt"
            output_file = tmpdir / "output.dat"

            # Write input files
            write_airfoil_file(airfoil_x, airfoil_y, airfoil_file)
            write_command_file(
                command_file,
                airfoil_file,
                output_file,
                **cmd_kwargs,
            )

            # Run XFOIL
            run_xfoil(self.xfoil_path, command_file)

            # Parse results
            results = parse_output_file(output_file)

        # Set outputs
        outputs["cl"] = np.array([results["cl"]])
        outputs["cd"] = np.array([results["cd"]])
        outputs["cm"] = np.array([results["cm"]])
