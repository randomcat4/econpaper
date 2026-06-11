from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VenueProfile:
    venue_id: str
    template_name: str
    citation_package: str
    abstract_word_target: int
    appendix_name: str
    star_policy: str
    table_note_style: str

    def to_dict(self) -> dict[str, object]:
        return {
            "venue_id": self.venue_id,
            "template_name": self.template_name,
            "citation_package": self.citation_package,
            "abstract_word_target": self.abstract_word_target,
            "appendix_name": self.appendix_name,
            "star_policy": self.star_policy,
            "table_note_style": self.table_note_style,
            "scope": "formatting_and_templates_only",
        }


VENUE_PROFILES = {
    "aea": VenueProfile(
        venue_id="aea",
        template_name="generic_aea_style",
        citation_package="natbib",
        abstract_word_target=100,
        appendix_name="Online Appendix",
        star_policy="conventional",
        table_note_style="economics",
    ),
    "jf-jfe": VenueProfile(
        venue_id="jf-jfe",
        template_name="generic_finance_style",
        citation_package="natbib",
        abstract_word_target=150,
        appendix_name="Internet Appendix",
        star_policy="conventional",
        table_note_style="finance",
    ),
    "generic-field-journal": VenueProfile(
        venue_id="generic-field-journal",
        template_name="generic_field_journal",
        citation_package="natbib",
        abstract_word_target=150,
        appendix_name="Appendix",
        star_policy="conventional",
        table_note_style="generic",
    ),
}


def resolve_venue(venue: str | None) -> VenueProfile:
    venue_id = (venue or "generic-field-journal").strip().lower()
    if venue_id not in VENUE_PROFILES:
        return VENUE_PROFILES["generic-field-journal"]
    return VENUE_PROFILES[venue_id]
