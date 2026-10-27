/**
 * @file phaistos_l0_ism.h
 * @brief Layer 0 Invariant State Matrix (L0-ISM) Firmware dla Dysku z Fajstos
 * @details Obrotowa tablica Look-Up Table (LUT) w czasie O(1) dla 61 sekcji
 *          spiralnych (Strona A: 31, Strona B: 30) i 45 stempli cyfrowych.
 */

#ifndef PHAISTOS_L0_ISM_H
#define PHAISTOS_L0_ISM_H

#include <stdint.h>
#include <stdbool.h>

#define PHAISTOS_SIDE_A_SECTIONS 31
#define PHAISTOS_SIDE_B_SECTIONS 30
#define PHAISTOS_TOTAL_SECTIONS  (PHAISTOS_SIDE_A_SECTIONS + PHAISTOS_SIDE_B_SECTIONS)
#define PHAISTOS_UNIQUE_STAMPS   45

#define L0_STATE_MIN      -9
#define L0_STATE_MAX       9
#define L0_HARD_STOP    -999

/* Trójwymiarowy Wektor Stanu Zasobów (IM) */
typedef struct {
    int8_t s_water;   /* Rejestr zasobu wody/ciśnienia [-9, +9] */
    int8_t s_thermal; /* Rejestr obciążenia cieplnego/energii [-9, +9] */
    int8_t s_flow;    /* Rejestr przepływu/alokacji [-9, +9] */
} L0_StateVector;

/* Rejestr pojedynczej sekcji spirali (Komórka LUT) */
typedef struct {
    uint8_t section_id;      /* Numer sekcji (0..60) */
    uint8_t side;            /* 0 = Strona A, 1 = Strona B */
    uint8_t stamp_count;     /* Liczba odciśniętych stempli w sekcji */
    uint8_t stamp_ids[5];    /* Identyfikatory stempli (1..45) */
    L0_StateVector delta;    /* Skwantowany wektor zmiany stanu Δs */
} Phaistos_LUT_Entry;

/* Wynik ewaluacji cyklu magistrali */
typedef struct {
    L0_StateVector current_state;
    bool is_sat;             /* Status SMT Z3: true = SAT, false = UNSAT */
    int16_t action_code;     /* Kod akcji sprzętowej (0 = OK, -999 = HARD_STOP) */
} Phaistos_EvalResult;

/* Funkcja wykonywania kroku odczytu w czasie O(1) */
Phaistos_EvalResult phaistos_step(L0_StateVector* current, uint8_t section_index);

#endif /* PHAISTOS_L0_ISM_H */
