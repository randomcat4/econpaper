"""R DID adapter facades.

R adapters are interface-first until local R/R packages pass smoke tests. They
emit explicit ``skipped_backend_unavailable`` records instead of fake results.
"""

from . import did_att_gt, didimputation, drdid, fixest, honestdid

__all__ = ["did_att_gt", "didimputation", "drdid", "fixest", "honestdid"]
