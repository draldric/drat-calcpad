# Beam-analysis benchmark basis

## Purpose

The beam benchmark worksheet qualifies the recommended model API against solutions derived independently of `Libraries/Analysis/BeamAnalysis.cpd`.
It is separate from the broader API regression worksheet so a refactor cannot redefine both the implementation and its expected results through the same helper.

The maintained executable benchmark is [`Tests/Libraries/Analysis/BeamAnalysisBenchmarkTest.cpd`](../Tests/Libraries/Analysis/BeamAnalysisBenchmarkTest.cpd).

## Assumptions and sign conventions

The derivations use a prismatic Euler-Bernoulli beam with constant elastic modulus `E` and second moment of area `I`.
Deflections are small, material response is linear elastic, and shear deformation is excluded.

Positive transverse loads act downward.
Positive deflection is downward, and positive rotation is its derivative toward increasing `x`.
Positive applied moments are counterclockwise.
The internal bending-moment signs below follow the public Beam Analysis API.

## Independent derivation method

Support reactions come from `sum(F_y) = 0` and `sum(M) = 0`.
Shear and bending moment are obtained from a cut at `x`.
Rotation and deflection are obtained by integrating the curvature relation `E I v''(x) = -M(x)` and applying the appropriate support boundary conditions.
Concentrated loads and moments are treated piecewise; no Beam Analysis helper is used to calculate an expected value.

## Benchmark cases

Let `L` be the span, `P` a point load, `w` a uniform load, `w_0` the peak of a triangular load increasing from zero at the left end, `M_0` a concentrated moment at `x = a`, and `R_A` and `R_B` the left and right vertical reactions.

| ID | Case | Independently derived checks |
| --- | --- | --- |
| `B-SS-PL-01` | Simply supported, centred point load | `R_A = R_B = P/2`; `V(L/4) = P/2`; `M(L/2) = P L/4`; `theta(0) = P L^2/(16 E I)`; `v(L/2) = P L^3/(48 E I)` |
| `B-SS-UDL-01` | Simply supported, full-span UDL | `R_A = R_B = w L/2`; `V(L/2) = 0`; `M(L/2) = w L^2/8`; `theta(0) = w L^3/(24 E I)`; `v(L/2) = 5 w L^4/(384 E I)` |
| `B-CF-PL-01` | Cantilever, free-end point load | `R_A = P`; `M_A = P L`; `V(L/2) = P`; `M(L/2) = P L/2`; `theta(L) = P L^2/(2 E I)`; `v(L) = P L^3/(3 E I)` |
| `B-CF-UDL-01` | Cantilever, full-span UDL | `R_A = w L`; `M_A = w L^2/2`; `theta(L) = w L^3/(6 E I)`; `v(L) = w L^4/(8 E I)` |
| `B-SS-M-01` | Simply supported, concentrated moment | `R_A = M_0/L`; `R_B = -M_0/L`; `M(a-) = R_A a`; `M(a+) = R_A a - M_0`; rotation and deflection follow the piecewise integration below |
| `B-SS-TRI-01` | Simply supported, triangular load increasing rightward | `R_A = w_0 L/6`; `R_B = w_0 L/3`; `V(L/2) = w_0 L/24`; `M(L/2) = w_0 L^2/16`; `theta(0) = 7 w_0 L^3/(360 E I)`; `v(L/2) = 5 w_0 L^4/(768 E I)` |
| `B-CF-TRI-01` | Cantilever, triangular load increasing rightward | `R_A = w_0 L/2`; `M_A = w_0 L^2/3`; `theta(L) = w_0 L^3/(8 E I)`; `v(L) = 11 w_0 L^4/(120 E I)` |
| `B-UNIT-01` | Centred point-load case in millimetres, megapascals, and centimetres to the fourth power | Confirms `R_A = 5 kN`, `M(L/2) = 15 kN m`, and `v(L/2) = 28.125 mm` for the same physical case as `B-SS-PL-01` |

For `B-SS-M-01`, define:

```text
R_A = M_0/L
C_1 = M_0 L/(6 E I) - M_0 (L - a)^2/(2 E I L)
```

For `0 <= x <= a`:

```text
theta(x) = C_1 - R_A x^2/(2 E I)
v(x) = C_1 x - R_A x^3/(6 E I)
```

The worksheet checks these expressions at the left support and the applied-moment location and separately checks the moment jump.

## Tolerances

The force tolerance is `1 N`, the bending-moment tolerance is `1 N m`, the rotation tolerance is `1e-9`, and the displacement tolerance is `1e-9 m`.
The force and moment limits are respectively no greater than one part in two thousand and one part in four thousand of the smallest nonzero checked values.
The rotation and displacement limits are several orders of magnitude below their smallest nonzero responses.
These absolute tolerances accommodate floating-point unit conversion without obscuring an engineering-significant error.

## Execution

Run the repository verifier and confirm the benchmark worksheet reports `all_tests = 1`:

```powershell
pwsh -NoProfile -File Tools/VerifyRepository.ps1
```
