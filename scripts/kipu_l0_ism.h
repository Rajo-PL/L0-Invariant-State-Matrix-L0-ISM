/**
 * @file kipu_l0_ism.h
 * @brief Layer 0 Invariant State Matrix (L0-ISM) Firmware dla Inkańskiego Kipu
 * @details Obsługa 3D Data Bus: magistrala główna, sznury wiszące (pendants),
 *          typ i skrętność węzłów (S/Z-twist) oraz weryfikacja SMT Z3 w czasie O(1).
 */

#ifndef KIPU_L0_ISM_H
#define KIPU_L0_ISM_H

#include <stdint.h>
#include <stdbool.h>

#define L0_STATE_MIN      -9
#define L0_STATE_MAX       9
#define L0_HARD_STOP    -999

#define MAX_PENDANTS_PER_BUS  32
#define MAX_KNOTS_PER_CORD     8

/* Identyfikatory domen surowcowych (Kolory sznurów) */
typedef enum {
    KIPU_COLOR_RED   = 0, /* Woda / Nawadnianie / Krew */
    KIPU_COLOR_BROWN = 1, /* Ziemia / Uprawy taro i kukurydzy */
    KIPU_COLOR_WHITE = 2, /* Srebro / Rezerwy terytorialne */
    KIPU_COLOR_BLACK = 3  /* Czas / Takt cyklu kalendarzowego */
} Kipu_ColorDomain;

/* Skrętność włókien (Parzystość / Kierunek strumienia) */
typedef enum {
    KIPU_TWIST_Z = 0, /* Z-twist: Zasilanie / Dodatnie odchylenie (+1) */
    KIPU_TWIST_S = 1  /* S-twist: Drenaż / Ujemne odchylenie (-1) */
} Kipu_TwistType;

/* Typy węzłów inkaskich */
typedef enum {
    KNOT_TYPE_SINGLE       = 1, /* Węzeł prosty (Dziesiątki / Setki) */
    KNOT_TYPE_LONG         = 2, /* Węzeł długi (Jedności: 2..9 pętli) */
    KNOT_TYPE_FIGURE_EIGHT = 3  /* Ósemka (Wartość jednostkowa 1) */
} Kipu_KnotType;

/* Pozycja wysokościowa węzła na sznurze */
typedef enum {
    POS_UNITS    = 0, /* Rząd jedności (Bottom) */
    POS_TENS     = 1, /* Rząd dziesiątek (Middle) */
    POS_HUNDREDS = 2  /* Rząd setek (Top) */
} Kipu_KnotPosition;

/* Struktura pojedynczego węzła */
typedef struct {
    Kipu_KnotType type;
    Kipu_KnotPosition position;
    uint8_t value; /* Wartość skwantowana (1..9) */
} Kipu_Knot;

/* Rejestr sznura wiszącego (Pendant Cord) */
typedef struct {
    uint8_t cord_id;
    Kipu_ColorDomain domain;
    Kipu_TwistType twist;
    uint8_t knot_count;
    Kipu_Knot knots[MAX_KNOTS_PER_CORD];
} Kipu_PendantCord;

/* Trójwymiarowy Wektor Stanu Kipu (IM) */
typedef struct {
    int8_t s_domain;    /* Rejestr wybranej domeny [-9, +9] */
    int8_t s_magnitude; /* Rejestr natężenia/wielkości zasobu [-9, +9] */
    int8_t s_parity;    /* Rejestr znaku strumienia [-9, +9] */
} Kipu_StateVector;

/* Wynik ewaluacji magistrali Kipu */
typedef struct {
    Kipu_StateVector state;
    bool is_sat;          /* Status Z3: true = SAT, false = UNSAT */
    int16_t action_code;  /* Kod akcji (0 = OK, -999 = HARD_STOP) */
} Kipu_EvalResult;

/* Funkcje interfejsu C99 */
Kipu_EvalResult kipu_evaluate_cord(const Kipu_PendantCord* cord, Kipu_StateVector current_state);
Kipu_EvalResult kipu_evaluate_bus(const Kipu_PendantCord bus[], uint8_t cord_count);

#endif /* KIPU_L0_ISM_H */
