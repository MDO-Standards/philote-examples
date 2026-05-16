"""OpenAeroStruct VLM aerodynamic discipline wrapped as a Philote sub-problem.

This module provides two classes:

* ``OasAeroGroup`` -- an OpenMDAO Group that wires together the OAS Geometry
  and AeroPoint components for a single lifting surface.
* ``OasDiscipline`` -- a Philote ``OpenMdaoSubProblem`` that exposes the group
  as a standalone gRPC discipline with flight-condition inputs and aerodynamic
  coefficient outputs.
"""

import logging

import numpy as np
import openmdao.api as om
from openaerostruct.aerodynamics.aero_groups import AeroPoint
from openaerostruct.geometry.geometry_group import Geometry
from openaerostruct.geometry.utils import generate_mesh
from philote_mdo.openmdao import OpenMdaoSubProblem

logger = logging.getLogger(__name__)


class OasAeroGroup(om.Group):
    """OpenMDAO Group containing OAS Geometry + AeroPoint for one surface.

    An ``IndepVarComp`` exposes six flow-condition variables (``v``,
    ``alpha``, ``Mach_number``, ``re``, ``rho``, ``cg``) at the group level.
    Explicit connections route them to AeroPoint and wire the mesh and
    thickness-to-chord ratio from Geometry.

    Parameters (via ``options``)
    ----------------------------
    surface : dict
        OAS surface dictionary (must include ``"name"``, ``"mesh"``, etc.).
    """

    def initialize(self):
        self.options.declare("surface", types=dict)

    def setup(self):
        surface = self.options["surface"]
        surfaces = [surface]
        name = surface["name"]

        # Flow-condition inputs promoted to the group level
        indep = om.IndepVarComp()
        indep.add_output("v", val=1.0, units="m/s")
        indep.add_output("alpha", val=0.0, units="deg")
        indep.add_output("Mach_number", val=0.0)
        indep.add_output("re", val=1.0, units="1/m")
        indep.add_output("rho", val=1.0, units="kg/m**3")
        indep.add_output("cg", val=np.zeros(3), units="m")
        self.add_subsystem("flow_vars", indep, promotes=["*"])

        # Geometry: applies twist / chord / shear design variables to the mesh
        self.add_subsystem(name, Geometry(surface=surface))

        # AeroPoint: VLM solver for a single flight condition
        self.add_subsystem("aero_point_0", AeroPoint(surfaces=surfaces))

        # Connect flow conditions to the aero point
        for var in ("v", "alpha", "Mach_number", "re", "rho", "cg"):
            self.connect(var, f"aero_point_0.{var}")

        # Connect deformed mesh from Geometry to AeroPoint
        self.connect(f"{name}.mesh", f"aero_point_0.{name}.def_mesh")
        self.connect(f"{name}.mesh", f"aero_point_0.aero_states.{name}_def_mesh")

        # Connect thickness-to-chord ratio to the wing performance component
        self.connect(f"{name}.t_over_c", f"aero_point_0.{name}_perf.t_over_c")


class OasDiscipline(OpenMdaoSubProblem):
    """Philote discipline wrapping an OAS VLM aerodynamic analysis.

    This discipline accepts flight conditions as inputs and returns
    aerodynamic coefficients.  The wing geometry (mesh and surface
    properties) is fixed at construction time.

    Parameters
    ----------
    mesh_dict : dict, optional
        Dictionary passed to ``openaerostruct.geometry.utils.generate_mesh``.
        Defaults to a rectangular wing with 10 m span, 1 m chord, and 7
        spanwise panels.
    surface_options : dict, optional
        Extra entries merged into the OAS surface dictionary, allowing
        callers to override defaults such as ``with_viscous`` or ``CD0``.
    """

    def __init__(self, mesh_dict=None, surface_options=None):
        self._mesh_dict = mesh_dict
        self._surface_options = surface_options
        super().__init__()

    def initialize(self):
        self.add_option("mesh_dict", "dict")
        self.add_option("surface", "dict")

    def _build_discipline(self):
        """Generate mesh, build the OAS group, and map variables."""
        # --- mesh generation ---
        if self._mesh_dict is None:
            self._mesh_dict = {
                "num_y": 7,
                "num_x": 2,
                "wing_type": "rect",
                "symmetry": True,
                "span": 10.0,
                "root_chord": 1.0,
            }

        result = generate_mesh(self._mesh_dict)

        # generate_mesh returns (mesh, twist_cp) for CRM, bare mesh for rect
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
            "CD0": 0.0,
            "k_lam": 0.05,
            "t_over_c_cp": np.array([0.15]),
            "c_max_t": 0.303,
            "with_viscous": False,
            "with_wave": False,
        }

        if twist_cp is not None:
            surface["twist_cp"] = twist_cp

        if self._surface_options is not None:
            surface.update(self._surface_options)
            # Protobuf Struct serializes arrays as lists; convert back
            for key, val in surface.items():
                if isinstance(val, list):
                    surface[key] = np.array(val)

        # --- build OpenMDAO group ---
        self.add_group(OasAeroGroup(surface=surface))

        # --- map inputs (flight conditions) ---
        self.add_mapped_input("v", "v", shape=(1,), units="m/s")
        self.add_mapped_input("alpha", "alpha", shape=(1,), units="deg")
        self.add_mapped_input("Mach_number", "Mach_number", shape=(1,), units="")
        self.add_mapped_input("re", "re", shape=(1,), units="1/m")
        self.add_mapped_input("rho", "rho", shape=(1,), units="kg/m**3")
        self.add_mapped_input("cg", "cg", shape=(3,), units="m")

        # --- map outputs (aerodynamic coefficients) ---
        self.add_mapped_output("CL", "aero_point_0.wing_perf.CL", shape=(1,), units="")
        self.add_mapped_output("CD", "aero_point_0.wing_perf.CD", shape=(1,), units="")
        self.add_mapped_output("CM", "aero_point_0.CM", shape=(3,), units="")

        logger.info(
            "OasDiscipline built (surface=%s, inputs=%d, outputs=%d)",
            surface["name"],
            len(self._input_map),
            len(self._output_map),
        )
        logger.debug("Mapped inputs: %s", list(self._input_map.keys()))
        logger.debug("Mapped outputs: %s", list(self._output_map.keys()))

    def set_options(self, options):
        if "mesh_dict" in options:
            self._mesh_dict = dict(options["mesh_dict"])
        if "surface" in options:
            self._surface_options = dict(options["surface"])

    def setup(self):
        self._build_discipline()
        super().setup()
