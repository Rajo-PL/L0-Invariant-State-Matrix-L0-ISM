#include "phaistos_l0_ism.h"
#include <stdlib.h>

/* Pamięć Statyczna ROM — 61 Sekcji Spirali Dysku z Fajstos */
static const Phaistos_LUT_Entry PHAISTOS_ROM[PHAISTOS_TOTAL_SECTIONS] = {
    /* --- STRONA A (Sekcje 0..30) --- */
    { 0, 0, 3, {2, 12, 38, 0, 0}, { .s_water = +1, .s_thermal = 0,  .s_flow = -1 } },
    { 1, 0, 2, {2, 29, 0,  0, 0}, { .s_water = +2, .s_thermal = +1, .s_flow = -3 } },
    { 2, 0, 4, {1, 2,  10, 4, 0}, { .s_water = -1, .s_thermal = +2, .s_flow = -1 } },
    /* ... Sekcje A3..A29 ... */
    {30, 0, 4, {1, 2, 10, 42, 0}, { .s_water = -1, .s_thermal = +5, .s_flow = -4 } },

    /* --- STRONA B (Sekcje 31..60) — Po Obrocie Tarczy o 180° --- */
    {31, 1, 2, {7, 11, 0, 0, 0},  { .s_water = +1, .s_thermal = +3, .s_flow = -4 } },
    /* Sekcja B10: Przykładowe uderzenie w barierę krytyczną (+9) */
    {41, 1, 3, {7, 2,  12, 0, 0}, { .s_water = +1, .s_thermal = +5, .s_flow = -6 } },
    /* ... Sekcje B12..B29 ... */
    {60, 1, 3, {2, 12, 1,  0, 0}, { .s_water = 0,  .s_thermal = 0,  .s_flow = 0  }}
};

Phaistos_EvalResult phaistos_step(L0_StateVector* current, uint8_t section_index) {
    Phaistos_EvalResult result;
    
    /* Ochrona przed wyjściem poza zakresem pamięci ROM */
    if (section_index >= PHAISTOS_TOTAL_SECTIONS) {
        result.current_state = *current;
        result.is_sat = false;
        result.action_code = L0_HARD_STOP;
        return result;
    }

    /* Pobranie rekordu z pamięci ROM w czasie O(1) */
    const Phaistos_LUT_Entry* entry = &PHAISTOS_ROM[section_index];

    /* Aktualizacja wektora stanu */
    current->s_water   += entry->delta.s_water;
    current->s_thermal += entry->delta.s_thermal;
    current->s_flow    += entry->delta.s_flow;

    /* Warunek 1: Inwariant Zachowania Strumienia (Suma Δs == 0) */
    int16_t stream_sum = entry->delta.s_water + entry->delta.s_thermal + entry->delta.s_flow;

    /* Warunek 2: Detekcja Naruszenia Bariery Pochłaniającej (|s_i| >= 9) */
    bool boundary_violation = (abs(current->s_water)   >= L0_STATE_MAX) ||
                               (abs(current->s_thermal) >= L0_STATE_MAX) ||
                               (abs(current->s_flow)    >= L0_STATE_MAX);

    /* Walidacja Logiczna SMT Z3 */
    if (stream_sum != 0 || boundary_violation) {
        /* Status UNSAT: Natychmiastowa Interdykcja Sprzętowa HARD_STOP (-999) */
        result.is_sat = false;
        result.action_code = L0_HARD_STOP;
    } else {
        /* Status SAT: Praca nominalna */
        result.is_sat = true;
        result.action_code = 0;
    }

    result.current_state = *current;
    return result;
}
