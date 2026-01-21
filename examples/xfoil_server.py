"""Example server script for the XFOIL discipline.

This script demonstrates how to run the XfoilDiscipline as a Philote server.

Before running, ensure:
1. XFOIL is installed and the XFOIL_PATH environment variable is set
2. The philote-examples package is installed

Usage:
    export XFOIL_PATH=/path/to/xfoil
    python xfoil_server.py
"""

from concurrent import futures

import grpc
import philote_mdo.general as pmdo

from philote_examples import XfoilDiscipline


def run(n_points: int = 100, port: int = 50051):
    """Start the XFOIL discipline server.

    Parameters
    ----------
    n_points : int, optional
        Number of points defining the airfoil geometry, by default 100.
    port : int, optional
        Port to listen on, by default 50051.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    discipline = pmdo.ExplicitServer(discipline=XfoilDiscipline(n_points=n_points))
    discipline.attach_to_server(server)

    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"XFOIL server started. Listening on port {port}.")
    print(f"Airfoil geometry configured for {n_points} points.")
    server.wait_for_termination()


if __name__ == "__main__":
    run()
