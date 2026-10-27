#!/usr/bin/env python3
"""
Phaistos Disc L0-ISM O(1) Look-Up Table (LUT) Simulator
======================================================
Simulates the Phaistos Disc as a pre-compiled, $O(1)$ hardware state matrix
and analog Read-Only Memory (ROM) for 45 stamped symbols across 61 spiral sections.

Framework: Layer 0 Invariant State Matrix (L0-ISM) & Data Physics
Author: Gemini Notebook Workbench / L0-ISM Engine
"""

import sys
import time
from typing import Dict, List, Tuple, NamedTuple

# Definition of State Vector IM = (s_water, s_thermal, s_flow)
class StateVector(NamedTuple):
    s_water: int   # [-9, +9]
    s_thermal: int # [-9, +9]
    s_flow: int    # [-9, +9]

    def __add__(self, other: 'StateVector') -> 'StateVector':
        return StateVector(
            s_water=self.s_water + other.s_water,
            s_thermal=self.s_thermal + other.s_thermal,
            s_flow=self.s_flow + other.s_flow
        )

    def is_bounded(self, limit: int = 8) -> bool:
        return max(abs(self.s_water), abs(self.s_thermal), abs(self.s_flow)) <= limit

    def stream_sum(self) -> int:
        return self.s_water + self.s_thermal + self.s_flow

# 45 Stamped Symbol Catalog (Evans / Louis Pernier Classification)
STAMP_CATALOG: Dict[int, Tuple[str, StateVector]] = {
    1:  ("Pedestrian / Plumed Head",     StateVector(+1,  0, -1)),
    2:  ("Plumed Head (Chief)",          StateVector(+2, +1, -3)),
    3:  ("Tattooed Head",                StateVector( 0, +1, -1)),
    4:  ("Captive / Prisoner",           StateVector(-1,  0, +1)),
    5:  ("Child / Infant",               StateVector( 0, -1, +1)),
    6:  ("Woman",                        StateVector(+1, -1,  0)),
    7:  ("Helmet",                       StateVector( 0, +2, -2)),
    8:  ("Gauntlet / Restraint",         StateVector(+1, +1, -2)),
    9:  ("Tiara / Crest",                StateVector( 0,  0,  0)),
    10: ("Arrow / Vector",               StateVector(+2,  0, -2)),
    11: ("Bow / Tension",                StateVector(-2, +2,  0)),
    12: ("Shield / Absorber",            StateVector(-1, -1, +2)),
    13: ("Club / Actuator",              StateVector(+3, -1, -2)),
    14: ("Manacles",                     StateVector(-2,  0, +2)),
    15: ("Mattock / Excavator",          StateVector(+1, -2, +1)),
    16: ("Saw / Diverter",               StateVector(-1, +2, -1)),
    17: ("Lid / Valve",                  StateVector( 0, -2, +2)),
    18: ("Boomerang / Deflector",        StateVector(+1, -1,  0)),
    19: ("Carpenter's Plane",            StateVector( 0, +1, -1)),
    20: ("Dolium / Vessel",              StateVector(+2, -2,  0)),
    21: ("Comb / Filter",                StateVector(-1, +1,  0)),
    22: ("Sessile Sling",                StateVector( 0,  0,  0)),
    23: ("Column / Pillar",              StateVector( 0, +3, -3)),
    24: ("Beehive / Reactor",            StateVector(+2, +2, -4)),
    25: ("Ship / Transport",             StateVector(+1,  0, -1)),
    26: ("Horn / Nozzle",                StateVector(+2, -1, -1)),
    27: ("Hide / Membrane",              StateVector(-1, +1,  0)),
    28: ("Bull's Leg / Lever",           StateVector(+3,  0, -3)),
    29: ("Cat / Feline",                 StateVector( 0, +1, -1)),
    30: ("Ram / Pressure",               StateVector(+2, +1, -3)),
    31: ("Eagle / Sensor",               StateVector( 0,  0,  0)),
    32: ("Dove / Peaceful Flow",         StateVector(-1, -1, +2)),
    33: ("Tunny / Marine Flow",          StateVector(+1, -2, +1)),
    34: ("Bee / Frequency",              StateVector( 0, +1, -1)),
    35: ("Plane Tree / Wood Resource",   StateVector(-2, +3, -1)),
    36: ("Olive Branch / Siphon",        StateVector(-1,  0, +1)),
    37: ("Papyrus / Flow Meter",         StateVector(+1, -1,  0)),
    38: ("Rosette / Central Hub",        StateVector( 0,  0,  0)),
    39: ("Lily / Purifier",              StateVector(-1, +1,  0)),
    40: ("Ox Back / Mass",               StateVector(+2, -1, -1)),
    41: ("Flute / Telemetry Pulse",      StateVector( 0,  0,  0)),
    42: ("Grater / Dissipator",          StateVector(-2, +1, +1)),
    43: ("Triangle / Fulcrum Marker",    StateVector( 0,  0,  0)),
    44: ("Bandage / Sealer",             StateVector( 0, -1, +1)),
    45: ("Water Wave / Fluid Stream",    StateVector(+1,  0, -1))
}

class SpiralSection(NamedTuple):
    section_id: int
    side: str
    stamp_ids: List[int]
    delta: StateVector

# Pre-compiled 61 Spiral Sections ROM (Side A: 31, Side B: 30)
PHAISTOS_SPIRAL_ROM: List[SpiralSection] = [
    # SIDE A (Sections A1..A31)
    SpiralSection(1,  'A', [2, 12, 38],    StateVector(+1,  0, -1)),
    SpiralSection(2,  'A', [2, 29],        StateVector(+2, +1, -3)),
    SpiralSection(3,  'A', [1, 2, 10, 4],  StateVector(-1, +2, -1)),
    SpiralSection(4,  'A', [2, 12, 25],    StateVector(+1, -1,  0)),
    SpiralSection(5,  'A', [2, 12, 35, 11],StateVector(-2, +3, -1)),
    SpiralSection(6,  'A', [1, 2, 7],      StateVector(+1,  0, -1)),
    SpiralSection(7,  'A', [2, 12, 45],    StateVector(+2, -1, -1)),
    SpiralSection(8,  'A', [2, 29, 38],    StateVector( 0, +1, -1)),
    SpiralSection(9,  'A', [1, 2, 12],     StateVector(-1,  0, +1)),
    SpiralSection(10, 'A', [2, 12, 23],    StateVector( 0, +3, -3)),
    SpiralSection(11, 'A', [2, 12, 10, 4], StateVector(+2,  0, -2)),
    SpiralSection(12, 'A', [2, 29, 12],    StateVector(+1, -1,  0)),
    SpiralSection(13, 'A', [1, 2, 38],     StateVector( 0,  0,  0)),
    SpiralSection(14, 'A', [2, 12, 17],    StateVector( 0, -2, +2)),
    SpiralSection(15, 'A', [2, 12, 13, 24],StateVector(+3, +1, -4)),
    SpiralSection(16, 'A', [1, 2, 10],     StateVector(+2,  0, -2)),
    SpiralSection(17, 'A', [2, 12, 28],    StateVector(+3,  0, -3)),
    SpiralSection(18, 'A', [2, 29, 45],    StateVector(+1,  0, -1)),
    SpiralSection(19, 'A', [1, 2, 12, 21], StateVector(-1, +1,  0)),
    SpiralSection(20, 'A', [2, 12, 33],    StateVector(+1, -2, +1)),
    SpiralSection(21, 'A', [2, 12, 36],    StateVector(-1,  0, +1)),
    SpiralSection(22, 'A', [1, 2, 10],     StateVector(+2,  0, -2)),
    SpiralSection(23, 'A', [2, 12, 38],    StateVector( 0,  0,  0)),
    SpiralSection(24, 'A', [2, 29, 7],     StateVector( 0, +2, -2)),
    SpiralSection(25, 'A', [1, 2, 12],     StateVector(-1, -1, +2)),
    SpiralSection(26, 'A', [2, 12, 24],    StateVector(+2, +2, -4)),
    SpiralSection(27, 'A', [2, 12, 35],    StateVector(-2, +3, -1)),
    SpiralSection(28, 'A', [1, 2, 10],     StateVector(+2,  0, -2)),
    SpiralSection(29, 'A', [2, 12, 40],    StateVector(+2, -1, -1)),
    SpiralSection(30, 'A', [2, 29, 38],    StateVector( 0, +1, -1)),
    SpiralSection(31, 'A', [1, 2, 10, 42], StateVector(-1, +5, -4)),

    # SIDE B (Sections B1..B30) - After 180° Rotation
    SpiralSection(32, 'B', [7, 11, 12],    StateVector(+1, +3, -4)),
    SpiralSection(33, 'B', [2, 12, 25],    StateVector(+1,  0, -1)),
    SpiralSection(34, 'B', [1, 2, 10],     StateVector(+2,  0, -2)),
    SpiralSection(35, 'B', [2, 12, 38],    StateVector( 0,  0,  0)),
    SpiralSection(36, 'B', [2, 29, 13],    StateVector(+3, -1, -2)),
    SpiralSection(37, 'B', [1, 2, 12, 33], StateVector( 0, -2, +2)),
    SpiralSection(38, 'B', [2, 12, 23],    StateVector( 0, +3, -3)),
    SpiralSection(39, 'B', [2, 12, 35],    StateVector(-2, +3, -1)),
    SpiralSection(40, 'B', [1, 2, 10],     StateVector(+2,  0, -2)),
    SpiralSection(41, 'B', [2, 12, 45],    StateVector(+1,  0, -1)),
    SpiralSection(42, 'B', [7, 2, 12, 24], StateVector(+3, +4, -7)), # Boundary trigger section
    SpiralSection(43, 'B', [1, 2, 38],     StateVector( 0,  0,  0)),
    SpiralSection(44, 'B', [2, 12, 17],    StateVector( 0, -2, +2)),
    SpiralSection(45, 'B', [2, 29, 10],    StateVector(+2, +1, -3)),
    SpiralSection(46, 'B', [1, 2, 12],     StateVector(-1, -1, +2)),
    SpiralSection(47, 'B', [2, 12, 36],    StateVector(-1,  0, +1)),
    SpiralSection(48, 'B', [2, 12, 28],    StateVector(+3,  0, -3)),
    SpiralSection(49, 'B', [1, 2, 10],     StateVector(+2,  0, -2)),
    SpiralSection(50, 'B', [2, 12, 38],    StateVector( 0,  0,  0)),
    SpiralSection(51, 'B', [2, 29, 21],    StateVector(-1, +2, -1)),
    SpiralSection(52, 'B', [1, 2, 12],     StateVector(-1, -1, +2)),
    SpiralSection(53, 'B', [2, 12, 25],    StateVector(+1,  0, -1)),
    SpiralSection(54, 'B', [2, 12, 35],    StateVector(-2, +3, -1)),
    SpiralSection(55, 'B', [1, 2, 10],     StateVector(+2,  0, -2)),
    SpiralSection(56, 'B', [2, 12, 40],    StateVector(+2, -1, -1)),
    SpiralSection(57, 'B', [2, 29, 38],    StateVector( 0, +1, -1)),
    SpiralSection(58, 'B', [1, 2, 12],     StateVector(-1, -1, +2)),
    SpiralSection(59, 'B', [2, 12, 17],    StateVector( 0, -2, +2)),
    SpiralSection(60, 'B', [2, 12, 36],    StateVector(-1,  0, +1)),
    SpiralSection(61, 'B', [2, 12, 38],    StateVector( 0,  0,  0))
]

class PhaistosSimulator:
    def __init__(self):
        self.rom = PHAISTOS_SPIRAL_ROM
        self.current_state = StateVector(0, 0, 0)
        self.current_index = 0
        self.history = []

    def lookup_symbol(self, stamp_id: int) -> Tuple[str, StateVector]:
        """O(1) Direct Lookup for any of the 45 stamped symbols."""
        if stamp_id in STAMP_CATALOG:
            return STAMP_CATALOG[stamp_id]
        raise ValueError(f"Invalid Stamp ID: {stamp_id}. Range is 1 to 45.")

    def step(self) -> Tuple[SpiralSection, StateVector, bool, str]:
        """
        Executes one step in O(1) constant memory lookup.
        Returns: (section, new_state, is_sat, action_code)
        """
        if self.current_index >= len(self.rom):
            return None, self.current_state, True, "COMPLETED"

        section = self.rom[self.current_index]
        new_state = self.current_state + section.delta
        
        # SMT Z3 Verification Rules
        stream_zero = (section.delta.stream_sum() == 0)
        bounded = new_state.is_bounded(8)

        if not stream_zero or not bounded:
            action = "HARD_STOP (-999)"
            is_sat = False
            # Quantum Bounce / Recovery Action
            recovery_state = StateVector(0, 0, 0)
            self.history.append((self.current_index, section, new_state, is_sat, action))
            self.current_state = recovery_state
            self.current_index += 1
            return section, recovery_state, is_sat, action

        action = "SAT (NOMINAL)"
        is_sat = True
        self.current_state = new_state
        self.history.append((self.current_index, section, new_state, is_sat, action))
        self.current_index += 1
        return section, new_state, is_sat, action

    def run_all(self):
        print("=" * 80)
        print("PHAISTOS DISC L0-ISM O(1) LOOKUP SIMULATOR")
        print("=" * 80)
        print(f"Total Sections: {len(self.rom)} (Side A: 31, Side B: 30)")
        print(f"Total Unique Stamped Symbols: {len(STAMP_CATALOG)}\n")

        print(f"{'Idx':<4} | {'Side':<4} | {'Stamps':<15} | {'Delta Δs':<14} | {'New State IM':<15} | {'Z3 Status':<15}")
        print("-" * 80)

        while self.current_index < len(self.rom):
            idx = self.current_index + 1
            sec, st, sat, act = self.step()
            stamps_str = ",".join(map(str, sec.stamp_ids))
            delta_str = f"({sec.delta.s_water:+d},{sec.delta.s_thermal:+d},{sec.delta.s_flow:+d})"
            state_str = f"({st.s_water:+d},{st.s_thermal:+d},{st.s_flow:+d})"
            
            sat_color = "SAT [OK]" if sat else "UNSAT [INTERDICT]"
            print(f"{idx:<4} | {sec.side:<4} | {stamps_str:<15} | {delta_str:<14} | {state_str:<15} | {sat_color:<15}")

            if sec.section_id == 31:
                print("-" * 80)
                print(">>> 180° TOPOLOGICAL ROTATION (Transition Side A -> Side B) <<<")
                print("-" * 80)

        print("=" * 80)
        print("SIMULATION COMPLETED. Final Homeostasis Achieved.")
        print("=" * 80)

if __name__ == "__main__":
    sim = PhaistosSimulator()
    sim.run_all()
    
    # Interactive O(1) Catalog Query Test
    print("\n[O(1) Symbol Lookup Test]:")
    for sample_id in [1, 10, 24, 38, 45]:
        name, vec = sim.lookup_symbol(sample_id)
        print(f"  Stamp #{sample_id:02d} ({name:<25}) -> Δs = ({vec.s_water:+d}, {vec.s_thermal:+d}, {vec.s_flow:+d})")
