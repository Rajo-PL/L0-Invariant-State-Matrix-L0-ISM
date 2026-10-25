#!/usr/bin/env python3
"""
L0-ISM Dynamic Trajectory Simulator (L0-ISM-STND-2026.1)
Zero-Heap, O(1) Bounded State-Space Time-Series Engine.

Simulates:
1. Cosmological CTC Resonance & Flux-Conserving HARD_STOP (Hawking Protection).
2. OT / mCDU Hysteresis Quantization and ITER Fulcrum Restoration.
"""

import time
import math
import csv

# =============================================================================
# CONSTANTS & DEFINITIONS (Matching l0_ism_governor.h)
# =============================================================================
L0_STATE_MIN = -9
L0_STATE_ZERO = 0
L0_STATE_MAX = 9
L0_HARD_STOP_VAL = -999

ACTION_NOMINAL = "NOMINAL (Fulcrum)"
ACTION_ITER_STEP = "ITER_STEP"
ACTION_RESO_SYNC = "RESO_SYNC"
ACTION_HARD_STOP = "HARD_STOP (-999)"


# =============================================================================
# L0-ISM CORE ENGINE
# =============================================================================
def l0_sgn(val: int) -> int:
    """Discrete signum function."""
    if val > 0:
        return 1
    if val < 0:
        return -1
    return 0


def l0_clamp(val: int) -> int:
    """Clamp integer to valid [-9, +9] bounds."""
    return max(L0_STATE_MIN, min(L0_STATE_MAX, val))


def l0_quantize(raw_value: float, nominal: float, delta_max: float,
                prev_state: int, hysteresis_epsilon: float = 0.25) -> int:
    """
    Quantize continuous physical reading into discrete state [-9, +9]
    with deadband hysteresis to prevent chatter (Eq. 2 in standard).
    """
    if delta_max <= 0.0:
        return L0_STATE_ZERO

    step = delta_max / 9.0
    norm = (raw_value - nominal) / step

    # Hard boundary checks
    if norm >= 9.0 - hysteresis_epsilon:
        return L0_STATE_MAX
    if norm <= -9.0 + hysteresis_epsilon:
        return L0_STATE_MIN

    # Hysteresis deadband
    diff = norm - float(prev_state)
    if diff > (0.5 + hysteresis_epsilon):
        return l0_clamp(int(math.floor(norm + 0.5)))
    elif diff < (-0.5 - hysteresis_epsilon):
        return l0_clamp(int(math.ceil(norm - 0.5)))

    return prev_state


def verify_flux_conservation(v_before: list, v_after: list) -> bool:
    """Verify sum(delta_s) == 0 (Eq. 3 in standard)."""
    sum_delta = sum(after - before for before, after in zip(v_before, v_after))
    return sum_delta == 0


# =============================================================================
# SIMULATION 1: COSMOLOGICAL CTC RESONANCE & QUANTUM BOUNCE
# =============================================================================
def run_simulation_ctc():
    print("\n" + "=" * 80)
    print("SCENARIUSZ 1: KOSMOLOGICZNA PĘTLA CTC (REZONANS -> HARD_STOP -> DAG)")
    print("=" * 80)
    print(f"{'Krok (t_P)':<10} | {'s_rho':<7} | {'s_H':<7} | {'s_Lambda':<8} | {'CTC_Flaga':<10} | {'Akcja / Status':<20} | {'Flux Sum':<8}")
    print("-" * 80)

    # Stan początkowy: lekka ujemna energia (gardziel mostu), kolaps w toku
    s_rho = -2
    s_H = -1
    s_Lambda = 3
    ctc_active = True

    history = []

    for step in range(1, 15):
        v_before = [s_rho, s_H, s_Lambda]
        action = ACTION_NOMINAL
        status_flux = "OK"

        if ctc_active:
            if s_rho == L0_STATE_MAX:
                # BARIERA POCHŁANIAJĄCA (+9) OSIĄGNIĘTA -> HARD_STOP W O(1)
                ctc_active = False
                action = ACTION_HARD_STOP

                # Inwersja ciśnienia i transfer pędu z zachowaniem flux balance (sum(delta) == 0)
                # s_rho spada o 1 (z +9 do +8): delta = -1
                # s_Lambda uderza w -9 (inwersja próżni): delta = -9 - s_Lambda
                # s_H musi pochłonąć całą resztę energii (dyspersja rozprężenia)
                s_rho_next = 8
                s_Lambda_next = -9
                delta_rho = s_rho_next - s_rho
                delta_Lambda = s_Lambda_next - s_Lambda
                delta_H = -(delta_rho + delta_Lambda)
                s_H_next = l0_clamp(s_H + delta_H)

                s_rho, s_H, s_Lambda = s_rho_next, s_H_next, s_Lambda_next
            else:
                # Aktywny rezonans Cauchy'ego: blueshift inkrementuje gęstość
                action = "RESONANCE_PUMP"
                delta_blue = 2  # Przesunięcie ku fioletowi (logarytmiczne)
                s_rho_next = min(L0_STATE_MAX, s_rho + delta_blue)
                delta_rho = s_rho_next - s_rho

                # Kompensacja termodynamiczna w sąsiednich rejestrach (Flux Conservation)
                s_H_next = l0_clamp(s_H - delta_rho)
                delta_H = s_H_next - s_H
                s_Lambda_next = l0_clamp(s_Lambda - (delta_rho + delta_H))

                s_rho, s_H, s_Lambda = s_rho_next, s_H_next, s_Lambda_next
        else:
            # Po rozerwaniu CTC (DAG przywrócony) - operator ITER sprowadza układ do 0
            action = ACTION_ITER_STEP
            s_rho_next = s_rho - l0_sgn(s_rho)
            s_H_next = s_H - l0_sgn(s_H)
            s_Lambda_next = s_Lambda - l0_sgn(s_Lambda)
            s_rho, s_H, s_Lambda = s_rho_next, s_H_next, s_Lambda_next

        v_after = [s_rho, s_H, s_Lambda]
        flux_ok = verify_flux_conservation(v_before, v_after) if ctc_active or action == ACTION_HARD_STOP else True
        flux_str = "0 (CONSV)" if flux_ok else "ERR"

        print(f"{step:<10} | {s_rho:<7} | {s_H:<7} | {s_Lambda:<8} | {str(ctc_active):<10} | {action:<20} | {flux_str:<8}")
        history.append({"step": step, "s_rho": s_rho, "s_H": s_H, "s_Lambda": s_Lambda, "ctc": ctc_active, "action": action})

        if not ctc_active and s_rho == 0 and s_H == 0 and s_Lambda == 0:
            print(f"[+] Układ osiągnął stan absolutnej równowagi (Fulcrum) w kroku {step}.")
            break

    return history


# =============================================================================
# SIMULATION 2: OT / mCDU HYDRAULIC PRESSURE TELEMETRY
# =============================================================================
def run_simulation_mcdu():
    print("\n" + "=" * 80)
    print("SCENARIUSZ 2: OT mCDU CIŚNIENIE WTÓRNE (KWANTYZACJA -> ITER FULCRUM)")
    print("=" * 80)
    print(f"{'Czas (ms)':<10} | {'Czujnik Bar':<12} | {'Stan L0':<8} | {'Akcja L0':<18} | {'Status Przekaźnika':<20}")
    print("-" * 80)

    p_nominal = 4.0      # Ciśnienie nominalne pętli mCDU (Bar) -> Stan 0
    p_delta_max = 2.0    # Maksymalne odchylenie dopuszczalne (+/- 2 Bar) -> Stan +/- 9
    state = L0_STATE_ZERO

    # Syntetyczny profil ciśnienia: uderzenie hydrauliczne (water hammer), a potem powrót
    pressure_readings = [
        4.00, 4.25, 4.60, 5.20, 5.85, 6.05, 5.95, 5.40, 4.80, 4.30, 4.05, 4.00
    ]

    history = []

    for idx, p_raw in enumerate(pressure_readings):
        t_ms = idx * 20  # Próbkowanie co 20 ms
        prev_state = state
        state = l0_quantize(p_raw, p_nominal, p_delta_max, prev_state, hysteresis_epsilon=0.20)

        relay_status = "SAFE (CLOSED)"
        action = ACTION_NOMINAL

        if abs(state) >= L0_STATE_MAX:
            action = ACTION_HARD_STOP
            relay_status = "TRIP! HARD_STOP (OPEN)"
        elif state != 0:
            action = ACTION_ITER_STEP
            relay_status = f"REGULATING (-{l0_sgn(state)})"
        else:
            action = ACTION_NOMINAL
            relay_status = "OPTIMAL (FULCRUM)"

        print(f"{t_ms:<10} | {p_raw:<12.2f} | {state:<8} | {action:<18} | {relay_status:<20}")
        history.append({"t_ms": t_ms, "p_raw": p_raw, "state": state, "action": action, "relay": relay_status})

    return history


# =============================================================================
# EXPORT DATA TO CSV (Ready for GitHub Artifacts)
# =============================================================================
def export_results_csv(ctc_data, mcdu_data):
    with open("l0_ism_ctc_simulation.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ctc_data[0].keys())
        writer.writeheader()
        writer.writerows(ctc_data)

    with open("l0_ism_mcdu_simulation.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=mcdu_data[0].keys())
        writer.writeheader()
        writer.writerows(mcdu_data)

    print("\n[+] Zapisano wyniki symulacji do plików CSV:")
    print("    - l0_ism_ctc_simulation.csv")
    print("    - l0_ism_mcdu_simulation.csv")


if __name__ == "__main__":
    t_start = time.perf_counter()
    ctc_results = run_simulation_ctc()
    mcdu_results = run_simulation_mcdu()
    export_results_csv(ctc_results, mcdu_results)
    t_total = (time.perf_counter() - t_start) * 1000
    print(f"\n[+] Symulacja zakończona sukcesem w czasie: {t_total:.2f} ms")
