"""Vendored DEA / Super-SBM / Malmquist backend.

Originally sourced from D:\\myproject\\dea_calculator (user-owned). Refactored
into a function-call API so the EvoScientist agent can run efficiency
calculations in-process without rewriting source files or shelling out.

Public surface:

    compute_indices(data, dmus, periods, nx, ny, nb, undesirable, sup) -> dict
    write_excel(result, path)
"""

from .engine import DEAResult, compute_indices, write_excel

__all__ = ["DEAResult", "compute_indices", "write_excel"]
