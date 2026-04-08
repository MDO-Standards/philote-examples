"""Philote Examples - Example disciplines for Philote MDO."""

import logging

from philote_examples.naca import NacaDiscipline
from philote_examples.oas import OasDiscipline
from philote_examples.xfoil import XfoilDiscipline

# Library-level NullHandler: no output unless the user configures logging.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = ["NacaDiscipline", "OasDiscipline", "XfoilDiscipline"]
