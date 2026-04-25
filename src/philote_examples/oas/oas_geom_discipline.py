"""OpenAeroStruct aerostructural geometry discipline wrapped as a Philote sub-problem.

This module provides two classes:

* ``OasGeomGroup`` -- an OpenMDAO Group that wraps ``AerostructGeometry``
  with design-variable inputs (twist, thickness control points).
* ``OasGeomDiscipline`` -- a Philote ``OpenMdaoSubProblem`` that exposes the
  group as a standalone gRPC discipline producing geometry constants consumed
  by separate aero and structural disciplines.
"""

import logging

import numpy as np
import openmdao.api as om
from openaerostruct.geometry.utils import generate_mesh
from openaerostruct.integration.aerostruct_groups import AerostructGeometry
from philote_mdo.openmdao import OpenMdaoSubProblem

logger = logging.getLogger(__name__)


class OasGeomGroup(om.Group):
    """OpenMDAO Group wrapping AerostructGeometry with design-variable inputs.

    An ``IndepVarComp`` exposes ``twist_cp`` and ``thickness_cp`` as
    group-level inputs.  ``AerostructGeometry`` computes the mesh, FEM nodes,
    stiffness matrices, tube cross-sections, and structural mass.

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

        # Design-variable inputs
        indep = om.IndepVarComp()
        if "twist_cp" in surface:
            indep.add_output("twist_cp", val=surface["twist_cp"], units="deg")
        if "thickness_cp" in surface:
            indep.add_output("thickness_cp", val=surface["thickness_cp"], units="m")
        self.add_subsystem("dv_vars", indep, promotes=["*"])

        # Geometry + structural setup
        self.add_subsystem(
            "wing", AerostructGeometry(surface=surface), promotes_inputs=["*"]
        )


class OasGeomDiscipline(OpenMdaoSubProblem):
    """Philote discipline wrapping OAS aerostructural geometry computation.

    This discipline accepts wing design variables as inputs and returns
    geometry constants (mesh, nodes, stiffness matrices, etc.) that are
    consumed by the split aero and structural disciplines.

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
        """Generate mesh, build the geometry group, and map variables."""
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

        nx = mesh.shape[0]
        ny = mesh.shape[1]

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
            for key, val in surface.items():
                if isinstance(val, list):
                    surface[key] = np.array(val)

        # Store surface for reuse by split disciplines
        self.surface = surface

        # --- build OpenMDAO group ---
        self.add_group(OasGeomGroup(surface=surface))

        # --- map inputs (design variables) ---
        if "twist_cp" in surface:
            self.add_mapped_input(
                "twist_cp",
                "twist_cp",
                shape=surface["twist_cp"].shape,
                units="deg",
            )
        if "thickness_cp" in surface:
            self.add_mapped_input(
                "thickness_cp",
                "thickness_cp",
                shape=surface["thickness_cp"].shape,
                units="m",
            )

        # --- map outputs (geometry constants) ---
        self.add_mapped_output("mesh", "wing.mesh", shape=(nx, ny, 3), units="m")
        self.add_mapped_output("nodes", "wing.nodes", shape=(ny, 3), units="m")
        self.add_mapped_output("t_over_c", "wing.t_over_c", shape=(1, ny - 1), units="")
        self.add_mapped_output(
            "local_stiff_transformed",
            "wing.local_stiff_transformed",
            shape=(ny - 1, 12, 12),
            units="",
        )
        self.add_mapped_output("radius", "wing.radius", shape=(ny - 1,), units="m")
        self.add_mapped_output(
            "thickness", "wing.thickness", shape=(1, ny - 1), units="m"
        )
        self.add_mapped_output(
            "structural_mass", "wing.structural_mass", shape=(1,), units="kg"
        )
        self.add_mapped_output("cg_location", "wing.cg_location", shape=(3,), units="m")

        logger.info(
            "OasGeomDiscipline built (inputs=%d, outputs=%d)",
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
