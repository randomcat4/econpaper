from __future__ import annotations

from typing import Any

import pandas as pd

from ...core import RunContext, Skill4EconError, read_table, require_columns, write_audit, write_manifest, write_model_table
from .base import parse_r_json_result, render_r_plan, run_r_json, skipped


ADAPTER = {
    "name": "fixest_twfe",
    "backend": "r_fixest",
    "r_package": "fixest",
    "role": "twfe_fallback",
    "supports": ["feols_twfe", "fepois_later", "conley_vcov_later"],
}


def render(spec: dict[str, Any]) -> dict[str, Any]:
    plan = render_r_plan(adapter=ADAPTER, spec=spec)
    plan["r_calls"] = ["fixest::feols()", "fixest::fepois()"]
    return plan


def skipped_backend_unavailable(design_type: str, message: str) -> dict[str, Any]:
    return skipped(ADAPTER, design_type=design_type, message=message)


def parse_result_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("model_table")
    if not isinstance(rows, list):
        raise Skill4EconError("fixest R result JSON lacks model_table rows.")
    parsed: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise Skill4EconError("fixest R model_table rows must be objects.")
        parsed.append(
            {
                "term": str(row.get("term") or ""),
                "coef": float(row.get("coef")),
                "std_error": float(row.get("std_error")),
                "p_value": float(row.get("p_value")),
                "t_stat": float(row.get("t_stat")) if row.get("t_stat") is not None else float("nan"),
                "backend": "R fixest::feols",
            }
        )
    if not parsed:
        raise Skill4EconError("fixest R result JSON model_table is empty.")
    return parsed


def execute(ctx: RunContext) -> dict[str, Any]:
    df, _ = read_table(ctx.spec)
    y = str(ctx.spec.get("y"))
    id_col = str(ctx.spec.get("id"))
    time_col = str(ctx.spec.get("time"))
    treat = str(ctx.spec.get("treat") or ctx.spec.get("treatment"))
    post = str(ctx.spec.get("post"))
    cluster = str(ctx.spec.get("cluster", id_col))
    if not y or not id_col or not time_col or not treat or not post:
        raise Skill4EconError("fixest_twfe requires y, id, time, treat, and post.")
    require_columns(df, [y, id_col, time_col, treat, post, cluster], "R fixest TWFE")
    data_path = ctx.artifact("r_input.csv")
    df[[y, id_col, time_col, treat, post, cluster]].dropna().to_csv(data_path, index=False)
    script_body = """
if (!requireNamespace("fixest", quietly=TRUE)) {
  stop("R package fixest is required")
}
data <- utils::read.csv(spec$data_for_r, stringsAsFactors=FALSE)
data$`_did_treat_post` <- as.numeric(data[[spec$treat]]) * as.numeric(data[[spec$post]])
formula_text <- paste0(spec$y, " ~ `_did_treat_post` | ", spec$id, " + ", spec$time)
model <- fixest::feols(stats::as.formula(formula_text), data=data, cluster=stats::as.formula(paste0("~", spec$cluster)))
ct <- as.data.frame(fixest::coeftable(model))
ct$term <- rownames(ct)
names(ct) <- gsub("Std. Error", "std_error", names(ct), fixed=TRUE)
names(ct) <- gsub("Estimate", "coef", names(ct), fixed=TRUE)
names(ct) <- gsub("Pr(>|t|)", "p_value", names(ct), fixed=TRUE)
names(ct) <- gsub("t value", "t_stat", names(ct), fixed=TRUE)
model_table <- ct[, c("term", "coef", "std_error", "p_value", "t_stat")]
jsonlite::write_json(list(status="ok", model_table=model_table, estimator="fixest::feols"), result_path, auto_unbox=TRUE, dataframe="rows", null="null")
"""
    ctx.spec["data_for_r"] = str(data_path).replace("\\", "/")
    payload = run_r_json(ctx=ctx, adapter=ADAPTER, script_body=script_body, timeout=int(ctx.spec.get("timeout", 300)))
    if payload.get("status") == "interface_only_until_r_smoke":
        write_audit(ctx, "interface_only", [str(payload.get("reason"))], backend=ADAPTER["backend"])
        return write_manifest(ctx, "interface_only", backend=ADAPTER["backend"], package=ADAPTER["r_package"])
    if payload.get("status") != "ok":
        write_audit(ctx, "failed", [str(payload.get("error") or "R fixest adapter failed.")], backend=ADAPTER["backend"])
        return write_manifest(ctx, "failed", backend=ADAPTER["backend"], warnings=[{"severity": "red", "code": payload.get("risk_code", "BACKEND_ERROR"), "message": str(payload.get("error")), "action": "Inspect r_stdout.log/r_stderr.log and fix the R adapter output."}])
    try:
        rows = parse_result_payload(payload)
    except Exception as exc:
        write_audit(ctx, "failed", [str(exc)], backend=ADAPTER["backend"])
        return write_manifest(ctx, "failed", backend=ADAPTER["backend"], warnings=[{"severity": "red", "code": "BACKEND_PARSE_FAILED", "message": str(exc), "action": "Fix the R JSON parser fixture before using this adapter."}])
    write_model_table(ctx, rows)
    pd.DataFrame(rows).to_csv(ctx.artifact("r_model_table_parsed.csv"), index=False, encoding="utf-8-sig")
    write_audit(ctx, "ok", ["R fixest TWFE completed."], estimator="fixest::feols")
    return write_manifest(
        ctx,
        "ok",
        estimator="fixest::feols",
        backend=ADAPTER["backend"],
        nobs=int(len(df)),
        claim_level="exploratory_only",
        paper_readiness="not_for_claim",
        main_claim_available=False,
    )


def parse_result_file(path) -> list[dict[str, Any]]:
    return parse_result_payload(parse_r_json_result(path))
