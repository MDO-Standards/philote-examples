"""Split aerodynamic discipline for OAS aerostructural analysis.

This module provides two classes:

* ``OasSplitAeroGroup`` -- an OpenMDAO Group that performs the aerodynamic
  side of the aerostructural coupling loop: displacement transfer, VLM
  geometry, VLM solve, load transfer, and aerodynamic functionals.
* ``OasSplitAeroDiscipline`` -- a Philote ``OpenMdaoSubProblem`` that exposes
  the group as a standalone gRPC discipline.

In a split aerostructural analysis the coupling variables are:

* **Input from structures**: ``disp`` (ny, 6) -- structural displacements
* **Output to structures**: ``loads`` (ny, 6) -- aerodynamic loads
"""

import logging

import numpy as np
import openmdao.api as om
from openaerostruct.aerodynamics.functionals import VLMFunctionals
from openaerostruct.aerodynamics.geometry import VLMGeometry
from openaerostruct.aerodynamics.states import VLMStates
from openaerostruct.geometry.utils import generate_mesh
from openaerostruct.transfer.displacement_transfer_group import (
    DisplacementTransferGroup,
)
from openaerostruct.transfer.load_transfer import LoadTransfer
from philote_mdo.openmdao import OpenMdaoSubProblem

logger = logging.getLogger(__name__)


class OasSplitAeroGroup(om.Group):
    """OpenMDAO Group for the aerodynamic side of a split aerostructural analysis.

    Replicates the aero portion of the ``CoupledAS`` loop: takes structural
    displacements and produces aerodynamic loads, plus CL and CD.

    Parameters (via ``options``)
    ----------------------------
    surface : dict
        OAS surface dictionary.
    """

    def initialize(self):
        self.options.declare("surface", types=dict)

    def setup(self):
        surface = self.options["surface"]
        name = surface["name"]
        ny = surface["mesh"].shape[1]

        # Flow-condition inputs
        indep = om.IndepVarComp()
        indep.add_output("v", val=1.0, units="m/s")
        indep.add_output("alpha", val=0.0, units="deg")
        indep.add_output("beta", val=0.0, units="deg")
        indep.add_output("Mach_number", val=0.0)
        indep.add_output("re", val=1.0, units="1/m")
        indep.add_output("rho", val=1.0, units="kg/m**3")
        self.add_subsystem("flow_vars", indep, promotes=["*"])

        # Displacement transfer: disp + nodes + mesh → def_mesh
        self.add_subsystem(
            "disp_xfer",
            DisplacementTransferGroup(surface=surface),
            promotes_inputs=["nodes", "mesh", "disp"],
            promotes_outputs=["def_mesh"],
        )
        # Resolve ambiguous default for 'disp' inside DisplacementTransferGroup
        self.disp_xfer.set_input_defaults("disp", val=np.zeros((ny, 6)))

        # VLM geometry: def_mesh → normals, widths, lengths, etc.
        self.add_subsystem(
            "aero_geom",
            VLMGeometry(surface=surface),
            promotes_inputs=["def_mesh"],
            promotes_outputs=[
                "b_pts",
                "widths",
                "lengths_spanwise",
                "lengths",
                "chords",
                "normals",
                "S_ref",
            ],
        )

        # VLM states: def_mesh + normals + flow conditions → sec_forces
        self.add_subsystem(
            "aero_states",
            VLMStates(surfaces=[surface]),
            promotes_inputs=["v", "alpha", "beta", "rho"],
        )
        self.connect("def_mesh", f"aero_states.{name}_def_mesh")
        self.connect("normals", f"aero_states.{name}_normals")

        # Load transfer: def_mesh + sec_forces → loads
        self.add_subsystem(
            "load_xfer",
            LoadTransfer(surface=surface),
            promotes_outputs=["loads"],
        )
        self.connect("def_mesh", "load_xfer.def_mesh")
        self.connect(f"aero_states.{name}_sec_forces", "load_xfer.sec_forces")

        # VLM functionals: geometric quantities + sec_forces + flow → CL, CD
        self.add_subsystem(
            "aero_funcs",
            VLMFunctionals(surface=surface),
            promotes_inputs=[
                "v",
                "alpha",
                "beta",
                "Mach_number",
                "re",
                "rho",
                "widths",
                "lengths_spanwise",
                "lengths",
                "S_ref",
                "t_over_c",
            ],
            promotes_outputs=["CL", "CD"],
        )
        self.connect(f"aero_states.{name}_sec_forces", "aero_funcs.sec_forces")


class OasSplitAeroDiscipline(OpenMdaoSubProblem):
    """Philote discipline for the aerodynamic side of a split aerostructural analysis.

    Accepts structural displacements (``disp``), geometry constants, and
    flight conditions as inputs.  Returns aerodynamic loads (``loads``) for
    the structural discipline and aerodynamic coefficients ``CL`` / ``CD``.

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
        """Generate mesh, build the aero group, and map variables."""
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
            "Mesh generated (type=%s, nx=%d, ny=%d)",
            self._mesh_dict.get("wing_type", "unknown"),
            nx,
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
        self.add_group(OasSplitAeroGroup(surface=surface))

        # --- map inputs ---
        # Flow conditions
        self.add_mapped_input("v", "v", shape=(1,), units="m/s")
        self.add_mapped_input("alpha", "alpha", shape=(1,), units="deg")
        self.add_mapped_input("Mach_number", "Mach_number", shape=(1,), units="")
        self.add_mapped_input("re", "re", shape=(1,), units="1/m")
        self.add_mapped_input("rho", "rho", shape=(1,), units="kg/m**3")

        # Geometry constants (from geometry discipline)
        self.add_mapped_input("mesh", "mesh", shape=(nx, ny, 3), units="m")
        self.add_mapped_input("nodes", "nodes", shape=(ny, 3), units="m")
        self.add_mapped_input("t_over_c", "t_over_c", shape=(1, ny - 1), units="")

        # Coupling input (from structural discipline)
        self.add_mapped_input("disp", "disp", shape=(ny, 6), units="")

        # --- map outputs ---
        # Coupling output (to structural discipline)
        self.add_mapped_output("loads", "loads", shape=(ny, 6), units="")

        # Aerodynamic performance
        self.add_mapped_output("CL", "CL", shape=(1,), units="")
        self.add_mapped_output("CD", "CD", shape=(1,), units="")

        logger.info(
            "OasSplitAeroDiscipline built (inputs=%d, outputs=%d)",
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
