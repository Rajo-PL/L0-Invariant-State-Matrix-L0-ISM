/**
 * @file wow_governor.h
 * @brief The Wow! Signal Architecture: Hardware-Level LLM Interdiction & Venturi Governor Engine
 * @version 2026.1 (WOW-L0-SMT-2026)
 * @author Rajmund Olszewski (Data Physics Laboratory / L0-ISM Research Group)
 * @details ISO C99 compliant, zero-heap, deterministic runtime header for embedded controllers,
 *          FPGAs, and OT PLCs. Filters stochastic LLM hallucinations via Venturi compression,
 *          thermodynamic invariants, and time-bound OTP windows.
 */

#ifndef WOW_GOVERNOR_H
#define WOW_GOVERNOR_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>
#include <math.h>

/* =========================================================================
 * HARDWARE & SYSTEM CONSTANTS
 * ========================================================================= */

#define WOW_L0_STATE_MIN          ((int8_t)-9)
#define WOW_L0_FULCRUM            ((int8_t)0)
#define WOW_L0_STATE_MAX          ((int8_t)9)
#define WOW_HARD_STOP_VAL         ((int16_t)-999)

#define WOW_MAX_OTP_WINDOW_MS     ((uint32_t)72000) /* 72-second Wow! Signal beam window */
#define WOW_DEFAULT_O2_BUDGET     ((uint16_t)100)   /* Initial oxygen budget units */
#define WOW_HYPOXIA_PENALTY       ((uint16_t)15)    /* O2 penalty per hallucination / UNSAT */

/* =========================================================================
 * TYPE DEFINITIONS
 * ========================================================================= */

typedef int8_t l0_state_t;

typedef enum {
    WOW_STATUS_SAT       = 0,  /* Verified physically grounded trajectory */
    WOW_STATUS_UNSAT     = 1,  /* Physics / invariant breach (filtered) */
    WOW_STATUS_HARD_STOP = 2   /* Absorbing boundary hit / Oxygen exhaustion */
} wow_status_t;

/**
 * @brief Venturi Nozzle Configuration Parameters
 */
typedef struct {
    double scale_weight;
    double offset;
    double gain;
} wow_venturi_config_t;

/**
 * @brief Raw Stochastic Output from LLM Layer 7
 */
typedef struct {
    double raw_p_power;     /* Continuous estimated power load */
    double raw_t_ambient;   /* Continuous estimated ambient temp */
    double raw_q_cooling;   /* Continuous estimated cooling capacity */
    uint32_t timestamp_ms;  /* Generation timestamp (ms) */
} wow_llm_output_t;

/**
 * @brief Quantized L0 State Vector
 */
typedef struct {
    l0_state_t s_P;         /* Power state [-9, +9] */
    l0_state_t s_T;         /* Temperature state [-9, +9] */
    l0_state_t s_Q;         /* Cooling capacity state [-9, +9] */
    uint32_t timestamp_ms;
} wow_vector_t;

/**
 * @brief Governor System Runtime State
 */
typedef struct {
    uint16_t oxygen_budget;
    uint32_t sat_count;
    uint32_t unsat_count;
    bool hard_stop_active;
    l0_state_t last_output_state;
} wow_governor_t;

/* =========================================================================
 * VENTURI COMPRESSION NOZZLE (LAYER 7 -> LAYER 0)
 * ========================================================================= */

/**
 * @brief Venturi Quantization Function (Phi_v)
 * @details Compresses continuous neural float embeddings into discrete L0 interval [-9, +9].
 */
static inline l0_state_t wow_venturi_compress(double val, const wow_venturi_config_t *cfg) {
    if (!cfg) return WOW_L0_FULCRUM;
    
    double scaled = (val - cfg->offset) * cfg->scale_weight * cfg->gain;
    double rounded = (scaled >= 0.0) ? floor(scaled + 0.5) : ceil(scaled - 0.5);
    int32_t state = (int32_t)rounded;

    if (state > WOW_L0_STATE_MAX) return WOW_L0_STATE_MAX;
    if (state < WOW_L0_STATE_MIN) return WOW_L0_STATE_MIN;
    return (l0_state_t)state;
}

/**
 * @brief Compress full LLM neural output into quantized L0 vector.
 */
static inline wow_vector_t wow_venturi_compress_output(const wow_llm_output_t *llm, const wow_venturi_config_t *cfg) {
    wow_vector_t vec;
    vec.s_P = wow_venturi_compress(llm->raw_p_power, cfg);
    vec.s_T = wow_venturi_compress(llm->raw_t_ambient, cfg);
    vec.s_Q = wow_venturi_compress(llm->raw_q_cooling, cfg);
    vec.timestamp_ms = llm->timestamp_ms;
    return vec;
}

/* =========================================================================
 * INVARIANT & SMT SOLVER VERIFICATION LOGIC
 * ========================================================================= */

/**
 * @brief Thermodynamic Invariant Check: P + T - Q <= 0
 */
static inline bool wow_check_thermodynamic_invariant(const wow_vector_t *vec) {
    int16_t energy_balance = (int16_t)vec->s_P + (int16_t)vec->s_T - (int16_t)vec->s_Q;
    return (energy_balance <= 0);
}

/**
 * @brief Temporal OTP Window Check (72-second maximum beam window)
 */
static inline bool wow_check_otp_window(uint32_t gen_time_ms, uint32_t curr_time_ms) {
    if (curr_time_ms < gen_time_ms) return false;
    return ((curr_time_ms - gen_time_ms) <= WOW_MAX_OTP_WINDOW_MS);
}

/* =========================================================================
 * GOVERNOR CORE CONTROL STEP
 * ========================================================================= */

/**
 * @brief Initialize Governor Engine State
 */
static inline void wow_governor_init(wow_governor_t *gov) {
    if (!gov) return;
    gov->oxygen_budget = WOW_DEFAULT_O2_BUDGET;
    gov->sat_count = 0;
    gov->unsat_count = 0;
    gov->hard_stop_active = false;
    gov->last_output_state = WOW_L0_FULCRUM;
}

/**
 * @brief Execute Deterministic L0-ISM Interdiction Step (O(1) execution)
 */
static inline wow_status_t wow_governor_step(
    wow_governor_t *gov,
    const wow_llm_output_t *llm_input,
    const wow_venturi_config_t *cfg,
    uint32_t current_time_ms,
    l0_state_t *out_actuator_state
) {
    if (!gov || !llm_input || !cfg || !out_actuator_state) {
        if (out_actuator_state) *out_actuator_state = (l0_state_t)WOW_HARD_STOP_VAL;
        return WOW_STATUS_HARD_STOP;
    }

    /* Check if system is already locked in HARD_STOP */
    if (gov->hard_stop_active || gov->oxygen_budget == 0) {
        gov->hard_stop_active = true;
        *out_actuator_state = (l0_state_t)WOW_HARD_STOP_VAL;
        return WOW_STATUS_HARD_STOP;
    }

    /* 1. Venturi Quantization Nozzle */
    wow_vector_t vec = wow_venturi_compress_output(llm_input, cfg);

    /* 2. Check Absorbing Boundary Interdiction (|s_i| == 9) */
    if (vec.s_P == WOW_L0_STATE_MAX || vec.s_P == WOW_L0_STATE_MIN ||
        vec.s_T == WOW_L0_STATE_MAX || vec.s_T == WOW_L0_STATE_MIN ||
        vec.s_Q == WOW_L0_STATE_MAX || vec.s_Q == WOW_L0_STATE_MIN) {
        
        gov->hard_stop_active = true;
        gov->unsat_count++;
        *out_actuator_state = (l0_state_t)WOW_HARD_STOP_VAL;
        return WOW_STATUS_HARD_STOP;
    }

    /* 3. Invariant Checks (Thermodynamics & Time-Bound OTP) */
    bool thermo_sat = wow_check_thermodynamic_invariant(&vec);
    bool otp_sat    = wow_check_otp_window(vec.timestamp_ms, current_time_ms);

    if (thermo_sat && otp_sat) {
        /* SAT: Grounded Signal Passed */
        gov->sat_count++;
        gov->last_output_state = vec.s_P;
        *out_actuator_state = vec.s_P;
        return WOW_STATUS_SAT;
    } else {
        /* UNSAT: Neural Hallucination / Physics Breach */
        gov->unsat_count++;
        
        /* Apply Digital Hypoxia (Oxygen Penalty) */
        if (gov->oxygen_budget > WOW_HYPOXIA_PENALTY) {
            gov->oxygen_budget -= WOW_HYPOXIA_PENALTY;
        } else {
            gov->oxygen_budget = 0;
            gov->hard_stop_active = true;
            *out_actuator_state = (l0_state_t)WOW_HARD_STOP_VAL;
            return WOW_STATUS_HARD_STOP;
        }

        /* Hold previous safe state or return zero (Fulcrum) */
        *out_actuator_state = gov->last_output_state;
        return WOW_STATUS_UNSAT;
    }
}

#ifdef __cplusplus
}
#endif

#endif /* WOW_GOVERNOR_H */
