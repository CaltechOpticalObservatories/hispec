import numpy as np

def redPM_newton_core(
    move_to,
    read_power,
    start_pos,
    deltas,
    max_rel_move,
    pause=0.0,
    max_iters=6,
    step_tol=1e-4,
    eta_tol=1e-4,
    axis_names=None
):
    """
    Finite-difference Newton ascent on log(power).

    Parameters
    ----------
    move_to : callable(pos)
        Moves hardware to pos (array-like)
    read_power : callable()
        Returns measured power (uW)
    start_pos : array-like
    deltas : array-like
    max_rel_move : array-like
    axis_names : list of str, optional

    Returns
    -------
    best_pos : np.ndarray
    best_eta : float
    history  : list of dict
    """

    start_pos = np.asarray(start_pos, dtype=float)
    deltas = np.asarray(deltas, dtype=float)
    max_rel_move = np.asarray(max_rel_move, dtype=float)

    ndim = len(start_pos)
    axis_names = axis_names or [f"axis{i}" for i in range(ndim)]

    cur_pos = start_pos.copy()
    prev_eta = None

    best_eta = -np.inf
    best_pos = cur_pos.copy()

    history = []

    for it in range(max_iters):
        print(f"\n=== Newton iteration {it} ===")

        # --- Center measurement ---
        move_to(cur_pos, pause=pause)
        eta0 = read_power()
        f0 = np.log(max(eta0, 1e-12)) # use 1e-12 as a floor so we don't get Nan's

        # --- Track best-ever ---
        if eta0 > best_eta:
            best_eta = eta0
            best_pos = cur_pos.copy()

        grad = np.zeros(ndim)
        hess = np.zeros(ndim)

        # --- Finite differences ---
        for i in range(ndim):
            step_vec = np.zeros(ndim)
            step_vec[i] = deltas[i]

            # + sample step
            move_to(cur_pos + step_vec, pause=pause)
            fp = np.log(max(read_power(), 1e-12)) # use 1e-12 as a floor so we don't get Nan's

            # - sample step
            move_to(cur_pos - step_vec, pause=pause)
            fm = np.log(max(read_power(), 1e-12)) # use 1e-12 as a floor so we don't get Nan's

            grad[i] = (fp - fm) / (2 * deltas[i])
            hess[i] = (fp - 2 * f0 + fm) / (deltas[i] ** 2)

            print(f" {axis_names[i]}: grad={grad[i]:+.3e}, hess={hess[i]:+.3e}")


        # --- Newton step ---
        step = np.zeros(ndim)
        for i in range(ndim):
            if hess[i] < 0:
                step[i] = -grad[i] / hess[i]

        proposed_pos = cur_pos + step

        # --- Safety clamp to prevent moving too far ---
        lower = start_pos - max_rel_move
        upper = start_pos + max_rel_move
        proposed_pos = np.minimum(np.maximum(proposed_pos, lower), upper)

        # --- Evaluate proposed position ---
        move_to(proposed_pos, pause=pause)
        eta_new = read_power()

        # --- Track best-ever ---
        if eta_new > best_eta:
            best_eta = eta_new
            best_pos = proposed_pos.copy()

        history.append({
            "iter": it,
            "pos": cur_pos.copy(),
            "power": eta0,
            "grad": grad.copy(),
            "hess": hess.copy(),
            "step": step.copy(),
            "best_power_so_far": best_eta,
        })

        print(
            f" Power: {eta0:.5f} uW --> {eta_new:.5f} uW, "
            f"|step|={np.linalg.norm(step)*1e3:.3f}"
        )

        # --- Convergence checks ---
        # Check if eta is improving by a meaningful amount
        rel_eta_improve = (
            np.inf if prev_eta is None
            else (eta_new - prev_eta) / max(prev_eta, 1e-12)
        )

        if (prev_eta is not None) and (rel_eta_improve < eta_tol):
            print("** Converged: coupling improvement below threshold")
            cur_pos = proposed_pos
            break

        # Check if proposed next step is meaningful
        if np.linalg.norm(proposed_pos - cur_pos) < step_tol:
            print("** Converged: step size below threshold")
            cur_pos = proposed_pos
            break

        # Accept step
        cur_pos = proposed_pos
        prev_eta = eta_new

        # Shrink deltas so we take smaller steps as we get closer
        deltas *= 0.7

    # --- Move to best position ---
    move_to(best_pos, pause=pause)

    # --- Report ---
    print("\n=== BEST COUPLING POSITION FOUND ===")
    print(f"Power = {best_eta:.5f} uW")
    for i in range(ndim):
        print(f" {axis_names[i]}: {best_pos[i]:0.6f}")

    return best_pos, best_eta, history
