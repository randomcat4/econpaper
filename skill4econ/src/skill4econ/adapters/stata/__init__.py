"""Stata DID adapter facades.

These modules expose stable adapter metadata and common-output parsers around
the tested wrapper methods in ``skill4econ.stata_wrappers``. They do not
silently substitute estimators.
"""

from . import bacondecomp, csdid, did_imputation, drdid, eventstudyinteract, honestdid, reghdfe

__all__ = [
    "bacondecomp",
    "csdid",
    "did_imputation",
    "drdid",
    "eventstudyinteract",
    "honestdid",
    "reghdfe",
]
