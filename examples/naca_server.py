"""Example server script for the NACA 4-digit airfoil discipline.

This script demonstrates how to run the NacaDiscipline as a Philote server.

Usage:
    python naca_server.py
"""

from concurrent import futures

import grpc
import philote_mdo.general as pmdo

from philote_examples import NacaDiscipline


def run(n_points: int = 100, port: int = 50052):
    """Start the NACA airfoil discipline server.

    Parameters
    ----------
    n_points : int, optional
        Number of points in the output airfoil contour, by default 100.
    port : int, optional
        Port to listen on, by default 50052.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    discipline = pmdo.ExplicitServer(
        discipline=NacaDiscipline(n_points=n_points)
    )
    discipline.attach_to_server(server)

    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"NACA server started. Listening on port {port}.")
    print(f"Airfoil contour configured for {n_points} points.")
    server.wait_for_termination()


if __name__ == "__main__":
    run()
