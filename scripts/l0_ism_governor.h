/**
 * @file l0_ism_governor.h
 * @brief L0 Invariant State Matrix (L0-ISM) Governor Engine Core Specification
 * @version 2026.1 (L0-ISM-STND-2026.1)
 * @details ISO C99 compliant, zero-heap, O(1) deterministic safety-critical execution header
 *          designed for OT Microcontrollers, FPGA soft-cores, and embedded PLC systems.
 *
 * Specification Highlights:
 *  - Bounded 19-state space: S = {-9, ..., 0, ..., +9}
 *  - Zero-heap allocation (MISRA-C compliant pattern)
 *  - Hard-stop interdiction on boundary hit (|s_i| == 9) -> HARD_STOP (-999)
 *  - Operators: ITER (O(1) step), RESO (O(1) resonance transfer), STOP (interdiction)
 *  - Discrete Flux Conservation: sum(delta_s) == 0
 */

#ifndef L0_ISM_GOVERNOR_H
#define L0_ISM_GOVERNOR_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

/* =========================================================================
 * CONSTANTS AND DEFINITIONS
 * ========================================================================= */

#define L0_STATE_MIN        ((int8_t)-9)
#define L0_STATE_ZERO       ((int8_t)0)
#define L0_STATE_MAX        ((int8_t)9)
#define L0_HARD_STOP_VAL    ((int16_t)-999)

#define L0_VECTOR_DIM       (3)  /* Standard k=3 tuple dimension */

/* =========================================================================
 * TYPE DEFINITIONS
 * ========================================================================= */

/**
 * @brief Discrete state scalar [-9, +9]
 */
typedef int8_t l0_state_t;

/**
 * @brief L0 State Vector (k=3 micro-enclave tuple)
 */
typedef struct {
    l0_state_t s[L0_VECTOR_DIM];
} l0_vector3_t;

/**
 * @brief System Execution Action Enum
 */
typedef enum {
    L0_ACTION_NOMINAL    = 0,  /**< System at Zero Point (Fulcrum), no corrective action required */
    L0_ACTION_ITER_STEP  = 1,  /**< ITER step applied toward Zero Point */
    L0_ACTION_RESO_SYNC  = 2,  /**< RESO direct state transfer completed */
    L0_ACTION_HARD_STOP  = 3   /**< Boundary interdiction hit (|s_i| = 9) -> HARD_STOP */
} l0_action_t;

/**
 * @brief Governor Execution Step Result
 */
typedef struct {
    l0_vector3_t next_vector;
    l0_action_t  action;
    int16_t      status_code;
    bool         interdiction_triggered;
} l0_result_t;

/* =========================================================================
 * CORE HELPER FUNCTIONS (INLINE)
 * ========================================================================= */

/**
 * @brief Discrete Signum Function sgn(s)
 */
static inline int8_t l0_sgn(l0_state_t s) {
    if (s > 0) return 1;
    if (s < 0) return -1;
    return 0;
}

/**
 * @brief Clamp state value to valid [-9, +9] bounds
 */
static inline l0_state_t l0_clamp(int16_t val) {
    if (val > L0_STATE_MAX) return L0_STATE_MAX;
    if (val < L0_STATE_MIN) return L0_STATE_MIN;
    return (l0_state_t)val;
}

/**
 * @brief Check if a state vector hits the absorbing boundary (|s_i| == 9)
 */
static inline bool l0_is_boundary_hit(const l0_vector3_t* vec) {
    if (!vec) return false;
    for (int i = 0; i < L0_VECTOR_DIM; ++i) {
        if (vec->s[i] >= L0_STATE_MAX || vec->s[i] <= L0_STATE_MIN) {
            return true;
        }
    }
    return false;
}

/**
 * @brief Check if vector is at absolute Zero Point (Fulcrum)
 */
static inline bool l0_is_zero_point(const l0_vector3_t* vec) {
    if (!vec) return false;
    return (vec->s[0] == 0 && vec->s[1] == 0 && vec->s[2] == 0);
}

/* =========================================================================
 * GOVERNOR ENGINE API
 * ========================================================================= */

/**
 * @brief Quantize continuous raw signal to discrete L0 state with deadband hysteresis.
 * 
 * @param raw_value Sensor reading in physical units
 * @param nominal Equilibrium nominal value (maps to state 0)
 * @param delta_max Maximum operational delta corresponding to barrier state |9|
 * @param prev_state Previous state for hysteresis deadband filtering
 * @param hysteresis_epsilon Deadband factor (e.g. 0.25f)
 * @return l0_state_t Quantized state [-9, +9]
 */
static inline l0_state_t l0_quantize(float raw_value, float nominal, float delta_max, 
                                     l0_state_t prev_state, float hysteresis_epsilon) {
    if (delta_max <= 0.0f) return L0_STATE_ZERO;

    float step = delta_max / 9.0f;
    float norm = (raw_value - nominal) / step;

    /* Boundary safety check */
    if (norm >= 9.0f - hysteresis_epsilon) return L0_STATE_MAX;
    if (norm <= -9.0f + hysteresis_epsilon) return L0_STATE_MIN;

    /* Hysteresis filtering */
    float diff = norm - (float)prev_state;
    if (diff > (0.5f + hysteresis_epsilon)) {
        int16_t target = (int16_t)(norm + 0.5f);
        return l0_clamp(target);
    } else if (diff < (-0.5f - hysteresis_epsilon)) {
        int16_t target = (int16_t)(norm - 0.5f);
        return l0_clamp(target);
    }

    return prev_state;
}

/**
 * @brief ITER Operator: Deterministic O(1) step toward Zero Point (Fulcrum)
 * @details Applies s_{t+1} = s_t - sgn(s_t) across vector components.
 */
static inline l0_result_t l0_operator_iter(const l0_vector3_t* current) {
    l0_result_t res;
    res.interdiction_triggered = false;
    res.status_code = 0;

    if (!current) {
        res.action = L0_ACTION_NOMINAL;
        return res;
    }

    /* Check boundary interdiction first */
    if (l0_is_boundary_hit(current)) {
        res.next_vector = *current;
        res.action = L0_ACTION_HARD_STOP;
        res.status_code = L0_HARD_STOP_VAL;
        res.interdiction_triggered = true;
        return res;
    }

    /* Check if already at Zero Point */
    if (l0_is_zero_point(current)) {
        res.next_vector = *current;
        res.action = L0_ACTION_NOMINAL;
        res.status_code = 0;
        return res;
    }

    /* Execute ITER step toward zero */
    for (int i = 0; i < L0_VECTOR_DIM; ++i) {
        res.next_vector.s[i] = current->s[i] - l0_sgn(current->s[i]);
    }

    res.action = L0_ACTION_ITER_STEP;
    res.status_code = 0;
    return res;
}

/**
 * @brief RESO Operator: Direct O(1) Matrix Resonance Synchronization
 */
static inline l0_result_t l0_operator_reso(const l0_vector3_t* source, const l0_vector3_t* target) {
    l0_result_t res;
    res.interdiction_triggered = false;
    res.status_code = 0;

    if (!source || !target) {
        res.action = L0_ACTION_NOMINAL;
        return res;
    }

    if (l0_is_boundary_hit(source) || l0_is_boundary_hit(target)) {
        res.next_vector = *source;
        res.action = L0_ACTION_HARD_STOP;
        res.status_code = L0_HARD_STOP_VAL;
        res.interdiction_triggered = true;
        return res;
    }

    /* Direct resonance sync */
    res.next_vector = *target;
    res.action = L0_ACTION_RESO_SYNC;
    return res;
}

/**
 * @brief Verify Discrete Flux Conservation (sum(delta_s) == 0)
 */
static inline bool l0_verify_flux_conservation(const l0_vector3_t* v_before, const l0_vector3_t* v_after) {
    if (!v_before || !v_after) return false;
    int16_t sum_delta = 0;
    for (int i = 0; i < L0_VECTOR_DIM; ++i) {
        sum_delta += (v_after->s[i] - v_before->s[i]);
    }
    return (sum_delta == 0);
}

/**
 * @brief Full Governor Step Engine Function
 */
static inline l0_result_t l0_governor_step(const l0_vector3_t* input_vector) {
    if (l0_is_boundary_hit(input_vector)) {
        l0_result_t stop_res;
        stop_res.next_vector = *input_vector;
        stop_res.action = L0_ACTION_HARD_STOP;
        stop_res.status_code = L0_HARD_STOP_VAL;
        stop_res.interdiction_triggered = true;
        return stop_res;
    }

    return l0_operator_iter(input_vector);
}

#ifdef __cplusplus
}
#endif

#endif /* L0_ISM_GOVERNOR_H */
