"""Split structural discipline for OAS aerostructural analysis.

This module provides two classes:

* ``OasSplitStructGroup`` -- an OpenMDAO Group that performs the structural
  side of the aerostructural coupling loop: FEM beam solve and structural
  failure computation.
* ``OasSplitStructDiscipline`` -- a Philote ``OpenMdaoSubProblem`` that
  exposes the group as a standalone gRPC discipline.

In a split aerostructural analysis the coupling variables are:

* **Input from aero**: ``loads`` (ny, 6) -- aerodynamic loads
* **Output to aero**: ``disp`` (ny, 6) -- structural displacements
"""

import logging

import numpy as np
import openmdao.api as om
from openaerostruct.geometry.utils import generate_mesh
from openaerostruct.structures.spatial_beam_functionals import (
    SpatialBeamFunctionals,
)
from openaerostruct.structures.spatial_beam_states import SpatialBeamStates
from philote_mdo.openmdao import OpenMdaoSubProblem

logger = logging.getLogger(__name__)


class OasSplitStructGroup(om.Group):
    """OpenMDAO Group for the structural side of a split aerostructural analysis.

    Contains the FEM beam solver (``SpatialBeamStates``) and structural
    failure evaluation (``SpatialBeamFunctionals``).

    Parameters (via ``options``)
    ----------------------------
    surface : dict
        OAS surface dictionary (must include structural material properties).
    """

    def initialize(self):
        self.options.declare("surface", types=dict)

    def setup(self):
        surface = self.options["surface"]

        # FEM solver: local_stiff_transformed + loads → disp
        self.add_subsystem(
            "struct_states",
            SpatialBeamStates(surface=surface),
            promotes_inputs=["local_stiff_transformed", "loads"],
            promotes_outputs=["disp"],
        )

        # Structural failure evaluation: thickness + radius + nodes + disp → failure
        self.add_subsystem(
            "struct_funcs",
            SpatialBeamFunctionals(surface=surface),
            promotes_inputs=["thickness", "radius", "nodes", "disp"],
            promotes_outputs=["failure"],
        )


class OasSplitStructDiscipline(OpenMdaoSubProblem):
    """Philote discipline for the structural side of a split aerostructural analysis.

    Accepts aerodynamic loads (``loads``), geometry constants, and returns
    structural displacements (``disp``) for the aero discipline and the
    structural ``failure`` metric.

    Parameters
    ----------
    mesh_dict : dict, optional
        Dictionary passed to ``openaerostruct.geometry.utils.generate_mesh``.
        Defaults to a CRM wing with 5 spanwise and 2 chordwise panels.
    surface_options : dict, optional
        Extra entries merged into the OAS surface dictionary.
    """

    def __init__(self, mesh_dict=None, surface_options=None):
        self._mesh_dict = mesh_dict
        self._surface_options = surface_options
        super().__init__()

    def initialize(self):
        self.add_option("mesh_dict", "dict")
        self.add_option("surface", "dict")

    def _build_discipline(self):
        """Generate mesh, build the struct group, and map variables."""
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

        ny = mesh.shape[1]

        logger.info(
            "Mesh generated (type=%s, ny=%d)",
            self._mesh_dict.get("wing_type", "unknown"),
            ny,
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
            for key, val in surface.items():
                if isinstance(val, list):
                    surface[key] = np.array(val)

        # --- build OpenMDAO group ---
        self.add_group(OasSplitStructGroup(surface=surface))

        # --- map inputs ---
        # Coupling input (from aero discipline)
        self.add_mapped_input("loads", "loads", shape=(ny, 6), units="")

        # Geometry constants (from geometry discipline)
        self.add_mapped_input(
            "local_stiff_transformed",
            "local_stiff_transformed",
            shape=(ny - 1, 12, 12),
            units="",
        )
        self.add_mapped_input("nodes", "nodes", shape=(ny, 3), units="m")
        self.add_mapped_input("radius", "radius", shape=(ny - 1,), units="m")
        self.add_mapped_input("thickness", "thickness", shape=(1, ny - 1), units="m")

        # --- map outputs ---
        # Coupling output (to aero discipline)
        self.add_mapped_output("disp", "disp", shape=(ny, 6), units="")

        # Structural performance
        self.add_mapped_output("failure", "failure", shape=(1,), units="")

        logger.info(
            "OasSplitStructDiscipline built (inputs=%d, outputs=%d)",
            len(self._input_map),
            len(self._output_map),
        )

    def set_options(self, options):
        if "mesh_dict" in options:
            self._mesh_dict = dict(options["mesh_dict"])
        if "surface" in options:
            self._surface_options = dict(options["surface"])

    def setup(self):
        self._build_discipline()
        super().setup()
