# Aparat Matematyczny Architektury "Invariant Bytes" (IB)
**Wersja:** 1.0 (Standard Zamknięty / Wdrożeniowy)
**Zastosowanie:** Infrastruktura Krytyczna (L0/OT), Systemy Deterministyczne, Edge Computing

---

## 1. Przestrzeń Stanów i Oś Dyskretna ($\mathcal{S}$)
Odrzucamy ciągłą przestrzeń liczb rzeczywistych ($\mathbb{R}$) stosowaną w klasycznej automatyce (PID) i modelach stochastycznych (AI). Podstawą systemu jest zamknięta, skwantyzowana przestrzeń stanów $\mathcal{S}$ oparta na osi symetrycznej:

$$ \mathcal{S} = \{-9, -8, \dots, -1, 0, 1, \dots, 8, 9\} $$

*   **Punkt Zerowy ($0$):** Definiuje absolutny stan równowagi (termodynamicznej, operacyjnej, logicznej).
*   **Wektory Odchyleń ($\pm 1$ do $\pm 8$):** Określają siłę i zwrot wytrącenia z równowagi.
*   **Bariery Pochłaniające ($\pm 9$):** Twarde granice awaryjne. Osiągnięcie tego stanu wymusza interdykcję bezwarunkową (Hard Stop).

## 2. Wielowymiarowa Krotka Inwariantna ($\mathcal{IB}$)
Stan fizyczny węzła nie jest opisywany przez macierze prawdopodobieństw, lecz przez krotkę (wektor) o stałym wymiarze $k$:

$$ \mathcal{IB} = (s_1, s_2, \dots, s_k) \in \mathcal{S}^k $$

Całkowita, skończona przestrzeń stanów dla danego węzła wynosi dokładnie $19^k$. (np. dla $k=3$, przestrzeń wynosi $19^3 = 6859$ unikalnych wektorów).

## 3. Deterministyczna Matryca Przejść (Lookup Function)
Zastępujemy mnożenie macierzy wag ($\mathbf{y} = \mathbf{W}\mathbf{x} + \mathbf{b}$) dyskretną, stałoczasową funkcją odwzorowania $\mathcal{F}$. Dla każdego wektora $\mathcal{IB}$ istnieje dokładnie jedno zdefiniowane przypisanie w zbiorze akcji fizycznych $\mathcal{A}$:

$$ \mathcal{F}: \mathcal{S}^k \longrightarrow \mathcal{A} $$

Złożoność obliczeniowa wyznaczenia akcji wynosi zawsze $O(1)$. 

## 4. Rygory Inżynieryjne i Ulepszenia Wykonawcze

### 4.1. Kaskadowanie i Hierarchia (Redukcja $19^k$)
Aby zapobiec eksplozji kombinatorycznej w złożonych systemach obiektowych (np. $k=10$, co daje $>6 \times 10^{12}$ stanów), wprowadzamy operator złożenia (drzewo decyzyjne). Wektor nadrzędny $\mathcal{IB}_{master}$ przyjmuje jako swoje współrzędne wyniki ($a \in \mathcal{A}$) z wektorów podrzędnych (skalowanych z powrotem do przestrzeni $\mathcal{S}$):

$$ \mathcal{IB}_{master} = \big( \mathcal{F}_{1}(\mathcal{IB}_{node1}), \mathcal{F}_{2}(\mathcal{IB}_{node2}), \dots \big) $$

Dzięki temu system dzielony jest na małe, audytowalne segmenty (np. $k \le 4$), chroniąc zasoby pamięci mikrokontrolera.

### 4.2. Wektor Gradientu i Dynamika Czasu ($\Delta t$)
Aby odróżnić naturalne opory instalacji od stanów awaryjnych (np. powolny spadek ciśnienia vs. pęknięcie rury), jeden z wymiarów krotki zostaje zarezerwowany dla skwantyzowanej pochodnej stanu względem czasu. Jeśli $x(t)$ to wartość odczytu w czasie $t$:

$$ s_{\Delta} = \mathcal{Q} \left( \frac{x(t) - x(t - \Delta t)}{\Delta t} \right) \in \mathcal{S} $$

Gdzie $\mathcal{Q}$ to funkcja kwantyzująca gradient do przestrzeni $[-9, 9]$. Wektor przyjmuje postać: $\mathcal{IB} = (s_{ciśnienie}, s_{\Delta ciśnienia}, \dots)$.

### 4.3. Fizyczna Histereza Wejściowa (Deadband Filter)
Aby zapobiec zjawisku "trzepotania" (flapping) zaworów wywołanemu szumem sensorycznym, wejście do systemu IB jest chronione funkcją histerezy $\mathcal{H}$. Przejście z pozycji $s_i$ na $s_{i+1}$ wymaga przekroczenia wyższego progu fizycznego progu aktywacji ($\tau_{up}$) niż powrót na $s_i$ ($\tau_{down}$):

$$ s_{i}^{(t)} = \begin{cases} s_{i}^{(t-1)} + 1, & \text{jeśli } x(t) > \tau_{up} \\ s_{i}^{(t-1)} - 1, & \text{jeśli } x(t) < \tau_{down} \\ s_{i}^{(t-1)}, & \text{w przeciwnym wypadku} \end{cases} $$

## 5. Aksjomat Bezpieczeństwa i Weryfikacja Formalna (Z3)
Podstawą bezpieczeństwa architektury IB jest zdolność do matematycznego dowodu jej poprawności (Formal Verification). Silnik wykonawczy gwarantuje bezwarunkowe zachowanie poniższego aksjomatu:

$$ \forall s_i \in \mathcal{IB}, \quad -9 \le s_i \le 9 $$

Jeśli warunek ten zostanie naruszony przed wejściem do matrycy przejść lub w jej wyniku (przekroczenie przestrzeni $\mathcal{S}$), system inicjuje procedurę:

$$ \text{if } \exists s_i \notin \mathcal{S} \implies \text{Action} = \text{HARD\_STOP} $$