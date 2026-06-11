from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from .config import resolve_stata, resolve_stata_batch_args, stata_discovery_chain
from .contracts.stata_safety import StataSpecSafetyError, validate_stata_spec
from .core import (
    ROOT,
    REPO_ROOT,
    RunContext,
    Skill4EconError,
    data_path_from_spec,
    listify,
    write_audit,
    write_manifest,
    write_text,
)


VENDOR_ROOT = ROOT / "vendor_sources"


def _quote(path: Path) -> str:
    return str(path).replace("\\", "/")


def _vendor_adopath_block() -> str:
    paths = [
        VENDOR_ROOT / "stata-require" / "src",
        VENDOR_ROOT / "ftools" / "src",
        # ppmlhdfe 2.x loads reghdfe5.mata at runtime; the vendored src
        # directory carries that compatibility entrypoint while retaining
        # reghdfe 6.13.1.
        VENDOR_ROOT / "reghdfe" / "src",
        VENDOR_ROOT / "ivreghdfe" / "src",
        VENDOR_ROOT / "ppmlhdfe" / "src",
        VENDOR_ROOT / "rdrobust" / "stata",
        VENDOR_ROOT / "stpackages" / "drdid",
        VENDOR_ROOT / "stpackages" / "csdid",
        VENDOR_ROOT / "stpackages" / "f_able",
        VENDOR_ROOT / "stpackages" / "lbsvmat",
        VENDOR_ROOT / "stpackages" / "jwdid",
        VENDOR_ROOT / "did_imputation",
    ]
    return "\n".join(f'capture adopath ++ "{_quote(path)}"' for path in paths if path.exists())


def _absorb_vars(ctx: RunContext) -> list[str]:
    absorb = listify(ctx.spec.get("absorb") or ctx.spec.get("fe"))
    id_col = ctx.spec.get("id")
    time_col = ctx.spec.get("time")
    mapped = []
    for value in absorb:
        if value == "entity" and id_col:
            mapped.append(str(id_col))
        elif value == "time" and time_col:
            mapped.append(str(time_col))
        else:
            mapped.append(value)
    if not mapped and id_col and time_col:
        mapped = [str(id_col), str(time_col)]
    return mapped


def _state_plan(ctx: RunContext, requirements: list[str]) -> dict[str, Any] | None:
    if ctx.state in {"plan", "dry-run", "audit"}:
        write_audit(
            ctx,
            "planned" if ctx.state == "plan" else "validated",
            [f"{ctx.method} state={ctx.state}; Stata estimation was not executed.", *requirements],
        )
        return write_manifest(ctx, "planned" if ctx.state == "plan" else "validated")
    return None


def _resolve(ctx: RunContext):
    return resolve_stata(ctx.spec)


def _run_stata(ctx: RunContext, do_text: str, timeout: int = 180, **extra: Any) -> dict[str, Any]:
    try:
        validate_stata_spec(ctx.spec)
    except StataSpecSafetyError as exc:
        raise Skill4EconError(f"Unsafe Stata spec: {exc}") from exc
    executable, source = _resolve(ctx)
    if executable is None:
        messages = [
            "Stata executable not found via the discovery chain.",
            *[f"  - {step}" for step in stata_discovery_chain()],
            "Set SKILL4ECON_STATA or spec.stata.executable to enable Stata methods.",
        ]
        write_audit(ctx, "missing_dependency", messages)
        return write_manifest(
            ctx,
            "missing_dependency",
            stata_source=source,
            discovery_chain=stata_discovery_chain(),
        )
    do_path = ctx.artifact("run.do")
    write_text(do_path, do_text)
    stdout_path = ctx.artifact("stdout.log")
    stderr_path = ctx.artifact("stderr.log")
    batch_args = resolve_stata_batch_args(executable, ctx.spec)
    cmd = [str(executable), *batch_args, str(do_path)]
    with stdout_path.open("w", encoding="utf-8", errors="replace") as out, stderr_path.open(
        "w", encoding="utf-8", errors="replace"
    ) as err:
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(ctx.run_dir),
                stdout=out,
                stderr=err,
                timeout=timeout,
                check=False,
                text=True,
            )
            rc = int(proc.returncode)
        except subprocess.TimeoutExpired:
            rc = 124
    run_log = ctx.run_dir / f"{do_path.stem}.log"
    if rc == 0 and run_log.exists():
        log_text = run_log.read_text(encoding="utf-8", errors="replace")
        if re.search(r"\nr\(\d+\);", log_text):
            rc = 1
    status = "ok" if rc == 0 else "failed"
    write_audit(
        ctx,
        status,
        ["Stata batch completed."],
        returncode=rc,
        do_file=str(do_path),
        executable=str(executable),
        stata_source=source,
        **extra,
    )
    return write_manifest(
        ctx,
        status,
        returncode=rc,
        do_file=str(do_path),
        executable=str(executable),
        stata_source=source,
        **extra,
    )


def _import_block(ctx: RunContext) -> str:
    data = data_path_from_spec(ctx.spec)
    if data is None:
        raise Skill4EconError("Stata method requires data/input/input_path in spec.")
    if not data.exists():
        raise Skill4EconError(f"Input data not found: {data}")
    suffix = data.suffix.lower()
    if suffix == ".csv":
        return f'import delimited using "{_quote(data)}", clear varnames(1)'
    if suffix in {".xlsx", ".xlsm"}:
        return f'import excel using "{_quote(data)}", clear firstrow'
    raise Skill4EconError("Stata methods support CSV and XLSX inputs.")


def _export_estimates_block(ctx: RunContext) -> str:
    return f"""
tempname b V
matrix `b' = e(b)
matrix `V' = e(V)
local names : colnames `b'
local k = colsof(`b')
capture scalar __df_r = e(df_r)
local has_dfr = (_rc == 0)
preserve
clear
set obs `k'
gen str128 term = ""
gen double coef = .
gen double std_error = .
gen double t_stat = .
gen double p_value = .
forvalues i = 1/`k' {{
    local nm : word `i' of `names'
    replace term = "`nm'" in `i'
    replace coef = `b'[1,`i'] in `i'
    replace std_error = sqrt(`V'[`i',`i']) in `i'
    replace t_stat = coef[`i'] / std_error[`i'] in `i'
    if `has_dfr' {{
        replace p_value = 2 * ttail(__df_r, abs(t_stat[`i'])) in `i'
    }}
    else {{
        replace p_value = 2 * normal(-abs(t_stat[`i'])) in `i'
    }}
}}
export delimited using "{_quote(ctx.artifact("model_table.csv"))}", replace
restore
"""


def _export_estimates_block_to(ctx: RunContext, target_macro: str) -> str:
    return f"""
tempname b V
matrix `b' = e(b)
matrix `V' = e(V)
local names : colnames `b'
local k = colsof(`b')
capture scalar __df_r = e(df_r)
local has_dfr = (_rc == 0)
preserve
clear
set obs `k'
gen str128 term = ""
gen double coef = .
gen double std_error = .
gen double t_stat = .
gen double p_value = .
forvalues i = 1/`k' {{
    local nm : word `i' of `names'
    replace term = "`nm'" in `i'
    replace coef = `b'[1,`i'] in `i'
    replace std_error = sqrt(`V'[`i',`i']) in `i'
    replace t_stat = coef[`i'] / std_error[`i'] in `i'
    if `has_dfr' {{
        replace p_value = 2 * ttail(__df_r, abs(t_stat[`i'])) in `i'
    }}
    else {{
        replace p_value = 2 * normal(-abs(t_stat[`i'])) in `i'
    }}
}}
export delimited using `{target_macro}', replace
restore
"""


def stata_preflight(ctx: RunContext) -> dict[str, Any]:
    do_text = f"""
version 17
set more off
{_vendor_adopath_block()}
display "skill4econ Stata preflight"
display c(stata_version)
which regress
which xtreg
which ivregress
which teffects
capture which reghdfe
display "reghdfe_rc=" _rc
capture which ivreghdfe
display "ivreghdfe_rc=" _rc
capture which ppmlhdfe
display "ppmlhdfe_rc=" _rc
capture which csdid
display "csdid_rc=" _rc
capture which drdid
display "drdid_rc=" _rc
capture which rdrobust
display "rdrobust_rc=" _rc
capture which qreg
display "qreg_rc=" _rc
capture which xthreg
display "xthreg_rc=" _rc
exit
"""
    return _run_stata(ctx, do_text)


def data_audit(ctx: RunContext) -> dict[str, Any]:
    planned = _state_plan(ctx, ["Requires CSV/XLSX data."])
    if planned:
        return planned
    do_text = f"""
version 17
set more off
log using "{_quote(ctx.artifact("stata.log"))}", replace text
{_import_block(ctx)}
describe
summarize
duplicates report
log close
exit
"""
    return _run_stata(ctx, do_text)


def ols_cluster(ctx: RunContext) -> dict[str, Any]:
    planned = _state_plan(ctx, ["Requires y and x. Optional cluster."])
    if planned:
        return planned
    y = ctx.spec.get("y")
    x = " ".join(listify(ctx.spec.get("x") or ctx.spec.get("covars")))
    if not y or not x:
        raise Skill4EconError("ols_cluster requires y and x.")
    cluster = ctx.spec.get("cluster")
    vce = f", vce(cluster {cluster})" if cluster else ", vce(robust)"
    do_text = f"""
version 17
set more off
log using "{_quote(ctx.artifact("stata.log"))}", replace text
{_import_block(ctx)}
regress {y} {x}{vce}
{_export_estimates_block(ctx)}
log close
exit
"""
    return _run_stata(ctx, do_text)


def reghdfe_fe(ctx: RunContext) -> dict[str, Any]:
    planned = _state_plan(ctx, ["Requires y, x, and absorb/fe variables. Uses local reghdfe source."])
    if planned:
        return planned
    y = ctx.spec.get("y")
    x = " ".join(listify(ctx.spec.get("x") or ctx.spec.get("covars")))
    absorb = _absorb_vars(ctx)
    if not all([y, x]) or not absorb:
        raise Skill4EconError("reghdfe_fe requires y, x, and absorb/fe variables.")
    cluster = ctx.spec.get("cluster")
    vce = f" vce(cluster {cluster})" if cluster else " vce(robust)"
    do_text = f"""
version 17
set more off
{_vendor_adopath_block()}
log using "{_quote(ctx.artifact("stata.log"))}", replace text
{_import_block(ctx)}
which reghdfe
reghdfe {y} {x}, absorb({" ".join(absorb)}){vce}
{_export_estimates_block(ctx)}
log close
exit
"""
    return _run_stata(ctx, do_text, timeout=240, backend="local reghdfe")


def rdrobust_rdd(ctx: RunContext) -> dict[str, Any]:
    planned = _state_plan(ctx, ["Requires y and running. Optional cutoff, bandwidth, covariates."])
    if planned:
        return planned
    y = ctx.spec.get("y")
    running = ctx.spec.get("running")
    if not all([y, running]):
        raise Skill4EconError("rdrobust_rdd requires y and running.")
    cutoff = float(ctx.spec.get("cutoff", 0))
    bandwidth = ctx.spec.get("bandwidth")
    covs = " ".join(listify(ctx.spec.get("x") or ctx.spec.get("covars")))
    opts = [f"c({cutoff})"]
    if bandwidth is not None:
        opts.append(f"h({float(bandwidth)})")
    if covs:
        opts.append(f"covs({covs})")
    do_text = f"""
version 17
set more off
{_vendor_adopath_block()}
log using "{_quote(ctx.artifact("stata.log"))}", replace text
{_import_block(ctx)}
which rdrobust
rdrobust {y} {running}, {" ".join(opts)}
{_export_estimates_block(ctx)}
log close
exit
"""
    return _run_stata(ctx, do_text, timeout=240, backend="local rdrobust")


def quantile_regression(ctx: RunContext) -> dict[str, Any]:
    planned = _state_plan(ctx, ["Requires y and x. Optional quantile/tau."])
    if planned:
        return planned
    y = ctx.spec.get("y")
    x = " ".join(listify(ctx.spec.get("x") or ctx.spec.get("covars")))
    if not y or not x:
        raise Skill4EconError("quantile_regression requires y and x.")
    tau = float(ctx.spec.get("quantile", ctx.spec.get("tau", 0.5)))
    do_text = f"""
version 17
set more off
log using "{_quote(ctx.artifact("stata.log"))}", replace text
{_import_block(ctx)}
qreg {y} {x}, quantile({tau})
{_export_estimates_block(ctx)}
log close
exit
"""
    return _run_stata(ctx, do_text, timeout=240)


def poisson_ppml_fe(ctx: RunContext) -> dict[str, Any]:
    planned = _state_plan(ctx, ["Requires nonnegative y, x, and absorb/fe variables. Uses local ppmlhdfe source."])
    if planned:
        return planned
    y = ctx.spec.get("y")
    x = " ".join(listify(ctx.spec.get("x") or ctx.spec.get("covars")))
    absorb = _absorb_vars(ctx)
    if not all([y, x]) or not absorb:
        raise Skill4EconError("poisson_ppml_fe requires y, x, and absorb/fe variables.")
    cluster = ctx.spec.get("cluster")
    vce = f" vce(cluster {cluster})" if cluster else " vce(robust)"
    do_text = f"""
version 17
set more off
{_vendor_adopath_block()}
log using "{_quote(ctx.artifact("stata.log"))}", replace text
{_import_block(ctx)}
which ppmlhdfe
ppmlhdfe {y} {x}, absorb({" ".join(absorb)}){vce}
{_export_estimates_block(ctx)}
log close
exit
"""
    return _run_stata(
        ctx,
        do_text,
        timeout=300,
        backend="local ppmlhdfe",
        estimator_identity="ppmlhdfe PPML with high-dimensional fixed effects; no poisson fallback",
    )


def panel_fe_re(ctx: RunContext) -> dict[str, Any]:
    planned = _state_plan(ctx, ["Requires y, x, id, time."])
    if planned:
        return planned
    y = ctx.spec.get("y")
    x = " ".join(listify(ctx.spec.get("x") or ctx.spec.get("covars")))
    id_col = ctx.spec.get("id")
    time_col = ctx.spec.get("time")
    if not all([y, x, id_col, time_col]):
        raise Skill4EconError("panel_fe_re requires y, x, id, and time.")
    model = str(ctx.spec.get("model", "fe")).lower()
    if model not in {"fe", "re"}:
        raise Skill4EconError("panel_fe_re model must be 'fe' or 're'.")
    cluster = ctx.spec.get("cluster") or id_col
    do_text = f"""
version 17
set more off
log using "{_quote(ctx.artifact("stata.log"))}", replace text
{_import_block(ctx)}
xtset {id_col} {time_col}
xtreg {y} {x}, {model} vce(cluster {cluster})
{_export_estimates_block(ctx)}
log close
exit
"""
    return _run_stata(ctx, do_text, estimator=f"Stata xtreg {model}", panel_model=model)


def did_twfe_event(ctx: RunContext) -> dict[str, Any]:
    planned = _state_plan(ctx, ["Requires y, treat, post, id, time."])
    if planned:
        return planned
    y = ctx.spec.get("y")
    treat = ctx.spec.get("treat")
    post = ctx.spec.get("post")
    id_col = ctx.spec.get("id")
    time_col = ctx.spec.get("time")
    x = " ".join(listify(ctx.spec.get("x") or ctx.spec.get("covars")))
    if not all([y, treat, post, id_col, time_col]):
        raise Skill4EconError("did_twfe_event requires y, treat, post, id, and time.")
    controls = f" {x}" if x else ""
    cluster = ctx.spec.get("cluster") or id_col
    do_text = f"""
version 17
set more off
log using "{_quote(ctx.artifact("stata.log"))}", replace text
{_import_block(ctx)}
regress {y} c.{treat}#c.{post}{controls} i.{id_col} i.{time_col}, vce(cluster {cluster})
{_export_estimates_block(ctx)}
log close
exit
"""
    return _run_stata(ctx, do_text)


def did_event_study(ctx: RunContext) -> dict[str, Any]:
    planned = _state_plan(ctx, ["Requires y, id, time, and event_time or gvar/adoption_time."])
    if planned:
        return planned
    y = ctx.spec.get("y")
    id_col = ctx.spec.get("id")
    time_col = ctx.spec.get("time")
    event_time = ctx.spec.get("event_time")
    gvar = ctx.spec.get("gvar") or ctx.spec.get("adoption_time") or ctx.spec.get("treat_time")
    x = " ".join(listify(ctx.spec.get("x") or ctx.spec.get("covars")))
    if not all([y, id_col, time_col]) or not (event_time or gvar):
        raise Skill4EconError("did_event_study requires y, id, time, and event_time or gvar/adoption_time.")
    window = ctx.spec.get("window", [-3, 3])
    lo, hi = int(window[0]), int(window[1])
    base = int(ctx.spec.get("base_period", -1))
    if lo > hi:
        raise Skill4EconError("did_event_study window lower bound must be <= upper bound.")
    event_setup = []
    if event_time:
        event_setup.extend(
            [
                f"gen double _event_time = {event_time}",
                "gen byte _treated_event = !missing(_event_time)",
            ]
        )
    else:
        event_setup.extend(
            [
                f"gen double _gvar = {gvar}",
                "replace _gvar = . if _gvar <= 0",
                f"gen double _event_time = {time_col} - _gvar",
                "gen byte _treated_event = !missing(_gvar)",
            ]
        )
    event_terms = []
    for k in range(lo, hi + 1):
        if k == base:
            continue
        suffix = f"m{abs(k)}" if k < 0 else str(k)
        term = f"_event_{suffix}"
        event_terms.append(term)
        event_setup.append(f"gen byte {term} = (_event_time == {k} & _treated_event)")
    controls = f" {x}" if x else ""
    cluster = ctx.spec.get("cluster") or id_col
    do_text = f"""
version 17
set more off
log using "{_quote(ctx.artifact("stata.log"))}", replace text
{_import_block(ctx)}
{chr(10).join(event_setup)}
regress {y} {" ".join(event_terms)}{controls} i.{id_col} i.{time_col}, vce(cluster {cluster})
{_export_estimates_block(ctx)}
log close
exit
"""
    return _run_stata(
        ctx,
        do_text,
        estimator="Stata TWFE event study",
        window=[lo, hi],
        base_period=base,
    )


def csdid_staggered(ctx: RunContext) -> dict[str, Any]:
    planned = _state_plan(ctx, ["Requires y, id, time, gvar. Optional x and method. Uses local csdid/drdid source."])
    if planned:
        return planned
    y = ctx.spec.get("y")
    x = " ".join(listify(ctx.spec.get("x") or ctx.spec.get("covars")))
    id_col = ctx.spec.get("id")
    time_col = ctx.spec.get("time")
    gvar = ctx.spec.get("gvar") or ctx.spec.get("adoption_time")
    if not all([y, id_col, time_col, gvar]):
        raise Skill4EconError("csdid_staggered requires y, id, time, and gvar/adoption_time.")
    method = ctx.spec.get("method", "reg")
    cluster = ctx.spec.get("cluster")
    cluster_opt = f" cluster({cluster})" if cluster and str(cluster) != str(id_col) else ""
    do_text = f"""
version 17
set more off
{_vendor_adopath_block()}
log using "{_quote(ctx.artifact("stata.log"))}", replace text
{_import_block(ctx)}
which csdid
which drdid
csdid {y} {x}, ivar({id_col}) time({time_col}) gvar({gvar}) method({method}){cluster_opt}
{_export_estimates_block(ctx)}
log close
exit
"""
    return _run_stata(ctx, do_text, timeout=360, backend="local csdid/drdid")


def dr_did_2x2(ctx: RunContext) -> dict[str, Any]:
    planned = _state_plan(
        ctx,
        [
            "Requires y, time, treatment/treat, and optional id for panel data.",
            "Uses local Stata drdid; no TWFE fallback is attempted.",
        ],
    )
    if planned:
        return planned
    y = ctx.spec.get("y")
    x = " ".join(listify(ctx.spec.get("x") or ctx.spec.get("covars") or ctx.spec.get("controls")))
    id_col = ctx.spec.get("id")
    time_col = ctx.spec.get("time")
    treat = ctx.spec.get("treatment") or ctx.spec.get("treat")
    if not all([y, time_col, treat]):
        raise Skill4EconError("dr_did_2x2 requires y, time, and treatment/treat.")
    data_type = str(ctx.spec.get("data_type", "panel" if id_col else "repeated_cross_section")).lower()
    if data_type not in {"panel", "repeated_cross_section", "rc"}:
        raise Skill4EconError("dr_did_2x2 data_type must be panel or repeated_cross_section.")
    if data_type == "panel" and not id_col:
        raise Skill4EconError("dr_did_2x2 panel data requires id.")
    method = str(ctx.spec.get("method", "drimp")).lower()
    allowed_methods = {"drimp", "dripw", "reg", "stdipw", "ipw", "ipwra", "all"}
    if method not in allowed_methods:
        raise Skill4EconError(f"dr_did_2x2 method must be one of {sorted(allowed_methods)}.")
    id_opt = f" ivar({id_col})" if data_type == "panel" else ""
    cluster = ctx.spec.get("cluster")
    cluster_opt = ""
    if cluster and not (data_type == "panel" and str(cluster) == str(id_col)):
        cluster_opt = f" cluster({cluster})"
    wboot = bool(ctx.spec.get("wboot", False))
    wboot_opt = " wboot" if wboot else ""
    seed = ctx.spec.get("seed") or ctx.spec.get("rseed")
    seed_opt = f" rseed({int(seed)})" if seed is not None else ""
    method_opt = " all" if method == "all" else f" {method}"
    sample_if = ctx.spec.get("if") or ctx.spec.get("sample_if")
    if_text = f" if {sample_if}" if sample_if else ""
    do_text = f"""
version 17
set more off
{_vendor_adopath_block()}
log using "{_quote(ctx.artifact("stata.log"))}", replace text
{_import_block(ctx)}
which drdid
drdid {y} {x}{if_text}, time({time_col}) treatment({treat}){id_opt}{cluster_opt}{method_opt}{wboot_opt}{seed_opt}
{_export_estimates_block(ctx)}
preserve
keep if e(sample)
collapse (count) obs={y} (mean) y_mean={y}, by({treat} {time_col})
export delimited using "{_quote(ctx.artifact("group_time_summary.csv"))}", replace
restore
preserve
clear
set obs 1
gen str32 estimator = "dr_did_2x2"
gen str32 backend = "drdid"
gen str32 data_type = "{data_type}"
gen str32 requested_method = "{method}"
gen str32 e_method = "`e(method)'"
gen str32 e_semethod = "`e(semethod)'"
gen double N = .
capture replace N = e(N) in 1
gen double N_clust = .
capture replace N_clust = e(N_clust) in 1
gen str64 cluster = "{cluster or id_col or ""}"
export delimited using "{_quote(ctx.artifact("did_diagnostics.csv"))}", replace
restore
log close
exit
"""
    return _run_stata(
        ctx,
        do_text,
        timeout=360,
        backend="local drdid",
        estimator="Sant'Anna-Zhao DRDID 2x2",
        data_type=data_type,
        drdid_method=method,
    )


def cs_did_attgt(ctx: RunContext) -> dict[str, Any]:
    planned = _state_plan(
        ctx,
        [
            "Requires y, id, time, gvar/adoption_time.",
            "Uses local Stata csdid/drdid and exports ATT(g,t), simple ATT, and event aggregation.",
        ],
    )
    if planned:
        return planned
    y = ctx.spec.get("y")
    x = " ".join(listify(ctx.spec.get("x") or ctx.spec.get("covars") or ctx.spec.get("controls")))
    id_col = ctx.spec.get("id")
    time_col = ctx.spec.get("time")
    gvar = ctx.spec.get("gvar") or ctx.spec.get("adoption_time")
    if not all([y, id_col, time_col, gvar]):
        raise Skill4EconError("cs_did_attgt requires y, id, time, and gvar/adoption_time.")
    method = str(ctx.spec.get("method", ctx.spec.get("csdid_method", "dripw"))).lower()
    allowed_methods = {"drimp", "dripw", "reg", "stdipw", "ipw"}
    if method not in allowed_methods:
        raise Skill4EconError(f"cs_did_attgt method must be one of {sorted(allowed_methods)}.")
    cluster = ctx.spec.get("cluster")
    cluster_opt = f" cluster({cluster})" if cluster and str(cluster) != str(id_col) else ""
    control_group = str(ctx.spec.get("control_group", "never_treated")).lower()
    if control_group not in {"never_treated", "not_yet_treated"}:
        raise Skill4EconError("cs_did_attgt control_group must be never_treated or not_yet_treated.")
    notyet_opt = " notyet" if control_group == "not_yet_treated" else ""
    rc1_opt = " rc1" if bool(ctx.spec.get("rc1", False)) else ""
    window = ctx.spec.get("event_window") or ctx.spec.get("window") or [-5, 5]
    if not isinstance(window, list | tuple) or len(window) != 2:
        raise Skill4EconError("cs_did_attgt event_window/window must be [lo, hi].")
    lo, hi = int(window[0]), int(window[1])
    if lo > hi:
        raise Skill4EconError("cs_did_attgt event_window lower bound must be <= upper bound.")
    seed = ctx.spec.get("seed") or ctx.spec.get("rseed")
    seed_opt = f" rseed({int(seed)})" if seed is not None else ""
    wboot = bool(ctx.spec.get("wboot", False))
    wboot_opt = " wboot" if wboot else ""
    do_text = f"""
version 17
set more off
{_vendor_adopath_block()}
log using "{_quote(ctx.artifact("stata.log"))}", replace text
{_import_block(ctx)}
which csdid
which drdid
tempfile __attgt_out __simple_out __event_out __combined
csdid {y} {x}, ivar({id_col}) time({time_col}) gvar({gvar}) method({method}){cluster_opt}{notyet_opt}{rc1_opt}{wboot_opt}{seed_opt}
estimates store __csdid_base
{_export_estimates_block_to(ctx, "__attgt_out")}
preserve
import delimited using `__attgt_out', clear varnames(1)
gen str32 estimator = "att_gt"
export delimited using "{_quote(ctx.artifact("att_gt.csv"))}", replace
save `__combined', replace
restore
estimates restore __csdid_base
estat simple, post
{_export_estimates_block_to(ctx, "__simple_out")}
preserve
import delimited using `__simple_out', clear varnames(1)
gen str32 estimator = "simple_att"
export delimited using "{_quote(ctx.artifact("simple_att.csv"))}", replace
append using `__combined'
save `__combined', replace
restore
estimates restore __csdid_base
estat event, window({lo} {hi}) post
{_export_estimates_block_to(ctx, "__event_out")}
preserve
import delimited using `__event_out', clear varnames(1)
gen str32 estimator = "event"
export delimited using "{_quote(ctx.artifact("event_study.csv"))}", replace
append using `__combined'
order estimator term coef std_error t_stat p_value
export delimited using "{_quote(ctx.artifact("model_table.csv"))}", replace
restore
preserve
clear
set obs 1
gen str32 estimator = "cs_did_attgt"
gen str32 backend = "csdid"
gen str32 csdid_method = "{method}"
gen str32 control_group = "{control_group}"
gen str32 event_window = "{lo} {hi}"
gen double N = .
capture replace N = e(N) in 1
gen double N_clust = .
capture replace N_clust = e(N_clust) in 1
gen str64 cluster = "{cluster or id_col}"
export delimited using "{_quote(ctx.artifact("did_diagnostics.csv"))}", replace
restore
log close
exit
"""
    return _run_stata(
        ctx,
        do_text,
        timeout=480,
        backend="local csdid/drdid",
        estimator="Callaway-Sant'Anna ATT(g,t)",
        csdid_method=method,
        control_group=control_group,
        event_window=[lo, hi],
    )


def did_imputation_event(ctx: RunContext) -> dict[str, Any]:
    planned = _state_plan(
        ctx,
        [
            "Requires y, id, time, gvar/adoption_time.",
            "Uses local Stata did_imputation plus reghdfe; no substitute estimator is attempted.",
        ],
    )
    if planned:
        return planned
    y = ctx.spec.get("y")
    id_col = ctx.spec.get("id")
    time_col = ctx.spec.get("time")
    gvar = ctx.spec.get("gvar") or ctx.spec.get("adoption_time")
    if not all([y, id_col, time_col, gvar]):
        raise Skill4EconError("did_imputation_event requires y, id, time, and gvar/adoption_time.")
    controls = " ".join(listify(ctx.spec.get("x") or ctx.spec.get("covars") or ctx.spec.get("controls")))
    fe = " ".join(listify(ctx.spec.get("fe"))) or f"{id_col} {time_col}"
    cluster = ctx.spec.get("cluster") or id_col
    horizons = ctx.spec.get("horizons", None)
    allhorizons = bool(ctx.spec.get("allhorizons", False))
    if horizons is not None and allhorizons:
        raise Skill4EconError("did_imputation_event cannot combine horizons and allhorizons.")
    if isinstance(horizons, list | tuple):
        horizons_text = " ".join(str(int(v)) for v in horizons)
        horizons_opt = f" horizons({horizons_text})"
    elif horizons is not None:
        horizons_opt = f" horizons({horizons})"
    else:
        horizons_opt = " allhorizons" if allhorizons else " horizons(0/3)"
    pretrends = int(ctx.spec.get("pretrends", ctx.spec.get("pretrend", 0)))
    pretrend_opt = f" pretrends({pretrends})" if pretrends > 0 else ""
    autosample_opt = " autosample" if bool(ctx.spec.get("autosample", False)) else ""
    saveweights_opt = " saveweights" if bool(ctx.spec.get("saveweights", ctx.spec.get("save_weights", False))) else ""
    leaveout_opt = " leaveout" if bool(ctx.spec.get("leaveout", False)) else ""
    hbalance_opt = " hbalance" if bool(ctx.spec.get("hbalance", False)) else ""
    minn = ctx.spec.get("minn")
    minn_opt = f" minn({int(minn)})" if minn is not None else ""
    controls_opt = f" controls({controls})" if controls else ""
    seed = ctx.spec.get("seed")
    seed_line = f"set seed {int(seed)}" if seed is not None else ""
    do_text = f"""
version 17
set more off
{_vendor_adopath_block()}
log using "{_quote(ctx.artifact("stata.log"))}", replace text
{_import_block(ctx)}
{seed_line}
which reghdfe
which did_imputation
gen double _s4e_ei = {gvar}
replace _s4e_ei = . if _s4e_ei <= 0
did_imputation {y} {id_col} {time_col} _s4e_ei, fe({fe}){controls_opt}{horizons_opt}{pretrend_opt} cluster({cluster}){autosample_opt}{saveweights_opt}{leaveout_opt}{hbalance_opt}{minn_opt} saveestimates(_s4e_tauhat)
tempfile __model_out __model_dta
{_export_estimates_block_to(ctx, "__model_out")}
preserve
import delimited using `__model_out', clear varnames(1)
gen str32 estimator = "did_imputation_event"
order estimator term coef std_error t_stat p_value
export delimited using "{_quote(ctx.artifact("model_table.csv"))}", replace
save `__model_dta', replace
keep if substr(term, 1, 3) == "tau"
gen event_time = real(substr(term, 4, .))
order event_time estimator term coef std_error t_stat p_value
export delimited using "{_quote(ctx.artifact("event_study.csv"))}", replace
use `__model_dta', clear
keep if substr(term, 1, 3) == "pre"
gen lead = real(substr(term, 4, .))
order lead estimator term coef std_error t_stat p_value
export delimited using "{_quote(ctx.artifact("pretrend_coefficients.csv"))}", replace
restore
preserve
clear
set obs 1
gen str32 estimator = "did_imputation_event"
gen str32 backend = "did_imputation"
gen str64 cluster = "{cluster}"
gen str128 fe = "{fe}"
gen str128 horizons = "{horizons_opt.strip()}"
gen double pre_F = .
capture replace pre_F = e(pre_F) in 1
gen double pre_p = .
capture replace pre_p = e(pre_p) in 1
gen double pre_df = .
capture replace pre_df = e(pre_df) in 1
gen str244 autosample_drop = "`e(autosample_drop)'"
gen str244 autosample_trim = "`e(autosample_trim)'"
export delimited using "{_quote(ctx.artifact("pretrend_test.csv"))}", replace
restore
preserve
keep {id_col} {time_col} {gvar} _s4e_ei _s4e_tauhat
export delimited using "{_quote(ctx.artifact("individual_effects.csv"))}", replace
restore
local weightvars ""
capture ds __w*
if !_rc local weightvars `r(varlist)'
if "`weightvars'" != "" {{
    preserve
    keep {id_col} {time_col} {gvar} _s4e_ei `weightvars'
    export delimited using "{_quote(ctx.artifact("weights.csv"))}", replace
    restore
}}
log close
exit
"""
    return _run_stata(
        ctx,
        do_text,
        timeout=480,
        backend="local did_imputation/reghdfe",
        estimator="Borusyak-Jaravel-Spiess imputation DID",
        horizons=horizons if horizons is not None else ("all" if allhorizons else "0/3"),
        pretrends=pretrends,
    )


def iv_2sls(ctx: RunContext) -> dict[str, Any]:
    planned = _state_plan(ctx, ["Requires y, x, endog, instrument."])
    if planned:
        return planned
    y = ctx.spec.get("y")
    x = " ".join(listify(ctx.spec.get("x") or ctx.spec.get("covars")))
    endog = ctx.spec.get("endog")
    instr = ctx.spec.get("instrument")
    if not all([y, endog, instr]):
        raise Skill4EconError("iv_2sls requires y, endog, and instrument.")
    cluster = ctx.spec.get("cluster")
    vce = f", vce(cluster {cluster})" if cluster else ", vce(robust)"
    do_text = f"""
version 17
set more off
log using "{_quote(ctx.artifact("stata.log"))}", replace text
{_import_block(ctx)}
ivregress 2sls {y} {x} ({endog} = {instr}){vce}
{_export_estimates_block(ctx)}
log close
exit
"""
    return _run_stata(ctx, do_text)


def teffects_psm_ipw(ctx: RunContext) -> dict[str, Any]:
    planned = _state_plan(ctx, ["Requires y, treat, x. Runs both teffects psmatch and teffects ipw."])
    if planned:
        return planned
    y = ctx.spec.get("y")
    treat = ctx.spec.get("treat")
    x = " ".join(listify(ctx.spec.get("x") or ctx.spec.get("covars")))
    if not all([y, treat, x]):
        raise Skill4EconError("teffects_psm_ipw requires y, treat, and x.")
    do_text = f"""
version 17
set more off
log using "{_quote(ctx.artifact("stata.log"))}", replace text
{_import_block(ctx)}
teffects psmatch ({y}) ({treat} {x})
estimates store __psmatch
teffects ipw ({y}) ({treat} {x})
estimates store __ipw

tempfile __psmatch_out __ipw_out
estimates restore __psmatch
{_export_estimates_block_to(ctx, "__psmatch_out")}
estimates restore __ipw
{_export_estimates_block_to(ctx, "__ipw_out")}
preserve
import delimited using `__psmatch_out', clear varnames(1)
gen str32 estimator = "teffects_psmatch"
tempfile __combined
save `__combined', replace
import delimited using `__ipw_out', clear varnames(1)
gen str32 estimator = "teffects_ipw"
append using `__combined'
order estimator term coef std_error t_stat p_value
export delimited using "{_quote(ctx.artifact("model_table.csv"))}", replace
restore
log close
exit
"""
    return _run_stata(ctx, do_text, estimator="Stata teffects psmatch + ipw")


def dynamic_panel_gmm(ctx: RunContext) -> dict[str, Any]:
    planned = _state_plan(ctx, ["Requires y, x, id, time. Uses built-in xtabond."])
    if planned:
        return planned
    y = ctx.spec.get("y")
    x = " ".join(listify(ctx.spec.get("x") or ctx.spec.get("covars")))
    id_col = ctx.spec.get("id")
    time_col = ctx.spec.get("time")
    if not all([y, x, id_col, time_col]):
        raise Skill4EconError("dynamic_panel_gmm requires y, x, id, and time.")
    do_text = f"""
version 17
set more off
log using "{_quote(ctx.artifact("stata.log"))}", replace text
{_import_block(ctx)}
xtset {id_col} {time_col}
xtabond {y} {x}, lags(1)
{_export_estimates_block(ctx)}
log close
exit
"""
    return _run_stata(ctx, do_text, timeout=240)


def spatial_panel_preflight(ctx: RunContext) -> dict[str, Any]:
    planned = _state_plan(ctx, ["Preflight only; full spatial estimation is P1."])
    if planned:
        return planned
    do_text = """
version 17
set more off
log using "stata.log", replace text
capture which spxtregress
display "spxtregress_rc=" _rc
capture which xsmle
display "xsmle_rc=" _rc
capture which spmat
display "spmat_rc=" _rc
log close
exit
"""
    return _run_stata(ctx, do_text)


def export_log_manifest(ctx: RunContext) -> dict[str, Any]:
    write_audit(ctx, "ok", ["No estimation requested; manifest export only."])
    return write_manifest(ctx, "ok")


STATA_METHODS = {
    "stata_preflight": stata_preflight,
    "data_audit": data_audit,
    "ols_cluster": ols_cluster,
    "reghdfe_fe": reghdfe_fe,
    "rdrobust_rdd": rdrobust_rdd,
    "quantile_regression": quantile_regression,
    "poisson_ppml_fe": poisson_ppml_fe,
    "panel_fe_re": panel_fe_re,
    "did_twfe_event": did_twfe_event,
    "did_event_study": did_event_study,
    "csdid_staggered": csdid_staggered,
    "dr_did_2x2": dr_did_2x2,
    "cs_did_attgt": cs_did_attgt,
    "did_imputation_event": did_imputation_event,
    "iv_2sls": iv_2sls,
    "teffects_psm_ipw": teffects_psm_ipw,
    "dynamic_panel_gmm": dynamic_panel_gmm,
    "spatial_panel_preflight": spatial_panel_preflight,
    "export_log_manifest": export_log_manifest,
}
