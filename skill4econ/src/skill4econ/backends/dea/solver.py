"""SBM / Super-SBM linear-programming kernels.

Verbatim port (with the script driver removed) of the user-authored
``dea_calculator.py``. All eight LP builders below return ``(rescrs, resvrs)``
tuples from ``scipy.optimize.linprog`` for the CRS and VRS specifications
respectively. Their ``.fun`` attribute is the SBM efficiency score (already
sign-flipped where appropriate).

Convention used by the original code:
    cur     : column index of the DMU being evaluated within the period slice.
    cur_g   : column index of the DMU within the pooled global slice.
    x_t     : (m, n) period-t inputs.
    yg_t    : (s1, n) period-t desirable outputs.
    yb_t    : (s2, n) period-t undesirable outputs; size 0 when absent.

Shape conventions are preserved so the engine.py driver can call these as-is.
"""

from __future__ import annotations

import numpy as np
from scipy import optimize


def Ecv_tt(cur, x_t, yg_t, yb_t=np.ndarray(0)):
    m, n = x_t.shape
    s1 = yg_t.shape[0]
    if (yb_t.size > 0):
        s2 = yb_t.shape[0]
        f = np.concatenate([np.zeros(n), -1/(m*x_t[:, cur]),
                            np.zeros(s1+s2), np.array([1])])
        Aeq1 = np.hstack([x_t,
                          np.identity(m),
                          np.zeros((m, s1+s2)),
                          -x_t[:, cur, None]])
        Aeq2 = np.hstack([yg_t,
                          np.zeros((s1, m)),
                          -np.identity(s1),
                          np.zeros((s1, s2)),
                          -yg_t[:, cur, None]])
        Aeq3 = np.hstack([yb_t,
                          np.zeros((s2, m)),
                          np.zeros((s2, s1)),
                          np.identity(s2),
                          -yb_t[:, cur, None]])
        Aeq4 = np.hstack([np.zeros(n),
                          np.zeros(m),
                          1/((s1+s2)*(yg_t[:, cur])),
                          1/((s1+s2)*(yb_t[:, cur])),
                          np.array([1])]).reshape(1, -1)
        Aeq5 = np.hstack([np.ones(n),
                          np.zeros((m+s1+s2)),
                          np.array([-1])]).reshape(1, -1)
        Aeqvrs = np.vstack([Aeq1, Aeq2, Aeq3, Aeq4, Aeq5])
        beqvrs = np.concatenate(
            [np.zeros(m+s1+s2), np.array([1]), np.array([0])])
        Aeqcrs = np.vstack([Aeq1, Aeq2, Aeq3, Aeq4])
        beqcrs = np.concatenate([np.zeros(m+s1+s2), np.array([1])])
        bounds = tuple([(0, None) for _ in range(n+s1+s2+m+1)])
        rescrs = optimize.linprog(c=f, A_eq=Aeqcrs, b_eq=beqcrs, bounds=bounds)
        resvrs = optimize.linprog(c=f, A_eq=Aeqvrs, b_eq=beqvrs, bounds=bounds)
    else:
        f = np.concatenate([np.zeros(n), -1/(m*x_t[:, cur]),
                            np.zeros(s1), np.array([1])])
        Aeq1 = np.hstack([x_t,
                          np.identity(m),
                          np.zeros((m, s1)),
                          -x_t[:, cur, None]])
        Aeq2 = np.hstack([yg_t,
                          np.zeros((s1, m)),
                          -np.identity(s1),
                          -yg_t[:, cur, None]])
        Aeq4 = np.hstack([np.zeros(n),
                          np.zeros(m),
                          1/((s1)*(yg_t[:, cur])),
                          np.array([1])]).reshape(1, -1)
        Aeq5 = np.hstack([np.ones(n),
                          np.zeros((m+s1)),
                          np.array([-1])]).reshape(1, -1)
        Aeqvrs = np.vstack([Aeq1, Aeq2, Aeq4, Aeq5])
        beqvrs = np.concatenate([np.zeros(m+s1), np.array([1]), np.array([0])])
        Aeqcrs = np.vstack([Aeq1, Aeq2, Aeq4])
        beqcrs = np.concatenate([np.zeros(m+s1), np.array([1])])
        bounds = tuple([(0, None) for _ in range(n+s1+m+1)])
        resvrs = optimize.linprog(c=f, A_eq=Aeqvrs, b_eq=beqvrs, bounds=bounds)
        rescrs = optimize.linprog(c=f, A_eq=Aeqcrs, b_eq=beqcrs, bounds=bounds)
    return (rescrs, resvrs)


def Ecv_tt1(cur, x_t, x_t1, yg_t, yg_t1, yb_t=np.ndarray(0), yb_t1=np.ndarray(0)):
    m, n = x_t.shape
    s1 = yg_t.shape[0]
    if (yb_t.size > 0):
        s2 = yb_t.shape[0]
        f_tt1 = np.concatenate([np.zeros(n), -1/(m*x_t1[:, cur]),
                                np.zeros(s1+s2), np.array([1])])
        Aeq1_tt1 = np.hstack([x_t,
                              np.identity(m),
                              np.zeros((m, s1+s2)),
                              -x_t1[:, cur, None]])
        Aeq2_tt1 = np.hstack([yg_t,
                              np.zeros((s1, m)),
                              -np.identity(s1),
                              np.zeros((s1, s2)),
                              -yg_t1[:, cur, None]])
        Aeq3_tt1 = np.hstack([yb_t,
                              np.zeros((s2, m)),
                              np.zeros((s2, s1)),
                              np.identity(s2),
                              -yb_t1[:, cur, None]])
        Aeq4_tt1 = np.hstack([np.zeros(n),
                              np.zeros(m),
                              1/((s1+s2)*(yg_t1[:, cur])),
                              1/((s1+s2)*(yb_t1[:, cur])),
                              np.array([1])]).reshape(1, -1)
        Aeq5_tt1 = np.hstack([np.ones(n),
                              np.zeros((m+s1+s2)),
                              np.array([-1])]).reshape(1, -1)
        Aeqvrs_tt1 = np.vstack(
            [Aeq1_tt1, Aeq2_tt1, Aeq3_tt1, Aeq4_tt1, Aeq5_tt1])
        beqvrs_tt1 = np.concatenate(
            [np.zeros(m+s1+s2), np.array([1]), np.array([0])])
        Aeqcrs_tt1 = np.vstack([Aeq1_tt1, Aeq2_tt1, Aeq3_tt1, Aeq4_tt1])
        beqcrs_tt1 = np.concatenate([np.zeros(m+s1+s2), np.array([1])])
        bounds = tuple([(0, None) for _ in range(n+s1+s2+m+1)])
        rescrs_tt1 = optimize.linprog(
            c=f_tt1, A_eq=Aeqcrs_tt1, b_eq=beqcrs_tt1, bounds=bounds)
        resvrs_tt1 = optimize.linprog(
            c=f_tt1, A_eq=Aeqvrs_tt1, b_eq=beqvrs_tt1, bounds=bounds)
    else:
        f_tt1 = np.concatenate([np.zeros(n), -1/(m*x_t1[:, cur]),
                                np.zeros(s1), np.array([1])])
        Aeq1_tt1 = np.hstack([x_t,
                              np.identity(m),
                              np.zeros((m, s1)),
                              -x_t1[:, cur, None]])
        Aeq2_tt1 = np.hstack([yg_t,
                              np.zeros((s1, m)),
                              -np.identity(s1),
                              -yg_t1[:, cur, None]])
        Aeq4_tt1 = np.hstack([np.zeros(n),
                              np.zeros(m),
                              1/((s1)*(yg_t1[:, cur])),
                              np.array([1])]).reshape(1, -1)
        Aeq5_tt1 = np.hstack([np.ones(n),
                              np.zeros((m+s1)),
                              np.array([-1])]).reshape(1, -1)
        Aeqvrs_tt1 = np.vstack([Aeq1_tt1, Aeq2_tt1, Aeq4_tt1, Aeq5_tt1])
        beqvrs_tt1 = np.concatenate(
            [np.zeros(m+s1), np.array([1]), np.array([0])])
        Aeqcrs_tt1 = np.vstack([Aeq1_tt1, Aeq2_tt1, Aeq4_tt1])
        beqcrs_tt1 = np.concatenate([np.zeros(m+s1), np.array([1])])
        bounds = tuple([(0, None) for _ in range(n+s1+m+1)])
        resvrs_tt1 = optimize.linprog(
            c=f_tt1, A_eq=Aeqvrs_tt1, b_eq=beqvrs_tt1, bounds=bounds)
        rescrs_tt1 = optimize.linprog(
            c=f_tt1, A_eq=Aeqcrs_tt1, b_eq=beqcrs_tt1, bounds=bounds)
    return (rescrs_tt1, resvrs_tt1)


def Ecv_t1t(cur, x_t, x_t1, yg_t, yg_t1, yb_t=np.ndarray(0), yb_t1=np.ndarray(0)):
    m, n = x_t.shape
    s1 = yg_t.shape[0]
    if (yb_t.size > 0):
        s2 = yb_t.shape[0]
        f_t1t = np.concatenate([np.zeros(n), -1/(m*x_t[:, cur]),
                                np.zeros(s1+s2), np.array([1])])
        Aeq1_t1t = np.hstack([x_t1,
                              np.identity(m),
                              np.zeros((m, s1+s2)),
                              -x_t[:, cur, None]])
        Aeq2_t1t = np.hstack([yg_t1,
                              np.zeros((s1, m)),
                              -np.identity(s1),
                              np.zeros((s1, s2)),
                              -yg_t[:, cur, None]])
        Aeq3_t1t = np.hstack([yb_t1,
                              np.zeros((s2, m)),
                              np.zeros((s2, s1)),
                              np.identity(s2),
                              -yb_t[:, cur, None]])
        Aeq4_t1t = np.hstack([np.zeros(n),
                              np.zeros(m),
                              1/((s1+s2)*(yg_t[:, cur])),
                              1/((s1+s2)*(yb_t[:, cur])),
                              np.array([1])]).reshape(1, -1)
        Aeq5_t1t = np.hstack([np.ones(n),
                              np.zeros((m+s1+s2)),
                              np.array([-1])]).reshape(1, -1)
        Aeqvrs_t1t = np.vstack(
            [Aeq1_t1t, Aeq2_t1t, Aeq3_t1t, Aeq4_t1t, Aeq5_t1t])
        beqvrs_t1t = np.concatenate(
            [np.zeros(m+s1+s2), np.array([1]), np.array([0])])
        Aeqcrs_t1t = np.vstack([Aeq1_t1t, Aeq2_t1t, Aeq3_t1t, Aeq4_t1t])
        beqcrs_t1t = np.concatenate([np.zeros(m+s1+s2), np.array([1])])
        bounds = tuple([(0, None) for _ in range(n+s1+s2+m+1)])
        rescrs_t1t = optimize.linprog(
            c=f_t1t, A_eq=Aeqcrs_t1t, b_eq=beqcrs_t1t, bounds=bounds)
        resvrs_t1t = optimize.linprog(
            c=f_t1t, A_eq=Aeqvrs_t1t, b_eq=beqvrs_t1t, bounds=bounds)
    else:
        f_t1t = np.concatenate([np.zeros(n), -1/(m*x_t[:, cur]),
                                np.zeros(s1), np.array([1])])
        Aeq1_t1t = np.hstack([x_t1,
                              np.identity(m),
                              np.zeros((m, s1)),
                              -x_t[:, cur, None]])
        Aeq2_t1t = np.hstack([yg_t1,
                              np.zeros((s1, m)),
                              -np.identity(s1),
                              -yg_t[:, cur, None]])
        Aeq4_t1t = np.hstack([np.zeros(n),
                              np.zeros(m),
                              1/((s1)*(yg_t[:, cur])),
                              np.array([1])]).reshape(1, -1)
        Aeq5_t1t = np.hstack([np.ones(n),
                              np.zeros((m+s1)),
                              np.array([-1])]).reshape(1, -1)
        Aeqvrs_t1t = np.vstack([Aeq1_t1t, Aeq2_t1t, Aeq4_t1t, Aeq5_t1t])
        beqvrs_t1t = np.concatenate(
            [np.zeros(m+s1), np.array([1]), np.array([0])])
        Aeqcrs_t1t = np.vstack([Aeq1_t1t, Aeq2_t1t, Aeq4_t1t])
        beqcrs_t1t = np.concatenate([np.zeros(m+s1), np.array([1])])
        bounds = tuple([(0, None) for _ in range(n+s1+m+1)])
        resvrs_t1t = optimize.linprog(
            c=f_t1t, A_eq=Aeqvrs_t1t, b_eq=beqvrs_t1t, bounds=bounds)
        rescrs_t1t = optimize.linprog(
            c=f_t1t, A_eq=Aeqcrs_t1t, b_eq=beqcrs_t1t, bounds=bounds)
    return (rescrs_t1t, resvrs_t1t)


def SupEcv_tt(cur, x_t, yg_t, yb_t=np.ndarray(0)):
    m, n = x_t.shape
    s1 = yg_t.shape[0]
    if (yb_t.size > 0):
        s2 = yb_t.shape[0]
        f = np.concatenate([np.zeros(n), 1/(m*x_t[:, cur]),
                            np.zeros(s1+s2), np.array([1])])
        Aeq1 = np.hstack([np.zeros(n),
                          np.zeros(m),
                          -1/((s1+s2)*(yg_t[:, cur])),
                          -1/((s1+s2)*(yb_t[:, cur])),
                          np.array([1])]).reshape(1, -1)
        Aeq2 = np.hstack([np.ones(n),
                          np.zeros((m+s1+s2)),
                          np.array([-1])]).reshape(1, -1)
        Aeqvrs = np.vstack([Aeq1, Aeq2])
        Aeqvrs[:, cur] = 0
        beqvrs = np.concatenate([np.array([1]), np.array([0])])
        Aeqcrs = Aeq1
        beqcrs = np.array([1])
        Aub1 = np.hstack([x_t,
                          -np.identity(m),
                          np.zeros((m, s1+s2)),
                          -x_t[:, cur, None]])
        Aub2 = np.hstack([-yg_t,
                          np.zeros((s1, m)),
                          -np.identity(s1),
                          np.zeros((s1, s2)),
                          yg_t[:, cur, None]])
        Aub3 = np.hstack([yb_t,
                          np.zeros((s2, m)),
                          np.zeros((s2, s1)),
                          -np.identity(s2),
                          -yb_t[:, cur, None]])
        Aub = np.vstack([Aub1, Aub2, Aub3])
        bub = np.zeros(m+s1+s2)
        Aub[:, cur] = 0
        bounds = tuple([(0, None) for _ in range(n+s1+s2+m+1)])
        resvrs = optimize.linprog(
            c=f, A_ub=Aub, b_ub=bub, A_eq=Aeqvrs, b_eq=beqvrs, bounds=bounds)
        rescrs = optimize.linprog(
            c=f, A_ub=Aub, b_ub=bub, A_eq=Aeqcrs, b_eq=beqcrs, bounds=bounds)
    else:
        f = np.concatenate([np.zeros(n), 1/(m*x_t[:, cur]),
                            np.zeros(s1), np.array([1])])
        Aeq1 = np.hstack([np.zeros(n),
                          np.zeros(m),
                          -1/((s1)*(yg_t[:, cur])),
                          np.array([1])]).reshape(1, -1)
        Aeq2 = np.hstack([np.ones(n),
                          np.zeros((m+s1)),
                          np.array([-1])]).reshape(1, -1)
        Aeqvrs = np.vstack([Aeq1, Aeq2])
        Aeqvrs[:, cur] = 0
        beqvrs = np.concatenate([np.array([1]), np.array([0])])
        Aeqcrs = Aeq1
        beqcrs = np.array([1])
        Aub1 = np.hstack([x_t,
                          -np.identity(m),
                          np.zeros((m, s1)),
                          -x_t[:, cur, None]])
        Aub2 = np.hstack([-yg_t,
                          np.zeros((s1, m)),
                          -np.identity(s1),
                          yg_t[:, cur, None]])
        Aub = np.vstack([Aub1, Aub2])
        bub = np.zeros(m+s1)
        Aub[:, cur] = 0
        bounds = tuple([(0, None) for _ in range(n+s1+m+1)])
        resvrs = optimize.linprog(
            c=f, A_ub=Aub, b_ub=bub, A_eq=Aeqvrs, b_eq=beqvrs, bounds=bounds)
        rescrs = optimize.linprog(
            c=f, A_ub=Aub, b_ub=bub, A_eq=Aeqcrs, b_eq=beqcrs, bounds=bounds)
    return (rescrs, resvrs)


def SupEcv_tt1(cur, x_t, x_t1, yg_t, yg_t1, yb_t=np.ndarray(0), yb_t1=np.ndarray(0)):
    m, n = x_t.shape
    s1 = yg_t.shape[0]
    if (yb_t.size > 0):
        s2 = yb_t.shape[0]
        f_tt1 = np.concatenate([np.zeros(n), 1/(m*x_t1[:, cur]),
                                np.zeros(s1+s2), np.array([1])])
        Aeq1_tt1 = np.hstack([np.zeros(n),
                              np.zeros(m),
                              -1/((s1+s2)*(yg_t1[:, cur])),
                              -1/((s1+s2)*(yb_t1[:, cur])),
                              np.array([1])]).reshape(1, -1)
        Aeq2_tt1 = np.hstack([np.ones(n),
                              np.zeros((m+s1+s2)),
                              np.array([-1])]).reshape(1, -1)
        Aeqvrs_tt1 = np.vstack([Aeq1_tt1, Aeq2_tt1])
        beqvrs_tt1 = np.concatenate([np.array([1]), np.array([0])])
        Aeqcrs_tt1 = Aeq1_tt1
        beqcrs_tt1 = np.array([1])
        Aub1_tt1 = np.hstack([x_t,
                              -np.identity(m),
                              np.zeros((m, s1+s2)),
                              -x_t1[:, cur, None]])
        Aub2_tt1 = np.hstack([-yg_t,
                              np.zeros((s1, m)),
                              -np.identity(s1),
                              np.zeros((s1, s2)),
                              yg_t1[:, cur, None]])
        Aub3_tt1 = np.hstack([yb_t,
                              np.zeros((s2, m)),
                              np.zeros((s2, s1)),
                              -np.identity(s2),
                              -yb_t1[:, cur, None]])
        Aub_tt1 = np.vstack([Aub1_tt1, Aub2_tt1, Aub3_tt1])
        bub_tt1 = np.zeros(m+s1+s2)
        bounds = tuple([(0, None) for _ in range(n+s1+s2+m+1)])
        resvrs_tt1 = optimize.linprog(
            c=f_tt1, A_ub=Aub_tt1, b_ub=bub_tt1, A_eq=Aeqvrs_tt1, b_eq=beqvrs_tt1, bounds=bounds)
        rescrs_tt1 = optimize.linprog(
            c=f_tt1, A_ub=Aub_tt1, b_ub=bub_tt1, A_eq=Aeqcrs_tt1, b_eq=beqcrs_tt1, bounds=bounds)
    else:
        f_tt1 = np.concatenate([np.zeros(n), 1/(m*x_t1[:, cur]),
                                np.zeros(s1), np.array([1])])
        Aeq1_tt1 = np.hstack([np.zeros(n),
                              np.zeros(m),
                              -1/((s1)*(yg_t1[:, cur])),
                              np.array([1])]).reshape(1, -1)
        Aeq2_tt1 = np.hstack([np.ones(n),
                              np.zeros((m+s1)),
                              np.array([-1])]).reshape(1, -1)
        Aeqvrs_tt1 = np.vstack([Aeq1_tt1, Aeq2_tt1])
        beqvrs_tt1 = np.concatenate([np.array([1]), np.array([0])])
        Aeqcrs_tt1 = Aeq1_tt1
        beqcrs_tt1 = np.array([1])
        Aub1_tt1 = np.hstack([x_t,
                              -np.identity(m),
                              np.zeros((m, s1)),
                              -x_t1[:, cur, None]])
        Aub2_tt1 = np.hstack([-yg_t,
                              np.zeros((s1, m)),
                              -np.identity(s1),
                              yg_t1[:, cur, None]])
        Aub_tt1 = np.vstack([Aub1_tt1, Aub2_tt1])
        bub_tt1 = np.zeros(m+s1)
        bounds = tuple([(0, None) for _ in range(n+s1+m+1)])
        resvrs_tt1 = optimize.linprog(
            c=f_tt1, A_ub=Aub_tt1, b_ub=bub_tt1, A_eq=Aeqvrs_tt1, b_eq=beqvrs_tt1, bounds=bounds)
        rescrs_tt1 = optimize.linprog(
            c=f_tt1, A_ub=Aub_tt1, b_ub=bub_tt1, A_eq=Aeqcrs_tt1, b_eq=beqcrs_tt1, bounds=bounds)
    return (rescrs_tt1, resvrs_tt1)


def SupEcv_t1t(cur, x_t, x_t1, yg_t, yg_t1, yb_t=np.ndarray(0), yb_t1=np.ndarray(0)):
    m, n = x_t.shape
    s1 = yg_t.shape[0]
    if (yb_t.size > 0):
        s2 = yb_t.shape[0]
        f_t1t = np.concatenate([np.zeros(n), 1/(m*x_t[:, cur]),
                                np.zeros(s1+s2), np.array([1])])
        Aeq1_t1t = np.hstack([np.zeros(n),
                              np.zeros(m),
                              -1/((s1+s2)*(yg_t[:, cur])),
                              -1/((s1+s2)*(yb_t[:, cur])),
                              np.array([1])]).reshape(1, -1)
        Aeq2_t1t = np.hstack([np.ones(n),
                              np.zeros((m+s1+s2)),
                              np.array([-1])]).reshape(1, -1)
        Aeqvrs_t1t = np.vstack([Aeq1_t1t, Aeq2_t1t])
        beqvrs_t1t = np.concatenate([np.array([1]), np.array([0])])
        Aeqcrs_t1t = Aeq1_t1t
        beqcrs_t1t = np.array([1])
        Aub1_t1t = np.hstack([x_t1,
                              -np.identity(m),
                              np.zeros((m, s1+s2)),
                              -x_t[:, cur, None]])
        Aub2_t1t = np.hstack([-yg_t1,
                              np.zeros((s1, m)),
                              -np.identity(s1),
                              np.zeros((s1, s2)),
                              yg_t[:, cur, None]])
        Aub3_t1t = np.hstack([yb_t1,
                              np.zeros((s2, m)),
                              np.zeros((s2, s1)),
                              -np.identity(s2),
                              -yb_t[:, cur, None]])
        Aub_t1t = np.vstack([Aub1_t1t, Aub2_t1t, Aub3_t1t])
        bub_t1t = np.zeros(m+s1+s2)
        bounds = tuple([(0, None) for _ in range(n+s1+s2+m+1)])
        resvrs_t1t = optimize.linprog(
            c=f_t1t, A_ub=Aub_t1t, b_ub=bub_t1t, A_eq=Aeqvrs_t1t, b_eq=beqvrs_t1t, bounds=bounds)
        rescrs_t1t = optimize.linprog(
            c=f_t1t, A_ub=Aub_t1t, b_ub=bub_t1t, A_eq=Aeqcrs_t1t, b_eq=beqcrs_t1t, bounds=bounds)
    else:
        f_t1t = np.concatenate([np.zeros(n), 1/(m*x_t[:, cur]),
                                np.zeros(s1), np.array([1])])
        Aeq1_t1t = np.hstack([np.zeros(n),
                              np.zeros(m),
                              -1/((s1)*(yg_t[:, cur])),
                              np.array([1])]).reshape(1, -1)
        Aeq2_t1t = np.hstack([np.ones(n),
                              np.zeros((m+s1)),
                              np.array([-1])]).reshape(1, -1)
        Aeqvrs_t1t = np.vstack([Aeq1_t1t, Aeq2_t1t])
        beqvrs_t1t = np.concatenate([np.array([1]), np.array([0])])
        Aeqcrs_t1t = Aeq1_t1t
        beqcrs_t1t = np.array([1])
        Aub1_t1t = np.hstack([x_t1,
                              -np.identity(m),
                              np.zeros((m, s1)),
                              -x_t[:, cur, None]])
        Aub2_t1t = np.hstack([-yg_t1,
                              np.zeros((s1, m)),
                              -np.identity(s1),
                              yg_t[:, cur, None]])
        Aub_t1t = np.vstack([Aub1_t1t, Aub2_t1t])
        bub_t1t = np.zeros(m+s1)
        bounds = tuple([(0, None) for _ in range(n+s1+m+1)])
        resvrs_t1t = optimize.linprog(
            c=f_t1t, A_ub=Aub_t1t, b_ub=bub_t1t, A_eq=Aeqvrs_t1t, b_eq=beqvrs_t1t, bounds=bounds)
        rescrs_t1t = optimize.linprog(
            c=f_t1t, A_ub=Aub_t1t, b_ub=bub_t1t, A_eq=Aeqcrs_t1t, b_eq=beqcrs_t1t, bounds=bounds)
    return (rescrs_t1t, resvrs_t1t)


def Ec_g(cur_g, x_t, yg_t, x_g, yg_g, yb_t=np.ndarray(0), yb_g=np.ndarray(0)):
    m, n = x_t.shape
    mg, ng = x_g.shape
    s1 = yg_t.shape[0]
    if (yb_t.size > 0):
        s2 = yb_t.shape[0]
        f = np.concatenate([np.zeros(ng), -1/(m*x_g[:, cur_g]),
                            np.zeros(s1+s2), np.array([1])])
        Aeq1 = np.hstack([x_g,
                          np.identity(m),
                          np.zeros((m, s1+s2)),
                          -x_g[:, cur_g, None]])
        Aeq2 = np.hstack([yg_g,
                          np.zeros((s1, m)),
                          -np.identity(s1),
                          np.zeros((s1, s2)),
                          -yg_g[:, cur_g, None]])
        Aeq3 = np.hstack([yb_g,
                          np.zeros((s2, m)),
                          np.zeros((s2, s1)),
                          np.identity(s2),
                          -yb_g[:, cur_g, None]])
        Aeq4 = np.hstack([np.zeros(ng),
                          np.zeros(m),
                          1/((s1+s2)*(yg_g[:, cur_g])),
                          1/((s1+s2)*(yb_g[:, cur_g])),
                          np.array([1])]).reshape(1, -1)
        Aeq5 = np.hstack([np.ones(ng),
                          np.zeros((m+s1+s2)),
                          np.array([-1])]).reshape(1, -1)
        Aeqvrs = np.vstack([Aeq1, Aeq2, Aeq3, Aeq4, Aeq5])
        beqvrs = np.concatenate(
            [np.zeros(m+s1+s2), np.array([1]), np.array([0])])
        Aeqcrs = np.vstack([Aeq1, Aeq2, Aeq3, Aeq4])
        beqcrs = np.concatenate([np.zeros(m+s1+s2), np.array([1])])
        bounds = tuple([(0, None) for _ in range(ng+s1+s2+m+1)])
        rescrs = optimize.linprog(c=f, A_eq=Aeqcrs, b_eq=beqcrs, bounds=bounds)
        resvrs = optimize.linprog(c=f, A_eq=Aeqvrs, b_eq=beqvrs, bounds=bounds)
    else:
        f = np.concatenate([np.zeros(ng), -1/(m*x_g[:, cur_g]),
                            np.zeros(s1), np.array([1])])
        Aeq1 = np.hstack([x_g,
                          np.identity(m),
                          np.zeros((m, s1)),
                          -x_g[:, cur_g, None]])
        Aeq2 = np.hstack([yg_g,
                          np.zeros((s1, m)),
                          -np.identity(s1),
                          -yg_g[:, cur_g, None]])
        Aeq4 = np.hstack([np.zeros(ng),
                          np.zeros(m),
                          1/((s1)*(yg_g[:, cur_g])),
                          np.array([1])]).reshape(1, -1)
        Aeq5 = np.hstack([np.ones(ng),
                          np.zeros((m+s1)),
                          np.array([-1])]).reshape(1, -1)
        Aeqvrs = np.vstack([Aeq1, Aeq2, Aeq4, Aeq5])
        beqvrs = np.concatenate([np.zeros(m+s1), np.array([1]), np.array([0])])
        Aeqcrs = np.vstack([Aeq1, Aeq2, Aeq4])
        beqcrs = np.concatenate([np.zeros(m+s1), np.array([1])])
        bounds = tuple([(0, None) for _ in range(ng+s1+m+1)])
        resvrs = optimize.linprog(c=f, A_eq=Aeqvrs, b_eq=beqvrs, bounds=bounds)
        rescrs = optimize.linprog(c=f, A_eq=Aeqcrs, b_eq=beqcrs, bounds=bounds)
    return (rescrs, resvrs)


def SupEc_g(cur_g, x_t, yg_t, x_g, yg_g, yb_t=np.ndarray(0), yb_g=np.ndarray(0)):
    m, n = x_t.shape
    mg, ng = x_g.shape
    s1 = yg_t.shape[0]
    if (yb_t.size > 0):
        s2 = yb_t.shape[0]
        f = np.concatenate([np.zeros(ng), 1/(m*x_g[:, cur_g]),
                            np.zeros(s1+s2), np.array([1])])
        Aeq1 = np.hstack([np.zeros(ng),
                          np.zeros(m),
                          -1/((s1+s2)*(yg_g[:, cur_g])),
                          -1/((s1+s2)*(yb_g[:, cur_g])),
                          np.array([1])]).reshape(1, -1)
        Aeq2 = np.hstack([np.ones(ng),
                          np.zeros((m+s1+s2)),
                          np.array([-1])]).reshape(1, -1)
        Aeqvrs = np.vstack([Aeq1, Aeq2])
        Aeqvrs[:, cur_g] = 0
        beqvrs = np.concatenate([np.array([1]), np.array([0])])
        Aeqcrs = Aeq1
        beqcrs = np.array([1])
        Aub1 = np.hstack([x_g,
                          -np.identity(m),
                          np.zeros((m, s1+s2)),
                          -x_g[:, cur_g, None]])
        Aub2 = np.hstack([-yg_g,
                          np.zeros((s1, m)),
                          -np.identity(s1),
                          np.zeros((s1, s2)),
                          yg_g[:, cur_g, None]])
        Aub3 = np.hstack([yb_g,
                          np.zeros((s2, m)),
                          np.zeros((s2, s1)),
                          -np.identity(s2),
                          -yb_g[:, cur_g, None]])
        Aub = np.vstack([Aub1, Aub2, Aub3])
        bub = np.zeros(m+s1+s2)
        Aub[:, cur_g] = 0
        bounds = tuple([(0, None) for _ in range(ng+s1+s2+m+1)])
        resvrs = optimize.linprog(
            c=f, A_ub=Aub, b_ub=bub, A_eq=Aeqvrs, b_eq=beqvrs, bounds=bounds)
        rescrs = optimize.linprog(
            c=f, A_ub=Aub, b_ub=bub, A_eq=Aeqcrs, b_eq=beqcrs, bounds=bounds)
    else:
        f = np.concatenate([np.zeros(ng), 1/(m*x_g[:, cur_g]),
                            np.zeros(s1), np.array([1])])
        Aeq1 = np.hstack([np.zeros(ng),
                          np.zeros(m),
                          -1/((s1)*(yg_g[:, cur_g])),
                          np.array([1])]).reshape(1, -1)
        Aeq2 = np.hstack([np.ones(ng),
                          np.zeros((m+s1)),
                          np.array([-1])]).reshape(1, -1)
        Aeqvrs = np.vstack([Aeq1, Aeq2])
        Aeqvrs[:, cur_g] = 0
        beqvrs = np.concatenate([np.array([1]), np.array([0])])
        Aeqcrs = Aeq1
        beqcrs = np.array([1])
        Aub1 = np.hstack([x_g,
                          -np.identity(m),
                          np.zeros((m, s1)),
                          -x_g[:, cur_g, None]])
        Aub2 = np.hstack([-yg_g,
                          np.zeros((s1, m)),
                          -np.identity(s1),
                          yg_g[:, cur_g, None]])
        Aub = np.vstack([Aub1, Aub2])
        bub = np.zeros(m+s1)
        Aub[:, cur_g] = 0
        bounds = tuple([(0, None) for _ in range(ng+s1+m+1)])
        resvrs = optimize.linprog(
            c=f, A_ub=Aub, b_ub=bub, A_eq=Aeqvrs, b_eq=beqvrs, bounds=bounds)
        rescrs = optimize.linprog(
            c=f, A_ub=Aub, b_ub=bub, A_eq=Aeqcrs, b_eq=beqcrs, bounds=bounds)
    return (rescrs, resvrs)
