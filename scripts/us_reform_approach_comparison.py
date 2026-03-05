"""Minimal reproduction: US reform application — construction-time vs post-construction.

This script demonstrates whether applying reforms via p.update() AFTER
Microsimulation construction produces the same results as passing reform=
at construction time for policyengine-us.

We test with two parameters to be thorough:
  1. Standard deduction (SINGLE) — doubled from ~15,750 to 50,000
  2. Top bracket rate — raised from 0.37 to 0.50
"""

from policyengine_core.periods import period as make_period
from policyengine_us import Microsimulation

# ── Configuration ──────────────────────────────────────────────────────
YEAR = 2025
PERIOD_STR = f"{YEAR}-01-01"
VARIABLE = "income_tax"

REFORMS = {
    "gov.irs.deductions.standard.amount.SINGLE": 50_000,
    "gov.irs.income.bracket.rates.7": 0.50,
}


def get_param_value(sim, path, instant):
    node = sim.tax_benefit_system.parameters
    for part in path.split("."):
        node = getattr(node, part)
    return float(node(instant))


def print_params(label, sim):
    print(f"  [{label}] Parameter values:")
    for path, target in REFORMS.items():
        val = get_param_value(sim, path, PERIOD_STR)
        print(f"    {path} = {val}")


# ── Approach C: baseline (no reform) — run first for reference ────────
print("Building baseline (no reform)...")
sim_c = Microsimulation()
tax_c = float(sim_c.calculate(VARIABLE, period=YEAR).sum())
print("BASELINE (no reform)")
print_params("C", sim_c)
print(f"  income_tax (sum): {tax_c:,.2f}\n")


# ── Approach A: reform dict at construction time ───────────────────────
print("Building Approach A (reform= at construction time)...")
reform_dict = {path: {PERIOD_STR: val} for path, val in REFORMS.items()}
sim_a = Microsimulation(reform=reform_dict)
tax_a = float(sim_a.calculate(VARIABLE, period=YEAR).sum())
print("APPROACH A: reform= at construction time")
print_params("A", sim_a)
print(f"  income_tax (sum): {tax_a:,.2f}\n")


# ── Approach B: p.update() after construction (UK-style) ───────────────
print("Building Approach B (p.update() after construction)...")
sim_b = Microsimulation()
for path, val in REFORMS.items():
    p = sim_b.tax_benefit_system.parameters.get_child(path)
    p.update(value=val, start=make_period(PERIOD_STR))
tax_b = float(sim_b.calculate(VARIABLE, period=YEAR).sum())
print("APPROACH B: p.update() after construction (UK-style)")
print_params("B", sim_b)
print(f"  income_tax (sum): {tax_b:,.2f}\n")


# ── Comparison ─────────────────────────────────────────────────────────
print("=" * 70)
print("COMPARISON")
print(f"  C (baseline / no reform):      {tax_c:>25,.2f}")
print(f"  A (construction-time reform):  {tax_a:>25,.2f}")
print(f"  B (post-construction update):  {tax_b:>25,.2f}")
print()
print(f"  Delta A vs C (reform effect):  {tax_a - tax_c:>25,.2f}")
print(f"  Delta B vs C (reform effect):  {tax_b - tax_c:>25,.2f}")
print(f"  Delta A vs B:                  {tax_a - tax_b:>25,.2f}")
print()

if abs(tax_a - tax_c) < 1.0:
    print("WARNING: Approach A shows no difference from baseline.")
    print(
        "  The reform may not have taken effect. Check parameter values above."
    )
elif abs(tax_a - tax_b) < 0.01:
    print(
        "RESULT: A and B match — both approaches work identically for policyengine-us."
    )
else:
    print("RESULT: A and B DIFFER — post-construction p.update() does NOT")
    print("        produce the same result as construction-time reform=.")
    print()
    if abs(tax_b - tax_c) < 1.0:
        print("  ** B matches baseline C — the p.update() had NO EFFECT on")
        print(
            "     the calculated income_tax. The reform was silently ignored."
        )
    else:
        print(
            "  ** B differs from both A and C — partial/incorrect application."
        )
