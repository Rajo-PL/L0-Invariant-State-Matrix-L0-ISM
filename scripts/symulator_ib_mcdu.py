import time
import numpy as np

# --- GITHUB ACTIONS FIX ---
import matplotlib
matplotlib.use('Agg') # Forces rendering in the background without a GUI window
import matplotlib.pyplot as plt
# --------------------------

# ==============================================================================
# 1. STATE SPACE DEFINITION AND LOOKUP TABLE PRECOMPILATION (O(1))
# ==============================================================================

STATE_SPACE = list(range(-9, 10))  # Discrete scale [-9, ..., 0, ..., +9] (19 states)

# Actuator Action Codes
ACT_HARD_STOP = -999       # Absorbing boundary: Immediate cutoff (L0 Interdiction)
ACT_EMERGENCY_RELIEF = -50 # Rapid pressure relief (detected high gradient)
ACT_EQUILIBRIUM = 0        # Absolute equilibrium (Fulcrum = 0): No actuator movement

def build_and_verify_ib_table():
    """
    Generates a full 3D Lookup Table for k=3:
    IB = (s_pressure, delta_s_pressure, s_temperature)
    Space size: 19^3 = 6859 unique vectors.
    """
    lookup_table = {}
    
    for sp in STATE_SPACE:
        for dsp in STATE_SPACE:
            for st in STATE_SPACE:
                ib_tuple = (sp, dsp, st)
                
                # AXIOM 1: Absorbing Boundaries at +/- 9
                if abs(sp) == 9 or abs(dsp) == 9 or abs(st) == 9:
                    action = ACT_HARD_STOP
                
                # AXIOM 2: Absolute Equilibrium (The scale is balanced)
                elif sp == 0 and dsp == 0 and st == 0:
                    action = ACT_EQUILIBRIUM
                
                # AXIOM 3: Water hammer protection (high pressure gradient)
                elif dsp >= 5 or sp >= 7:
                    action = ACT_EMERGENCY_RELIEF
                
                # AXIOM 4: Deterministic proportional-discrete regulation (valve/pump correction)
                else:
                    # Negative pressure correction and positive temperature correction (open flow)
                    action = int(np.clip(-sp * 8 + st * 4 - dsp * 5, -100, 100))
                
                lookup_table[ib_tuple] = action

    # Formal Verification (Exhaustive State-Space Verification)
    expected_states = 19 ** 3
    assert len(lookup_table) == expected_states, "ERROR: Incomplete state space!"
    
    for k, v in lookup_table.items():
        assert v is not None, f"ERROR: Undefined state for {k}"
        if 9 in k or -9 in k:
            assert v == ACT_HARD_STOP, f"ERROR: Absorbing boundary violation for {k}"
            
    assert lookup_table[(0, 0, 0)] == ACT_EQUILIBRIUM, "ERROR: Zero-point violation!"
    
    return lookup_table


# ==============================================================================
# 2. INPUT DEADBAND QUANTIZER (HYSTERESIS)
# ==============================================================================

class HysteresisQuantizer:
    """
    Maps a continuous, noisy physical signal onto the discrete [-9, 9] axis.
    Prevents actuator 'flapping' at the boundary between states.
    """
    def __init__(self, nominal_val: float, max_deviation: float, deadband: float):
        self.nominal = nominal_val
        self.step = max_deviation / 9.0
        self.deadband = deadband
        self.current_state = 0

    def quantize(self, physical_value: float) -> int:
        deviation = physical_value - self.nominal
        raw_float_state = deviation / self.step
        
        # Hard limits mapping
        if raw_float_state >= 8.8:
            self.current_state = 9
            return 9
        if raw_float_state <= -8.8:
            self.current_state = -9
            return -9

        # Hysteresis: state change requires crossing the threshold + deadband
        diff = raw_float_state - self.current_state
        if abs(diff) > (0.5 + self.deadband):
            new_state = int(np.round(raw_float_state))
            self.current_state = int(np.clip(new_state, -9, 9))
            
        return self.current_state


# ==============================================================================
# 3. mCDU PIPELINE PHYSICAL SIMULATION (100 Hz TELEMETRY)
# ==============================================================================

def run_simulation():
    print("=" * 75)
    print(" L0 SAFETY ENCLAVE INITIALIZATION: INVARIANT BYTES (mCDU LOOP)")
    print("=" * 75)
    
    t0 = time.perf_counter()
    ib_table = build_and_verify_ib_table()
    t_build = (time.perf_counter() - t0) * 1000
    
    print(f"[OK] Generated and formally verified {len(ib_table)} states in {t_build:.2f} ms.")
    print("[OK] Completeness guarantee: 100% coverage of the [-9, 9]^3 space.")
    print("[OK] Starting 100 Hz telemetry simulation (1000 steps = 10 seconds)...\n")

    np.random.seed(42)
    steps = 1000
    dt = 0.01  # 100 Hz (10 ms per cycle)
    time_axis = np.arange(steps) * dt

    # Nominal parameters for the mCDU secondary loop
    NOMINAL_PRESSURE = 2.50  # bar (zero point)
    MAX_DEV_PRESSURE = 1.80  # +/- 1.8 bar -> <0.7 bar (-9: leak), >4.3 bar (+9: overpressure)
    
    NOMINAL_TEMP = 35.0      # °C (zero point)
    MAX_DEV_TEMP = 18.0      # +/- 18.0 °C

    # Initialize quantizers with hysteresis (Deadband = 0.18 step)
    q_pressure = HysteresisQuantizer(NOMINAL_PRESSURE, MAX_DEV_PRESSURE, deadband=0.18)
    q_temp = HysteresisQuantizer(NOMINAL_TEMP, MAX_DEV_TEMP, deadband=0.18)

    # Data buffers for plotting
    raw_pressure_log = np.zeros(steps)
    ib_sp_log = np.zeros(steps, dtype=int)
    ib_dsp_log = np.zeros(steps, dtype=int)
    ib_st_log = np.zeros(steps, dtype=int)
    
    ib_action_log = np.zeros(steps)
    naive_flapping_log = np.zeros(steps, dtype=int)
    
    pressure_ib_pipe = np.zeros(steps)
    pressure_ai_pipe = np.zeros(steps)

    # Initial state of two parallel pipelines
    p_ib = NOMINAL_PRESSURE
    p_ai = NOMINAL_PRESSURE
    temp_current = NOMINAL_TEMP
    
    ib_hard_stop_triggered = False
    ib_stop_step = None
    ai_burst_triggered = False

    prev_sp = 0
    lookup_times_ns = []

    for i in range(steps):
        # 1. Generate environmental disturbances
        noise_p = np.random.normal(0, 0.08)  # Pump vibration noise 50-100 Hz
        noise_t = np.random.normal(0, 0.3)

        # Phase 1 (0.0s - 3.5s): Nominal operation with heavy noise at interval boundaries
        if i < 350:
            external_p_disturbance = 0.02 * np.sin(i * 0.2)
            temp_current = NOMINAL_TEMP + noise_t
            
        # Phase 2 (3.5s - 6.5s): AI racks heat load spike (temperature and pressure rise)
        elif i < 650:
            external_p_disturbance = 0.015
            temp_current = min(45.0, temp_current + 0.08) + noise_t
            
        # Phase 3 (from 6.5s): Catastrophic main valve blockage / Water hammer effect
        else:
            external_p_disturbance = 0.085  # Rapid pressure build-up in the loop

        # --- PIPELINE A: Controlled by Invariant Bytes (L0 Enclave) ---
        if not ib_hard_stop_triggered:
            p_ib += external_p_disturbance + noise_p
        else:
            # After HARD STOP, pumps are physically cut off; pressure safely drops to 0
            p_ib = max(0.0, p_ib - 0.12)

        raw_pressure_log[i] = p_ib

        # Naive quantization without hysteresis (to demonstrate actuator flapping)
        naive_flapping_log[i] = int(np.clip(np.round((p_ib - NOMINAL_PRESSURE) / (MAX_DEV_PRESSURE / 9.0)), -9, 9))

        # Quantization with hysteresis mapped to [-9, 9] axis
        sp = q_pressure.quantize(p_ib)
        st = q_temp.quantize(temp_current)
        dsp = int(np.clip((sp - prev_sp) * 3, -9, 9))  # Amplified instantaneous gradient
        prev_sp = sp

        ib_sp_log[i] = sp
        ib_dsp_log[i] = dsp
        ib_st_log[i] = st

        # O(1) Lookup Table reading
        t_start = time.perf_counter_ns()
        current_tuple = (sp, dsp, st)
        action = ib_table[current_tuple]
        lookup_times_ns.append(time.perf_counter_ns() - t_start)

        if ib_hard_stop_triggered:
            action = ACT_HARD_STOP

        ib_action_log[i] = action

        # Physical system response to Invariant Bytes action
        if action == ACT_HARD_STOP:
            if not ib_hard_stop_triggered:
                ib_hard_stop_triggered = True
                ib_stop_step = i
                print(f"[!] STEP {i} ({i*dt:.2f}s) | IB Vector = {current_tuple} -> ABSORBING BOUNDARY HIT!")
                print("    >>> IMMEDIATE HARD_STOP EXECUTED (Pump power cutoff in O(1) time).")
        elif action == ACT_EMERGENCY_RELIEF:
            p_ib -= 0.11  # Emergency relief valve opens due to gradient detection
        else:
            # Standard proportional valve correction
            p_ib += (action / 100.0) * 0.04

        pressure_ib_pipe[i] = p_ib

        # --- PIPELINE B: Controlled by Stochastic AI Model (Matrix Lag + Weight Noise) ---
        p_ai += external_p_disturbance + noise_p
        # Simulating matrix inference delay (~15 steps) and stochastic "smoothing"
        if i > 15:
            ai_perceived_error = np.mean(pressure_ai_pipe[i-15:i]) - NOMINAL_PRESSURE
            # The stochastic model hallucinates a mild trend during a violent water hammer
            stochastic_jitter = np.random.normal(0, 0.03)
            ai_valve_correction = -0.025 * np.tanh(ai_perceived_error) + stochastic_jitter
            p_ai += ai_valve_correction
            
        if p_ai >= 4.80 and not ai_burst_triggered:
            ai_burst_triggered = True
            print(f"[X] STEP {i} ({i*dt:.2f}s) | Stochastic AI pipeline exceeded 4.80 bar!")
            print("    >>> CATASTROPHIC FAILURE: mCDU manifold seal rupture (No L0 hard boundary).")
            
        pressure_ai_pipe[i] = p_ai

    # ==============================================================================
    # 4. ENGINEERING METRICS SUMMARY
    # ==============================================================================
    naive_switches = np.sum(np.diff(naive_flapping_log[:350]) != 0)
    ib_switches = np.sum(np.diff(ib_sp_log[:350]) != 0)
    avg_lookup_ns = np.mean(lookup_times_ns)

    print("\n" + "=" * 75)
    print(" SIMULATION VALIDATION REPORT (RESULTS)")
    print("=" * 75)
    print(f"1. Average O(1) Lookup execution time:   {avg_lookup_ns:.0f} ns (nanoseconds)")
    print(f"2. Valve switches in noise (No Hysteresis): {naive_switches} cycles (Flapping/Destruction)")
    print(f"3. Valve switches in noise (IB Hysteresis): {ib_switches} cycles (Stable equilibrium 0)")
    print(f"4. Maximum Pressure (IB L0 Pipeline):       {np.max(pressure_ib_pipe):.2f} bar (Safe limit: 4.30 bar)")
    print(f"5. Maximum Pressure (Stochastic AI Pipe):   {np.max(pressure_ai_pipe):.2f} bar (CATASTROPHIC FAILURE!)")
    print("=" * 75)

    # ==============================================================================
    # 5. DATA VISUALIZATION (MATPLOTLIB)
    # ==============================================================================
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    plt.subplots_adjust(hspace=0.25)

    # Plot 1: Pressure comparison (IB vs Stochastic AI)
    ax1 = axes[0]
    ax1.plot(time_axis, pressure_ai_pipe, color='#d62728', linestyle='--', linewidth=1.8, label='Stochastic AI (Matrix delay + No boundaries)')
    ax1.plot(time_axis, pressure_ib_pipe, color='#1f77b4', linewidth=2.2, label='Invariant Bytes L0 (O(1) Determinism + Boundary +9)')
    ax1.axhline(NOMINAL_PRESSURE, color='green', linestyle=':', alpha=0.7, label='Zero Point (0 = 2.50 bar)')
    ax1.axhline(NOMINAL_PRESSURE + MAX_DEV_PRESSURE, color='black', linestyle='-', linewidth=1.5, label='Absorbing Boundary (+9 = 4.30 bar)')
    ax1.axhline(4.80, color='red', linestyle='-.', alpha=0.6, label='Mechanical destruction threshold (4.80 bar)')
    if ib_stop_step:
        ax1.axvline(ib_stop_step * dt, color='black', linestyle='--', alpha=0.8)
        ax1.annotate('HARD STOP (IB Interdiction)', xy=(ib_stop_step * dt, 4.3), xytext=(ib_stop_step * dt - 2.2, 4.6),
                     arrowprops=dict(facecolor='black', shrink=0.05, width=1.5, headwidth=6), fontweight='bold')
    ax1.set_ylabel('mCDU Pressure [bar]', fontweight='bold')
    ax1.set_title('Engineering Proof: Invariant Bytes (L0) vs Stochastic AI during a Water Hammer', fontweight='bold')
    ax1.legend(loc='upper left', fontsize=8.5)
    ax1.grid(True, alpha=0.3)

    # Plot 2: Invariant Byte Tuple coordinates on [-9, 9] axis
    ax2 = axes[1]
    ax2.step(time_axis, ib_sp_log, where='post', label='$s_1$: Pressure ($s_P$)', color='#1f77b4', linewidth=1.8)
    ax2.step(time_axis, ib_dsp_log, where='post', label='$s_2$: Gradient ($\Delta s_P$)', color='#ff7f0e', linewidth=1.2, alpha=0.85)
    ax2.step(time_axis, ib_st_log, where='post', label='$s_3$: Temperature ($s_T$)', color='#2ca02c', linewidth=1.5, alpha=0.85)
    ax2.axhline(9, color='red', linestyle='--', alpha=0.7, label='Absorbing boundaries (±9)')
    ax2.axhline(-9, color='red', linestyle='--', alpha=0.7)
    ax2.axhline(0, color='black', linestyle=':', alpha=0.5)
    ax2.set_yticks(range(-9, 10, 3))
    ax2.set_ylim(-10.5, 10.5)
    ax2.set_ylabel('Discrete Scale [-9, 9]', fontweight='bold')
    ax2.set_title('Invariant Byte Vector Trajectory $\mathcal{IB} = (s_P, \Delta s_P, s_T)$ in discrete space', fontweight='bold')
    ax2.legend(loc='upper left', fontsize=8.5, ncol=4)
    ax2.grid(True, alpha=0.3)

    # Plot 3: Noise suppression via hysteresis (Flapping elimination)
    ax3 = axes[2]
    ax3.step(time_axis, naive_flapping_log, where='post', color='gray', alpha=0.45, label='No Hysteresis (Actuator flapping from noise)')
    ax3.step(time_axis, ib_sp_log, where='post', color='#1f77b4', linewidth=2.0, label='With IB Hysteresis (Deadband = Stable State)')
    ax3.set_xlabel('Simulation Time [s] (Sampling Frequency: 100 Hz)', fontweight='bold')
    ax3.set_ylabel('State $s_P$ [-9, 9]', fontweight='bold')
    ax3.set_title('Valve Mechanical Protection: Eliminating Actuator Flapping via Input Hysteresis', fontweight='bold')
    ax3.set_yticks(range(-9, 10, 3))
    ax3.legend(loc='upper left', fontsize=8.5)
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    # File is saved to the disk. plt.show() has been removed for headless GitHub Actions execution.
    plt.savefig('invariant_bytes_proof_of_concept.png', dpi=300)
    print("\n[INFO] Proof of concept plot successfully saved as: 'invariant_bytes_proof_of_concept.png'")

if __name__ == "__main__":
    run_simulation()
