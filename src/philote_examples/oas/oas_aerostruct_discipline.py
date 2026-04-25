"""OpenAeroStruct aerostructural discipline wrapped as a Philote sub-problem.

This module provides two classes:

* ``OasAerostructGroup`` -- an OpenMDAO Group that wires together the OAS
  AerostructGeometry and AerostructPoint components for a single lifting
  surface, performing coupled aero-structural analysis.
* ``OasAerostructDiscipline`` -- a Philote ``OpenMdaoSubProblem`` that exposes
  the group as a standalone gRPC discipline with flight-condition / mission
  inputs and aerodynamic + structural outputs.
"""

import logging

import numpy as np
import openmdao.api as om
from openaerostruct.geometry.utils import generate_mesh
from openaerostruct.integration.aerostruct_groups import (
    AerostructGeometry,
    AerostructPoint,
)
from openaerostruct.utils.constants import grav_constant
from philote_mdo.openmdao import OpenMdaoSubProblem

logger = logging.getLogger(__name__)


class OasAerostructGroup(om.Group):
    """OpenMDAO Group for a coupled OAS aerostructural analysis.

    An ``IndepVarComp`` exposes flow-condition and mission variables at the
    group level.  ``AerostructGeometry`` computes the wing geometry and
    structural setup, and ``AerostructPoint`` performs the coupled
    aero-structural solve (VLM + FEM with ``NonlinearBlockGS``).

    Parameters (via ``options``)
    ----------------------------
    surface : dict
        OAS surface dictionary (must include ``"name"``, ``"mesh"``, and
        structural material properties).
    """

    def initialize(self):
        self.options.declare("surface", types=dict)

    def setup(self):
        surface = self.options["surface"]
        name = surface["name"]

        # Flow-condition and mission inputs promoted to the group level
        indep = om.IndepVarComp()
        indep.add_output("v", val=1.0, units="m/s")
        indep.add_output("alpha", val=0.0, units="deg")
        indep.add_output("Mach_number", val=0.0)
        indep.add_output("re", val=1.0, units="1/m")
        indep.add_output("rho", val=1.0, units="kg/m**3")
        indep.add_output("CT", val=grav_constant * 17.0e-6, units="1/s")
        indep.add_output("R", val=11.165e6, units="m")
        indep.add_output("W0", val=0.4 * 3e5, units="kg")
        indep.add_output("speed_of_sound", val=295.4, units="m/s")
        indep.add_output("load_factor", val=1.0)
        indep.add_output("empty_cg", val=np.zeros(3), units="m")
        self.add_subsystem("prob_vars", indep, promotes=["*"])

        # Geometry: mesh transformations + tube cross-sections + FEM setup
        self.add_subsystem(name, AerostructGeometry(surface=surface))

        # Aerostructural analysis point (coupled VLM + FEM)
        self.add_subsystem("AS_point_0", AerostructPoint(surfaces=[surface]))

        # Connect flow / mission variables to the analysis point
        for var in (
            "v",
            "alpha",
            "Mach_number",
            "re",
            "rho",
            "CT",
            "R",
            "W0",
            "speed_of_sound",
            "empty_cg",
            "load_factor",
        ):
            self.connect(var, f"AS_point_0.{var}")

        # Connect geometry outputs to the coupled group
        self.connect(
            f"{name}.local_stiff_transformed",
            f"AS_point_0.coupled.{name}.local_stiff_transformed",
        )
        self.connect(f"{name}.nodes", f"AS_point_0.coupled.{name}.nodes")
        self.connect(f"{name}.mesh", f"AS_point_0.coupled.{name}.mesh")

        # Connect geometry outputs to the performance groups
        self.connect(f"{name}.radius", f"AS_point_0.{name}_perf.radius")
        self.connect(f"{name}.thickness", f"AS_point_0.{name}_perf.thickness")
        self.connect(f"{name}.nodes", f"AS_point_0.{name}_perf.nodes")
        self.connect(
            f"{name}.cg_location",
            f"AS_point_0.total_perf.{name}_cg_location",
        )
        self.connect(
            f"{name}.structural_mass",
            f"AS_point_0.total_perf.{name}_structural_mass",
        )
        self.connect(f"{name}.t_over_c", f"AS_point_0.{name}_perf.t_over_c")


class OasAerostructDiscipline(OpenMdaoSubProblem):
    """Philote discipline wrapping a coupled OAS aerostructural analysis.

    This discipline accepts flight conditions and mission parameters as
    inputs and returns aerodynamic coefficients, fuel burn, structural
    failure, and structural mass.  The wing geometry is fixed at
    construction time.

    Parameters
    ----------
    mesh_dict : dict, optional
        Dictionary passed to ``openaerostruct.geometry.utils.generate_mesh``.
        Defaults to a CRM wing with 5 spanwise and 2 chordwise panels.
    surface_options : dict, optional
        Extra entries merged into the OAS surface dictionary, allowing
        callers to override defaults such as material properties.
    """

    def __init__(self, mesh_dict=None, surface_options=None):
        self._mesh_dict = mesh_dict
        self._surface_options = surface_options
        super().__init__()
        self._build_discipline()

    def initialize(self):
        pass

    def _build_discipline(self):
        """Generate mesh, build the aerostructural group, and map variables."""
        # --- mesh generation ---
        if self._mesh_dict is None:
            self._mesh_dict = {
                "num_y": 5,
                "num_x": 2,
                "wing_type": "CRM",
                "symmetry": True,
                "num_twist_cp": 5,
            }

        result = generate_mesh(self._mesh_dict)

        if isinstance(result, tuple):
            mesh, twist_cp = result
        else:
            mesh = result
            twist_cp = None

        logger.info(
            "Mesh generated (type=%s, shape=%s)",
            self._mesh_dict.get("wing_type", "unknown"),
            mesh.shape,
        )

        # --- surface dictionary ---
        surface = {
            "name": "wing",
            "symmetry": self._mesh_dict.get("symmetry", True),
            "S_ref_type": "wetted",
            "fem_model_type": "tube",
            "mesh": mesh,
            "CL0": 0.0,
            "CD0": 0.015,
            "k_lam": 0.05,
            "t_over_c_cp": np.array([0.15]),
            "c_max_t": 0.303,
            "with_viscous": True,
            "with_wave": False,
            # Structural properties (aluminum 7075)
            "E": 70.0e9,
            "G": 30.0e9,
            "yield": 500.0e6 / 2.5,
            "mrho": 3.0e3,
            "fem_origin": 0.35,
            "wing_weight_ratio": 2.0,
            "struct_weight_relief": False,
            "distributed_fuel_weight": False,
            "exact_failure_constraint": False,
            "thickness_cp": np.array([0.1, 0.2, 0.3]),
        }

        if twist_cp is not None:
            surface["twist_cp"] = twist_cp

        if self._surface_options is not None:
            surface.update(self._surface_options)

        # --- build OpenMDAO group ---
        self.add_group(OasAerostructGroup(surface=surface))

        # --- map inputs (flight conditions + mission parameters) ---
        self.add_mapped_input("v", "v", shape=(1,), units="m/s")
        self.add_mapped_input("alpha", "alpha", shape=(1,), units="deg")
        self.add_mapped_input("Mach_number", "Mach_number", shape=(1,), units="")
        self.add_mapped_input("re", "re", shape=(1,), units="1/m")
        self.add_mapped_input("rho", "rho", shape=(1,), units="kg/m**3")
        self.add_mapped_input("CT", "CT", shape=(1,), units="1/s")
        self.add_mapped_input("R", "R", shape=(1,), units="m")
        self.add_mapped_input("W0", "W0", shape=(1,), units="kg")
        self.add_mapped_input(
            "speed_of_sound", "speed_of_sound", shape=(1,), units="m/s"
        )
        self.add_mapped_input("load_factor", "load_factor", shape=(1,), units="")
        self.add_mapped_input("empty_cg", "empty_cg", shape=(3,), units="m")

        # --- map outputs ---
        self.add_mapped_output("CL", "AS_point_0.wing_perf.CL", shape=(1,), units="")
        self.add_mapped_output("CD", "AS_point_0.wing_perf.CD", shape=(1,), units="")
        self.add_mapped_output("CM", "AS_point_0.CM", shape=(3,), units="")
        self.add_mapped_output(
            "fuelburn", "AS_point_0.fuelburn", shape=(1,), units="kg"
        )
        self.add_mapped_output(
            "failure", "AS_point_0.wing_perf.failure", shape=(1,), units=""
        )
        self.add_mapped_output(
            "structural_mass", "wing.structural_mass", shape=(1,), units="kg"
        )

        logger.info(
            "OasAerostructDiscipline built (inputs=%d, outputs=%d)",
            len(self._input_map),
            len(self._output_map),
        )

    def set_options(self, options):
        pass
