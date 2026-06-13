"""Three-tier literature search support (L1 prescription, L2 open APIs, L3 deep search).

The only legitimate downstream output of every tier is structured notes
(`external_literature_notes.json` + normalized `refs.bib`); citation safety
hard rules in econpaper_roadmap_v3/03_citation_safety_not_search.md are unchanged.
"""

SEARCH_TIERS_VERSION = "v1.0"
