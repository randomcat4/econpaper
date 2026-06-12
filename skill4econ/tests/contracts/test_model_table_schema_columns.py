from __future__ import annotations

from skill4econ.validation.schema_loader import load_schema


def test_model_table_schema_documents_t_inference_columns() -> None:
    schema = load_schema("model_table.schema.json")
    properties = schema["$defs"]["model_table_row"]["properties"]

    assert {"ci_low", "ci_high", "df_inference"}.issubset(properties)
    assert properties["ci_low"]["type"] == ["number", "null"]
    assert properties["ci_high"]["type"] == ["number", "null"]
    assert properties["df_inference"]["type"] == ["number", "null"]
