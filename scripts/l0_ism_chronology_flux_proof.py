#!/usr/bin/env python3
import time
from z3 import And, Bool, If, Implies, Int, Not, Solver, unsat

def verify_l0_ism_flux_conservation():
    print("=========================================================================")
    print("--- DATA PHYSICS: CHRONOLOGY PROTECTION VERIFICATION + FLUX CONSERVATION ---")
    print("=========================================================================")
    
    def add_l0_bounds(solver, s_rho, s_H, s_Lambda):
        solver.add(
            s_rho >= -9, s_rho <= 9,
            s_H >= -9, s_H <= 9,
            s_Lambda >= -9, s_Lambda <= 9
        )

    def add_ctc_transition(solver, s_rho, s_H, s_Lambda, ctc_active,
                           s_rho_next, s_H_next, s_Lambda_next, ctc_active_next,
                           delta_blueshift):
        
        # Fundamental Discrete Flux Conservation Law (L0-ISM-STND-2026.1)
        # The sum of state differences (delta) in the vector must equal absolute zero in every step.
        delta_rho = s_rho_next - s_rho
        delta_H = s_H_next - s_H
        delta_Lambda = s_Lambda_next - s_Lambda
        solver.add(delta_rho + delta_H + delta_Lambda == 0)

        # Loop amplification limits (blueshift)
        solver.add(delta_blueshift >= 1, delta_blueshift <= 9)

        # 1. Triggering the HARD_STOP fuse at s_rho == 9
        # Z3 automatically calculates momentum dispersion (s_H_next) and density drop (s_rho_next)
        # based on the flux conservation equation, after enforcing vacuum interdiction (s_Lambda_next = -9).
        solver.add(
            Implies(
                And(ctc_active, s_rho == 9),
                And(
                    ctc_active_next == False,
                    s_Lambda_next == -9,
                    s_rho_next < 9 
                )
            )
        )

        # 2. Subcritical evolution (s_rho < 9) inside the Closed Timelike Curve (CTC)
        # Density increase by delta_blueshift forces the other registers to compensate the energy.
        solver.add(
            Implies(
                And(ctc_active, s_rho < 9),
                And(
                    ctc_active_next == True,
                    s_rho_next == If(s_rho + delta_blueshift <= 9, s_rho + delta_blueshift, 9)
                )
            )
        )

        # 3. Determinism closure for the inactive state (acyclic graph restoration)
        solver.add(
            Implies(
                Not(ctc_active),
                And(
                    ctc_active_next == False,
                    s_rho_next == s_rho,
                    s_H_next == s_H,
                    s_Lambda_next == s_Lambda
                )
            )
        )

    # -------------------------------------------------------------------------
    # TEST 1: Exhaustive Bounded Model Checking (BMC for K=19) with Flux Conservation
    # -------------------------------------------------------------------------
    s_bmc = Solver()
    K_STEPS = 19
    rho_seq = [Int(f"rho_{k}") for k in range(K_STEPS + 1)]
    H_seq = [Int(f"H_{k}") for k in range(K_STEPS + 1)]
    Lam_seq = [Int(f"Lam_{k}") for k in range(K_STEPS + 1)]
    ctc_seq = [Bool(f"ctc_{k}") for k in range(K_STEPS + 1)]
    blue_seq = [Int(f"blue_{k}") for k in range(K_STEPS)]

    for k in range(K_STEPS + 1):
        add_l0_bounds(s_bmc, rho_seq[k], H_seq[k], Lam_seq[k])

    for k in range(K_STEPS):
        add_ctc_transition(s_bmc, rho_seq[k], H_seq[k], Lam_seq[k], ctc_seq[k],
                           rho_seq[k+1], H_seq[k+1], Lam_seq[k+1], ctc_seq[k+1], blue_seq[k])

    for k in range(K_STEPS + 1):
        s_bmc.add(ctc_seq[k] == True)

    t0 = time.perf_counter()
    res_bmc = s_bmc.check()
    t1 = (time.perf_counter() - t0) * 1000

    print(f"\n[TEST 1] BMC (K={K_STEPS}) with the discrete total flux conservation law:")
    print(f"         Result: {str(res_bmc).upper()} (Time: {t1:.2f} ms)")
    if res_bmc == unsat:
        print("         -> PROVEN: The model with thermodynamic flux conservation remains absolutely airtight.")

if __name__ == "__main__":
    verify_l0_ism_flux_conservation()
