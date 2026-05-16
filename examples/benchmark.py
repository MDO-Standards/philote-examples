"""Benchmark: native OAS/OpenMDAO vs Philote for all example configurations.

Runs each analysis both directly in OpenMDAO and through Philote gRPC,
then prints a comparison table showing wall-clock times and overhead.

Usage:
    python -m examples.benchmark
"""

import time

import numpy as np
import openmdao.api as om
from openaerostruct.geometry.utils import generate_mesh
from openaerostruct.utils.constants import grav_constant

from philote_examples.oas.oas_aerostruct_discipline import OasAerostructGroup
from philote_examples.oas.oas_discipline import OasAeroGroup

# ── Mesh configurations ────────────────────────────────────────────────

SMALL_VLM_MESH = {
    "num_y": 7,
    "num_x": 2,
    "wing_type": "rect",
    "symmetry": True,
    "span": 10.0,
    "root_chord": 1.0,
}

SMALL_AEROSTRUCT_MESH = {
    "num_y": 5,
    "num_x": 2,
    "wing_type": "CRM",
    "symmetry": True,
    "num_twist_cp": 5,
}

LARGE_MESH = {
    "num_y": 21,
    "num_x": 7,
    "wing_type": "CRM",
    "symmetry": True,
    "num_twist_cp": 5,
}

# ── Flow conditions ────────────────────────────────────────────────────

FLOW = {
    "v": 248.136,
    "alpha": 5.0,
    "mach_number": 0.84,
    "re": 1e6,
    "rho": 0.38,
}


# ── Surface builders ───────────────────────────────────────────────────


def _build_vlm_surface(mesh_dict, viscous=False, cd0=0.0):
    result = generate_mesh(mesh_dict)
    mesh = result[0] if isinstance(result, tuple) else result
    return {
        "name": "wing",
        "symmetry": mesh_dict.get("symmetry", True),
        "S_ref_type": "wetted",
        "fem_model_type": "tube",
        "mesh": mesh,
        "CL0": 0.0,
        "CD0": cd0,
        "k_lam": 0.05,
        "t_over_c_cp": np.array([0.15]),
        "c_max_t": 0.303,
        "with_viscous": viscous,
        "with_wave": False,
    }


def _build_aerostruct_surface(mesh_dict):
    result = generate_mesh(mesh_dict)
    if isinstance(result, tuple):
        mesh, twist_cp = result
    else:
        mesh = result
        twist_cp = None
    surface = {
        "name": "wing",
        "symmetry": mesh_dict.get("symmetry", True),
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
    return surface


# ── Native OpenMDAO runs ───────────────────────────────────────────────


def native_vlm(surface):
    """Run VLM analysis directly in OpenMDAO."""
    prob = om.Problem(model=OasAeroGroup(surface=surface))
    prob.setup()
    prob.set_val("v", FLOW["v"])
    prob.set_val("alpha", FLOW["alpha"])
    prob.set_val("Mach_number", FLOW["mach_number"])
    prob.set_val("re", FLOW["re"])
    prob.set_val("rho", FLOW["rho"])
    prob.set_val("cg", np.zeros(3))
    prob.run_model()
    return prob.get_val("aero_point_0.wing_perf.CL")[0]


def native_aerostruct(surface):
    """Run aerostructural analysis directly in OpenMDAO."""
    prob = om.Problem(model=OasAerostructGroup(surface=surface))
    prob.setup()
    prob.set_val("v", FLOW["v"])
    prob.set_val("alpha", FLOW["alpha"])
    prob.set_val("Mach_number", FLOW["mach_number"])
    prob.set_val("re", FLOW["re"])
    prob.set_val("rho", FLOW["rho"])
    prob.set_val("CT", grav_constant * 17.0e-6)
    prob.set_val("R", 11.165e6)
    prob.set_val("W0", 0.4 * 3e5)
    prob.set_val("speed_of_sound", 295.4)
    prob.set_val("load_factor", 1.0)
    prob.set_val("empty_cg", np.zeros(3))
    prob.run_model()
    return prob.get_val("AS_point_0.wing_perf.CL")[0]


# ── Philote runs ───────────────────────────────────────────────────────


def philote_vlm_small():
    from examples.oas_vlm import run_analysis as mod

    mod.PORT = 50801
    mod.run()


def philote_vlm_large():
    from examples.oas_vlm_large import run_analysis as mod

    mod.PORT = 50802
    mod.run()


def philote_aerostruct_small():
    from examples.oas_aerostruct import run_analysis as mod

    mod.PORT = 50803
    mod.run()


def philote_aerostruct_large():
    from examples.oas_aerostruct_large import run_analysis as mod

    mod.PORT = 50804
    mod.run()


def philote_split_small():
    from examples.oas_aerostruct_split import run_analysis as mod

    mod.GEOM_PORT = 50805
    mod.AERO_PORT = 50806
    mod.STRUCT_PORT = 50807
    mod.run()


def philote_split_large():
    from examples.oas_aerostruct_split_large import run_analysis as mod

    mod.GEOM_PORT = 50808
    mod.AERO_PORT = 50809
    mod.STRUCT_PORT = 50810
    mod.run()


# ── Runner ─────────────────────────────────────────────────────────────


def _time(fn, *args):
    t0 = time.perf_counter()
    fn(*args)
    return time.perf_counter() - t0


def main():
    # Build surfaces
    vlm_small_surf = _build_vlm_surface(SMALL_VLM_MESH)
    vlm_large_surf = _build_vlm_surface(LARGE_MESH, viscous=True, cd0=0.015)
    as_small_surf = _build_aerostruct_surface(SMALL_AEROSTRUCT_MESH)
    as_large_surf = _build_aerostruct_surface(LARGE_MESH)

    cases = [
        ("VLM small", lambda: native_vlm(vlm_small_surf), philote_vlm_small),
        ("VLM large", lambda: native_vlm(vlm_large_surf), philote_vlm_large),
        (
            "Aerostruct small",
            lambda: native_aerostruct(as_small_surf),
            philote_aerostruct_small,
        ),
        (
            "Aerostruct large",
            lambda: native_aerostruct(as_large_surf),
            philote_aerostruct_large,
        ),
        ("Split small", lambda: native_aerostruct(as_small_surf), philote_split_small),
        ("Split large", lambda: native_aerostruct(as_large_surf), philote_split_large),
    ]

    # Warmup: run each case once to eliminate cold-start / import caching
    print("Warming up...")
    for _, native_fn, philote_fn in cases:
        native_fn()
        philote_fn()

    # Timed runs
    print("Running timed benchmarks...\n")
    results = []
    for label, native_fn, philote_fn in cases:
        t_native = _time(native_fn)
        t_philote = _time(philote_fn)
        overhead = (t_philote - t_native) / t_native * 100
        results.append((label, t_native, t_philote, overhead))

    # Print table
    print("\n")
    print("| Case | Native (s) | Philote (s) | Overhead |")
    print("|---|---|---|---|")
    for label, t_n, t_p, ovh in results:
        print(f"| {label} | {t_n:.3f} | {t_p:.3f} | {ovh:.0f}% |")
    print()


if __name__ == "__main__":
    main()
