#include "kipu_l0_ism.h"
#include <stdlib.h>

/**
 * @brief Ewaluacja pojedynczego sznura wiszącego w czasie O(1)
 */
Kipu_EvalResult kipu_evaluate_cord(const Kipu_PendantCord* cord, Kipu_StateVector current_state) {
    Kipu_EvalResult result;
    int16_t raw_value = 0;

    /* 1. Odczyt wysokościowy węzłów (Posicional Decoding) */
    for (uint8_t i = 0; i < cord->knot_count; i++) {
        const Kipu_Knot* knot = &cord->knots[i];
        int16_t multiplier = 1;
        
        if (knot->position == POS_TENS) {
            multiplier = 10;
        } else if (knot->position == POS_HUNDREDS) {
            multiplier = 100;
        }
        
        raw_value += (knot->value * multiplier);
    }

    /* 2. Kwantyzacja wielkości na dyskretną przestrzeń [-9, +9] */
    int8_t delta_mag = (int8_t)(raw_value % 9);
    if (delta_mag == 0 && raw_value > 0) delta_mag = 9;

    /* 3. Weryfikacja znaku przepływu na podstawie skrętności włókien (S/Z twist) */
    int8_t sign = (cord->twist == KIPU_TWIST_Z) ? +1 : -1;
    delta_mag *= sign;

    /* 4. Aktualizacja rejestrów wektora stanu */
    current_state.s_domain    = (int8_t)cord->domain;
    current_state.s_magnitude += delta_mag;
    current_state.s_parity    += sign;

    /* 5. Inwariant Zachowania i Detekcja Przekroczenia Bariery Absorbowania (|s_i| >= 9) */
    bool boundary_violated = (abs(current_state.s_magnitude) >= L0_STATE_MAX) ||
                             (abs(current_state.s_parity)    >= L0_STATE_MAX);

    if (boundary_violated) {
        /* Status UNSAT: Natychmiastowa Interdykcja HARD_STOP (-999) */
        result.is_sat = false;
        result.action_code = L0_HARD_STOP;
    } else {
        /* Status SAT: Praca bezpieczna */
        result.is_sat = true;
        result.action_code = 0;
    }

    result.state = current_state;
    return result;
}

/**
 * @brief Sekwencyjna ewaluacja całej magistrali Kipu (Bus Array)
 */
Kipu_EvalResult kipu_evaluate_bus(const Kipu_PendantCord bus[], uint8_t cord_count) {
    Kipu_StateVector state = { .s_domain = 0, .s_magnitude = 0, .s_parity = 0 };
    Kipu_EvalResult res = { .state = state, .is_sat = true, .action_code = 0 };

    for (uint8_t i = 0; i < cord_count; i++) {
        res = kipu_evaluate_cord(&bus[i], res.state);
        
        /* Natychmiastowe zamrożenie magistrali w przypadku statusu UNSAT */
        if (!res.is_sat) {
            res.action_code = L0_HARD_STOP;
            break;
        }
    }

    return res;
}
