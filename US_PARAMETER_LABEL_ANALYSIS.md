# US Parameter Label Analysis

Generated from policyengine.py analysis of policyengine-us parameters.

## Summary

| Metric | Count | Percentage |
|--------|-------|------------|
| Total parameters | 53,824 | 100% |
| **With final label** (explicit or generated) | 17,519 | 32.5% |
| **Without final label** | 36,305 | 67.5% |

## Breakdown by Category

| Category | Count | Percentage | Description |
|----------|-------|------------|-------------|
| Explicit label | 4,835 | 9.0% | Has label defined in YAML metadata |
| Bracket with scale label | 7,057 | 13.1% | Bracket param where parent scale has label → label generated |
| Bracket without scale label | 68 | 0.1% | Bracket param where parent scale has no label → NO label |
| Breakdown with parent label | 5,627 | 10.5% | Breakdown param where parent has label → label generated |
| Breakdown without parent label | 497 | 0.9% | Breakdown param where parent has no label → NO label |
| **Pseudo-breakdown** | 903 | 1.7% | Looks like breakdown (filing_status/state_code children) but no breakdown metadata |
| Regular without label | 35,740 | 66.4% | Not a bracket or breakdown, no explicit label |

---

## Bracket Without Scale Label (Complete List)

**68 params across 8 scales**

These bracket params have no label because their parent ParameterScale has no label.

### Scale: `gov.irs.credits.education.american_opportunity_credit.amount`

**6 params**

- `gov.irs.credits.education.american_opportunity_credit.amount[0].rate`
- `gov.irs.credits.education.american_opportunity_credit.amount[0].threshold`
- `gov.irs.credits.education.american_opportunity_credit.amount[1].rate`
- `gov.irs.credits.education.american_opportunity_credit.amount[1].threshold`
- `gov.irs.credits.education.american_opportunity_credit.amount[2].rate`
- `gov.irs.credits.education.american_opportunity_credit.amount[2].threshold`

### Scale: `gov.irs.credits.eitc.phase_out.joint_bonus`

**2 params**

- `gov.irs.credits.eitc.phase_out.joint_bonus[0].threshold`
- `gov.irs.credits.eitc.phase_out.joint_bonus[1].threshold`

### Scale: `gov.irs.credits.premium_tax_credit.eligibility`

**6 params**

- `gov.irs.credits.premium_tax_credit.eligibility[0].amount`
- `gov.irs.credits.premium_tax_credit.eligibility[0].threshold`
- `gov.irs.credits.premium_tax_credit.eligibility[1].amount`
- `gov.irs.credits.premium_tax_credit.eligibility[1].threshold`
- `gov.irs.credits.premium_tax_credit.eligibility[2].amount`
- `gov.irs.credits.premium_tax_credit.eligibility[2].threshold`

### Scale: `gov.irs.credits.premium_tax_credit.phase_out.ending_rate`

**14 params**

- `gov.irs.credits.premium_tax_credit.phase_out.ending_rate[0].amount`
- `gov.irs.credits.premium_tax_credit.phase_out.ending_rate[0].threshold`
- `gov.irs.credits.premium_tax_credit.phase_out.ending_rate[1].amount`
- `gov.irs.credits.premium_tax_credit.phase_out.ending_rate[1].threshold`
- `gov.irs.credits.premium_tax_credit.phase_out.ending_rate[2].amount`
- `gov.irs.credits.premium_tax_credit.phase_out.ending_rate[2].threshold`
- `gov.irs.credits.premium_tax_credit.phase_out.ending_rate[3].amount`
- `gov.irs.credits.premium_tax_credit.phase_out.ending_rate[3].threshold`
- `gov.irs.credits.premium_tax_credit.phase_out.ending_rate[4].amount`
- `gov.irs.credits.premium_tax_credit.phase_out.ending_rate[4].threshold`
- `gov.irs.credits.premium_tax_credit.phase_out.ending_rate[5].amount`
- `gov.irs.credits.premium_tax_credit.phase_out.ending_rate[5].threshold`
- `gov.irs.credits.premium_tax_credit.phase_out.ending_rate[6].amount`
- `gov.irs.credits.premium_tax_credit.phase_out.ending_rate[6].threshold`

### Scale: `gov.irs.credits.premium_tax_credit.phase_out.starting_rate`

**14 params**

- `gov.irs.credits.premium_tax_credit.phase_out.starting_rate[0].amount`
- `gov.irs.credits.premium_tax_credit.phase_out.starting_rate[0].threshold`
- `gov.irs.credits.premium_tax_credit.phase_out.starting_rate[1].amount`
- `gov.irs.credits.premium_tax_credit.phase_out.starting_rate[1].threshold`
- `gov.irs.credits.premium_tax_credit.phase_out.starting_rate[2].amount`
- `gov.irs.credits.premium_tax_credit.phase_out.starting_rate[2].threshold`
- `gov.irs.credits.premium_tax_credit.phase_out.starting_rate[3].amount`
- `gov.irs.credits.premium_tax_credit.phase_out.starting_rate[3].threshold`
- `gov.irs.credits.premium_tax_credit.phase_out.starting_rate[4].amount`
- `gov.irs.credits.premium_tax_credit.phase_out.starting_rate[4].threshold`
- `gov.irs.credits.premium_tax_credit.phase_out.starting_rate[5].amount`
- `gov.irs.credits.premium_tax_credit.phase_out.starting_rate[5].threshold`
- `gov.irs.credits.premium_tax_credit.phase_out.starting_rate[6].amount`
- `gov.irs.credits.premium_tax_credit.phase_out.starting_rate[6].threshold`

### Scale: `gov.states.dc.tax.income.credits.ptc.fraction_elderly`

**4 params**

- `gov.states.dc.tax.income.credits.ptc.fraction_elderly[0].amount`
- `gov.states.dc.tax.income.credits.ptc.fraction_elderly[0].threshold`
- `gov.states.dc.tax.income.credits.ptc.fraction_elderly[1].amount`
- `gov.states.dc.tax.income.credits.ptc.fraction_elderly[1].threshold`

### Scale: `gov.states.dc.tax.income.credits.ptc.fraction_nonelderly`

**8 params**

- `gov.states.dc.tax.income.credits.ptc.fraction_nonelderly[0].amount`
- `gov.states.dc.tax.income.credits.ptc.fraction_nonelderly[0].threshold`
- `gov.states.dc.tax.income.credits.ptc.fraction_nonelderly[1].amount`
- `gov.states.dc.tax.income.credits.ptc.fraction_nonelderly[1].threshold`
- `gov.states.dc.tax.income.credits.ptc.fraction_nonelderly[2].amount`
- `gov.states.dc.tax.income.credits.ptc.fraction_nonelderly[2].threshold`
- `gov.states.dc.tax.income.credits.ptc.fraction_nonelderly[3].amount`
- `gov.states.dc.tax.income.credits.ptc.fraction_nonelderly[3].threshold`

### Scale: `gov.states.dc.tax.income.rates`

**14 params**

- `gov.states.dc.tax.income.rates[0].rate`
- `gov.states.dc.tax.income.rates[0].threshold`
- `gov.states.dc.tax.income.rates[1].rate`
- `gov.states.dc.tax.income.rates[1].threshold`
- `gov.states.dc.tax.income.rates[2].rate`
- `gov.states.dc.tax.income.rates[2].threshold`
- `gov.states.dc.tax.income.rates[3].rate`
- `gov.states.dc.tax.income.rates[3].threshold`
- `gov.states.dc.tax.income.rates[4].rate`
- `gov.states.dc.tax.income.rates[4].threshold`
- `gov.states.dc.tax.income.rates[5].rate`
- `gov.states.dc.tax.income.rates[5].threshold`
- `gov.states.dc.tax.income.rates[6].rate`
- `gov.states.dc.tax.income.rates[6].threshold`

---

## Breakdown Without Parent Label (Complete List)

**497 params across 12 parents**

These breakdown params have no label because their parent node has `breakdown` metadata but no `label`.

### Parent: `gov.hhs.tanf.non_cash.asset_limit`

- **Breakdown variable**: `['state_code']`
- **59 params**

- `gov.hhs.tanf.non_cash.asset_limit.AA`
- `gov.hhs.tanf.non_cash.asset_limit.AE`
- `gov.hhs.tanf.non_cash.asset_limit.AK`
- `gov.hhs.tanf.non_cash.asset_limit.AL`
- `gov.hhs.tanf.non_cash.asset_limit.AP`
- `gov.hhs.tanf.non_cash.asset_limit.AR`
- `gov.hhs.tanf.non_cash.asset_limit.AZ`
- `gov.hhs.tanf.non_cash.asset_limit.CA`
- `gov.hhs.tanf.non_cash.asset_limit.CO`
- `gov.hhs.tanf.non_cash.asset_limit.CT`
- `gov.hhs.tanf.non_cash.asset_limit.DC`
- `gov.hhs.tanf.non_cash.asset_limit.DE`
- `gov.hhs.tanf.non_cash.asset_limit.FL`
- `gov.hhs.tanf.non_cash.asset_limit.GA`
- `gov.hhs.tanf.non_cash.asset_limit.GU`
- `gov.hhs.tanf.non_cash.asset_limit.HI`
- `gov.hhs.tanf.non_cash.asset_limit.IA`
- `gov.hhs.tanf.non_cash.asset_limit.ID`
- `gov.hhs.tanf.non_cash.asset_limit.IL`
- `gov.hhs.tanf.non_cash.asset_limit.IN`
- `gov.hhs.tanf.non_cash.asset_limit.KS`
- `gov.hhs.tanf.non_cash.asset_limit.KY`
- `gov.hhs.tanf.non_cash.asset_limit.LA`
- `gov.hhs.tanf.non_cash.asset_limit.MA`
- `gov.hhs.tanf.non_cash.asset_limit.MD`
- `gov.hhs.tanf.non_cash.asset_limit.ME`
- `gov.hhs.tanf.non_cash.asset_limit.MI`
- `gov.hhs.tanf.non_cash.asset_limit.MN`
- `gov.hhs.tanf.non_cash.asset_limit.MO`
- `gov.hhs.tanf.non_cash.asset_limit.MP`
- `gov.hhs.tanf.non_cash.asset_limit.MS`
- `gov.hhs.tanf.non_cash.asset_limit.MT`
- `gov.hhs.tanf.non_cash.asset_limit.NC`
- `gov.hhs.tanf.non_cash.asset_limit.ND`
- `gov.hhs.tanf.non_cash.asset_limit.NE`
- `gov.hhs.tanf.non_cash.asset_limit.NH`
- `gov.hhs.tanf.non_cash.asset_limit.NJ`
- `gov.hhs.tanf.non_cash.asset_limit.NM`
- `gov.hhs.tanf.non_cash.asset_limit.NV`
- `gov.hhs.tanf.non_cash.asset_limit.NY`
- `gov.hhs.tanf.non_cash.asset_limit.OH`
- `gov.hhs.tanf.non_cash.asset_limit.OK`
- `gov.hhs.tanf.non_cash.asset_limit.OR`
- `gov.hhs.tanf.non_cash.asset_limit.PA`
- `gov.hhs.tanf.non_cash.asset_limit.PR`
- `gov.hhs.tanf.non_cash.asset_limit.PW`
- `gov.hhs.tanf.non_cash.asset_limit.RI`
- `gov.hhs.tanf.non_cash.asset_limit.SC`
- `gov.hhs.tanf.non_cash.asset_limit.SD`
- `gov.hhs.tanf.non_cash.asset_limit.TN`
- `gov.hhs.tanf.non_cash.asset_limit.TX`
- `gov.hhs.tanf.non_cash.asset_limit.UT`
- `gov.hhs.tanf.non_cash.asset_limit.VA`
- `gov.hhs.tanf.non_cash.asset_limit.VI`
- `gov.hhs.tanf.non_cash.asset_limit.VT`
- `gov.hhs.tanf.non_cash.asset_limit.WA`
- `gov.hhs.tanf.non_cash.asset_limit.WI`
- `gov.hhs.tanf.non_cash.asset_limit.WV`
- `gov.hhs.tanf.non_cash.asset_limit.WY`

### Parent: `gov.hhs.tanf.non_cash.income_limit.gross`

- **Breakdown variable**: `['state_code']`
- **59 params**

- `gov.hhs.tanf.non_cash.income_limit.gross.AA`
- `gov.hhs.tanf.non_cash.income_limit.gross.AE`
- `gov.hhs.tanf.non_cash.income_limit.gross.AK`
- `gov.hhs.tanf.non_cash.income_limit.gross.AL`
- `gov.hhs.tanf.non_cash.income_limit.gross.AP`
- `gov.hhs.tanf.non_cash.income_limit.gross.AR`
- `gov.hhs.tanf.non_cash.income_limit.gross.AZ`
- `gov.hhs.tanf.non_cash.income_limit.gross.CA`
- `gov.hhs.tanf.non_cash.income_limit.gross.CO`
- `gov.hhs.tanf.non_cash.income_limit.gross.CT`
- `gov.hhs.tanf.non_cash.income_limit.gross.DC`
- `gov.hhs.tanf.non_cash.income_limit.gross.DE`
- `gov.hhs.tanf.non_cash.income_limit.gross.FL`
- `gov.hhs.tanf.non_cash.income_limit.gross.GA`
- `gov.hhs.tanf.non_cash.income_limit.gross.GU`
- `gov.hhs.tanf.non_cash.income_limit.gross.HI`
- `gov.hhs.tanf.non_cash.income_limit.gross.IA`
- `gov.hhs.tanf.non_cash.income_limit.gross.ID`
- `gov.hhs.tanf.non_cash.income_limit.gross.IL`
- `gov.hhs.tanf.non_cash.income_limit.gross.IN`
- `gov.hhs.tanf.non_cash.income_limit.gross.KS`
- `gov.hhs.tanf.non_cash.income_limit.gross.KY`
- `gov.hhs.tanf.non_cash.income_limit.gross.LA`
- `gov.hhs.tanf.non_cash.income_limit.gross.MA`
- `gov.hhs.tanf.non_cash.income_limit.gross.MD`
- `gov.hhs.tanf.non_cash.income_limit.gross.ME`
- `gov.hhs.tanf.non_cash.income_limit.gross.MI`
- `gov.hhs.tanf.non_cash.income_limit.gross.MN`
- `gov.hhs.tanf.non_cash.income_limit.gross.MO`
- `gov.hhs.tanf.non_cash.income_limit.gross.MP`
- `gov.hhs.tanf.non_cash.income_limit.gross.MS`
- `gov.hhs.tanf.non_cash.income_limit.gross.MT`
- `gov.hhs.tanf.non_cash.income_limit.gross.NC`
- `gov.hhs.tanf.non_cash.income_limit.gross.ND`
- `gov.hhs.tanf.non_cash.income_limit.gross.NE`
- `gov.hhs.tanf.non_cash.income_limit.gross.NH`
- `gov.hhs.tanf.non_cash.income_limit.gross.NJ`
- `gov.hhs.tanf.non_cash.income_limit.gross.NM`
- `gov.hhs.tanf.non_cash.income_limit.gross.NV`
- `gov.hhs.tanf.non_cash.income_limit.gross.NY`
- `gov.hhs.tanf.non_cash.income_limit.gross.OH`
- `gov.hhs.tanf.non_cash.income_limit.gross.OK`
- `gov.hhs.tanf.non_cash.income_limit.gross.OR`
- `gov.hhs.tanf.non_cash.income_limit.gross.PA`
- `gov.hhs.tanf.non_cash.income_limit.gross.PR`
- `gov.hhs.tanf.non_cash.income_limit.gross.PW`
- `gov.hhs.tanf.non_cash.income_limit.gross.RI`
- `gov.hhs.tanf.non_cash.income_limit.gross.SC`
- `gov.hhs.tanf.non_cash.income_limit.gross.SD`
- `gov.hhs.tanf.non_cash.income_limit.gross.TN`
- `gov.hhs.tanf.non_cash.income_limit.gross.TX`
- `gov.hhs.tanf.non_cash.income_limit.gross.UT`
- `gov.hhs.tanf.non_cash.income_limit.gross.VA`
- `gov.hhs.tanf.non_cash.income_limit.gross.VI`
- `gov.hhs.tanf.non_cash.income_limit.gross.VT`
- `gov.hhs.tanf.non_cash.income_limit.gross.WA`
- `gov.hhs.tanf.non_cash.income_limit.gross.WI`
- `gov.hhs.tanf.non_cash.income_limit.gross.WV`
- `gov.hhs.tanf.non_cash.income_limit.gross.WY`

### Parent: `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod`

- **Breakdown variable**: `['state_code']`
- **59 params**

- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.AA`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.AE`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.AK`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.AL`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.AP`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.AR`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.AZ`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.CA`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.CO`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.CT`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.DC`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.DE`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.FL`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.GA`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.GU`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.HI`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.IA`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.ID`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.IL`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.IN`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.KS`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.KY`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.LA`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.MA`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.MD`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.ME`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.MI`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.MN`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.MO`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.MP`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.MS`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.MT`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.NC`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.ND`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.NE`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.NH`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.NJ`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.NM`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.NV`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.NY`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.OH`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.OK`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.OR`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.PA`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.PR`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.PW`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.RI`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.SC`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.SD`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.TN`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.TX`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.UT`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.VA`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.VI`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.VT`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.WA`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.WI`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.WV`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.hheod.WY`

### Parent: `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod`

- **Breakdown variable**: `['state_code']`
- **59 params**

- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.AA`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.AE`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.AK`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.AL`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.AP`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.AR`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.AZ`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.CA`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.CO`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.CT`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.DC`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.DE`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.FL`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.GA`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.GU`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.HI`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.IA`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.ID`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.IL`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.IN`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.KS`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.KY`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.LA`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.MA`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.MD`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.ME`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.MI`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.MN`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.MO`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.MP`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.MS`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.MT`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.NC`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.ND`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.NE`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.NH`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.NJ`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.NM`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.NV`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.NY`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.OH`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.OK`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.OR`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.PA`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.PR`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.PW`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.RI`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.SC`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.SD`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.TN`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.TX`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.UT`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.VA`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.VI`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.VT`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.WA`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.WI`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.WV`
- `gov.hhs.tanf.non_cash.income_limit.net_applies.non_hheod.WY`

### Parent: `gov.hhs.tanf.non_cash.requires_all_for_hheod`

- **Breakdown variable**: `['state_code']`
- **59 params**

- `gov.hhs.tanf.non_cash.requires_all_for_hheod.AA`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.AE`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.AK`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.AL`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.AP`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.AR`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.AZ`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.CA`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.CO`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.CT`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.DC`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.DE`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.FL`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.GA`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.GU`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.HI`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.IA`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.ID`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.IL`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.IN`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.KS`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.KY`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.LA`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.MA`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.MD`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.ME`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.MI`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.MN`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.MO`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.MP`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.MS`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.MT`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.NC`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.ND`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.NE`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.NH`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.NJ`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.NM`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.NV`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.NY`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.OH`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.OK`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.OR`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.PA`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.PR`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.PW`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.RI`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.SC`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.SD`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.TN`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.TX`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.UT`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.VA`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.VI`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.VT`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.WA`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.WI`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.WV`
- `gov.hhs.tanf.non_cash.requires_all_for_hheod.WY`

### Parent: `gov.states.md.tanf.maximum_benefit.main`

- **Breakdown variable**: `['range(1, 9)']`
- **8 params**

- `gov.states.md.tanf.maximum_benefit.main.1`
- `gov.states.md.tanf.maximum_benefit.main.2`
- `gov.states.md.tanf.maximum_benefit.main.3`
- `gov.states.md.tanf.maximum_benefit.main.4`
- `gov.states.md.tanf.maximum_benefit.main.5`
- `gov.states.md.tanf.maximum_benefit.main.6`
- `gov.states.md.tanf.maximum_benefit.main.7`
- `gov.states.md.tanf.maximum_benefit.main.8`

### Parent: `gov.states.wi.tax.income.deductions.standard.max`

- **Breakdown variable**: `['filing_status']`
- **5 params**

- `gov.states.wi.tax.income.deductions.standard.max.HEAD_OF_HOUSEHOLD`
- `gov.states.wi.tax.income.deductions.standard.max.JOINT`
- `gov.states.wi.tax.income.deductions.standard.max.SEPARATE`
- `gov.states.wi.tax.income.deductions.standard.max.SINGLE`
- `gov.states.wi.tax.income.deductions.standard.max.SURVIVING_SPOUSE`

### Parent: `gov.states.wi.tax.income.subtractions.unemployment_compensation.income_phase_out.base`

- **Breakdown variable**: `['filing_status']`
- **5 params**

- `gov.states.wi.tax.income.subtractions.unemployment_compensation.income_phase_out.base.HEAD_OF_HOUSEHOLD`
- `gov.states.wi.tax.income.subtractions.unemployment_compensation.income_phase_out.base.JOINT`
- `gov.states.wi.tax.income.subtractions.unemployment_compensation.income_phase_out.base.SEPARATE`
- `gov.states.wi.tax.income.subtractions.unemployment_compensation.income_phase_out.base.SINGLE`
- `gov.states.wi.tax.income.subtractions.unemployment_compensation.income_phase_out.base.SURVIVING_SPOUSE`

### Parent: `gov.usda.snap.income.deductions.excess_medical_expense.standard`

- **Breakdown variable**: `['state_code']`
- **59 params**

- `gov.usda.snap.income.deductions.excess_medical_expense.standard.AA`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.AE`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.AK`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.AL`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.AP`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.AR`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.AZ`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.CA`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.CO`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.CT`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.DC`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.DE`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.FL`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.GA`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.GU`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.HI`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.IA`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.ID`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.IL`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.IN`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.KS`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.KY`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.LA`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.MA`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.MD`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.ME`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.MI`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.MN`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.MO`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.MP`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.MS`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.MT`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.NC`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.ND`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.NE`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.NH`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.NJ`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.NM`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.NV`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.NY`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.OH`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.OK`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.OR`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.PA`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.PR`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.PW`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.RI`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.SC`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.SD`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.TN`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.TX`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.UT`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.VA`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.VI`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.VT`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.WA`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.WI`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.WV`
- `gov.usda.snap.income.deductions.excess_medical_expense.standard.WY`

### Parent: `gov.usda.snap.income.deductions.utility.limited.main`

- **Breakdown variable**: `['snap_utility_region']`
- **59 params**

- `gov.usda.snap.income.deductions.utility.limited.main.AA`
- `gov.usda.snap.income.deductions.utility.limited.main.AE`
- `gov.usda.snap.income.deductions.utility.limited.main.AK`
- `gov.usda.snap.income.deductions.utility.limited.main.AL`
- `gov.usda.snap.income.deductions.utility.limited.main.AP`
- `gov.usda.snap.income.deductions.utility.limited.main.AR`
- `gov.usda.snap.income.deductions.utility.limited.main.AZ`
- `gov.usda.snap.income.deductions.utility.limited.main.CA`
- `gov.usda.snap.income.deductions.utility.limited.main.CO`
- `gov.usda.snap.income.deductions.utility.limited.main.CT`
- `gov.usda.snap.income.deductions.utility.limited.main.DC`
- `gov.usda.snap.income.deductions.utility.limited.main.DE`
- `gov.usda.snap.income.deductions.utility.limited.main.FL`
- `gov.usda.snap.income.deductions.utility.limited.main.GA`
- `gov.usda.snap.income.deductions.utility.limited.main.GU`
- `gov.usda.snap.income.deductions.utility.limited.main.HI`
- `gov.usda.snap.income.deductions.utility.limited.main.IA`
- `gov.usda.snap.income.deductions.utility.limited.main.ID`
- `gov.usda.snap.income.deductions.utility.limited.main.IL`
- `gov.usda.snap.income.deductions.utility.limited.main.IN`
- `gov.usda.snap.income.deductions.utility.limited.main.KS`
- `gov.usda.snap.income.deductions.utility.limited.main.KY`
- `gov.usda.snap.income.deductions.utility.limited.main.LA`
- `gov.usda.snap.income.deductions.utility.limited.main.MA`
- `gov.usda.snap.income.deductions.utility.limited.main.MD`
- `gov.usda.snap.income.deductions.utility.limited.main.ME`
- `gov.usda.snap.income.deductions.utility.limited.main.MI`
- `gov.usda.snap.income.deductions.utility.limited.main.MN`
- `gov.usda.snap.income.deductions.utility.limited.main.MO`
- `gov.usda.snap.income.deductions.utility.limited.main.MP`
- `gov.usda.snap.income.deductions.utility.limited.main.MS`
- `gov.usda.snap.income.deductions.utility.limited.main.MT`
- `gov.usda.snap.income.deductions.utility.limited.main.NC`
- `gov.usda.snap.income.deductions.utility.limited.main.ND`
- `gov.usda.snap.income.deductions.utility.limited.main.NE`
- `gov.usda.snap.income.deductions.utility.limited.main.NH`
- `gov.usda.snap.income.deductions.utility.limited.main.NJ`
- `gov.usda.snap.income.deductions.utility.limited.main.NM`
- `gov.usda.snap.income.deductions.utility.limited.main.NV`
- `gov.usda.snap.income.deductions.utility.limited.main.NY`
- `gov.usda.snap.income.deductions.utility.limited.main.OH`
- `gov.usda.snap.income.deductions.utility.limited.main.OK`
- `gov.usda.snap.income.deductions.utility.limited.main.OR`
- `gov.usda.snap.income.deductions.utility.limited.main.PA`
- `gov.usda.snap.income.deductions.utility.limited.main.PR`
- `gov.usda.snap.income.deductions.utility.limited.main.PW`
- `gov.usda.snap.income.deductions.utility.limited.main.RI`
- `gov.usda.snap.income.deductions.utility.limited.main.SC`
- `gov.usda.snap.income.deductions.utility.limited.main.SD`
- `gov.usda.snap.income.deductions.utility.limited.main.TN`
- `gov.usda.snap.income.deductions.utility.limited.main.TX`
- `gov.usda.snap.income.deductions.utility.limited.main.UT`
- `gov.usda.snap.income.deductions.utility.limited.main.VA`
- `gov.usda.snap.income.deductions.utility.limited.main.VI`
- `gov.usda.snap.income.deductions.utility.limited.main.VT`
- `gov.usda.snap.income.deductions.utility.limited.main.WA`
- `gov.usda.snap.income.deductions.utility.limited.main.WI`
- `gov.usda.snap.income.deductions.utility.limited.main.WV`
- `gov.usda.snap.income.deductions.utility.limited.main.WY`

### Parent: `gov.usda.snap.max_allotment.additional`

- **Breakdown variable**: `['snap_region']`
- **7 params**

- `gov.usda.snap.max_allotment.additional.AK_RURAL_1`
- `gov.usda.snap.max_allotment.additional.AK_RURAL_2`
- `gov.usda.snap.max_allotment.additional.AK_URBAN`
- `gov.usda.snap.max_allotment.additional.CONTIGUOUS_US`
- `gov.usda.snap.max_allotment.additional.GU`
- `gov.usda.snap.max_allotment.additional.HI`
- `gov.usda.snap.max_allotment.additional.VI`

### Parent: `openfisca.completed_programs.state`

- **Breakdown variable**: `['state_code']`
- **59 params**

- `openfisca.completed_programs.state.AA`
- `openfisca.completed_programs.state.AE`
- `openfisca.completed_programs.state.AK`
- `openfisca.completed_programs.state.AL`
- `openfisca.completed_programs.state.AP`
- `openfisca.completed_programs.state.AR`
- `openfisca.completed_programs.state.AZ`
- `openfisca.completed_programs.state.CA`
- `openfisca.completed_programs.state.CO`
- `openfisca.completed_programs.state.CT`
- `openfisca.completed_programs.state.DC`
- `openfisca.completed_programs.state.DE`
- `openfisca.completed_programs.state.FL`
- `openfisca.completed_programs.state.GA`
- `openfisca.completed_programs.state.GU`
- `openfisca.completed_programs.state.HI`
- `openfisca.completed_programs.state.IA`
- `openfisca.completed_programs.state.ID`
- `openfisca.completed_programs.state.IL`
- `openfisca.completed_programs.state.IN`
- `openfisca.completed_programs.state.KS`
- `openfisca.completed_programs.state.KY`
- `openfisca.completed_programs.state.LA`
- `openfisca.completed_programs.state.MA`
- `openfisca.completed_programs.state.MD`
- `openfisca.completed_programs.state.ME`
- `openfisca.completed_programs.state.MI`
- `openfisca.completed_programs.state.MN`
- `openfisca.completed_programs.state.MO`
- `openfisca.completed_programs.state.MP`
- `openfisca.completed_programs.state.MS`
- `openfisca.completed_programs.state.MT`
- `openfisca.completed_programs.state.NC`
- `openfisca.completed_programs.state.ND`
- `openfisca.completed_programs.state.NE`
- `openfisca.completed_programs.state.NH`
- `openfisca.completed_programs.state.NJ`
- `openfisca.completed_programs.state.NM`
- `openfisca.completed_programs.state.NV`
- `openfisca.completed_programs.state.NY`
- `openfisca.completed_programs.state.OH`
- `openfisca.completed_programs.state.OK`
- `openfisca.completed_programs.state.OR`
- `openfisca.completed_programs.state.PA`
- `openfisca.completed_programs.state.PR`
- `openfisca.completed_programs.state.PW`
- `openfisca.completed_programs.state.RI`
- `openfisca.completed_programs.state.SC`
- `openfisca.completed_programs.state.SD`
- `openfisca.completed_programs.state.TN`
- `openfisca.completed_programs.state.TX`
- `openfisca.completed_programs.state.UT`
- `openfisca.completed_programs.state.VA`
- `openfisca.completed_programs.state.VI`
- `openfisca.completed_programs.state.VT`
- `openfisca.completed_programs.state.WA`
- `openfisca.completed_programs.state.WI`
- `openfisca.completed_programs.state.WV`
- `openfisca.completed_programs.state.WY`

---

## Pseudo-Breakdown Params (Complete List)

**903 params across 61 parents**

These params have children that look like breakdown values (filing_status or state_code enum values) but the parent node does NOT have `breakdown` metadata set. Adding `breakdown` metadata to these parents would allow automatic label generation.

### Parent: `calibration.gov.census.populations.by_state`

- **Expected breakdown type**: `state_code`
- **Parent has label**: False
- **51 params**

- `calibration.gov.census.populations.by_state.AK`
- `calibration.gov.census.populations.by_state.AL`
- `calibration.gov.census.populations.by_state.AR`
- `calibration.gov.census.populations.by_state.AZ`
- `calibration.gov.census.populations.by_state.CA`
- `calibration.gov.census.populations.by_state.CO`
- `calibration.gov.census.populations.by_state.CT`
- `calibration.gov.census.populations.by_state.DC`
- `calibration.gov.census.populations.by_state.DE`
- `calibration.gov.census.populations.by_state.FL`
- `calibration.gov.census.populations.by_state.GA`
- `calibration.gov.census.populations.by_state.HI`
- `calibration.gov.census.populations.by_state.IA`
- `calibration.gov.census.populations.by_state.ID`
- `calibration.gov.census.populations.by_state.IL`
- `calibration.gov.census.populations.by_state.IN`
- `calibration.gov.census.populations.by_state.KS`
- `calibration.gov.census.populations.by_state.KY`
- `calibration.gov.census.populations.by_state.LA`
- `calibration.gov.census.populations.by_state.MA`
- `calibration.gov.census.populations.by_state.MD`
- `calibration.gov.census.populations.by_state.ME`
- `calibration.gov.census.populations.by_state.MI`
- `calibration.gov.census.populations.by_state.MN`
- `calibration.gov.census.populations.by_state.MO`
- `calibration.gov.census.populations.by_state.MS`
- `calibration.gov.census.populations.by_state.MT`
- `calibration.gov.census.populations.by_state.NC`
- `calibration.gov.census.populations.by_state.ND`
- `calibration.gov.census.populations.by_state.NE`
- `calibration.gov.census.populations.by_state.NH`
- `calibration.gov.census.populations.by_state.NJ`
- `calibration.gov.census.populations.by_state.NM`
- `calibration.gov.census.populations.by_state.NV`
- `calibration.gov.census.populations.by_state.NY`
- `calibration.gov.census.populations.by_state.OH`
- `calibration.gov.census.populations.by_state.OK`
- `calibration.gov.census.populations.by_state.OR`
- `calibration.gov.census.populations.by_state.PA`
- `calibration.gov.census.populations.by_state.RI`
- `calibration.gov.census.populations.by_state.SC`
- `calibration.gov.census.populations.by_state.SD`
- `calibration.gov.census.populations.by_state.TN`
- `calibration.gov.census.populations.by_state.TX`
- `calibration.gov.census.populations.by_state.UT`
- `calibration.gov.census.populations.by_state.VA`
- `calibration.gov.census.populations.by_state.VT`
- `calibration.gov.census.populations.by_state.WA`
- `calibration.gov.census.populations.by_state.WI`
- `calibration.gov.census.populations.by_state.WV`
- `calibration.gov.census.populations.by_state.WY`

### Parent: `calibration.gov.hhs.medicaid.totals.enrollment`

- **Expected breakdown type**: `state_code`
- **Parent has label**: False
- **51 params**

- `calibration.gov.hhs.medicaid.totals.enrollment.AK`
- `calibration.gov.hhs.medicaid.totals.enrollment.AL`
- `calibration.gov.hhs.medicaid.totals.enrollment.AR`
- `calibration.gov.hhs.medicaid.totals.enrollment.AZ`
- `calibration.gov.hhs.medicaid.totals.enrollment.CA`
- `calibration.gov.hhs.medicaid.totals.enrollment.CO`
- `calibration.gov.hhs.medicaid.totals.enrollment.CT`
- `calibration.gov.hhs.medicaid.totals.enrollment.DC`
- `calibration.gov.hhs.medicaid.totals.enrollment.DE`
- `calibration.gov.hhs.medicaid.totals.enrollment.FL`
- `calibration.gov.hhs.medicaid.totals.enrollment.GA`
- `calibration.gov.hhs.medicaid.totals.enrollment.HI`
- `calibration.gov.hhs.medicaid.totals.enrollment.IA`
- `calibration.gov.hhs.medicaid.totals.enrollment.ID`
- `calibration.gov.hhs.medicaid.totals.enrollment.IL`
- `calibration.gov.hhs.medicaid.totals.enrollment.IN`
- `calibration.gov.hhs.medicaid.totals.enrollment.KS`
- `calibration.gov.hhs.medicaid.totals.enrollment.KY`
- `calibration.gov.hhs.medicaid.totals.enrollment.LA`
- `calibration.gov.hhs.medicaid.totals.enrollment.MA`
- `calibration.gov.hhs.medicaid.totals.enrollment.MD`
- `calibration.gov.hhs.medicaid.totals.enrollment.ME`
- `calibration.gov.hhs.medicaid.totals.enrollment.MI`
- `calibration.gov.hhs.medicaid.totals.enrollment.MN`
- `calibration.gov.hhs.medicaid.totals.enrollment.MO`
- `calibration.gov.hhs.medicaid.totals.enrollment.MS`
- `calibration.gov.hhs.medicaid.totals.enrollment.MT`
- `calibration.gov.hhs.medicaid.totals.enrollment.NC`
- `calibration.gov.hhs.medicaid.totals.enrollment.ND`
- `calibration.gov.hhs.medicaid.totals.enrollment.NE`
- `calibration.gov.hhs.medicaid.totals.enrollment.NH`
- `calibration.gov.hhs.medicaid.totals.enrollment.NJ`
- `calibration.gov.hhs.medicaid.totals.enrollment.NM`
- `calibration.gov.hhs.medicaid.totals.enrollment.NV`
- `calibration.gov.hhs.medicaid.totals.enrollment.NY`
- `calibration.gov.hhs.medicaid.totals.enrollment.OH`
- `calibration.gov.hhs.medicaid.totals.enrollment.OK`
- `calibration.gov.hhs.medicaid.totals.enrollment.OR`
- `calibration.gov.hhs.medicaid.totals.enrollment.PA`
- `calibration.gov.hhs.medicaid.totals.enrollment.RI`
- `calibration.gov.hhs.medicaid.totals.enrollment.SC`
- `calibration.gov.hhs.medicaid.totals.enrollment.SD`
- `calibration.gov.hhs.medicaid.totals.enrollment.TN`
- `calibration.gov.hhs.medicaid.totals.enrollment.TX`
- `calibration.gov.hhs.medicaid.totals.enrollment.UT`
- `calibration.gov.hhs.medicaid.totals.enrollment.VA`
- `calibration.gov.hhs.medicaid.totals.enrollment.VT`
- `calibration.gov.hhs.medicaid.totals.enrollment.WA`
- `calibration.gov.hhs.medicaid.totals.enrollment.WI`
- `calibration.gov.hhs.medicaid.totals.enrollment.WV`
- `calibration.gov.hhs.medicaid.totals.enrollment.WY`

### Parent: `calibration.gov.hhs.medicaid.totals.spending`

- **Expected breakdown type**: `state_code`
- **Parent has label**: False
- **51 params**

- `calibration.gov.hhs.medicaid.totals.spending.AK`
- `calibration.gov.hhs.medicaid.totals.spending.AL`
- `calibration.gov.hhs.medicaid.totals.spending.AR`
- `calibration.gov.hhs.medicaid.totals.spending.AZ`
- `calibration.gov.hhs.medicaid.totals.spending.CA`
- `calibration.gov.hhs.medicaid.totals.spending.CO`
- `calibration.gov.hhs.medicaid.totals.spending.CT`
- `calibration.gov.hhs.medicaid.totals.spending.DC`
- `calibration.gov.hhs.medicaid.totals.spending.DE`
- `calibration.gov.hhs.medicaid.totals.spending.FL`
- `calibration.gov.hhs.medicaid.totals.spending.GA`
- `calibration.gov.hhs.medicaid.totals.spending.HI`
- `calibration.gov.hhs.medicaid.totals.spending.IA`
- `calibration.gov.hhs.medicaid.totals.spending.ID`
- `calibration.gov.hhs.medicaid.totals.spending.IL`
- `calibration.gov.hhs.medicaid.totals.spending.IN`
- `calibration.gov.hhs.medicaid.totals.spending.KS`
- `calibration.gov.hhs.medicaid.totals.spending.KY`
- `calibration.gov.hhs.medicaid.totals.spending.LA`
- `calibration.gov.hhs.medicaid.totals.spending.MA`
- `calibration.gov.hhs.medicaid.totals.spending.MD`
- `calibration.gov.hhs.medicaid.totals.spending.ME`
- `calibration.gov.hhs.medicaid.totals.spending.MI`
- `calibration.gov.hhs.medicaid.totals.spending.MN`
- `calibration.gov.hhs.medicaid.totals.spending.MO`
- `calibration.gov.hhs.medicaid.totals.spending.MS`
- `calibration.gov.hhs.medicaid.totals.spending.MT`
- `calibration.gov.hhs.medicaid.totals.spending.NC`
- `calibration.gov.hhs.medicaid.totals.spending.ND`
- `calibration.gov.hhs.medicaid.totals.spending.NE`
- `calibration.gov.hhs.medicaid.totals.spending.NH`
- `calibration.gov.hhs.medicaid.totals.spending.NJ`
- `calibration.gov.hhs.medicaid.totals.spending.NM`
- `calibration.gov.hhs.medicaid.totals.spending.NV`
- `calibration.gov.hhs.medicaid.totals.spending.NY`
- `calibration.gov.hhs.medicaid.totals.spending.OH`
- `calibration.gov.hhs.medicaid.totals.spending.OK`
- `calibration.gov.hhs.medicaid.totals.spending.OR`
- `calibration.gov.hhs.medicaid.totals.spending.PA`
- `calibration.gov.hhs.medicaid.totals.spending.RI`
- `calibration.gov.hhs.medicaid.totals.spending.SC`
- `calibration.gov.hhs.medicaid.totals.spending.SD`
- `calibration.gov.hhs.medicaid.totals.spending.TN`
- `calibration.gov.hhs.medicaid.totals.spending.TX`
- `calibration.gov.hhs.medicaid.totals.spending.UT`
- `calibration.gov.hhs.medicaid.totals.spending.VA`
- `calibration.gov.hhs.medicaid.totals.spending.VT`
- `calibration.gov.hhs.medicaid.totals.spending.WA`
- `calibration.gov.hhs.medicaid.totals.spending.WI`
- `calibration.gov.hhs.medicaid.totals.spending.WV`
- `calibration.gov.hhs.medicaid.totals.spending.WY`

### Parent: `calibration.gov.irs.soi.returns_by_filing_status`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: True
- **4 params**

- `calibration.gov.irs.soi.returns_by_filing_status.HEAD_OF_HOUSEHOLD`
- `calibration.gov.irs.soi.returns_by_filing_status.JOINT`
- `calibration.gov.irs.soi.returns_by_filing_status.SEPARATE`
- `calibration.gov.irs.soi.returns_by_filing_status.SINGLE`

### Parent: `gov.contrib.additional_tax_bracket.bracket.thresholds.1`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.contrib.additional_tax_bracket.bracket.thresholds.1.HEAD_OF_HOUSEHOLD`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.1.JOINT`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.1.SEPARATE`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.1.SINGLE`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.1.SURVIVING_SPOUSE`

### Parent: `gov.contrib.additional_tax_bracket.bracket.thresholds.2`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.contrib.additional_tax_bracket.bracket.thresholds.2.HEAD_OF_HOUSEHOLD`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.2.JOINT`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.2.SEPARATE`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.2.SINGLE`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.2.SURVIVING_SPOUSE`

### Parent: `gov.contrib.additional_tax_bracket.bracket.thresholds.3`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.contrib.additional_tax_bracket.bracket.thresholds.3.HEAD_OF_HOUSEHOLD`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.3.JOINT`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.3.SEPARATE`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.3.SINGLE`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.3.SURVIVING_SPOUSE`

### Parent: `gov.contrib.additional_tax_bracket.bracket.thresholds.4`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.contrib.additional_tax_bracket.bracket.thresholds.4.HEAD_OF_HOUSEHOLD`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.4.JOINT`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.4.SEPARATE`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.4.SINGLE`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.4.SURVIVING_SPOUSE`

### Parent: `gov.contrib.additional_tax_bracket.bracket.thresholds.5`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.contrib.additional_tax_bracket.bracket.thresholds.5.HEAD_OF_HOUSEHOLD`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.5.JOINT`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.5.SEPARATE`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.5.SINGLE`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.5.SURVIVING_SPOUSE`

### Parent: `gov.contrib.additional_tax_bracket.bracket.thresholds.6`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.contrib.additional_tax_bracket.bracket.thresholds.6.HEAD_OF_HOUSEHOLD`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.6.JOINT`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.6.SEPARATE`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.6.SINGLE`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.6.SURVIVING_SPOUSE`

### Parent: `gov.contrib.additional_tax_bracket.bracket.thresholds.7`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.contrib.additional_tax_bracket.bracket.thresholds.7.HEAD_OF_HOUSEHOLD`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.7.JOINT`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.7.SEPARATE`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.7.SINGLE`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.7.SURVIVING_SPOUSE`

### Parent: `gov.contrib.additional_tax_bracket.bracket.thresholds.8`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.contrib.additional_tax_bracket.bracket.thresholds.8.HEAD_OF_HOUSEHOLD`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.8.JOINT`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.8.SEPARATE`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.8.SINGLE`
- `gov.contrib.additional_tax_bracket.bracket.thresholds.8.SURVIVING_SPOUSE`

### Parent: `gov.contrib.congress.wftca.bonus_guaranteed_deduction.amount`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: True
- **5 params**

- `gov.contrib.congress.wftca.bonus_guaranteed_deduction.amount.HEAD_OF_HOUSEHOLD`
- `gov.contrib.congress.wftca.bonus_guaranteed_deduction.amount.JOINT`
- `gov.contrib.congress.wftca.bonus_guaranteed_deduction.amount.SEPARATE`
- `gov.contrib.congress.wftca.bonus_guaranteed_deduction.amount.SINGLE`
- `gov.contrib.congress.wftca.bonus_guaranteed_deduction.amount.SURVIVING_SPOUSE`

### Parent: `gov.contrib.congress.wftca.bonus_guaranteed_deduction.phase_out.threshold`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: True
- **5 params**

- `gov.contrib.congress.wftca.bonus_guaranteed_deduction.phase_out.threshold.HEAD_OF_HOUSEHOLD`
- `gov.contrib.congress.wftca.bonus_guaranteed_deduction.phase_out.threshold.JOINT`
- `gov.contrib.congress.wftca.bonus_guaranteed_deduction.phase_out.threshold.SEPARATE`
- `gov.contrib.congress.wftca.bonus_guaranteed_deduction.phase_out.threshold.SINGLE`
- `gov.contrib.congress.wftca.bonus_guaranteed_deduction.phase_out.threshold.SURVIVING_SPOUSE`

### Parent: `gov.contrib.harris.capital_gains.thresholds.1`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.contrib.harris.capital_gains.thresholds.1.HEAD_OF_HOUSEHOLD`
- `gov.contrib.harris.capital_gains.thresholds.1.JOINT`
- `gov.contrib.harris.capital_gains.thresholds.1.SEPARATE`
- `gov.contrib.harris.capital_gains.thresholds.1.SINGLE`
- `gov.contrib.harris.capital_gains.thresholds.1.SURVIVING_SPOUSE`

### Parent: `gov.contrib.harris.capital_gains.thresholds.2`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.contrib.harris.capital_gains.thresholds.2.HEAD_OF_HOUSEHOLD`
- `gov.contrib.harris.capital_gains.thresholds.2.JOINT`
- `gov.contrib.harris.capital_gains.thresholds.2.SEPARATE`
- `gov.contrib.harris.capital_gains.thresholds.2.SINGLE`
- `gov.contrib.harris.capital_gains.thresholds.2.SURVIVING_SPOUSE`

### Parent: `gov.contrib.harris.capital_gains.thresholds.3`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.contrib.harris.capital_gains.thresholds.3.HEAD_OF_HOUSEHOLD`
- `gov.contrib.harris.capital_gains.thresholds.3.JOINT`
- `gov.contrib.harris.capital_gains.thresholds.3.SEPARATE`
- `gov.contrib.harris.capital_gains.thresholds.3.SINGLE`
- `gov.contrib.harris.capital_gains.thresholds.3.SURVIVING_SPOUSE`

### Parent: `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child`

- **Expected breakdown type**: `state_code`
- **Parent has label**: True
- **51 params**

- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.AK`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.AL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.AR`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.AZ`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.CA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.CO`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.CT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.DC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.DE`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.FL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.GA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.HI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.IA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.ID`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.IL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.IN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.KS`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.KY`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.LA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.MA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.MD`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.ME`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.MI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.MN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.MO`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.MS`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.MT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.NC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.ND`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.NE`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.NH`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.NJ`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.NM`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.NV`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.NY`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.OH`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.OK`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.OR`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.PA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.RI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.SC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.SD`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.TN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.TX`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.UT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.VA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.VT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.WA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.WI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.WV`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.child.child.WY`

### Parent: `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled`

- **Expected breakdown type**: `state_code`
- **Parent has label**: True
- **51 params**

- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.AK`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.AL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.AR`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.AZ`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.CA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.CO`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.CT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.DC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.DE`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.FL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.GA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.HI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.IA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.ID`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.IL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.IN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.KS`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.KY`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.LA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.MA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.MD`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.ME`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.MI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.MN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.MO`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.MS`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.MT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.NC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.ND`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.NE`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.NH`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.NJ`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.NM`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.NV`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.NY`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.OH`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.OK`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.OR`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.PA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.RI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.SC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.SD`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.TN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.TX`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.UT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.VA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.VT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.WA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.WI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.WV`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.disabled.WY`

### Parent: `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent`

- **Expected breakdown type**: `state_code`
- **Parent has label**: False
- **51 params**

- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.AK`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.AL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.AR`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.AZ`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.CA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.CO`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.CT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.DC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.DE`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.FL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.GA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.HI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.IA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.ID`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.IL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.IN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.KS`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.KY`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.LA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.MA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.MD`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.ME`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.MI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.MN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.MO`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.MS`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.MT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.NC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.ND`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.NE`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.NH`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.NJ`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.NM`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.NV`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.NY`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.OH`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.OK`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.OR`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.PA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.RI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.SC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.SD`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.TN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.TX`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.UT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.VA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.VT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.WA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.WI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.WV`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.parent.WY`

### Parent: `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant`

- **Expected breakdown type**: `state_code`
- **Parent has label**: True
- **51 params**

- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.AK`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.AL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.AR`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.AZ`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.CA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.CO`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.CT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.DC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.DE`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.FL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.GA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.HI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.IA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.ID`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.IL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.IN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.KS`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.KY`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.LA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.MA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.MD`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.ME`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.MI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.MN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.MO`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.MS`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.MT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.NC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.ND`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.NE`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.NH`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.NJ`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.NM`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.NV`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.NY`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.OH`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.OK`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.OR`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.PA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.RI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.SC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.SD`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.TN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.TX`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.UT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.VA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.VT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.WA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.WI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.WV`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.pregnant.WY`

### Parent: `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior`

- **Expected breakdown type**: `state_code`
- **Parent has label**: True
- **51 params**

- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.AK`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.AL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.AR`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.AZ`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.CA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.CO`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.CT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.DC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.DE`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.FL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.GA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.HI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.IA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.ID`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.IL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.IN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.KS`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.KY`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.LA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.MA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.MD`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.ME`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.MI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.MN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.MO`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.MS`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.MT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.NC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.ND`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.NE`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.NH`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.NJ`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.NM`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.NV`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.NY`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.OH`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.OK`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.OR`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.PA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.RI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.SC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.SD`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.TN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.TX`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.UT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.VA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.VT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.WA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.WI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.WV`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.categories.senior.WY`

### Parent: `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple`

- **Expected breakdown type**: `state_code`
- **Parent has label**: True
- **51 params**

- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.AK`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.AL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.AR`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.AZ`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.CA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.CO`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.CT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.DC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.DE`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.FL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.GA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.HI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.IA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.ID`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.IL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.IN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.KS`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.KY`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.LA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.MA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.MD`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.ME`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.MI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.MN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.MO`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.MS`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.MT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.NC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.ND`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.NE`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.NH`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.NJ`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.NM`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.NV`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.NY`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.OH`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.OK`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.OR`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.PA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.RI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.SC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.SD`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.TN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.TX`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.UT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.VA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.VT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.WA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.WI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.WV`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.couple.WY`

### Parent: `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual`

- **Expected breakdown type**: `state_code`
- **Parent has label**: True
- **51 params**

- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.AK`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.AL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.AR`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.AZ`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.CA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.CO`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.CT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.DC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.DE`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.FL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.GA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.HI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.IA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.ID`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.IL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.IN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.KS`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.KY`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.LA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.MA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.MD`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.ME`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.MI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.MN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.MO`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.MS`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.MT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.NC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.ND`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.NE`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.NH`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.NJ`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.NM`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.NV`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.NY`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.OH`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.OK`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.OR`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.PA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.RI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.SC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.SD`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.TN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.TX`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.UT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.VA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.VT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.WA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.WI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.WV`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.assets.individual.WY`

### Parent: `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple`

- **Expected breakdown type**: `state_code`
- **Parent has label**: True
- **51 params**

- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.AK`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.AL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.AR`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.AZ`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.CA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.CO`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.CT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.DC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.DE`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.FL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.GA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.HI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.IA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.ID`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.IL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.IN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.KS`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.KY`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.LA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.MA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.MD`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.ME`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.MI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.MN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.MO`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.MS`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.MT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.NC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.ND`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.NE`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.NH`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.NJ`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.NM`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.NV`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.NY`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.OH`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.OK`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.OR`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.PA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.RI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.SC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.SD`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.TN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.TX`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.UT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.VA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.VT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.WA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.WI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.WV`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.couple.WY`

### Parent: `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual`

- **Expected breakdown type**: `state_code`
- **Parent has label**: True
- **51 params**

- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.AK`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.AL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.AR`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.AZ`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.CA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.CO`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.CT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.DC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.DE`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.FL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.GA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.HI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.IA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.ID`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.IL`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.IN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.KS`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.KY`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.LA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.MA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.MD`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.ME`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.MI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.MN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.MO`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.MS`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.MT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.NC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.ND`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.NE`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.NH`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.NJ`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.NM`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.NV`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.NY`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.OH`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.OK`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.OR`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.PA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.RI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.SC`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.SD`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.TN`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.TX`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.UT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.VA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.VT`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.WA`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.WI`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.WV`
- `gov.hhs.medicaid.eligibility.categories.medically_needy.limit.income.individual.WY`

### Parent: `gov.hhs.smi.amount`

- **Expected breakdown type**: `state_code`
- **Parent has label**: True
- **52 params**

- `gov.hhs.smi.amount.AK`
- `gov.hhs.smi.amount.AL`
- `gov.hhs.smi.amount.AR`
- `gov.hhs.smi.amount.AZ`
- `gov.hhs.smi.amount.CA`
- `gov.hhs.smi.amount.CO`
- `gov.hhs.smi.amount.CT`
- `gov.hhs.smi.amount.DC`
- `gov.hhs.smi.amount.DE`
- `gov.hhs.smi.amount.FL`
- `gov.hhs.smi.amount.GA`
- `gov.hhs.smi.amount.HI`
- `gov.hhs.smi.amount.IA`
- `gov.hhs.smi.amount.ID`
- `gov.hhs.smi.amount.IL`
- `gov.hhs.smi.amount.IN`
- `gov.hhs.smi.amount.KS`
- `gov.hhs.smi.amount.KY`
- `gov.hhs.smi.amount.LA`
- `gov.hhs.smi.amount.MA`
- `gov.hhs.smi.amount.MD`
- `gov.hhs.smi.amount.ME`
- `gov.hhs.smi.amount.MI`
- `gov.hhs.smi.amount.MN`
- `gov.hhs.smi.amount.MO`
- `gov.hhs.smi.amount.MS`
- `gov.hhs.smi.amount.MT`
- `gov.hhs.smi.amount.NC`
- `gov.hhs.smi.amount.ND`
- `gov.hhs.smi.amount.NE`
- `gov.hhs.smi.amount.NH`
- `gov.hhs.smi.amount.NJ`
- `gov.hhs.smi.amount.NM`
- `gov.hhs.smi.amount.NV`
- `gov.hhs.smi.amount.NY`
- `gov.hhs.smi.amount.OH`
- `gov.hhs.smi.amount.OK`
- `gov.hhs.smi.amount.OR`
- `gov.hhs.smi.amount.PA`
- `gov.hhs.smi.amount.PR`
- `gov.hhs.smi.amount.RI`
- `gov.hhs.smi.amount.SC`
- `gov.hhs.smi.amount.SD`
- `gov.hhs.smi.amount.TN`
- `gov.hhs.smi.amount.TX`
- `gov.hhs.smi.amount.UT`
- `gov.hhs.smi.amount.VA`
- `gov.hhs.smi.amount.VT`
- `gov.hhs.smi.amount.WA`
- `gov.hhs.smi.amount.WI`
- `gov.hhs.smi.amount.WV`
- `gov.hhs.smi.amount.WY`

### Parent: `gov.irs.ald.loss.max`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: True
- **5 params**

- `gov.irs.ald.loss.max.HEAD_OF_HOUSEHOLD`
- `gov.irs.ald.loss.max.JOINT`
- `gov.irs.ald.loss.max.SEPARATE`
- `gov.irs.ald.loss.max.SINGLE`
- `gov.irs.ald.loss.max.SURVIVING_SPOUSE`

### Parent: `gov.irs.ald.misc.max_business_losses`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.irs.ald.misc.max_business_losses.HEAD_OF_HOUSEHOLD`
- `gov.irs.ald.misc.max_business_losses.JOINT`
- `gov.irs.ald.misc.max_business_losses.SEPARATE`
- `gov.irs.ald.misc.max_business_losses.SINGLE`
- `gov.irs.ald.misc.max_business_losses.SURVIVING_SPOUSE`

### Parent: `gov.irs.capital_gains.loss_limit`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.irs.capital_gains.loss_limit.HEAD_OF_HOUSEHOLD`
- `gov.irs.capital_gains.loss_limit.JOINT`
- `gov.irs.capital_gains.loss_limit.SEPARATE`
- `gov.irs.capital_gains.loss_limit.SINGLE`
- `gov.irs.capital_gains.loss_limit.SURVIVING_SPOUSE`

### Parent: `gov.irs.capital_gains.thresholds.1`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.irs.capital_gains.thresholds.1.HEAD_OF_HOUSEHOLD`
- `gov.irs.capital_gains.thresholds.1.JOINT`
- `gov.irs.capital_gains.thresholds.1.SEPARATE`
- `gov.irs.capital_gains.thresholds.1.SINGLE`
- `gov.irs.capital_gains.thresholds.1.SURVIVING_SPOUSE`

### Parent: `gov.irs.capital_gains.thresholds.2`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.irs.capital_gains.thresholds.2.HEAD_OF_HOUSEHOLD`
- `gov.irs.capital_gains.thresholds.2.JOINT`
- `gov.irs.capital_gains.thresholds.2.SEPARATE`
- `gov.irs.capital_gains.thresholds.2.SINGLE`
- `gov.irs.capital_gains.thresholds.2.SURVIVING_SPOUSE`

### Parent: `gov.irs.credits.cdcc.phase_out.amended_structure.second_increment`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: True
- **5 params**

- `gov.irs.credits.cdcc.phase_out.amended_structure.second_increment.HEAD_OF_HOUSEHOLD`
- `gov.irs.credits.cdcc.phase_out.amended_structure.second_increment.JOINT`
- `gov.irs.credits.cdcc.phase_out.amended_structure.second_increment.SEPARATE`
- `gov.irs.credits.cdcc.phase_out.amended_structure.second_increment.SINGLE`
- `gov.irs.credits.cdcc.phase_out.amended_structure.second_increment.SURVIVING_SPOUSE`

### Parent: `gov.irs.credits.ctc.phase_out.arpa.threshold`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: True
- **5 params**

- `gov.irs.credits.ctc.phase_out.arpa.threshold.HEAD_OF_HOUSEHOLD`
- `gov.irs.credits.ctc.phase_out.arpa.threshold.JOINT`
- `gov.irs.credits.ctc.phase_out.arpa.threshold.SEPARATE`
- `gov.irs.credits.ctc.phase_out.arpa.threshold.SINGLE`
- `gov.irs.credits.ctc.phase_out.arpa.threshold.SURVIVING_SPOUSE`

### Parent: `gov.irs.credits.elderly_or_disabled.phase_out.threshold`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.irs.credits.elderly_or_disabled.phase_out.threshold.HEAD_OF_HOUSEHOLD`
- `gov.irs.credits.elderly_or_disabled.phase_out.threshold.JOINT`
- `gov.irs.credits.elderly_or_disabled.phase_out.threshold.SEPARATE`
- `gov.irs.credits.elderly_or_disabled.phase_out.threshold.SINGLE`
- `gov.irs.credits.elderly_or_disabled.phase_out.threshold.SURVIVING_SPOUSE`

### Parent: `gov.irs.deductions.itemized.salt_and_real_estate.cap`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: True
- **5 params**

- `gov.irs.deductions.itemized.salt_and_real_estate.cap.HEAD_OF_HOUSEHOLD`
- `gov.irs.deductions.itemized.salt_and_real_estate.cap.JOINT`
- `gov.irs.deductions.itemized.salt_and_real_estate.cap.SEPARATE`
- `gov.irs.deductions.itemized.salt_and_real_estate.cap.SINGLE`
- `gov.irs.deductions.itemized.salt_and_real_estate.cap.SURVIVING_SPOUSE`

### Parent: `gov.irs.deductions.qbi.phase_out.length`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: True
- **5 params**

- `gov.irs.deductions.qbi.phase_out.length.HEAD_OF_HOUSEHOLD`
- `gov.irs.deductions.qbi.phase_out.length.JOINT`
- `gov.irs.deductions.qbi.phase_out.length.SEPARATE`
- `gov.irs.deductions.qbi.phase_out.length.SINGLE`
- `gov.irs.deductions.qbi.phase_out.length.SURVIVING_SPOUSE`

### Parent: `gov.irs.income.amt.exemption.amount`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.irs.income.amt.exemption.amount.HEAD_OF_HOUSEHOLD`
- `gov.irs.income.amt.exemption.amount.JOINT`
- `gov.irs.income.amt.exemption.amount.SEPARATE`
- `gov.irs.income.amt.exemption.amount.SINGLE`
- `gov.irs.income.amt.exemption.amount.SURVIVING_SPOUSE`

### Parent: `gov.irs.income.amt.exemption.phase_out.start`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.irs.income.amt.exemption.phase_out.start.HEAD_OF_HOUSEHOLD`
- `gov.irs.income.amt.exemption.phase_out.start.JOINT`
- `gov.irs.income.amt.exemption.phase_out.start.SEPARATE`
- `gov.irs.income.amt.exemption.phase_out.start.SINGLE`
- `gov.irs.income.amt.exemption.phase_out.start.SURVIVING_SPOUSE`

### Parent: `gov.irs.income.bracket.thresholds.1`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.irs.income.bracket.thresholds.1.HEAD_OF_HOUSEHOLD`
- `gov.irs.income.bracket.thresholds.1.JOINT`
- `gov.irs.income.bracket.thresholds.1.SEPARATE`
- `gov.irs.income.bracket.thresholds.1.SINGLE`
- `gov.irs.income.bracket.thresholds.1.SURVIVING_SPOUSE`

### Parent: `gov.irs.income.bracket.thresholds.2`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.irs.income.bracket.thresholds.2.HEAD_OF_HOUSEHOLD`
- `gov.irs.income.bracket.thresholds.2.JOINT`
- `gov.irs.income.bracket.thresholds.2.SEPARATE`
- `gov.irs.income.bracket.thresholds.2.SINGLE`
- `gov.irs.income.bracket.thresholds.2.SURVIVING_SPOUSE`

### Parent: `gov.irs.income.bracket.thresholds.3`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.irs.income.bracket.thresholds.3.HEAD_OF_HOUSEHOLD`
- `gov.irs.income.bracket.thresholds.3.JOINT`
- `gov.irs.income.bracket.thresholds.3.SEPARATE`
- `gov.irs.income.bracket.thresholds.3.SINGLE`
- `gov.irs.income.bracket.thresholds.3.SURVIVING_SPOUSE`

### Parent: `gov.irs.income.bracket.thresholds.4`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.irs.income.bracket.thresholds.4.HEAD_OF_HOUSEHOLD`
- `gov.irs.income.bracket.thresholds.4.JOINT`
- `gov.irs.income.bracket.thresholds.4.SEPARATE`
- `gov.irs.income.bracket.thresholds.4.SINGLE`
- `gov.irs.income.bracket.thresholds.4.SURVIVING_SPOUSE`

### Parent: `gov.irs.income.bracket.thresholds.5`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.irs.income.bracket.thresholds.5.HEAD_OF_HOUSEHOLD`
- `gov.irs.income.bracket.thresholds.5.JOINT`
- `gov.irs.income.bracket.thresholds.5.SEPARATE`
- `gov.irs.income.bracket.thresholds.5.SINGLE`
- `gov.irs.income.bracket.thresholds.5.SURVIVING_SPOUSE`

### Parent: `gov.irs.income.bracket.thresholds.6`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.irs.income.bracket.thresholds.6.HEAD_OF_HOUSEHOLD`
- `gov.irs.income.bracket.thresholds.6.JOINT`
- `gov.irs.income.bracket.thresholds.6.SEPARATE`
- `gov.irs.income.bracket.thresholds.6.SINGLE`
- `gov.irs.income.bracket.thresholds.6.SURVIVING_SPOUSE`

### Parent: `gov.irs.income.bracket.thresholds.7`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.irs.income.bracket.thresholds.7.HEAD_OF_HOUSEHOLD`
- `gov.irs.income.bracket.thresholds.7.JOINT`
- `gov.irs.income.bracket.thresholds.7.SEPARATE`
- `gov.irs.income.bracket.thresholds.7.SINGLE`
- `gov.irs.income.bracket.thresholds.7.SURVIVING_SPOUSE`

### Parent: `gov.irs.income.exemption.phase_out.start`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.irs.income.exemption.phase_out.start.HEAD_OF_HOUSEHOLD`
- `gov.irs.income.exemption.phase_out.start.JOINT`
- `gov.irs.income.exemption.phase_out.start.SEPARATE`
- `gov.irs.income.exemption.phase_out.start.SINGLE`
- `gov.irs.income.exemption.phase_out.start.SURVIVING_SPOUSE`

### Parent: `gov.irs.income.exemption.phase_out.step_size`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.irs.income.exemption.phase_out.step_size.HEAD_OF_HOUSEHOLD`
- `gov.irs.income.exemption.phase_out.step_size.JOINT`
- `gov.irs.income.exemption.phase_out.step_size.SEPARATE`
- `gov.irs.income.exemption.phase_out.step_size.SINGLE`
- `gov.irs.income.exemption.phase_out.step_size.SURVIVING_SPOUSE`

### Parent: `gov.irs.investment.net_investment_income_tax.threshold`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.irs.investment.net_investment_income_tax.threshold.HEAD_OF_HOUSEHOLD`
- `gov.irs.investment.net_investment_income_tax.threshold.JOINT`
- `gov.irs.investment.net_investment_income_tax.threshold.SEPARATE`
- `gov.irs.investment.net_investment_income_tax.threshold.SINGLE`
- `gov.irs.investment.net_investment_income_tax.threshold.SURVIVING_SPOUSE`

### Parent: `gov.irs.payroll.medicare.additional.exclusion`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: True
- **5 params**

- `gov.irs.payroll.medicare.additional.exclusion.HEAD_OF_HOUSEHOLD`
- `gov.irs.payroll.medicare.additional.exclusion.JOINT`
- `gov.irs.payroll.medicare.additional.exclusion.SEPARATE`
- `gov.irs.payroll.medicare.additional.exclusion.SINGLE`
- `gov.irs.payroll.medicare.additional.exclusion.SURVIVING_SPOUSE`

### Parent: `gov.irs.unemployment_compensation.exemption.cutoff`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.irs.unemployment_compensation.exemption.cutoff.HEAD_OF_HOUSEHOLD`
- `gov.irs.unemployment_compensation.exemption.cutoff.JOINT`
- `gov.irs.unemployment_compensation.exemption.cutoff.SEPARATE`
- `gov.irs.unemployment_compensation.exemption.cutoff.SINGLE`
- `gov.irs.unemployment_compensation.exemption.cutoff.SURVIVING_SPOUSE`

### Parent: `gov.states.ca.calepa.carb.cvrp.income_cap`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: False
- **5 params**

- `gov.states.ca.calepa.carb.cvrp.income_cap.HEAD_OF_HOUSEHOLD`
- `gov.states.ca.calepa.carb.cvrp.income_cap.JOINT`
- `gov.states.ca.calepa.carb.cvrp.income_cap.SEPARATE`
- `gov.states.ca.calepa.carb.cvrp.income_cap.SINGLE`
- `gov.states.ca.calepa.carb.cvrp.income_cap.SURVIVING_SPOUSE`

### Parent: `gov.states.il.tax.income.exemption.income_limit`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: True
- **5 params**

- `gov.states.il.tax.income.exemption.income_limit.HEAD_OF_HOUSEHOLD`
- `gov.states.il.tax.income.exemption.income_limit.JOINT`
- `gov.states.il.tax.income.exemption.income_limit.SEPARATE`
- `gov.states.il.tax.income.exemption.income_limit.SINGLE`
- `gov.states.il.tax.income.exemption.income_limit.SURVIVING_SPOUSE`

### Parent: `gov.states.ks.tax.income.exemptions.by_filing_status.amount`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: True
- **5 params**

- `gov.states.ks.tax.income.exemptions.by_filing_status.amount.HEAD_OF_HOUSEHOLD`
- `gov.states.ks.tax.income.exemptions.by_filing_status.amount.JOINT`
- `gov.states.ks.tax.income.exemptions.by_filing_status.amount.SEPARATE`
- `gov.states.ks.tax.income.exemptions.by_filing_status.amount.SINGLE`
- `gov.states.ks.tax.income.exemptions.by_filing_status.amount.SURVIVING_SPOUSE`

### Parent: `gov.states.mn.tax.income.subtractions.social_security.reduction.increment`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: True
- **5 params**

- `gov.states.mn.tax.income.subtractions.social_security.reduction.increment.HEAD_OF_HOUSEHOLD`
- `gov.states.mn.tax.income.subtractions.social_security.reduction.increment.JOINT`
- `gov.states.mn.tax.income.subtractions.social_security.reduction.increment.SEPARATE`
- `gov.states.mn.tax.income.subtractions.social_security.reduction.increment.SINGLE`
- `gov.states.mn.tax.income.subtractions.social_security.reduction.increment.SURVIVING_SPOUSE`

### Parent: `gov.states.ny.tax.income.deductions.itemized.phase_out.start`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: True
- **5 params**

- `gov.states.ny.tax.income.deductions.itemized.phase_out.start.HEAD_OF_HOUSEHOLD`
- `gov.states.ny.tax.income.deductions.itemized.phase_out.start.JOINT`
- `gov.states.ny.tax.income.deductions.itemized.phase_out.start.SEPARATE`
- `gov.states.ny.tax.income.deductions.itemized.phase_out.start.SINGLE`
- `gov.states.ny.tax.income.deductions.itemized.phase_out.start.SURVIVING_SPOUSE`

### Parent: `gov.states.ny.tax.income.deductions.itemized.reduction.incremental.lower.income_threshold`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: True
- **5 params**

- `gov.states.ny.tax.income.deductions.itemized.reduction.incremental.lower.income_threshold.HEAD_OF_HOUSEHOLD`
- `gov.states.ny.tax.income.deductions.itemized.reduction.incremental.lower.income_threshold.JOINT`
- `gov.states.ny.tax.income.deductions.itemized.reduction.incremental.lower.income_threshold.SEPARATE`
- `gov.states.ny.tax.income.deductions.itemized.reduction.incremental.lower.income_threshold.SINGLE`
- `gov.states.ny.tax.income.deductions.itemized.reduction.incremental.lower.income_threshold.SURVIVING_SPOUSE`

### Parent: `gov.states.ut.tax.income.credits.retirement.phase_out.threshold`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: True
- **5 params**

- `gov.states.ut.tax.income.credits.retirement.phase_out.threshold.HEAD_OF_HOUSEHOLD`
- `gov.states.ut.tax.income.credits.retirement.phase_out.threshold.JOINT`
- `gov.states.ut.tax.income.credits.retirement.phase_out.threshold.SEPARATE`
- `gov.states.ut.tax.income.credits.retirement.phase_out.threshold.SINGLE`
- `gov.states.ut.tax.income.credits.retirement.phase_out.threshold.SURVIVING_SPOUSE`

### Parent: `gov.states.ut.tax.income.credits.ss_benefits.phase_out.threshold`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: True
- **5 params**

- `gov.states.ut.tax.income.credits.ss_benefits.phase_out.threshold.HEAD_OF_HOUSEHOLD`
- `gov.states.ut.tax.income.credits.ss_benefits.phase_out.threshold.JOINT`
- `gov.states.ut.tax.income.credits.ss_benefits.phase_out.threshold.SEPARATE`
- `gov.states.ut.tax.income.credits.ss_benefits.phase_out.threshold.SINGLE`
- `gov.states.ut.tax.income.credits.ss_benefits.phase_out.threshold.SURVIVING_SPOUSE`

### Parent: `gov.states.ut.tax.income.credits.taxpayer.phase_out.threshold`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: True
- **5 params**

- `gov.states.ut.tax.income.credits.taxpayer.phase_out.threshold.HEAD_OF_HOUSEHOLD`
- `gov.states.ut.tax.income.credits.taxpayer.phase_out.threshold.JOINT`
- `gov.states.ut.tax.income.credits.taxpayer.phase_out.threshold.SEPARATE`
- `gov.states.ut.tax.income.credits.taxpayer.phase_out.threshold.SINGLE`
- `gov.states.ut.tax.income.credits.taxpayer.phase_out.threshold.SURVIVING_SPOUSE`

### Parent: `gov.states.wi.tax.income.additions.capital_loss.limit`

- **Expected breakdown type**: `filing_status`
- **Parent has label**: True
- **5 params**

- `gov.states.wi.tax.income.additions.capital_loss.limit.HEAD_OF_HOUSEHOLD`
- `gov.states.wi.tax.income.additions.capital_loss.limit.JOINT`
- `gov.states.wi.tax.income.additions.capital_loss.limit.SEPARATE`
- `gov.states.wi.tax.income.additions.capital_loss.limit.SINGLE`
- `gov.states.wi.tax.income.additions.capital_loss.limit.SURVIVING_SPOUSE`

---

## Pseudo-Bracket Params

**0 params**

All bracket-style params (`[n].field`) have proper ParameterScale parents.

---

## Examples of Each Category

### Explicit Labels (first 10)
- `calibration.gov.cbo.snap`: "Total SNAP outlays"
- `calibration.gov.cbo.social_security`: "Social Security benefits"
- `calibration.gov.cbo.ssi`: "SSI outlays"
- `calibration.gov.cbo.unemployment_compensation`: "Unemployment compensation outlays"
- `calibration.gov.cbo.income_by_source.adjusted_gross_income`: "Total AGI"
- `calibration.gov.cbo.income_by_source.employment_income`: "Total employment income"
- `calibration.gov.cbo.payroll_taxes`: "Payroll tax revenues"
- `calibration.gov.cbo.income_tax`: "Income tax revenue"
- `calibration.gov.irs.soi.rental_income`: "SOI rental income"
- `calibration.gov.irs.soi.returns_by_filing_status.SINGLE`: "Single"

### Bracket Params WITH Scale Label (first 10)
- `calibration.gov.irs.soi.agi.total_agi[0].threshold`: "AGI aggregate by band (bracket 1 threshold)"
- `calibration.gov.irs.soi.agi.total_agi[0].amount`: "AGI aggregate by band (bracket 1 amount)"
- `calibration.gov.irs.soi.agi.total_agi[1].threshold`: "AGI aggregate by band (bracket 2 threshold)"
- `calibration.gov.irs.soi.agi.total_agi[1].amount`: "AGI aggregate by band (bracket 2 amount)"
- `calibration.gov.irs.soi.agi.total_agi[2].threshold`: "AGI aggregate by band (bracket 3 threshold)"
- `calibration.gov.irs.soi.agi.total_agi[2].amount`: "AGI aggregate by band (bracket 3 amount)"
- `calibration.gov.irs.soi.agi.total_agi[3].threshold`: "AGI aggregate by band (bracket 4 threshold)"
- `calibration.gov.irs.soi.agi.total_agi[3].amount`: "AGI aggregate by band (bracket 4 amount)"
- `calibration.gov.irs.soi.agi.total_agi[4].threshold`: "AGI aggregate by band (bracket 5 threshold)"
- `calibration.gov.irs.soi.agi.total_agi[4].amount`: "AGI aggregate by band (bracket 5 amount)"

### Breakdown Params WITH Parent Label (first 10)
- `calibration.gov.aca.enrollment.state.AK`: "ACA enrollment by state (AK)"
- `calibration.gov.aca.enrollment.state.AL`: "ACA enrollment by state (AL)"
- `calibration.gov.aca.enrollment.state.AR`: "ACA enrollment by state (AR)"
- `calibration.gov.aca.enrollment.state.AZ`: "ACA enrollment by state (AZ)"
- `calibration.gov.aca.enrollment.state.CA`: "ACA enrollment by state (CA)"
- `calibration.gov.aca.enrollment.state.CO`: "ACA enrollment by state (CO)"
- `calibration.gov.aca.enrollment.state.CT`: "ACA enrollment by state (CT)"
- `calibration.gov.aca.enrollment.state.DC`: "ACA enrollment by state (DC)"
- `calibration.gov.aca.enrollment.state.DE`: "ACA enrollment by state (DE)"
- `calibration.gov.aca.enrollment.state.FL`: "ACA enrollment by state (FL)"

### Regular Params Without Label (first 20)
- `calibration.gov.cbo.income_by_source.taxable_interest_and_ordinary_dividends`
- `calibration.gov.cbo.income_by_source.qualified_dividend_income`
- `calibration.gov.cbo.income_by_source.net_capital_gain`
- `calibration.gov.cbo.income_by_source.self_employment_income`
- `calibration.gov.cbo.income_by_source.taxable_pension_income`
- `calibration.gov.cbo.income_by_source.taxable_social_security`
- `calibration.gov.cbo.income_by_source.irs_other_income`
- `calibration.gov.cbo.income_by_source.above_the_line_deductions`
- `calibration.gov.usda.snap.participation`
- `calibration.gov.ssa.ssi.participation`
- `calibration.gov.ssa.social_security.participation`
- `calibration.gov.census.populations.total`
- `calibration.gov.census.populations.by_state.AK`
- `calibration.gov.census.populations.by_state.AL`
- `calibration.gov.census.populations.by_state.AR`
- `calibration.gov.census.populations.by_state.AZ`
- `calibration.gov.census.populations.by_state.CA`
- `calibration.gov.census.populations.by_state.CO`
- `calibration.gov.census.populations.by_state.CT`
- `calibration.gov.census.populations.by_state.DC`

---

## Updated Analysis (Corrected Counts)

**Note**: This updated analysis corrects the earlier counts by properly accounting for all breakdown parents with labels. Many parameters previously classified as "regular without label" are actually breakdown parameters with parent labels.

### Revised Summary

| Category | Count | Percentage | Description |
|----------|-------|------------|-------------|
| Breakdown With Parent Label | 40,115 | 73.2% | Breakdown param with parent label → label auto-generated |
| Bracket With Scale Label | 7,235 | 13.2% | Bracket param with scale label → label auto-generated |
| Explicit Label | 5,228 | 9.5% | Has explicit label in YAML metadata |
| Regular Without Label | 925 | 1.7% | Not breakdown/bracket, no explicit label |
| Pseudo Breakdown | 799 | 1.5% | Looks like breakdown but no metadata |
| Breakdown Without Parent Label | 445 | 0.8% | Breakdown param but parent has no label |
| Bracket Without Scale Label | 68 | 0.1% | Bracket param but scale has no label |

**Total parameters**: 54,815
**Parameters with labels (explicit or generated)**: 52,578 (95.9%)
**Parameters without labels**: 2,237 (4.1%)

---

## Regular Parameters Without Labels (925 params)

These are the truly "orphan" parameters that cannot get labels through any automatic mechanism.

### Breakdown by Program Area

| Program Area | Count | Examples |
|--------------|-------|----------|
| HHS (CCDF, SMI) | 530 | first_person, second_to_sixth_person, additional_person... |
| State: IN | 92 | ADAMS_COUNTY_IN, ALLEN_COUNTY_IN, BATHOLOMEW_COUNTY_IN... |
| State: CA | 73 | categorical_eligibility, True, False... |
| State: CO | 70 | subtractions, ADAMS_COUNTY_CO, ALAMOSA_COUNTY_CO... |
| USDA (SNAP, WIC, School Meals) | 35 | maximum_household_size, rate, relevant_max_allotment_household_size... |
| Local Tax | 24 | ALLEGANY_COUNTY_MD, ANNE_ARUNDEL_COUNTY_MD, BALTIMORE_CITY_MD... |
| ACA (Affordable Care Act) | 22 | 906, 907, 908... |
| IRS (Federal Tax) | 22 | rate, amount, additional_earned_income... |
| Calibration Data | 12 | taxable_interest_and_ordinary_dividends, qualified_dividend_income... |
| Education (Pell Grant) | 11 | A, B, C... |
| State: WI | 10 | exemption, rate... |
| FCC (Broadband Benefits) | 5 | prior_enrollment_required, tribal, standard... |
| Contributed/Proposed Policies | 4 | 1, 2, 3... |
| State: NC | 3 | value, mortgage_and_property_tax, deductions |
| State: MD | 3 | non_refundable, refundable, additional |
| State: NJ | 2 | unearned, earned |
| State: NY | 2 | unearned, earned |
| Simulation Config | 1 | marginal_tax_rate_delta |
| OpenFisca Meta | 1 | us |
| SSA (Social Security) | 1 | pass_rate |
| State: KY | 1 | subtractions |
| State: WV | 1 | applies |

### Key Trends Identified

1. **CCDF (Child Care) Parameters (530)**: Most are NY county-specific copay percentages and cluster assignments, plus multi-dimensional rate tables (care type × duration × age group)

2. **County-Level Tax Rates (190+)**: Indiana (92), Colorado (64), Maryland (24) counties have individual tax rate parameters

3. **LA County Rating Areas (22)**: ACA health insurance rating area costs for Los Angeles sub-areas

4. **Multi-Dimensional Lookup Tables**: Parameters with numeric suffixes (1-5) or code-based keys (A, B, C) that aren't using proper breakdown metadata

---

## High-Priority Parameters for Policy Understanding

These parameters are most relevant for understanding US tax and benefit policy:

### Federal Tax (IRS)

| Parameter | Description |
|-----------|-------------|
| `gov.irs.credits.elderly_or_disabled.amount.base` | Base credit for elderly/disabled |
| `gov.irs.credits.elderly_or_disabled.amount.joint_both_eligible` | Joint credit when both qualify |
| `gov.irs.credits.elderly_or_disabled.amount.married_separate` | Credit for married filing separately |
| `gov.irs.credits.education.american_opportunity_credit.phase_out` | AOTC phase-out threshold |
| `gov.irs.income.amt.exemption.SINGLE/JOINT/SEPARATE` | AMT exemption amounts by filing status |
| `gov.irs.income.exemption.base` | Personal exemption amount |
| `gov.irs.income.exemption.phase_out` | Personal exemption phase-out threshold |
| `gov.irs.deductions.standard.dependent.additional_earned_income` | Standard deduction for dependents |
| `gov.irs.deductions.standard.dependent.base` | Base standard deduction for dependents |
| `gov.irs.capital_gains.rates.0_percent_rate` | 0% capital gains rate threshold |
| `gov.irs.capital_gains.rates.15_percent_rate` | 15% capital gains rate threshold |
| `gov.irs.capital_gains.rates.20_percent_rate` | 20% capital gains rate |
| `gov.irs.investment.net_investment_income_tax.rate` | NIIT rate (3.8%) |
| `gov.irs.ald.misc.educator_expense` | Teacher expense deduction |
| `gov.irs.ald.self_employment_tax.employer_half_rate` | SE tax employer portion rate |
| `gov.irs.unemployment_compensation.exemption.amount` | UI benefit exemption amount |

### SNAP (Food Stamps)

| Parameter | Description |
|-----------|-------------|
| `gov.usda.snap.min_allotment.rate` | Minimum benefit as fraction of max |
| `gov.usda.snap.min_allotment.maximum_household_size` | Max HH size for minimum allotment |
| `gov.usda.snap.expected_contribution` | Expected income contribution rate |
| `gov.usda.snap.categorical_eligibility` | Categorical eligibility rules |
| `gov.usda.snap.asset_test.limit.non_elderly` | Asset limit for non-elderly |
| `gov.usda.snap.asset_test.limit.elderly_disabled` | Asset limit for elderly/disabled |
| `gov.usda.snap.income.sources.earned/unearned` | Income source definitions |
| `gov.usda.snap.income.deductions.earned` | Earned income deduction rate |

### SSI/SSA

| Parameter | Description |
|-----------|-------------|
| `gov.ssa.ssi.eligibility.pass_rate` | Pass eligibility rate |

### Education

| Parameter | Description |
|-----------|-------------|
| `gov.ed.pell_grant.head.asset_assessment_rate.A/B/C` | Asset assessment rates by category |
| `gov.ed.pell_grant.head.income_assessment_rate.A/B/C` | Income assessment rates by category |
| `gov.ed.pell_grant.sai.fpg_fraction.min_pell_limits.*` | Min Pell eligibility thresholds |

### FCC Broadband Benefits

| Parameter | Description |
|-----------|-------------|
| `gov.fcc.ebb.amount.standard` | Standard EBB monthly benefit |
| `gov.fcc.ebb.amount.tribal` | Tribal lands EBB benefit |
| `gov.fcc.acp.categorical_eligibility.applies` | ACP categorical eligibility |

### WIC

| Parameter | Description |
|-----------|-------------|
| `gov.usda.wic.value.PREGNANT` | WIC package value for pregnant women |
| `gov.usda.wic.value.BREASTFEEDING` | WIC value for breastfeeding |
| `gov.usda.wic.value.POSTPARTUM` | WIC value for postpartum |
| `gov.usda.wic.value.INFANT` | WIC value for infants |
| `gov.usda.wic.value.CHILD` | WIC value for children |

---

## Recommendations

### Quick Wins (Fix 81 YAML files to cover 1,312 params)

1. **Add labels to 8 bracket scales** (covers 68 params):
   - `gov.irs.credits.education.american_opportunity_credit.amount`
   - `gov.irs.credits.eitc.phase_out.joint_bonus`
   - `gov.irs.credits.premium_tax_credit.eligibility`
   - `gov.irs.credits.premium_tax_credit.phase_out.ending_rate`
   - `gov.irs.credits.premium_tax_credit.phase_out.starting_rate`
   - Plus 3 state-level scales

2. **Add labels to 12 breakdown parents** (covers 445 params):
   - Child care rate parents
   - State tax thresholds

3. **Add breakdown metadata + labels to 61 pseudo-breakdown parents** (covers 799 params):
   - Filing status breakdowns missing metadata
   - State-level breakdowns missing metadata

### Medium-Priority Fixes

1. Add explicit labels to the 22 high-priority federal IRS params
2. Add explicit labels to the 10 SNAP params
3. Add explicit labels to WIC package value params

### Low Priority (Administrative/Calibration)

- County cluster mappings (124 params) - internal lookup tables
- Copay percentages (62 params) - county-specific rates
- Calibration data (12 params) - historical data points
- LA County rating areas (22 params) - geographic codes

---

## Complete List: Regular Parameters Without Labels

### HHS (530 params)

#### CCDF Amount Tables (400 params)
Multi-dimensional rate tables by cluster (1-5), care type, duration, and age group:
- Clusters: 1, 2, 3, 4, 5
- Care types: DCC_SACC, FDC_GFDC, LE_ENH, LE_GC, LE_STD
- Durations: DAILY, HOURLY, PART_DAY, WEEKLY
- Age groups: INFANT, TODDLER, PRESCHOOLER, SCHOOL_AGE

#### CCDF County Clusters (62 params)
NY county → cluster mappings (e.g., `gov.hhs.ccdf.county_cluster.ALBANY_COUNTY_NY`)

#### CCDF Copay Percentages (62 params)
NY county copay rates (e.g., `gov.hhs.ccdf.copay_percent.ALBANY_COUNTY_NY`)

#### Other CCDF (3 params)
- `gov.hhs.ccdf.age_limit`
- `gov.hhs.ccdf.asset_limit`
- `gov.hhs.ccdf.income_limit_smi`

#### SMI Household Adjustments (3 params)
- `gov.hhs.smi.household_size_adjustment.first_person`
- `gov.hhs.smi.household_size_adjustment.second_to_sixth_person`
- `gov.hhs.smi.household_size_adjustment.additional_person`

### State: IN (92 params)
Indiana county income tax rates:
- `gov.states.in.tax.income.county_rates.ADAMS_COUNTY_IN` through `WHITLEY_COUNTY_IN`

### State: CA (73 params)
California TANF parameters:
- `gov.states.ca.cdss.tanf.*` (various eligibility and benefit parameters)
- `gov.states.ca.calepa.cvrp.income_limit_ami` (EV rebate)

### State: CO (70 params)
Colorado child care and tax parameters:
- `gov.states.co.ccap.entry.*` (child care assistance, 64 params by county)
- `gov.states.co.cdhs.tanf.*` (5 params)
- `gov.states.co.tax.income.subtractions.pension_subtraction.age` (1 param)

### USDA (35 params)
- SNAP: 10 params (min_allotment, income, asset_test, categorical_eligibility)
- WIC: 21 params (value by participant category and formula type)
- School Meals: 2 params (school_days, income sources)
- Disabled Programs: 1 param
- Elderly Age Threshold: 1 param

### Local Tax (24 params)
Maryland county income tax rates:
- `gov.local.tax.income.flat_tax_rate.*` (24 MD counties)

### ACA (22 params)
LA County rating area mappings:
- `gov.aca.la_county_rating_area.900` through `gov.aca.la_county_rating_area.935`

### IRS (22 params)
- Elderly/disabled credit amounts (3 params)
- AMT exemption by filing status (3 params)
- Personal exemption (2 params)
- Dependent standard deduction (2 params)
- Capital gains rates (3 params)
- NIIT rate (1 param)
- Educator expense (1 param)
- SE tax rate (1 param)
- UI exemption (1 param)
- Education credit phase-out (1 param)
- Other misc (4 params)

### Calibration (12 params)
CBO income projections and program participation rates

### Education (11 params)
Pell Grant assessment rates and eligibility thresholds

### Other States (23 params combined)
- WI: 10 params (income tax)
- NC: 3 params
- MD: 3 params (TANF)
- NJ: 2 params (TANF)
- NY: 2 params (TANF)
- KY: 1 param
- WV: 1 param

### Misc (7 params)
- FCC: 5 params (EBB/ACP)
- Contrib: 4 params (Harris capital gains proposal)
- Simulation: 1 param
- OpenFisca: 1 param
- SSA: 1 param
