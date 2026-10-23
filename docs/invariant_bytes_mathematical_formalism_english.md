# The Mathematical Formalism of Invariant Bytes: Bounded State Spaces and Deterministic L0 Control

This document establishes the formal mathematical framework for the **Invariant Byte (IB)** architecture. It defines the foundational rules for replacing probabilistic, continuous-space control models with a strictly bounded, discrete positional system designed for critical operational technology (L0/OT).

---

### 1. The Bounded Discrete State Space ($\mathcal{S}$)
To eliminate floating-point arithmetic errors and stochastic drift, the continuous domain ($\mathbb{R}$) is entirely rejected. The foundation is a closed, symmetric discrete space based on the positional decimal axis:

$$
\mathcal{S} = \{-9, -8, -7, -6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9\}
$$

* **The Absolute Zero ($0$):** Represents perfect physical, thermodynamic, or operational equilibrium (the fulcrum of the mechanical balance scale).
* **Directional Vectors ($\pm 1$ to $\pm 8$):** Represent the magnitude and direction of physical deviation from the optimal state (e.g., negative values for pressure drop, positive for thermal excess).
* **Absorbing Boundaries ($\pm 9$):** Hard invariant limits representing critical structural failure.

---

### 2. The Invariant Byte Tuple ($\mathcal{IB}$)
A multi-dimensional physical state is not processed via continuous vector spaces. It is defined as a finite tuple of $k$ independent variables, where each coordinate strictly belongs to $\mathcal{S}$:

$$
\mathcal{IB} = (s_1, s_2, \dots, s_k) \in \mathcal{S}^k
$$

For any given subsystem with $k$ monitored dimensions, the total number of possible operational states is exactly $19^k$.

---

### 3. Deterministic Mapping Function (Lookup Table)
The architecture rejects probabilistic matrix multiplications and weight optimizations. Every invariant vector maps to a single, hard-coded actuator action ($\mathcal{A}$) via a deterministic mapping function $\mathcal{F}$, executed in constant time $O(1)$:

$$
\mathcal{F}: \mathcal{S}^k \longrightarrow \mathcal{A}
$$

This guarantees absolute predictability; the system retrieves the required physical command instantly without predictive calculation.

---

### 4. Axiomatic Safety and Formal Verification
The execution engine continuously enforces a strict boundary axiom. If any physical parameter hits the absorbing boundary, the system triggers an immediate hardware-level interdict:

$$
\text{if } \exists s_i = \pm 9 \implies \text{Action} = \text{HARD\_STOP}
$$

Because the state space is finite ($19^k$), the entire transition matrix can be formally verified (e.g., via Z3 SMT Solvers) to mathematically prove the absence of contradictory rules or deadlocks before deployment.

---

### 5. Input Hysteresis (Deadband Quantization)
To bridge the gap between continuous analog sensors and discrete logic, and to prevent mechanical actuator flapping caused by sensor noise, the input signal $x(t)$ is mapped to $\mathcal{S}$ using an asymmetric threshold function with a deadband $\delta$:

$$
s_i(t) = \text{Quantize}(x(t), \delta)
$$

Transitioning from state $+2$ to $+3$ requires crossing a higher physical threshold than reverting from $+3$ to $+2$.

---

### 6. Time Dynamics and Discrete Gradients ($\Delta \mathcal{IB}$)
To differentiate between natural operational wear and catastrophic failure (e.g., a burst pipe), the rate of change is incorporated. The gradient is quantized onto the same $[-9, 9]$ discrete scale:

$$
\Delta s_i = \text{Quantize}\left(\frac{s_i(t) - s_i(t - \Delta t)}{\Delta t}, \delta_{\Delta}\right)
$$

This allows the matrix to evaluate both the current state and its dynamic trajectory within the strict $19^k$ dimensional space.

---

### 7. Dimensional Cascading (Solving Combinatorial Explosion)
To bypass the exponential combinatorial explosion for complex systems ($k > 5$), the architecture utilizes hierarchical dependency trees. A primary IB tuple (e.g., controlling a single cooling loop) outputs an aggregate state action, which then acts as a single, quantized input coordinate for a higher-level supervisor tuple:

$$
\mathcal{IB}_{master} = (\mathcal{F}(\mathcal{IB}_{node1}), \mathcal{F}(\mathcal{IB}_{node2}), \dots)
$$

This modular approach ensures that each localized matrix remains small enough for $O(1)$ execution and full mathematical verification.