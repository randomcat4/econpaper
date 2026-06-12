"""R DID adapter facades.

R adapters are interface-first until local R/R packages pass smoke tests. They
emit explicit ``skipped_backend_unavailable`` records instead of fake results.
"""

from . import did_att_gt, didimputation, drdid, fixest, honestdid

R_METHODS = {
    "fixest_twfe": fixest.execute,
}

__all__ = ["R_METHODS", "did_att_gt", "didimputation", "drdid", "fixest", "honestdid"]
