"""Low-level XFOIL file I/O and subprocess wrapper."""

import subprocess
from pathlib import Path

import numpy as np


def write_airfoil_file(coords_x: np.ndarray, coords_y: np.ndarray, filepath: Path) -> None:
    """Write airfoil coordinates to a file in XFOIL format.

    Parameters
    ----------
    coords_x : np.ndarray
        X-coordinates of the airfoil points.
    coords_y : np.ndarray
        Y-coordinates of the airfoil points.
    filepath : Path
        Output file path.
    """
    with open(filepath, "w") as f:
        f.write("Airfoil\n")
        for x, y in zip(coords_x, coords_y):
            f.write(f" {x: .6f}  {y: .6f}\n")


def write_command_file(
    filepath: Path,
    airfoil_file: Path,
    output_file: Path,
    alpha: float,
    reynolds: float = 0.0,
    mach: float = 0.0,
    n_iter: int = 100,
    viscous: bool = True,
) -> None:
    """Generate XFOIL batch command script for a single operating point.

    Parameters
    ----------
    filepath : Path
        Output command file path.
    airfoil_file : Path
        Path to the airfoil coordinate file.
    output_file : Path
        Path where results will be written.
    alpha : float
        Angle of attack in degrees.
    reynolds : float, optional
        Reynolds number, by default 0.0. Unused when viscous is False.
    mach : float, optional
        Mach number, by default 0.0.
    n_iter : int, optional
        Maximum iterations for viscous solution, by default 100.
    viscous : bool, optional
        Whether to run viscous analysis, by default True.
    """
    commands = [
        "PLOP",  # Enter plotting options
        "G",  # Toggle graphics off
        "",  # Exit PLOP menu
        f"LOAD {airfoil_file}",
        "",  # Accept default name
        "OPER",
    ]

    if viscous:
        commands.append(f"VISC {reynolds:.0f}")
        commands.append(f"MACH {mach:.4f}")
        commands.append(f"ITER {n_iter}")

    dump_file = output_file.parent / "dump.dat" # same dir as output
    
    commands.extend([
        "PACC",
        str(output_file),
        str(dump_file),
        f"ALFA {alpha:.4f}",
        "",
        "QUIT",
        "",
    ])

    with open(filepath, "w") as f:
        f.write("\n".join(commands))


def run_xfoil(xfoil_path: str, command_file: Path, timeout: float = 30.0) -> subprocess.CompletedProcess:
    """Execute XFOIL via subprocess.

    Parameters
    ----------
    xfoil_path : str
        Path to the XFOIL executable.
    command_file : Path
        Path to the command file.
    timeout : float, optional
        Timeout in seconds, by default 30.0.

    Returns
    -------
    subprocess.CompletedProcess
        The completed process result.

    Raises
    ------
    subprocess.TimeoutExpired
        If XFOIL does not complete within the timeout.
    subprocess.CalledProcessError
        If XFOIL returns a non-zero exit code.
    """
    with open(command_file, "r") as f:
        result = subprocess.run(
            [xfoil_path],
            stdin=f,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            text=True,
        )

    return result


def parse_output_file(filepath: Path) -> dict:
    """Parse XFOIL polar output file for a single operating point.

    Parameters
    ----------
    filepath : Path
        Path to the output file.

    Returns
    -------
    dict
        Dictionary containing parsed values with keys:
        - alpha: angle of attack (deg)
        - cl: lift coefficient
        - cd: drag coefficient
        - cdp: pressure drag coefficient
        - cm: moment coefficient
        - top_xtr: top transition location
        - bot_xtr: bottom transition location

    Raises
    ------
    ValueError
        If the output file cannot be parsed or contains no data.
    """
    with open(filepath, "r") as f:
        lines = f.readlines()

    # Find the data line (skip headers)
    data_line = None
    for line in lines:
        line = line.strip()
        if not line or line.startswith("-") or line.startswith("alpha"):
            continue
        parts = line.split()
        if len(parts) >= 7:
            try:
                [float(p) for p in parts[:7]]
                data_line = line
                break
            except ValueError:
                continue

    if data_line is None:
        raise ValueError(f"No valid data found in output file: {filepath}")

    parts = data_line.split()
    return {
        "alpha": float(parts[0]),
        "cl": float(parts[1]),
        "cd": float(parts[2]),
        "cdp": float(parts[3]),
        "cm": float(parts[4]),
        "top_xtr": float(parts[5]),
        "bot_xtr": float(parts[6]),
    }
