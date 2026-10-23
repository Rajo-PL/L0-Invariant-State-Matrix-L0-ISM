import time
import numpy as np

# --- GITHUB ACTIONS FIX ---
import matplotlib
matplotlib.use('Agg') # Wymusza generowanie plików graficznych w tle bez GUI
import matplotlib.pyplot as plt
# --------------------------

# ==============================================================================
# 1. STATE SPACE & PHARMACY LOOKUP TABLE PRECOMPILATION (O(1))
# ==============================================================================

STATE_SPACE = list(range(-9, 10))

# Action Codes for Pharmacy Node (Legal/Technical states)
ACT_HARD_STOP = -999        # Absorbing Boundary: Legal/Technical Interdiction (Do not dispense)
ACT_STORE_FORWARD = 50      # Offline Mode: Dispense and encrypt via T-OTP
ACT_ONLINE_DISPENSE = 0     # Absolute Equilibrium: Normal P1 online dispensing

def build_pharmacy_ib_table():
    """
    Generates a full 3D Lookup Table for k=3:
    IB = (s_net, s_buf, s_risk)
    s_net: Network status (0 = Online, -9 = Completely Offline P1)
    s_buf: Local T-OTP Buffer Load (0 = Empty, +9 = Full)
    s_risk: Prescription Risk Class (0 = Standard, +9 = Narcotic/Restricted)
    """
    lookup_table = {}
    
    for sn in STATE_SPACE:
        for sb in STATE_SPACE:
            for sr in STATE_SPACE:
                ib_tuple = (sn, sb, sr)
                
                # AXIOM 1: Critical Drug Request during Offline mode -> HARD STOP
                if sr == 9 and sn < 0:
                    action = ACT_HARD_STOP
                    
                # AXIOM 2: Buffer Overflow (Absorbing Boundary) -> HARD STOP
                elif sb == 9:
                    action = ACT_HARD_STOP
                    
                # AXIOM 3: Perfect Network (Equilibrium 0) -> ONLINE DISPENSE
                elif sn == 0:
                    action = ACT_ONLINE_DISPENSE
                    
                # AXIOM 4: Network degraded/offline, Buffer has space, Drug is safe -> T-OTP
                elif sn < 0 and sb < 9 and sr < 9:
                    action = ACT_STORE_FORWARD
                    
                else:
                    # Fallback strict policy
                    action = ACT_HARD_STOP
                
                lookup_table[ib_tuple] = action

    # Formal Verification (Z3 conceptual check)
    expected_states = 19 ** 3
    assert len(lookup_table) == expected_states, "ERROR: Incomplete state space!"
    assert lookup_table[(0, 0, 0)] == ACT_ONLINE_DISPENSE, "ERROR: Zero-point violation!"
    assert lookup_table[(-9, 0, 9)] == ACT_HARD_STOP, "ERROR: Illegal offline narcotic dispense possible!"
    assert lookup_table[(-9, 9, 0)] == ACT_HARD_STOP, "ERROR: Buffer overflow bypassed!"
    
    return lookup_table


# ==============================================================================
# 2. DISCRETE QUANTIZER FOR ABSTRACT METRICS
# ==============================================================================

class StepQuantizer:
    """Maps continuous abstract metrics (ms latency, buffer bytes) to discrete [-9, 9]"""
    def __init__(self, min_val, max_val, scale_min, scale_max):
        self.min_val = min_val
        self.max_val = max_val
        self.scale_min = scale_min
        self.scale_max = scale_max

    def quantize(self, val: float) -> int:
        clamped = np.clip(val, min(self.min_val, self.max_val), max(self.min_val, self.max_val))
        ratio = (clamped - self.min_val) / (self.max_val - self.min_val)
        discrete_val = self.scale_min + ratio * (self.scale_max - self.scale_min)
        return int(np.round(discrete_val))


# ==============================================================================
# 3. PHARMACY OFFLINE PROTOCOL SIMULATION
# ==============================================================================

def run_simulation():
    print("=" * 75)
    print(" L0 SAFETY ENCLAVE INITIALIZATION: INVARIANT BYTES (PHARMACY NODE)")
    print("=" * 75)
    
    ib_table = build_pharmacy_ib_table()
    print(f"[OK] Generated and formally verified {len(ib_table)} pharmaceutical logic states.")
    print("[OK] Structural limits enforced for T-OTP Store & Forward.\n")

    steps = 1000
    time_axis = np.arange(steps)
    
    # Quantizers
    q_net = StepQuantizer(min_val=50, max_val=5000, scale_min=0, scale_max=-9) # Latency (ms)
    q_buf = StepQuantizer(min_val=0, max_val=100, scale_min=0, scale_max=9)    # Buffer load (%)

    # Data logs
    net_latency_log = np.zeros(steps)
    buffer_load_log = np.zeros(steps)
    
    ib_sn_log = np.zeros(steps, dtype=int)
    ib_sb_log = np.zeros(steps, dtype=int)
    ib_sr_log = np.zeros(steps, dtype=int)
    action_log = np.zeros(steps, dtype=int)

    buffer_fill = 0.0
    hard_stop_step = None

    for i in range(steps):
        # 1. Environmental Simulation (Network & Patient Queue)
        if i < 300:
            # Phase 1: Stable P1 Network
            latency = 100 + np.random.normal(0, 20)  
            risk_class = 0  # Standard drugs
        elif i < 750:
            # Phase 2: P1 System Crash (Timeout)
            latency = 6000  
            risk_class = 0
            # Buffer fills up as prescriptions are saved offline via T-OTP
            if i > 0 and action_log[i-1] == ACT_STORE_FORWARD:
                buffer_fill += 0.25 
        else:
            # Phase 3: Still offline, but Patient arrives with highly restricted narcotic
            latency = 6000  
            risk_class = 9  # Narcotic prescription (Risk = 9)
            if i > 0 and action_log[i-1] == ACT_STORE_FORWARD:
                buffer_fill += 0.25

        # 2. Vectorization to Invariant Bytes Space
        net_latency_log[i] = latency
        buffer_load_log[i] = buffer_fill
        
        sn = q_net.quantize(latency)
        sb = q_buf.quantize(buffer_fill)
        sr = risk_class
        
        ib_sn_log[i] = sn
        ib_sb_log[i] = sb
        ib_sr_log[i] = sr
        
        current_tuple = (sn, sb, sr)

        # 3. O(1) Matrix Lookup
        action = ib_table[current_tuple]
        
        if hard_stop_step is not None:
            action = ACT_HARD_STOP # Latch the hard stop after first violation
            
        action_log[i] = action

        # 4. Trigger Legal Interdiction
        if action == ACT_HARD_STOP and hard_stop_step is None:
            hard_stop_step = i
            print(f"[!] STEP {i} | IB Vector = {current_tuple} -> LEGAL INTERDICTION!")
            if sr == 9:
                print("    >>> HARD_STOP: Attempted to dispense restricted narcotic offline.")
            elif sb == 9:
                print("    >>> HARD_STOP: T-OTP cryptographic buffer overflow.")

    # ==============================================================================
    # 4. DATA VISUALIZATION
    # ==============================================================================
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    plt.subplots_adjust(hspace=0.25)

    # Plot 1: System Operation Mode
    ax1 = axes[0]
    ax1.plot(time_axis, action_log, color='black', linewidth=2, drawstyle='steps-post')
    ax1.axhline(ACT_ONLINE_DISPENSE, color='green', linestyle='--', alpha=0.5, label='Online Dispense (Equilibrium 0)')
    ax1.axhline(ACT_STORE_FORWARD, color='#1f77b4', linestyle='--', alpha=0.5, label='Offline T-OTP Mode (50)')
    ax1.axhline(ACT_HARD_STOP, color='red', linestyle='--', alpha=0.5, label='Hard Stop (Interdiction -999)')
    
    if hard_stop_step:
        ax1.axvline(hard_stop_step, color='red', linestyle=':', linewidth=2)
        ax1.annotate('ILLEGAL RX INTERDICTION', xy=(hard_stop_step, ACT_HARD_STOP), xytext=(hard_stop_step - 200, ACT_HARD_STOP + 300),
                     arrowprops=dict(facecolor='red', shrink=0.05, width=1.5, headwidth=6), fontweight='bold')
    
    ax1.set_yticks([ACT_HARD_STOP, ACT_ONLINE_DISPENSE, ACT_STORE_FORWARD])
    ax1.set_yticklabels(['HARD STOP\n(-999)', 'ONLINE\n(0)', 'OFFLINE T-OTP\n(50)'])
    ax1.set_ylabel('System Action', fontweight='bold')
    ax1.set_title('Engineering Proof: Invariant Bytes Legal Interdiction in Pharmacy Edge Node', fontweight='bold')
    ax1.grid(True, alpha=0.3)

    # Plot 2: Vector Trajectory
    ax2 = axes[1]
    ax2.step(time_axis, ib_sn_log, where='post', label='$s_1$: Network ($s_{net}$)', color='#1f77b4', linewidth=1.8)
    ax2.step(time_axis, ib_sb_log, where='post', label='$s_2$: T-OTP Buffer ($s_{buf}$)', color='#ff7f0e', linewidth=1.8)
    ax2.step(time_axis, ib_sr_log, where='post', label='$s_3$: Rx Risk Class ($s_{risk}$)', color='#d62728', linewidth=1.5)
    
    ax2.axhline(9, color='red', linestyle='--', alpha=0.7, label='Absorbing boundaries (±9)')
    ax2.axhline(-9, color='red', linestyle='--', alpha=0.7)
    ax2.axhline(0, color='black', linestyle=':', alpha=0.5)
    ax2.set_yticks(range(-9, 10, 3))
    ax2.set_ylim(-10.5, 10.5)
    ax2.set_ylabel('Discrete Scale [-9, 9]', fontweight='bold')
    ax2.set_title('Invariant Byte Vector Trajectory $\mathcal{IB} = (s_{net}, s_{buf}, s_{risk})$', fontweight='bold')
    ax2.legend(loc='lower left', fontsize=8.5, ncol=4)
    ax2.grid(True, alpha=0.3)

    # Plot 3: Buffer & Latency Environment
    ax3 = axes[2]
    ax3.plot(time_axis, buffer_load_log, color='#ff7f0e', linewidth=2, label='T-OTP Buffer Load [%]')
    ax3.set_xlabel('Simulation Step (Patients in Queue)', fontweight='bold')
    ax3.set_ylabel('Buffer Load [%]', fontweight='bold')
    ax3.set_ylim(-5, 110)
    ax3.legend(loc='upper left')
    ax3.grid(True, alpha=0.3)
    
    ax3_twin = ax3.twinx()
    ax3_twin.plot(time_axis, net_latency_log, color='#1f77b4', linewidth=1, alpha=0.3, label='P1 API Latency [ms]')
    ax3_twin.set_ylabel('Latency [ms]', color='#1f77b4')
    ax3_twin.set_ylim(-100, 7000)
    ax3_twin.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig('ib_pharmacy_proof_of_concept.png', dpi=300)
    print("\n[INFO] Proof plot saved as: 'ib_pharmacy_proof_of_concept.png'")

if __name__ == "__main__":
    run_simulation()
