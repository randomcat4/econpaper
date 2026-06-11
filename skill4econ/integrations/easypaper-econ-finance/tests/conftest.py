"""Shared fixtures for the EasyPaper test suite."""
from __future__ import annotations

import pytest


@pytest.fixture
def sample_core_refs() -> list[dict[str, str]]:
    return [
        {
            "ref_id": "smith2020",
            "title": "Deep Learning for Vision",
            "abstract": "A paper about image classification with neural networks.",
            "bibtex": "@article{smith2020, title={Deep Learning for Vision}, year={2020}}",
        },
        {
            "ref_id": "jones2021",
            "title": "Robustness in Neural Networks",
            "abstract": "A paper about robustness and adversarial training.",
            "bibtex": "@article{jones2021, title={Robustness in Neural Networks}, year={2021}}",
        },
    ]
