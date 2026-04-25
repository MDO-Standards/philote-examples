"""Split OAS aerostructural analysis using three Philote discipline servers.

Demonstrates decomposing an aerostructural analysis into three independent
Philote disciplines (geometry, aerodynamics, structures) and coupling them
on the client side using OpenMDAO's ``NonlinearBlockGS`` solver.

The geometry discipline runs once to produce constants (mesh, nodes,
stiffness matrices, etc.).  The aero and structural disciplines iterate
inside a coupled group until the MDA converges.

Usage:
    python run_analysis.py
"""

from concurrent import futures

import grpc
import numpy as np
import openmdao.api as om
import philote_mdo.general as pmdo
from openaerostruct.geometry.utils import generate_mesh
from philote_mdo.openmdao import RemoteExplicitComponent

from philote_examples import (
    OasGeomDiscipline,
    OasSplitAeroDiscipline,
    OasSplitStructDiscipline,
)

# Default mesh configuration (must match the discipline defaults)
DEFAULT_MESH_DICT = {
    "num_y": 5,
    "num_x": 2,
    "wing_type": "CRM",
    "symmetry": True,
    "num_twist_cp": 5,
}

GEOM_PORT = 50051
AERO_PORT = 50052
STRUCT_PORT = 50053


def _start_server(discipline, port):
    """Start a Philote server in a background thread."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    wrapped = pmdo.ExplicitServer(discipline=discipline)
    wrapped.attach_to_server(server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    return server


def run(
    v=248.136,
    alpha=5.0,
    mach_number=0.84,
    re=1e6,
    rho=0.38,
    start_servers=True,
):
    """Run a split OAS aerostructural analysis.

    Parameters
    ----------
    v : float
        Freestream velocity in m/s.
    alpha : float
        Angle of attack in degrees.
    mach_number : float
        Freestream Mach number.
    re : float
        Reynolds number per unit length in 1/m.
    rho : float
        Air density in kg/m**3.
    start_servers : bool
        If True, start all three gRPC servers in-process.
    """
    servers = []
    if start_servers:
        servers.append(_start_server(OasGeomDiscipline(), GEOM_PORT))
        servers.append(_start_server(OasSplitAeroDiscipline(), AERO_PORT))
        servers.append(_start_server(OasSplitStructDiscipline(), STRUCT_PORT))

    geom_channel = grpc.insecure_channel(f"localhost:{GEOM_PORT}")
    aero_channel = grpc.insecure_channel(f"localhost:{AERO_PORT}")
    struct_channel = grpc.insecure_channel(f"localhost:{STRUCT_PORT}")

    try:
        prob = om.Problem()
        model = prob.model

        # Flow-condition inputs
        indep = om.IndepVarComp()
        indep.add_output("v", val=v, units="m/s")
        indep.add_output("alpha", val=alpha, units="deg")
        indep.add_output("Mach_number", val=mach_number)
        indep.add_output("re", val=re, units="1/m")
        indep.add_output("rho", val=rho, units="kg/m**3")
        model.add_subsystem("prob_vars", indep, promotes=["*"])

        # Geometry discipline (runs once before coupling)
        model.add_subsystem("wing", RemoteExplicitComponent(channel=geom_channel))

        # Coupled group with MDA solver
        coupled = om.Group()
        coupled.add_subsystem("aero", RemoteExplicitComponent(channel=aero_channel))
        coupled.add_subsystem("struct", RemoteExplicitComponent(channel=struct_channel))

        # Coupling connections
        coupled.connect("aero.loads", "struct.loads")
        coupled.connect("struct.disp", "aero.disp")

        # Gauss-Seidel solver for aero-structural coupling
        coupled.nonlinear_solver = om.NonlinearBlockGS(use_aitken=True)
        coupled.nonlinear_solver.options["maxiter"] = 100
        coupled.nonlinear_solver.options["atol"] = 1e-7
        coupled.nonlinear_solver.options["rtol"] = 1e-30
        coupled.nonlinear_solver.options["iprint"] = 2
        coupled.nonlinear_solver.options["err_on_non_converge"] = True

        model.add_subsystem("coupled", coupled)

        # Connect geometry outputs to the aero discipline
        model.connect("wing.mesh", "coupled.aero.mesh")
        model.connect("wing.nodes", "coupled.aero.nodes")
        model.connect("wing.t_over_c", "coupled.aero.t_over_c")

        # Connect geometry outputs to the structural discipline
        model.connect("wing.nodes", "coupled.struct.nodes")
        model.connect(
            "wing.local_stiff_transformed",
            "coupled.struct.local_stiff_transformed",
        )
        model.connect("wing.radius", "coupled.struct.radius")
        model.connect("wing.thickness", "coupled.struct.thickness")

        # Connect flow conditions to the aero discipline
        for var in ("v", "alpha", "Mach_number", "re", "rho"):
            model.connect(var, f"coupled.aero.{var}")

        prob.setup()

        # Set geometry design variable defaults.  RemoteExplicitComponent
        # initialises all inputs to 1.0; we must provide the correct baseline
        # values so that the geometry discipline produces the right mesh.
        result = generate_mesh(DEFAULT_MESH_DICT)
        if isinstance(result, tuple):
            _, twist_cp = result
        else:
            twist_cp = None
        if twist_cp is not None:
            prob.set_val("wing.twist_cp", twist_cp)
        prob.set_val("wing.thickness_cp", np.array([0.1, 0.2, 0.3]))

        # Initialise coupling variables to zero (undeformed / no loads)
        ny = DEFAULT_MESH_DICT["num_y"]
        if DEFAULT_MESH_DICT.get("symmetry", False):
            ny = (ny + 1) // 2
        prob.set_val("coupled.aero.disp", np.zeros((ny, 6)))
        prob.set_val("coupled.struct.loads", np.zeros((ny, 6)))

        prob.run_model()

        cl = prob.get_val("coupled.aero.CL")[0]
        cd = prob.get_val("coupled.aero.CD")[0]
        failure = prob.get_val("coupled.struct.failure")[0]

        print(
            f"Split OAS aerostructural analysis: v={v} m/s, alpha={alpha} deg, "
            f"M={mach_number}, Re={re:.0e}/m, rho={rho} kg/m^3"
        )
        print(f"  CL      = {cl:.4f}")
        print(f"  CD      = {cd:.6f}")
        print(f"  Failure = {failure:.4f}")

        return cl, cd, failure

    finally:
        geom_channel.close()
        aero_channel.close()
        struct_channel.close()
        for s in servers:
            s.stop(grace=1)


if __name__ == "__main__":
    run()
