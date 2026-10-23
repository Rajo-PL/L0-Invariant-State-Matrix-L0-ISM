# Definicja Invariant Byte (IB) dla pętli mCDU: [Ciśnienie, Temperatura, Przepływ]
# Dozwolone stany w przedziale [-9, +9]

class InvariantByteEngine:
    def __init__(self):
        # Twarda matryca decyzyjna (Lookup Table) zamiast sieci neuronowej
        # Klucz: Invariant Byte -> Wartość: Fizyczna akcja siłownika (np. mm położenia zaworu)
        self.ib_lookup_table = {
            (0, 0, 0): "STAN_IDEALNY_STABILNY",
            (-3, 0, 6): "KOREKTA_POŚREDNIA_A",  # Twój przykład
            (9, 0, 9): "ALARM_KRYTYCZNY_BARR_9"  # Natychmiastowe odcięcie (Absorbing Barrier)
        }

    def evaluate_state(self, pressure: int, temp: int, flow: int) -> str:
        # 1. Rygorystyczna walidacja zakresu (Zablokowanie "nieskończoności")
        for val in [pressure, temp, flow]:
            if not (-9 <= val <= 9):
                raise ValueError("Naruszono twardą granicę osi [-9, +9]! Inicjuję awaryjne Z3-Stop.")

        # 2. Złożenie w Invariant Byte (Bajt Niezmienniczy)
        current_ib = (pressure, temp, flow)

        # 3. Natychmiastowe mapowanie tabelowe (Brak macierzy, brak opóźnień)
        action = self.ib_lookup_table.get(current_ib, "KOREKTA_STANDARDOWA_DYNAMIKI")
        
        return action

# --- Test działania silnika ---
engine = InvariantByteEngine()

# Test Twojego bytu [-3, 0, 6]
stan = engine.evaluate_state(-3, 0, 6)
print(f"Przetworzony Invariant Byte [-3, 0, 6] -> Akcja sterownika: {stan}")
