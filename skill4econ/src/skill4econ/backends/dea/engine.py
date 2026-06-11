"""Driver for the vendored DEA/SBM/Malmquist backend.

This module replaces the original script-style driver (module-level globals
plus ``pd.read_excel('t1.xlsx')`` plus ``pd.ExcelWriter('allindex.xlsx')``)
with a single function ``compute_indices`` that takes the data and parameters
as arguments and returns a dict of DataFrames. A separate ``write_excel``
helper persists the result in the same multi-sheet layout as the upstream
``allindex.xlsx``.

The math kernels in ``solver.py`` are unchanged, so results are byte-for-byte
comparable to the original script for the same inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .solver import (
    Ec_g,
    Ecv_t1t,
    Ecv_tt,
    Ecv_tt1,
    SupEc_g,
    SupEcv_t1t,
    SupEcv_tt,
    SupEcv_tt1,
)


@dataclass
class DEAResult:
    """Container for SBM efficiencies and Malmquist decompositions."""

    sbm_efficiencies: pd.DataFrame
    fglr1992_c: pd.DataFrame
    fglr1992_v: pd.DataFrame
    fglr1994: pd.DataFrame
    rd1997: pd.DataFrame
    zofio2007: pd.DataFrame
    pl2005_c: pd.DataFrame
    pl2005_v: pd.DataFrame
    meta: dict[str, Any] = field(default_factory=dict)

    def as_sheet_dict(self) -> dict[str, pd.DataFrame]:
        return {
            "sbmeffs": self.sbm_efficiencies,
            "FGLR1992_C": self.fglr1992_c,
            "FGLR1992_V": self.fglr1992_v,
            "FGLR1994": self.fglr1994,
            "RD1997": self.rd1997,
            "Zofio2007": self.zofio2007,
            "PL2005_C": self.pl2005_c,
            "PL2005_v": self.pl2005_v,
        }


def _normalize_input_array(data: Any) -> np.ndarray:
    if isinstance(data, pd.DataFrame):
        if data.index.name is not None or not isinstance(data.index, pd.RangeIndex):
            data = data.reset_index()
        return data.values
    return np.asarray(data)


def compute_indices(
    data: Any,
    *,
    dmus: int,
    periods: int,
    nx: int,
    ny: int,
    nb: int,
    undesirable: int,
    sup: int,
    progress: bool = False,
) -> DEAResult:
    """Run SBM efficiency + Malmquist decomposition on a stacked panel array.

    Expected layout (matching the original script convention):

        data shape  : (dmus * periods, 2 + nx + ny + nb_or_0)
        column 0    : DMU name
        column 1    : period label
        columns 2.. : nx input cols, ny desirable-output cols, then nb
                      undesirable-output cols if ``undesirable == 1``.

    Parameters mirror the upstream globals (``dmus``, ``periods``, ``nx``,
    ``ny``, ``nb``, ``undesirable``, ``sup``). ``progress=True`` enables a
    ``tqdm`` progress bar if the package is importable; otherwise the bars
    are silently skipped.
    """
    data = _normalize_input_array(data)
    if data.shape[0] != dmus * periods:
        raise ValueError(
            f"data rows {data.shape[0]} != dmus*periods {dmus * periods}"
        )

    bar = _progress_factory(progress)

    ec_tt: list[tuple] = []
    ev_tt: list[tuple] = []
    ec_tt1: list[tuple] = []
    ev_tt1: list[tuple] = []
    ec_t1t: list[tuple] = []
    ev_t1t: list[tuple] = []
    ec_gt: list[tuple] = []
    ev_gt: list[tuple] = []

    for t in bar(range(periods), desc="standard_efficiency_params"):
        data_t = data[dmus * t:dmus * (t + 1), :]
        data_t1 = data[dmus * (t + 1):dmus * (t + 2), :] if t != periods - 1 else None
        dmuname = data_t[:, 0]
        year = data_t[0, 1]
        x_t = data_t[:, 2:nx + 2].T
        x_g = data[:, 2:nx + 2].T
        yg_t = data_t[:, nx + 2:nx + ny + 2].T
        yg_g = data[:, nx + 2:nx + ny + 2].T
        x_t1 = data_t1[:, 2:nx + 2].T if data_t1 is not None else None
        yg_t1 = data_t1[:, nx + 2:nx + ny + 2].T if data_t1 is not None else None

        if undesirable == 1:
            yb_t = data_t[:, nx + ny + 2:nx + ny + nb + 2].T
            yb_g = data[:, nx + ny + 2:nx + ny + nb + 2].T
            yb_t1 = data_t1[:, nx + ny + 2:nx + ny + nb + 2].T if data_t1 is not None else None
        else:
            yb_t = yb_g = yb_t1 = np.ndarray(0)

        for i in range(dmus):
            if undesirable == 1:
                res = Ecv_tt(cur=i, x_t=x_t, yg_t=yg_t, yb_t=yb_t)
                ec_tt.append((dmuname[i], year, res[0].fun))
                ev_tt.append((dmuname[i], year, res[1].fun))

                res = Ec_g(cur_g=i + t * dmus, x_t=x_t, yg_t=yg_t, x_g=x_g,
                           yg_g=yg_g, yb_t=yb_t, yb_g=yb_g)
                ec_gt.append((dmuname[i], year, res[0].fun))
                ev_gt.append((dmuname[i], year, res[1].fun))

                if t == periods - 1:
                    continue

                res = Ecv_tt1(cur=i, x_t=x_t, x_t1=x_t1, yg_t=yg_t,
                              yg_t1=yg_t1, yb_t=yb_t, yb_t1=yb_t1)
                ec_tt1.append((dmuname[i], year, res[0].fun))
                ev_tt1.append((dmuname[i], year, res[1].fun))

                res = Ecv_t1t(cur=i, x_t=x_t, x_t1=x_t1, yg_t=yg_t,
                              yg_t1=yg_t1, yb_t=yb_t, yb_t1=yb_t1)
                ec_t1t.append((dmuname[i], year, res[0].fun))
                ev_t1t.append((dmuname[i], year, res[1].fun))
            else:
                res = Ecv_tt(cur=i, x_t=x_t, yg_t=yg_t)
                ec_tt.append((dmuname[i], year, res[0].fun))
                ev_tt.append((dmuname[i], year, res[1].fun))

                res = Ec_g(cur_g=i + t * dmus, x_t=x_t, yg_t=yg_t, x_g=x_g, yg_g=yg_g)
                ec_gt.append((dmuname[i], year, res[0].fun))
                ev_gt.append((dmuname[i], year, res[1].fun))

                if t == periods - 1:
                    continue

                res = Ecv_tt1(cur=i, x_t=x_t, x_t1=x_t1, yg_t=yg_t, yg_t1=yg_t1)
                ec_tt1.append((dmuname[i], year, res[0].fun))
                ev_tt1.append((dmuname[i], year, res[1].fun))

                res = Ecv_t1t(cur=i, x_t=x_t, x_t1=x_t1, yg_t=yg_t, yg_t1=yg_t1)
                ec_t1t.append((dmuname[i], year, res[0].fun))
                ev_t1t.append((dmuname[i], year, res[1].fun))

    for t in bar(range(periods), desc="super_efficiency_params"):
        data_t = data[dmus * t:dmus * (t + 1), :]
        data_t1 = data[dmus * (t + 1):dmus * (t + 2), :] if t != periods - 1 else None
        dmuname = data_t[:, 0]
        year = data_t[0, 1]
        x_t = data_t[:, 2:nx + 2].T
        x_g = data[:, 2:nx + 2].T
        yg_t = data_t[:, nx + 2:nx + ny + 2].T
        yg_g = data[:, nx + 2:nx + ny + 2].T
        x_t1 = data_t1[:, 2:nx + 2].T if data_t1 is not None else None
        yg_t1 = data_t1[:, nx + 2:nx + ny + 2].T if data_t1 is not None else None

        if undesirable == 1:
            yb_t = data_t[:, nx + ny + 2:nx + ny + nb + 2].T
            yb_g = data[:, nx + ny + 2:nx + ny + nb + 2].T
            yb_t1 = data_t1[:, nx + ny + 2:nx + ny + nb + 2].T if data_t1 is not None else None
        else:
            yb_t = yb_g = yb_t1 = np.ndarray(0)

        for i in range(dmus):
            if undesirable == 1:
                res = SupEcv_tt(cur=i, x_t=x_t, yg_t=yg_t, yb_t=yb_t)
                _patch_super(ec_tt, ev_tt, i + t * dmus, dmuname[i], year, res, sup)

                res = SupEc_g(cur_g=i + t * dmus, x_t=x_t, yg_t=yg_t,
                              x_g=x_g, yg_g=yg_g, yb_t=yb_t, yb_g=yb_g)
                _patch_super_no_fallback(ec_gt, ev_gt, i + t * dmus, dmuname[i], year, res, sup)

                if t == periods - 1:
                    continue

                res = SupEcv_tt1(cur=i, x_t=x_t, x_t1=x_t1, yg_t=yg_t,
                                 yg_t1=yg_t1, yb_t=yb_t, yb_t1=yb_t1)
                _patch_super(ec_tt1, ev_tt1, i + t * dmus, dmuname[i], year, res, sup)

                res = SupEcv_t1t(cur=i, x_t=x_t, x_t1=x_t1, yg_t=yg_t,
                                 yg_t1=yg_t1, yb_t=yb_t, yb_t1=yb_t1)
                _patch_super(ec_t1t, ev_t1t, i + t * dmus, dmuname[i], year, res, sup)
            else:
                res = SupEcv_tt(cur=i, x_t=x_t, yg_t=yg_t)
                _patch_super(ec_tt, ev_tt, i + t * dmus, dmuname[i], year, res, sup)

                res = SupEc_g(cur_g=i + t * dmus, x_t=x_t,
                              yg_t=yg_t, x_g=x_g, yg_g=yg_g)
                _patch_super(ec_gt, ev_gt, i + t * dmus, dmuname[i], year, res, sup)

                if t == periods - 1:
                    continue

                res = SupEcv_tt1(cur=i, x_t=x_t, x_t1=x_t1, yg_t=yg_t, yg_t1=yg_t1)
                _patch_super(ec_tt1, ev_tt1, i + t * dmus, dmuname[i], year, res, sup)

                res = SupEcv_t1t(cur=i, x_t=x_t, x_t1=x_t1, yg_t=yg_t, yg_t1=yg_t1)
                _patch_super(ec_t1t, ev_t1t, i + t * dmus, dmuname[i], year, res, sup)

    all_index: list[tuple] = []
    for i in range(dmus):
        all_index.append((ec_tt[i][0], ec_tt[i][1], ec_tt[i][2], ev_tt[i][2],
                          "-", "-", "-", "-", ec_gt[i][2], ev_gt[i][2]))
    for i in range(dmus * (periods - 1)):
        all_index.append((
            ec_tt[i + dmus][0], ec_tt[i + dmus][1], ec_tt[i + dmus][2],
            ev_tt[i + dmus][2], ec_tt1[i][2], ev_tt1[i][2],
            ec_t1t[i][2], ev_t1t[i][2], ec_gt[i + dmus][2], ev_gt[i + dmus][2],
        ))

    ecc: list = []
    ecv: list = []
    tcc: list = []
    pec: list = []
    ptc: list = []
    sec: list = []
    sch: list = []
    stc: list = []
    bpcc: list = []
    bpcv: list = []
    mlc: list = []
    mlv: list = []
    mgc: list = []
    mgv: list = []
    fglr1992_c: list = []
    fglr1992_v: list = []
    fglr1994: list = []
    rd1997: list = []
    zofio2007: list = []
    pl2005_c: list = []
    pl2005_v: list = []

    for i in range(dmus * (periods - 1)):
        ecc.append(_safe_ratio(all_index[i + dmus][2], all_index[i][2]))
        tcc.append(_safe_geomean(
            (all_index[i + dmus][4], all_index[i + dmus][2]),
            (all_index[i][2], all_index[i + dmus][6]),
        ))
        mlc.append(_safe_product(ecc[i], tcc[i]))
        fglr1992_c.append((
            all_index[i][0],
            f"{all_index[i][1]}-{all_index[i + dmus][1]}",
            mlc[i], ecc[i], tcc[i],
        ))

        pec.append(_safe_ratio(all_index[i + dmus][3], all_index[i][3]))
        ptc.append(_safe_geomean(
            (all_index[i + dmus][5], all_index[i + dmus][3]),
            (all_index[i][3], all_index[i + dmus][7]),
        ))
        mlv.append(_safe_product(pec[i], ptc[i]))
        fglr1992_v.append((
            all_index[i][0],
            f"{all_index[i][1]}-{all_index[i + dmus][1]}",
            mlv[i], pec[i], ptc[i],
        ))

        sec.append(_safe_scale_efficiency(
            all_index[i + dmus][2], all_index[i + dmus][3],
            all_index[i][2], all_index[i][3],
        ))
        fglr1994.append((
            all_index[i][0],
            f"{all_index[i][1]}-{all_index[i + dmus][1]}",
            mlc[i], pec[i], sec[i], tcc[i],
        ))

        sch.append(_safe_rd_scale_change(all_index, i, dmus))
        rd1997.append((
            all_index[i][0],
            f"{all_index[i][1]}-{all_index[i + dmus][1]}",
            mlc[i], pec[i], sch[i], ptc[i],
        ))

        stc.append(_safe_zofio_scale_tc(all_index, i, dmus))
        zofio2007.append((
            all_index[i][0],
            f"{all_index[i][1]}-{all_index[i + dmus][1]}",
            mlc[i], pec[i], sec[i], ptc[i], stc[i],
        ))

        bpcc.append(_safe_bpc(all_index[i + dmus][8], all_index[i + dmus][2],
                              all_index[i][8], all_index[i][2]))
        mgc.append(_safe_product(ecc[i], bpcc[i]))
        pl2005_c.append((
            all_index[i][0],
            f"{all_index[i][1]}-{all_index[i + dmus][1]}",
            mgc[i], ecc[i], bpcc[i],
        ))

        bpcv.append(_safe_bpc(all_index[i + dmus][9], all_index[i + dmus][3],
                              all_index[i][9], all_index[i][3]))
        ecv.append(_safe_ratio(all_index[i + dmus][3], all_index[i][3]))
        mgv.append(_safe_product(ecv[i], bpcv[i]))
        pl2005_v.append((
            all_index[i][0],
            f"{all_index[i][1]}-{all_index[i + dmus][1]}",
            mgv[i], ecv[i], bpcv[i],
        ))

    sbm_df = pd.DataFrame(all_index, columns=(
        "dmu", "period", "ectt_crs_current", "evtt_vrs_current",
        "ectt1_crs_t_to_t1", "evtt1_vrs_t_to_t1",
        "ect1t_crs_t1_to_t", "evt1t_vrs_t1_to_t",
        "ecgt_crs_global", "evgt_vrs_global",
    ))
    fglr1992_c_df = pd.DataFrame(fglr1992_c, columns=(
        "dmu", "period_pair", "mlc_malmquist", "ecc_efficiency_change",
        "tcc_technical_change",
    ))
    fglr1992_v_df = pd.DataFrame(fglr1992_v, columns=(
        "dmu", "period_pair", "mlv_malmquist", "pec_pure_efficiency_change",
        "ptc_pure_technical_change",
    ))
    fglr1994_df = pd.DataFrame(fglr1994, columns=(
        "dmu", "period_pair", "mlc_malmquist", "pec_pure_efficiency_change",
        "sec_scale_efficiency_change", "tcc_technical_change",
    ))
    rd1997_df = pd.DataFrame(rd1997, columns=(
        "dmu", "period_pair", "mlc_malmquist", "pec_pure_efficiency_change",
        "sch_scale_change", "ptc_pure_technical_change",
    ))
    zofio2007_df = pd.DataFrame(zofio2007, columns=(
        "dmu", "period_pair", "mlc_malmquist", "pec_pure_efficiency_change",
        "sec_scale_efficiency_change", "ptc_pure_technical_change",
        "stc_scale_technical_change",
    ))
    pl2005_c_df = pd.DataFrame(pl2005_c, columns=(
        "dmu", "period_pair", "mgc_global_malmquist",
        "ecc_efficiency_change", "bpcc_best_practice_gap_change",
    ))
    pl2005_v_df = pd.DataFrame(pl2005_v, columns=(
        "dmu", "period_pair", "mgv_global_malmquist",
        "ecv_efficiency_change", "bpcv_best_practice_gap_change",
    ))

    return DEAResult(
        sbm_efficiencies=sbm_df,
        fglr1992_c=fglr1992_c_df,
        fglr1992_v=fglr1992_v_df,
        fglr1994=fglr1994_df,
        rd1997=rd1997_df,
        zofio2007=zofio2007_df,
        pl2005_c=pl2005_c_df,
        pl2005_v=pl2005_v_df,
        meta={
            "dmus": dmus,
            "periods": periods,
            "nx": nx,
            "ny": ny,
            "nb": nb,
            "undesirable": undesirable,
            "sup": sup,
        },
    )


def write_excel(result: DEAResult, path: str | Path) -> Path:
    """Persist a DEAResult to a multi-sheet .xlsx mirroring the original layout."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sheets = result.as_sheet_dict()
    with pd.ExcelWriter(path) as writer:
        sheets["sbmeffs"].to_excel(writer, sheet_name="sbmeffs", index=False)
        for name, df in sheets.items():
            if name == "sbmeffs":
                continue
            df.to_excel(writer, sheet_name=name)
    return path


def _progress_factory(enabled: bool):
    if not enabled:
        return lambda it, desc="": it
    try:
        from tqdm import tqdm
    except Exception:
        return lambda it, desc="": it
    return lambda it, desc="": tqdm(it, desc=desc)


def _patch_super(eff_crs: list, eff_vrs: list, idx: int, name, year,
                 res, sup: int) -> None:
    if eff_crs[idx][2] is None:
        eff_crs[idx] = (name, year, res[0].fun)
    if eff_vrs[idx][2] is None:
        eff_vrs[idx] = (name, year, res[1].fun)
    if sup == 1:
        if res[0].fun is not None and res[0].fun > 1:
            eff_crs[idx] = (name, year, res[0].fun)
        if res[1].fun is not None and res[1].fun > 1:
            eff_vrs[idx] = (name, year, res[1].fun)


def _patch_super_no_fallback(eff_crs: list, eff_vrs: list, idx: int, name, year,
                             res, sup: int) -> None:
    if sup == 1:
        if res[0].fun is not None and res[0].fun > 1:
            eff_crs[idx] = (name, year, res[0].fun)
        if res[1].fun is not None and res[1].fun > 1:
            eff_vrs[idx] = (name, year, res[1].fun)


def _safe_ratio(num, den):
    if num is None or den is None or den == 0:
        return None
    return num / den


def _safe_product(a, b):
    if a is None or b is None:
        return None
    return a * b


def _safe_geomean(num_den_a, num_den_b):
    na, da = num_den_a
    nb, db = num_den_b
    if None in (na, da, nb, db) or da == 0 or db == 0:
        return None
    return float(np.sqrt((na / da) * (nb / db)))


def _safe_scale_efficiency(crs_t1, vrs_t1, crs_t, vrs_t):
    if None in (crs_t1, vrs_t1, crs_t, vrs_t):
        return None
    if vrs_t1 == 0 or vrs_t == 0 or (crs_t / vrs_t) == 0:
        return None
    return (crs_t1 / vrs_t1) / (crs_t / vrs_t)


def _safe_rd_scale_change(all_index, i, dmus):
    needed = (
        all_index[i + dmus][4], all_index[i + dmus][5],
        all_index[i][2], all_index[i][3],
        all_index[i + dmus][2], all_index[i + dmus][3],
        all_index[i + dmus][6], all_index[i + dmus][7],
    )
    if None in needed or any(v == 0 for v in (needed[1], needed[3], needed[5], needed[7])):
        return None
    temp1 = (all_index[i + dmus][4] / all_index[i + dmus][5]) / (
        all_index[i][2] / all_index[i][3]
    )
    temp2 = (all_index[i + dmus][2] / all_index[i + dmus][3]) / (
        all_index[i + dmus][6] / all_index[i + dmus][7]
    )
    return float(np.sqrt(temp1 * temp2))


def _safe_zofio_scale_tc(all_index, i, dmus):
    needed = (
        all_index[i][2], all_index[i][3],
        all_index[i + dmus][6], all_index[i + dmus][7],
        all_index[i + dmus][4], all_index[i + dmus][5],
        all_index[i + dmus][2], all_index[i + dmus][3],
    )
    if None in needed or any(v == 0 for v in (needed[1], needed[3], needed[5], needed[7])):
        return None
    temp1 = (all_index[i][2] / all_index[i][3]) / (
        all_index[i + dmus][6] / all_index[i + dmus][7]
    )
    temp2 = (all_index[i + dmus][4] / all_index[i + dmus][5]) / (
        all_index[i + dmus][2] / all_index[i + dmus][3]
    )
    return float(np.sqrt(temp1 * temp2))


def _safe_bpc(num_t1, ec_t1, num_t, ec_t):
    if None in (num_t1, ec_t1, num_t, ec_t) or ec_t1 == 0 or ec_t == 0:
        return None
    return (num_t1 / ec_t1) / (num_t / ec_t)
