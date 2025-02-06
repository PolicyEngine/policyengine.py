# US parameters

This page shows a list of available parameters for reforms for the US model.

We exclude from this list:

* Abolition parameters, which mirror each household property and allow the user to set the value of the property to zero (these take the format `gov.abolitions.variable_name`) because these roughly triple the size of this list and are repetitive.
### calibration.gov.cbo.snap
**Label:** Total SNAP outlays

Total SNAP benefits.

**Type:** int

**Current value:** 93499000000

---

### calibration.gov.cbo.social_security
**Label:** Social Security benefits

Social Security total benefits.

**Type:** int

**Current value:** 1549110000000

---

### calibration.gov.cbo.ssi
**Label:** SSI outlays

SSI total outlays.

**Type:** int

**Current value:** 64000000000

---

### calibration.gov.cbo.unemployment_compensation
**Label:** Unemployment compensation outlays

Unemployment compensation total outlays.

**Type:** int

**Current value:** 37801000000

---

### calibration.gov.cbo.income_by_source.adjusted_gross_income
**Label:** Total AGI

**Type:** int

**Current value:** 17326481000000

---

### calibration.gov.cbo.income_by_source.employment_income
**Label:** Total employment income

**Type:** int

**Current value:** 11422200000000

---

### calibration.gov.cbo.payroll_taxes
**Label:** Payroll tax revenues

Historical total federal revenues from payroll taxes (2017-2022)

**Type:** int

**Current value:** 1737193000000

---

### calibration.gov.cbo.income_tax
**Label:** Income tax revenue

Individual income tax revenue projections (excludes the Premium Tax Credit).

**Type:** int

**Current value:** 2550000000000

---

### calibration.gov.irs.soi.rental_income
**Label:** SOI rental income

Total rental/royalty net income.

**Type:** float

**Current value:** 53884109207.42199

---

### calibration.gov.irs.soi.returns_by_filing_status.SINGLE
**Label:** Single

**Type:** float

**Current value:** 84359456.52088538

---

### calibration.gov.irs.soi.returns_by_filing_status.JOINT
**Label:** Joint (includes widow(er)s)

**Type:** float

**Current value:** 56204914.57638226

---

### calibration.gov.irs.soi.returns_by_filing_status.HEAD_OF_HOUSEHOLD
**Label:** Head of household

**Type:** float

**Current value:** 22006397.47974301

---

### calibration.gov.irs.soi.returns_by_filing_status.SEPARATE
**Label:** Married filing separately

**Type:** float

**Current value:** 4054069.106143078

---

### calibration.gov.irs.soi.partnership_s_corp_income
**Label:** SOI partnership and S-corp income

Total partnership and S-corp income.

**Type:** float

**Current value:** 1145256886035.313

---

### calibration.gov.irs.soi.long_term_capital_gains
**Label:** SOI long-term capital gains

Total long-term capital gains.

**Type:** float

**Current value:** 1411800425608.3333

---

### calibration.gov.irs.soi.social_security
**Label:** SOI social security

Total social security.

**Type:** float

**Current value:** 1157378190142.132

---

### calibration.gov.irs.soi.employment_income
**Label:** SOI employment income

Total employment income.

**Type:** float

**Current value:** 11422140424132.184

---

### calibration.gov.irs.soi.self_employment_income
**Label:** SOI self-employment income

Total self-employment income.

**Type:** float

**Current value:** 681645787516.9231

---

### calibration.gov.irs.soi.farm_income
**Label:** SOI farm income

Total farm income.

**Type:** float

**Current value:** -30622507943.26761

---

### calibration.gov.irs.soi.unemployment_compensation
**Label:** SOI unemployment compensation

Total unemployment compensation.

**Type:** float

**Current value:** 311019579405.3662

---

### calibration.gov.irs.soi.farm_rent_income
**Label:** SOI farm rental income

Total farm rental income.

**Type:** float

**Current value:** 7161930234.715397

---

### calibration.gov.irs.soi.tax_exempt_pension_income
**Label:** SOI tax-exempt pension income

Total tax-exempt pension income.

**Type:** float

**Current value:** 810688304997.5155

---

### calibration.gov.irs.soi.non_qualified_dividend_income
**Label:** SOI non-qualified dividend income

Total non-qualified dividend income.

**Type:** float

**Current value:** 96664769126.82927

---

### calibration.gov.irs.soi.qualified_dividend_income
**Label:** SOI qualified dividend income

Total qualified dividend income.

**Type:** float

**Current value:** 371959126439.02435

---

### calibration.gov.irs.soi.short_term_capital_gains
**Label:** SOI short-term capital gains

Total short-term capital gains. Taken from the IRS PUF in the absence of a SOI target.

**Type:** float

**Current value:** -80009944064.63641

---

### calibration.gov.irs.soi.taxable_interest_income
**Label:** SOI taxable interest income

Total taxable interest income.

**Type:** float

**Current value:** 171032662482.98755

---

### calibration.gov.irs.soi.alimony_income
**Label:** SOI short-term capital gains

Total alimony income.

**Type:** float

**Current value:** 9965167847.280357

---

### calibration.gov.irs.soi.taxable_pension_income
**Label:** SOI taxable pension income

Total taxable pension income.

**Type:** float

**Current value:** 1156066637126.708

---

### calibration.gov.irs.soi.tax_exempt_interest_income
**Label:** SOI tax-exempt interest income

Total tax-exempt interest income.

**Type:** float

**Current value:** 79824610063.07053

---

### calibration.gov.treasury.tax_expenditures.eitc
**Label:** EITC outlays

EITC estimated outlays by the Treasury Department.

**Type:** int

**Current value:** 68650000000

---

### simulation.va.branch_to_determine_if_refundable_eitc
**Label:** Branch to determine Virginia refundability

PolicyEngine branches to determine whether filers claim the refundable over non-refundable Virginia EITC, as they can choose depending on which minimizes tax liability.

**Type:** bool

**Current value:** False

---

### simulation.marginal_tax_rate_adults
**Label:** Number of adults to simulate a marginal tax rate for

Number of adults to simulate a marginal tax rate for, in each household.

**Type:** int

**Current value:** 2

---

### simulation.branch_to_determine_itemization
**Label:** Branch to determine itemization

PolicyEngine branches to determine itemization if this is true; otherwise it compares the standard against itemized deductions.

**Type:** bool

**Current value:** False

---

### simulation.reported_state_income_tax
**Label:** Use reported State income tax

Whether to take State income tax liabilities as reported.

**Type:** bool

**Current value:** False

---

### simulation.de.branch_to_determine_if_refundable_eitc
**Label:** Branch to determine delaware refundability

PolicyEngine branches to determine whether filers claim the refundable over non-refundable Delaware EITC, as they can choose depending on which minimizes tax liability.

**Type:** bool

**Current value:** False

---

### gov.territories.pr.tax.income.credits.low_income.amount.base
**Label:** Puerto Rico low income tax credit amount

Puerto Rico provides the following low income tax credit amount.

**Type:** int

**Current value:** 400

---

### gov.territories.pr.tax.income.credits.low_income.age_threshold
**Label:** Puerto Rico low income tax credit age threshold

Puerto Rico limits the low income tax credit to filers at or above this age threshold.

**Type:** int

**Current value:** 65

---

### gov.ed.pell_grant.amount.max
**Label:** Maximum value of the Pell Grant

The Department of Education limits Pell Grants to this amount.

**Type:** int

**Current value:** 7395

---

### gov.ed.pell_grant.amount.min
**Label:** Minimum value of the Pell Grant

The Department of Education does not provide Pell Grants if the calculated amount is less than this value.

**Type:** int

**Current value:** 740

---

### gov.ed.pell_grant.months_in_school_year
**Label:** Months in school year

The Department of Education defines a full school year as this number of months.

**Type:** int

**Current value:** 9

---

### gov.ed.pell_grant.efc.simplified.applies
**Label:** Pell Grant EFC simplified formula applies

The simplified pell grant efc formula is applied if this is true.

**Type:** bool

**Current value:** False

---

### gov.ed.pell_grant.efc.simplified.income_limit
**Label:** Simplified formula max income

The Department of Education uses the simplified formula if the head and spouse income are below this amount.

**Type:** int

**Current value:** 50000

---

### gov.ed.pell_grant.efc.automatic_zero
**Label:** Max income for an automatic 0 EFC

The Department of Education sets the Expected Family Contribution to zero if a family has income below this value.

**Type:** int

**Current value:** 29000

---

### gov.ed.pell_grant.head.negative_rate
**Label:** Percent of income for negative head available income

The Department of Education defines the percent of negative available income that counts towards contibution as this value.

**Type:** float

**Current value:** 0.22

---

### gov.ed.pell_grant.head.min_contribution
**Label:** Minimum head contribution

The Department of Education defines the minimum contribution as this value.

**Type:** int

**Current value:** -1500

---

### gov.ed.pell_grant.sai.limits.max_sai
**Label:** Pell Grant maximum SAI

The Department of Eduction caps the Pell Grant student aid index at this amount.

**Type:** int

**Current value:** 999999

---

### gov.ed.pell_grant.sai.limits.min_sai
**Label:** Pell Grant minimum SAI

The Department of Education floors the Pell Grant student aid index at this amount.

**Type:** int

**Current value:** -1500

---

### gov.ed.pell_grant.dependent.asset_assessment_rate
**Label:** EFC dependent asset assessment rate

The Department of Education counts this share of a dependent student's assets towards the expected family contribution.

**Type:** float

**Current value:** 0.2

---

### gov.ed.pell_grant.dependent.income_assessment_rate
**Label:** Pell Grant EFC dependent income assessment rate

The Education Department counts this percent of a dependent student's income towards the Pell Grant expected family contribution.

**Type:** float

**Current value:** 0.5

---

### gov.ed.pell_grant.dependent.ipa
**Label:** Income protection allowance

The Department of Education disregards this amount of income when computing the expected family contribution.

**Type:** int

**Current value:** 7040

---

### gov.aca.slspc.last_same_child_age
**Label:** ACA last same-SLSPC child age

Highest age for which ACA SLSPC amount is the same as for newborns.

**Type:** int

**Current value:** 14

---

### gov.aca.slspc.max_child_age
**Label:** ACA maximum SLSPC child age

Maximum age for ACA SLSPC amounts.

**Type:** int

**Current value:** 20

---

### gov.aca.slspc.max_adult_age
**Label:** ACA maximum SLSPC adult age

Maximum age for ACA SLSPC amounts.

**Type:** int

**Current value:** 64

---

### gov.aca.max_child_count
**Label:** ACA maximum child count

Maximum number of children who pay an age-based ACA plan premium.

**Type:** int

**Current value:** 3

---

### gov.simulation.labor_supply_responses.bounds.effective_wage_rate_change
**Label:** Effective wage rate change LSR bound

Effective wage rate changes larger than this will be capped at this value.

**Type:** int

**Current value:** 1

---

### gov.simulation.labor_supply_responses.bounds.income_change
**Label:** Income change LSR bound

Net income changes larger than this will be capped at this value.

**Type:** int

**Current value:** 1

---

### gov.simulation.labor_supply_responses.elasticities.substitution.all
**Label:** substitution elasticity of labor supply

Percent change (of the change in the effective marginal wage) in labor supply given a 1% change in the effective marginal wage. This parameter overrides all other substitution elasticities if provided.

**Type:** int

**Current value:** 0

---

### gov.simulation.labor_supply_responses.elasticities.substitution.by_position_and_decile.primary.1
**Label:** primary adult, 1st decile substitution elasticity

**Type:** int

**Current value:** 0

---

### gov.simulation.labor_supply_responses.elasticities.substitution.by_position_and_decile.primary.2
**Label:** primary adult, 2nd decile substitution elasticity

**Type:** int

**Current value:** 0

---

### gov.simulation.labor_supply_responses.elasticities.substitution.by_position_and_decile.primary.3
**Label:** primary adult, 3rd decile substitution elasticity

**Type:** int

**Current value:** 0

---

### gov.simulation.labor_supply_responses.elasticities.substitution.by_position_and_decile.primary.4
**Label:** primary adult, 4th decile substitution elasticity

**Type:** int

**Current value:** 0

---

### gov.simulation.labor_supply_responses.elasticities.substitution.by_position_and_decile.primary.5
**Label:** primary adult, 5th decile substitution elasticity

**Type:** int

**Current value:** 0

---

### gov.simulation.labor_supply_responses.elasticities.substitution.by_position_and_decile.primary.6
**Label:** primary adult, 6th decile substitution elasticity

**Type:** int

**Current value:** 0

---

### gov.simulation.labor_supply_responses.elasticities.substitution.by_position_and_decile.primary.7
**Label:** primary adult, 7th decile substitution elasticity

**Type:** int

**Current value:** 0

---

### gov.simulation.labor_supply_responses.elasticities.substitution.by_position_and_decile.primary.8
**Label:** primary adult, 8th decile substitution elasticity

**Type:** int

**Current value:** 0

---

### gov.simulation.labor_supply_responses.elasticities.substitution.by_position_and_decile.primary.9
**Label:** primary adult, 9th decile substitution elasticity

**Type:** int

**Current value:** 0

---

### gov.simulation.labor_supply_responses.elasticities.substitution.by_position_and_decile.primary.10
**Label:** primary adult, 10th decile substitution elasticity

**Type:** int

**Current value:** 0

---

### gov.simulation.labor_supply_responses.elasticities.substitution.by_position_and_decile.secondary
**Label:** secondary adult, all deciles substitution elasticity

**Type:** int

**Current value:** 0

---

### gov.simulation.labor_supply_responses.elasticities.income
**Label:** income elasticity of labor supply

Percent change (of the change in disposable income) in labor supply given a 1% change in disposable income.

**Type:** int

**Current value:** 0

---

### gov.simulation.capital_gains_responses.elasticity
**Label:** capital gains elasticity

Elasticity of capital gains with respect to the capital gains marginal tax rate.

**Type:** int

**Current value:** 0

---

### gov.simulation.reported_broadband_subsidy
**Label:** Use reported broadband subsidies

Broadband subsidies are taken as reported in the CPS ASEC.

**Type:** bool

**Current value:** True

---

### gov.simulation.reported_snap
**Label:** Use reported SNAP benefits

SNAP benefits are taken as reported in the CPS ASEC.

**Type:** bool

**Current value:** False

---

### gov.contrib.biden.budget_2025.medicare.rate
**Label:** President Biden additional Medicare tax rate

President Biden proposed this additional Medicare tax rate.

**Type:** int

**Current value:** 0

---

### gov.contrib.biden.budget_2025.medicare.threshold
**Label:** President Biden additional Medicare tax rate threshold

President Biden proposed an additional Medicare tax rate for filers with adjusted gross income above this threshold.

**Type:** float

**Current value:** 411004.94825739285

---

### gov.contrib.biden.budget_2025.capital_gains.active
**Label:** Capital income over threshold taxed as ordinary income

The proposal of President Biden to tax capital income as ordinary is active if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.biden.budget_2025.net_investment_income.rate
**Label:** President Biden additional NIIT rate

President Biden proposed this additional net investment income tax rate.

**Type:** int

**Current value:** 0

---

### gov.contrib.biden.budget_2025.net_investment_income.threshold
**Label:** President Biden additional NIIT rate threshold

President Biden proposed an additional net investment income tax rate for filers with adjusted gross income above this threshold.

**Type:** float

**Current value:** 411004.94825739285

---

### gov.contrib.harris.rent_relief_act.rent_relief_credit.subsidized_rent_rate
**Label:** Rent Relief Credit subsidized rent rate

Kamala Harris proposed to provide a rent relief credit of this share of after-subsidy rent to residents of government-subsidized housing.

**Type:** float

**Current value:** 0.083

---

### gov.contrib.harris.rent_relief_act.rent_relief_credit.high_income_area_threshold_increase
**Label:** Rent Relief Credit high income area threshold increase

Kamala Harris proposed raising the Rent Relief Act thresholds by this amounts for residents of areas where HUD uses the small area fair market rent for the Housing Choice Voucher Program.

**Type:** int

**Current value:** 25000

---

### gov.contrib.harris.rent_relief_act.rent_relief_credit.in_effect
**Label:** Rent Relief Tax Credit in effect

The Rent Relief Tax Credit proposed by Kamala Harris applies if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.harris.rent_relief_act.rent_relief_credit.safmr_share_rent_cap
**Label:** Rent Relief Credit rent cap as fraction of SAFMR

Kamala Harris proposed capping rent at this fraction of small area fair market rent under the rent relief credit.

**Type:** int

**Current value:** 1

---

### gov.contrib.harris.rent_relief_act.rent_relief_credit.rent_income_share_threshold
**Label:** Rent Relief Credit income share threshold

Kamala Harris proposed to provide a rent relief credit to households who spend more than this share of income on rent.

**Type:** float

**Current value:** 0.3

---

### gov.contrib.harris.capital_gains.in_effect
**Label:** Harris capital gains tax reform in effect

Vice President Kamala Harris has proposed to add a top capital gains tax bracket, which comes into effect if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.harris.lift.middle_class_tax_credit.age_threshold
**Label:** Middle Class Tax Credit age threshold

The Middle Class Tax Credit is limited to filers below this age threshold.

**Type:** int

**Current value:** 18

---

### gov.contrib.harris.lift.middle_class_tax_credit.in_effect
**Label:** Middle Class Tax Credit in effect

The Middle Class Tax Credit applies if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.harris.lift.middle_class_tax_credit.joint_multiplier
**Label:** Middle Class Tax Credit joint multiplier

The amount of the Middle Class Tax Credit is multiplied by this factor for joint filers.

**Type:** int

**Current value:** 2

---

### gov.contrib.harris.lift.middle_class_tax_credit.cap
**Label:** Middle Class Tax Credit cap

The Middle Class Tax Credit is capped at the following amount.

**Type:** int

**Current value:** 3700

---

### gov.contrib.cbo.payroll.secondary_earnings_threshold
**Label:** Social Security payroll tax secondary earnings threshold

The US levies payroll taxes on earnings greater than this amount, in addition to earnings below the maximum taxable amount under current law.

**Type:** float

**Current value:** inf

---

### gov.contrib.ubi_center.basic_income.amount.tax_unit.fpg_percent
**Label:** Basic income as a percent of tax unit's poverty line

A basic income is provided to tax units at this percentage of the federal poverty guideline

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.amount.person.by_age[0].amount
**Label:** Young child basic income

Unconditional payment to young children.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.amount.person.by_age[1].amount
**Label:** Older child basic income

Unconditional payment to older children.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.amount.person.by_age[1].threshold
**Label:** Older child basic income age

**Type:** int

**Current value:** 6

---

### gov.contrib.ubi_center.basic_income.amount.person.by_age[2].amount
**Label:** Young adult basic income

Unconditional payment to working-age adults.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.amount.person.by_age[2].threshold
**Label:** Young adult basic income age

Age at which individuals receive the young adult payment, rather than the older child payment.

**Type:** int

**Current value:** 18

---

### gov.contrib.ubi_center.basic_income.amount.person.by_age[3].amount
**Label:** Older adult basic income

Unconditional payment to older adults.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.amount.person.by_age[3].threshold
**Label:** Older adult basic income age

Age at which individuals receive the older adult payment, rather than the young adult payment.

**Type:** int

**Current value:** 25

---

### gov.contrib.ubi_center.basic_income.amount.person.by_age[4].amount
**Label:** Senior citizen basic income

Unconditional payment to senior citizens.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.amount.person.by_age[4].threshold
**Label:** Senior citizen basic income age

Age at which individuals receive the senior citizen payment, rather than the working-age adult payment.

**Type:** int

**Current value:** 65

---

### gov.contrib.ubi_center.basic_income.amount.person.disability
**Label:** Disability-based UBI

Payment to individuals with SSI-qualifying disabilities.

**Type:** float

**Current value:** 0.0

---

### gov.contrib.ubi_center.basic_income.amount.person.flat
**Label:** Basic income

Basic income amount.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.amount.person.marriage_bonus
**Label:** Basic income marriage bonus rate

The following bonus is provided to married couples as a percentage of their basic income amount.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.agi_limit.in_effect
**Label:** Basic income AGI limit in effect

Basic income is limited to tax units below an AGI level if this switch is activated.

**Type:** bool

**Current value:** False

---

### gov.contrib.ubi_center.basic_income.phase_out.rate
**Label:** Basic income phase-out rate

The basic income phases out at this rate for tax filers with adjusted gross income above the threshold.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.phase_out.by_rate
**Label:** Phase out basic income as a rate

Basic incomes phase out as a rate above a threshold if this is selected; otherwise, they phase out between the threshold and a phase-out end.

**Type:** bool

**Current value:** True

---

### gov.contrib.ubi_center.basic_income.taxable
**Label:** Basic income taxability

Whether the IRS counts basic income in adjusted gross income. If true, this overrides and eliminates all other basic income phase-out parameters.

**Type:** bool

**Current value:** False

---

### gov.contrib.ubi_center.basic_income.phase_in.per_person
**Label:** Phase in basic income per person

Basic incomes phase in per person if this is selected; otherwise, they phase in at a flat rate irrespective of household size.

**Type:** bool

**Current value:** False

---

### gov.contrib.ubi_center.basic_income.phase_in.rate
**Label:** Basic income phase-in rate

The basic income phases in at this rate.

**Type:** int

**Current value:** 1

---

### gov.contrib.ubi_center.basic_income.phase_in.in_effect
**Label:** Basic income phase-in in effect

Basic income is phased in if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.ubi_center.basic_income.phase_in.include_ss_benefits_as_earnings
**Label:** SS benefits treated as earnings for basic income

Social Security benefits are treated as earnings under the basic income phase in if this is selected.

**Type:** bool

**Current value:** False

---

### gov.contrib.ubi_center.flat_tax.rate.gross_income
**Label:** Flat tax rate on gross income

Flat tax rate applied to federal gross income.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.flat_tax.rate.agi
**Label:** Flat tax rate on AGI

Flat tax rate applied to federal adjusted gross income.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.flat_tax.abolish_self_emp_tax
**Label:** Abolish self-employment tax

Abolish self-employment tax liabilities.

**Type:** bool

**Current value:** False

---

### gov.contrib.ubi_center.flat_tax.abolish_federal_income_tax
**Label:** Abolish federal income tax

Abolish all federal income tax liabilities.

**Type:** bool

**Current value:** False

---

### gov.contrib.ubi_center.flat_tax.abolish_payroll_tax
**Label:** Abolish payroll taxes

Abolish all payroll tax liabilities.

**Type:** bool

**Current value:** False

---

### gov.contrib.ubi_center.flat_tax.deduct_ptc
**Label:** Premium Tax Credit flat tax deduction

Deduct the Premium Tax Credit from the flat tax.

**Type:** bool

**Current value:** False

---

### gov.contrib.joint_eitc.in_effect
**Label:** Joint EITC phase-out rate halving in effect

A proposal to halve the EITC phase out rate for joint filers.

**Type:** bool

**Current value:** False

---

### gov.contrib.deductions.salt.limit_salt_deduction_to_property_taxes
**Label:** Limit SALT deduction to property taxes

The State and Local Tax (SALT) deduction is limited to the amount of property taxes paid, if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.repeal_state_dependent_exemptions.in_effect
**Label:** Repeal state dependent exemptions

The state dependent exemptions are repealed, if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.local.nyc.stc.adjust_income_limit_by_filing_status_and_eligibility_by_children
**Label:** Adjust NYC STC Income Limit by Filing Status and Eligibility by Children

Adjust the NYC School Tax Credit (Fixed and Rate Reduction components) Income Limit by Filing Status and Eligibility by Children.

**Type:** bool

**Current value:** False

---

### gov.contrib.local.nyc.stc.phase_out.in_effect
**Label:** NYC school tax credit phase out in effect

The NYC school tax credit phases out with state adjusted gross income, if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.local.nyc.stc.min_children
**Label:** NYC School Tax Credit Minimum Number of Children

Limit NYC School Tax Credit eligibility to tax units with at least this many children.

**Type:** int

**Current value:** 0

---

### gov.contrib.individual_eitc.agi_eitc_limit
**Label:** EITC AGI limit

Tax filers with combined earned income over this cannot claim the EITC. This is only active if the Winship EITC reform is active.

**Type:** int

**Current value:** 0

---

### gov.contrib.individual_eitc.enabled
**Label:** Individual-income EITCs

A proposal by Scott Winship to assess EITC income at the individual level, regardless of filing status.

**Type:** bool

**Current value:** False

---

### gov.contrib.states.mn.walz.hf1938.repeal
**Label:** Minnesota Bill HF1938 repeal

The Minnesota Bill HF1938, implemented by Gov. Walz, is repealed if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.states.dc.property_tax.phase_out.applies
**Label:** DC property tax credit phase out applies

The DC property tax credit phases out with adjusted gross income over the income limit, if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.states.dc.property_tax.phase_out.rate
**Label:** DC property tax credit phase out rate

DC phases the property tax credit out at this rate of adjusted gross income over the income limit.

**Type:** float

**Current value:** 0.1

---

### gov.contrib.states.dc.property_tax.in_effect
**Label:** DC property tax credit reform in effect

The DC property tax credit reform applies if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.states.ny.wftc.amount.max
**Label:** New York Working Families Tax Credit max amount

New York provides the following maximum Working Families Tax Credit amount per child.

**Type:** int

**Current value:** 550

---

### gov.contrib.states.ny.wftc.child_age_threshold
**Label:** New York Working Families Tax Credit child age threshold

New York limits the Working Families Tax Credit to children at or below this age.

**Type:** int

**Current value:** 16

---

### gov.contrib.states.ny.wftc.in_effect
**Label:** New York Working Families Tax Credit reform in effect

The New York Working Families Tax Credit reform applies if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.states.ny.wftc.exemptions.in_effect
**Label:** New York Working Families Tax Credit exemption reform applies

The Exemption reform of the New York Working Families Tax Credit reform applies if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.states.ny.wftc.eitc.match
**Label:** New York Working Families Tax Credit EITC match

New York matches this fraction of the Earned Income Tax Credit under the Working Families Tax Credit.

**Type:** float

**Current value:** 0.25

---

### gov.contrib.states.ny.inflation_rebates.in_effect
**Label:** New York inflation rebates in effect

New York's inflation rebates are in effect if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.states.or.rebate.state_tax_exempt
**Label:** Oregon Basic Income state tax exempt

The Basic Income amount is exempt from Oregon state income tax if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.snap.abolish_deductions.in_effect
**Label:** Abolish SNAP deductions in effect

SNAP deductions are abolished, if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.snap.abolish_net_income_test.in_effect
**Label:** Abolish SNAP net income test in effect

SNAP net income test is abolished, if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.dc_kccatc.expenses.max
**Label:** DC KCCATC maximum

DC caps the KCCATC at this amount per eligible child.

**Type:** int

**Current value:** 0

---

### gov.contrib.dc_kccatc.expenses.rate
**Label:** DC KCCATC expense share

The DC KCCATC covers this percentage of child care expenses for the tax unit.

**Type:** float

**Current value:** 0.0

---

### gov.contrib.dc_kccatc.phase_out.rate
**Label:** DC KCCATC phase-out rate

DC phases out the KCCATC at this rate of AGI above the threshold.

**Type:** float

**Current value:** 0.0

---

### gov.contrib.dc_kccatc.active
**Label:** DC KCCATC custom reforms active

Whether to reform the DC KCCATC in line with the parameters in this folder.

**Type:** bool

**Current value:** False

---

### gov.contrib.salt_phase_out.in_effect
**Label:** SALT deduction phase out in effect

The SALT deduction is phased out based on earnings, if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.dc_tax_threshold_joint_ratio
**Label:** DC single-joint tax threshold ratio

Ratio of single to joint tax thresholds for DC's income tax.

**Type:** int

**Current value:** 1

---

### gov.contrib.ctc.oldest_child_supplement.amount
**Label:** CTC oldest child supplement

An increased Child Tax Credit of this amount is provided to the oldest child in a household.

**Type:** int

**Current value:** 0

---

### gov.contrib.ctc.oldest_child_supplement.in_effect
**Label:** CTC oldest child supplement in effect

An increased Child Tax Credit amount is provided to the oldest child in a household, if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.ctc.eppc.expanded_ctc.in_effect
**Label:** Expanded CTC in effect

An expanded Child Tax Credit amount with an alternative phase-in structure is provided, if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.tax_exempt.in_effect
**Label:** Tax exemptions in effect

Various income sources are exempt from federal income or payroll tax, if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.tax_exempt.overtime.income_tax_exempt
**Label:** Overtime income, income tax exempt

The propsal to exempt overtime income from income tax applies, if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.tax_exempt.overtime.payroll_tax_exempt
**Label:** Overtime income payroll tax exempt

The propsal to exempt overtime income from payroll tax applies, if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.tax_exempt.tip_income.income_tax_exempt
**Label:** Tip income, income tax exempt

The propsal to exempt tip income from payroll tax applies, if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.tax_exempt.tip_income.payroll_tax_exempt
**Label:** Tip income payroll tax exempt

The propsal to exempt tip income from payroll tax applies, if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.treasury.repeal_dependent_exemptions
**Label:** Repeal dependent exemptions

The dependent exemptions will be repealed if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.congress.delauro.american_family_act.baby_bonus
**Label:** American Family Act baby bonus

The Child Tax Credit increases by this amount for newborns, above the normal amount for young children.

**Type:** int

**Current value:** 0

---

### gov.contrib.congress.wftca.bonus_guaranteed_deduction.phase_out.rate
**Label:** Bonus guaranteed deduction phase-out rate

Rate at which the bonus guaranteed deduction reduces with AGI.

**Type:** int

**Current value:** 0

---

### gov.contrib.congress.wftca.bonus_guaranteed_deduction.phase_out.threshold.SINGLE
**Label:** WFTCA single filer phase-out threshold

**Type:** int

**Current value:** 0

---

### gov.contrib.congress.wftca.bonus_guaranteed_deduction.phase_out.threshold.SEPARATE
**Label:** WFTCA separate filer phase-out threshold

**Type:** int

**Current value:** 0

---

### gov.contrib.congress.wftca.bonus_guaranteed_deduction.phase_out.threshold.HEAD_OF_HOUSEHOLD
**Label:** WFTCA head-of-household filer phase-out threshold

**Type:** int

**Current value:** 0

---

### gov.contrib.congress.wftca.bonus_guaranteed_deduction.phase_out.threshold.JOINT
**Label:** WFTCA joint filer phase-out threshold

**Type:** int

**Current value:** 0

---

### gov.contrib.congress.wftca.bonus_guaranteed_deduction.phase_out.threshold.SURVIVING_SPOUSE
**Label:** WFTCA widow filer phase-out threshold

**Type:** int

**Current value:** 0

---

### gov.contrib.congress.wftca.bonus_guaranteed_deduction.amount.SINGLE
**Label:** WFTCA single filer amount

**Type:** int

**Current value:** 0

---

### gov.contrib.congress.wftca.bonus_guaranteed_deduction.amount.SEPARATE
**Label:** WFTCA separate filer amount

**Type:** int

**Current value:** 0

---

### gov.contrib.congress.wftca.bonus_guaranteed_deduction.amount.HEAD_OF_HOUSEHOLD
**Label:** WFTCA head-of-household filer amount

**Type:** int

**Current value:** 0

---

### gov.contrib.congress.wftca.bonus_guaranteed_deduction.amount.JOINT
**Label:** WFTCA joint filer amount

**Type:** int

**Current value:** 0

---

### gov.contrib.congress.wftca.bonus_guaranteed_deduction.amount.SURVIVING_SPOUSE
**Label:** WFTCA widow filer amount

**Type:** int

**Current value:** 0

---

### gov.contrib.congress.wyden_smith.per_child_actc_phase_in
**Label:** Per-child ACTC phase-in

The US phases in the Additional Child Tax Credit on a per child basis if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.congress.wyden_smith.actc_lookback
**Label:** ACTC lookback

The US phases in the Additional Child Tax Credit on the greater of current and prior year earnings if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.congress.romney.family_security_act.remove_head_of_household
**Label:** Repeal head of household filing status

The head of household filing status will be eliminated if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.congress.romney.family_security_act_2024.pregnant_mothers_credit.income_phase_in_end
**Label:** Family Security Act 3.0 Child Tax Credit phase-in earnings limit

Senator Mitt Romney proposed phasing in the Pregnant Mothers Tax Credit linearly from zero to this earnings level under the Family Security Act 3.0.

**Type:** int

**Current value:** 0

---

### gov.contrib.congress.romney.family_security_act_2_0.ctc.child_cap
**Label:** Family Security Act 2.0 Child Tax Credit child cap

Senator Mitt Romney proposed limiting the Child Tax Credit to this number of children per filer under the Family Security Act 2.0.

**Type:** int

**Current value:** 0

---

### gov.contrib.congress.romney.family_security_act_2_0.ctc.apply_ctc_structure
**Label:** Apply Family Security Act 2.0 structure of CTC

Senator Mitt Romney proposed structural changes to the Child Tax Credit in the Family Security Act 2.0, which apply if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.congress.romney.family_security_act_2_0.ctc.phase_in.income_phase_in_end
**Label:** Family Security Act 2.0 Child Tax Credit phase-in earnings limit

Senator Mitt Romney proposed phasing in the Child Tax Credit linearly from zero to this earnings level under the Family Security Act 2.0.

**Type:** int

**Current value:** 0

---

### gov.contrib.congress.romney.family_security_act_2_0.eitc.apply_eitc_structure
**Label:** Apply Family Security Act 2.0 structure of EITC

Senator Mitt Romney proposed structural changes to the Earned Income Tax Credit in the Family Security Act 2.0, which apply if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.congress.tlaib.boost.middle_class_tax_credit.administered_through_ssa
**Label:** BOOST Act middle class credit administered through SSA

The BOOST Act middle class credit is administered through the Social Security Administration if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.congress.tlaib.end_child_poverty_act.filer_credit.phase_out.rate
**Label:** End Child Poverty Act filer credit phase-out rate

Phase-out rate for Rep Tlaib's End Child Poverty Act (2022) filer credit

**Type:** float

**Current value:** 0.05

---

### gov.contrib.congress.tlaib.end_child_poverty_act.filer_credit.eligibility.min_age
**Label:** End Child Poverty Act filer credit minimum age

Minimum age to qualify for Rep Tlaib's End Child Poverty Act (2022) filer credit

**Type:** int

**Current value:** 19

---

### gov.contrib.congress.tlaib.end_child_poverty_act.filer_credit.eligibility.max_age
**Label:** End Child Poverty Act filer credit maximum age

Maximum age to qualify for Rep Tlaib's End Child Poverty Act (2022) filer credit

**Type:** int

**Current value:** 64

---

### gov.contrib.congress.tlaib.end_child_poverty_act.child_benefit.age_limit
**Label:** End Child Poverty Act child benefit age limit

The child benefit component under the End Child Poverty Act is limited to dependents below this age.

**Type:** int

**Current value:** 19

---

### gov.contrib.congress.tlaib.end_child_poverty_act.in_effect
**Label:** End Child Poverty Act in effect

Rep Tlaib's End Child Poverty Act applies if this is true.

**Type:** bool

**Current value:** False

---

### gov.contrib.congress.tlaib.end_child_poverty_act.adult_dependent_credit.min_age
**Label:** End Child Poverty Act adult dependent credit minimum age

Minimum age to qualify for Rep Tlaib's End Child Poverty Act (2022) adult dependent credit

**Type:** int

**Current value:** 19

---

### gov.contrib.congress.tlaib.end_child_poverty_act.adult_dependent_credit.amount
**Label:** End Child Poverty Act adult dependent credit amount

Amount of Rep Tlaib's End Child Poverty Act (2022) adult dependent credit

**Type:** float

**Current value:** 651.7536401178518

---

### gov.contrib.maryland_child_alliance.abolish_non_refundable_child_eitc
**Label:** Abolish MD non-refundable EITC for families with children

Abolish the non-refundable Maryland EITC for tax units with children.

**Type:** bool

**Current value:** False

---

### gov.contrib.maryland_child_alliance.abolish_refundable_child_eitc
**Label:** Abolish MD refundable EITC for families with children

Abolish the refundable Maryland EITC for tax units with children.

**Type:** bool

**Current value:** False

---

### gov.contrib.second_earner_reform.in_effect
**Label:** Second earner tax reform in effect

The second earner tax reform is in effect if this is true.

**Type:** bool

**Current value:** False

---

### gov.local.co.denver.dhs.property_tax_relief.amount.homeowner
**Label:** Denver property tax relief program homeowner amount

Denver provides the following Property Tax Relief Program amount for homeowners.

**Type:** int

**Current value:** 1800

---

### gov.local.co.denver.dhs.property_tax_relief.amount.renter
**Label:** Denver property tax relief program renter amount

Denver provides the following Property Tax Relief Program amount for renters.

**Type:** int

**Current value:** 1000

---

### gov.local.co.denver.dhs.property_tax_relief.ami_rate.homeowner
**Label:** Denver homeowner AMI income limit

Denver limits its Property Tax Relief Program to homeowners with income below this fraction of area median income.

**Type:** float

**Current value:** 0.6

---

### gov.local.co.denver.dhs.elderly_age_threshold
**Label:** Denver property tax relief program elderly age threshold

Denver limits the property tax relief program to households with at least one person above this age threshold.

**Type:** int

**Current value:** 65

---

### gov.local.ca.sf.wftc.amount
**Label:** San Francisco Working Families Tax Credit amount

San Francisco provides this working families tax credit amount.

**Type:** int

**Current value:** 250

---

### gov.local.ca.la.general_relief.amount.married
**Label:** Los Angeles County general relief married amount

Los Angeles county provides a cash grant of this amount to married filers under the general relief program.

**Type:** int

**Current value:** 375

---

### gov.local.ca.la.general_relief.amount.single
**Label:** Los Angeles County general relief single amount

Los Angeles county provides a cash grant of this amount to single filers under the general relief program.

**Type:** int

**Current value:** 221

---

### gov.local.ca.la.general_relief.phase_out.max
**Label:** Los Angeles County general relief phase out max

Los Angeles county phases the general relief out for recipients with net income of up to this amount.

**Type:** int

**Current value:** 620

---

### gov.local.ca.la.general_relief.phase_out.start
**Label:** Los Angeles County general relief phase out start

Los Angeles county phases the general relief out for recipients with net income starting at this amount.

**Type:** int

**Current value:** 201

---

### gov.local.ca.la.general_relief.eligibility.limit.personal_property
**Label:** Los Angeles County general relief personal property value limit

Los Angeles county qualifies filers for the general relief program with personal property value below this limit.

**Type:** int

**Current value:** 2000

---

### gov.local.ca.la.general_relief.eligibility.limit.cash.recipient
**Label:** Los Angeles County general relief recipient cash value limit

Los Angeles county qualifies recipient filers for the general relief program with cash in addition to money in the bank account below this limit.

**Type:** int

**Current value:** 1500

---

### gov.local.ca.la.general_relief.eligibility.limit.cash.applicant.married
**Label:** Los Angeles County general relief married applicant cash value limit

Los Angeles county qualifies married applicant filers for the general relief program with cash in addition to money in the bank account below this limit.

**Type:** int

**Current value:** 200

---

### gov.local.ca.la.general_relief.eligibility.limit.cash.applicant.single
**Label:** Los Angeles County general relief single applicant cash value limit

Los Angeles county qualifies single applicant filers for the general relief program with cash in addition to money in the bank account below this limit.

**Type:** int

**Current value:** 100

---

### gov.local.ca.la.general_relief.eligibility.limit.income.recipient
**Label:** Los Angeles County general relief recipient income limit

Los Angeles county qualifies recipient filers for the general relief program with income below this limit.

**Type:** int

**Current value:** 621

---

### gov.local.ca.la.general_relief.eligibility.limit.income.applicant.married
**Label:** Los Angeles County general relief married applicant income limit

Los Angeles county qualifies married applicant filers for the general relief program with income below this limit.

**Type:** int

**Current value:** 375

---

### gov.local.ca.la.general_relief.eligibility.limit.income.applicant.single
**Label:** Los Angeles County general relief single applicant income limit

Los Angeles county qualifies single applicant filers for the general relief program with income below this limit.

**Type:** int

**Current value:** 221

---

### gov.local.ca.la.general_relief.eligibility.limit.motor_vehicle.value.resident
**Label:** Los Angeles County general relief resident motor vehicle value limit

Los Angeles county qualifies resident filers for the general relief program with motor vehicle value below this limit.

**Type:** int

**Current value:** 4500

---

### gov.local.ca.la.general_relief.eligibility.limit.motor_vehicle.value.homeless
**Label:** Los Angeles County general relief homeless motor vehicle value limit

Los Angeles county qualifies homeless filers for the general relief program with motor vehicle value below this limit.

**Type:** int

**Current value:** 11500

---

### gov.local.ca.la.general_relief.eligibility.limit.motor_vehicle.cap
**Label:** Los Angeles County general relief resident motor vehicle cap

Los Angeles county caps the number of motor vehicles that a filer can own to this number under the general relief program.

**Type:** int

**Current value:** 1

---

### gov.local.ca.la.general_relief.eligibility.limit.home_value
**Label:** Los Angeles County general relief home value limit

Los Angeles county qualifies filers for the general relief program with home value at or below this limit.

**Type:** int

**Current value:** 34000

---

### gov.local.ca.la.general_relief.eligibility.age_threshold
**Label:** Los Angeles County general relief age eligiblity threshold

Los Angeles county qualifies filers for the general relief program at this age or older.

**Type:** int

**Current value:** 18

---

### gov.local.ca.la.general_relief.housing_subsidy.amount.married
**Label:** Los Angeles County general relief housing subsidy married amount

Los Angeles county provides a housing subsidy of this amount under the general relief program for couples.

**Type:** int

**Current value:** 950

---

### gov.local.ca.la.general_relief.housing_subsidy.amount.single
**Label:** Los Angeles County general relief housing subsidy single amount

Los Angeles county provides a housing subsidy of this amount under the general relief program for single filers.

**Type:** int

**Current value:** 475

---

### gov.local.ca.la.general_relief.housing_subsidy.rent_contribution.married
**Label:** Los Angeles County general relief housing subsidy married rent contribution

Los Angeles county requires married filers who receive the general relief grant to contribute this amout of the total garnt towards their rent.

**Type:** int

**Current value:** 200

---

### gov.local.ca.la.general_relief.housing_subsidy.rent_contribution.single
**Label:** Los Angeles County general relief housing subsidy single rent contribution

Los Angeles county requires single filers who receive the general relief grant to contribute this amout of the total garnt towards their rent.

**Type:** int

**Current value:** 100

---

### gov.local.ca.la.general_relief.housing_subsidy.move_in_assistance
**Label:** Los Angeles County general relief housing subsidy move-in assistance

Los Angeles county provides this once-in-a-lifetime move-in assistance payment.

**Type:** int

**Current value:** 500

---

### gov.local.ca.la.dss.expectant_parent_payment.pregnancy_month.max
**Label:** California Department of Social Services Expectant Parent Payment maximum pregnancy month

The California Department of Social Services provides the Expectant Parent Payment on and before this pregnancy month.

**Type:** int

**Current value:** 9

---

### gov.local.ca.la.dss.expectant_parent_payment.pregnancy_month.min
**Label:** California Department of Social Services Expectant Parent Payment pregnancy months

The California Department of Social Services provides the Expectant Parent Payment on and after this pregnancy month.

**Type:** int

**Current value:** 6

---

### gov.local.ca.la.dss.expectant_parent_payment.amount
**Label:** California Department of Social Services Expectant Parent Payment amount

The California Department of Social Services provides the following Expectant Parent Payment.

**Type:** int

**Current value:** 900

---

### gov.local.ca.la.dss.infant_supplement.amount.base
**Label:** California Department of Social Services Infant Supplement base amount

The California Department of Social Services provides the following base Infant Supplement amount.

**Type:** int

**Current value:** 900

---

### gov.local.ca.la.dss.infant_supplement.amount.group_home
**Label:** California Department of Social Services Infant Supplement group home amount

The California Department of Social Services provides the following Infant Supplement amount for filers in group homes or STRTP placements.

**Type:** int

**Current value:** 1379

---

### gov.local.ca.la.dwp.ez_save.eligibility.fpg_limit_increase
**Label:** Los Angeles County EZ Save FPG limit

The Los Angeles Department of Water and Power limits the EZ Save program to households with income below this percentage of the federal poverty line.

**Type:** int

**Current value:** 2

---

### gov.local.ca.la.dwp.ez_save.eligibility.household_size_floor
**Label:** Los Angeles County EZ Save household size floor

Los Angeles County floors the household size to this number under the EZ Save program.

**Type:** int

**Current value:** 2

---

### gov.local.ca.la.dwp.ez_save.amount
**Label:** Los Angeles County EZ Save amount

The Los Angeles Department of Water and Power discounts electricity bills by this amount each month for EZ Save participants.

**Type:** float

**Current value:** 8.17

---

### gov.local.md.montgomery.tax.income.credits.eitc.refundable.match
**Label:** Montgomery County EITC match

Montgomery County matches this percentage of the refundable Maryland Earned Income Tax Credit.

**Type:** float

**Current value:** 0.56

---

### gov.local.ny.nyc.tax.income.credits.cdcc.child_age_restriction
**Label:** NYC CDCC child age limit

New York City limits its child and dependent care to expenses for children under this age.

**Type:** int

**Current value:** 4

---

### gov.local.ny.nyc.tax.income.credits.cdcc.max_rate
**Label:** NYC CDCC match

New York City matches this fraction of the Child and Dependent Care Credit.

**Type:** float

**Current value:** 0.75

---

### gov.local.ny.nyc.tax.income.credits.cdcc.phaseout_end
**Label:** NYC Child and Dependent Care Credit income limit.

New York City fully phases out its Child and Dependent Care Credit for filers with this income.

**Type:** int

**Current value:** 30000

---

### gov.local.ny.nyc.tax.income.credits.cdcc.phaseout_start
**Label:** NYC Child and Dependent Care Credit phaseout start.

New York City reduces its Child and Dependent Care Credit match for filers with income above the threshold.

**Type:** int

**Current value:** 25000

---

### gov.local.ny.nyc.tax.income.credits.school.rate_reduction.income_limit
**Label:** NYC School Tax Credit Rate Reduction Amount Income Limit

NYC limits its School Tax Credit Rate Reduction Amount to filers with NYC taxable income up to this amount.

**Type:** int

**Current value:** 500000

---

### gov.local.ny.nyc.tax.income.credits.school.fixed.income_limit
**Label:** NYC School Tax Credit Fixed Amount Income Limit

NYC limits its School Tax Credit Fixed Amount to filers with NY AGI of this amount or less.

**Type:** int

**Current value:** 250000

---

### gov.local.ny.nyc.tax.income.credits.eitc.percent_reduction
**Label:** NYC EITC reduction percentage

New York City reduces its earned income tax credit match by this fraction for filers with income above the threshold.

**Type:** float

**Current value:** 2e-05

---

### gov.usda.snap.abolish_snap
**Label:** Abolish SNAP

Abolish SNAP payments.

**Type:** bool

**Current value:** False

---

### gov.usda.snap.takeup_rate
**Label:** SNAP takeup rate

Percentage of eligible SNAP recipients who do not claim SNAP.

**Type:** float

**Current value:** 0.82

---

### gov.usda.snap.student.working_hours_threshold
**Label:** SNAP student working hours threshold

The United States includes students who work more than this number of weekly hours in the Supplemental Nutrition Assistance Program unit.

**Type:** int

**Current value:** 20

---

### gov.usda.snap.income.limit.gross
**Label:** SNAP gross income limit

SNAP gross income limit as a percentage of the poverty line.

**Type:** float

**Current value:** 1.3

---

### gov.usda.snap.income.limit.net
**Label:** SNAP net income limit

SNAP standard net income limit as a percentage of the poverty line.

**Type:** int

**Current value:** 1

---

### gov.usda.snap.income.deductions.earned_income
**Label:** SNAP earned income deduction

Share of earned income that can be deducted from gross income for SNAP

**Type:** float

**Current value:** 0.2

---

### gov.usda.snap.income.deductions.excess_shelter_expense.homeless.deduction
**Label:** SNAP homeless shelter deduction

SNAP homeless shelter deduction amount.

**Type:** float

**Current value:** 190.3

---

### gov.usda.snap.income.deductions.excess_shelter_expense.income_share_disregard
**Label:** Share of income disregarded for SNAP shelter deduction

Share of income disregarded for SNAP shelter deduction

**Type:** float

**Current value:** 0.5

---

### gov.usda.snap.income.deductions.excess_medical_expense.disregard
**Label:** Medical expense disregard for SNAP excess medical expense deduction

Monthly medical expenses disregarded for claiming SNAP excess medical expense deduction

**Type:** int

**Current value:** 35

---

### gov.usda.snap.emergency_allotment.minimum
**Label:** SNAP emergency allotment minimum

States provide SNAP emergency allotments of at least this amount.

**Type:** int

**Current value:** 95

---

### gov.usda.snap.emergency_allotment.allowed
**Label:** SNAP emergency allotment allowed

The federal government allows states to apply for SNAP emergency allotments when this is true.

**Type:** bool

**Current value:** False

---

### gov.usda.snap.uprating
**Label:** SNAP uprating

The US sets SNAP benefits at the Thrifty Food Plan each year, updating in October. This approximates that uprating via CPI-U.

**Type:** float

**Current value:** 313.7

---

### gov.usda.csfp.min_age
**Label:** Commodity Supplemental Food Program min age

The Commodity Supplemental Food Program is limited to filers at or above this age.

**Type:** int

**Current value:** 60

---

### gov.usda.csfp.fpg_limit
**Label:** Commodity Supplemental Food Program FPG limit

The US limits the Commodity Supplemental Food Program to individuals with household income below this percentage of the federal poverty guidelines.

**Type:** float

**Current value:** 1.3

---

### gov.usda.csfp.amount
**Label:** Commodity Supplemental Food Program amount

The following food value amount is provided under the Commodity Supplemental Food Program to each eligible person.

**Type:** int

**Current value:** 330

---

### gov.usda.school_meals.income.limit.FREE
**Label:** Free school meal income limit as a percent of the poverty line

**Type:** float

**Current value:** 1.3

---

### gov.usda.school_meals.income.limit.REDUCED
**Label:** Reduced school meal income limit as a percent of the poverty line

**Type:** float

**Current value:** 1.85

---

### gov.usda.wic.abolish_wic
**Label:** Abolish WIC

Abolish WIC payments.

**Type:** bool

**Current value:** False

---

### gov.ssa.sga.non_blind
**Label:** Non-blind Substantial Gainful Activity limit

The Social Security Administration considers non-blind individuals earning more than this amount, net of impairment-related work expenses, to be engaging in Substantial Gainful Activity.

**Type:** int

**Current value:** 1620

---

### gov.ssa.ssi.abolish_ssi
**Label:** Abolish SSI

Abolish SSI payments.

**Type:** bool

**Current value:** False

---

### gov.ssa.ssi.amount.couple
**Label:** Monthly maximum Federal SSI payment amounts for an eligible individual with an eligible spouse

Monthly maximum Federal SSI payment amounts for an eligible individual with an eligible spouse.

**Type:** int

**Current value:** 1450

---

### gov.ssa.ssi.amount.individual
**Label:** Monthly maximum Federal SSI payment amounts for an eligible individual

Monthly maximum Federal SSI payment amounts for an eligible individual.

**Type:** int

**Current value:** 967

---

### gov.ssa.ssi.income.exclusions.blind_or_disabled_working_student.amount
**Label:** SSI blind or disabled working student earned income exclusion amount

The Social Security Administration excludes the following earned income amount for blind or disabled student filers under the Supplemental Security Income.

**Type:** int

**Current value:** 2360

---

### gov.ssa.ssi.income.exclusions.blind_or_disabled_working_student.age_limit
**Label:** SSI blind or disabled working student earned income exclusion age limit

The Social Security Administration limits the blind or disabled Supplemental Security Income amount to student filers below this age limit.

**Type:** int

**Current value:** 22

---

### gov.ssa.ssi.income.exclusions.blind_or_disabled_working_student.cap
**Label:** SSI blind or disabled working student earned income exclusion cap

The Social Security Administration caps the annual earned income exclusion for blind or disabled students receiving Supplemental Security Income at this amount.

**Type:** int

**Current value:** 9530

---

### gov.ssa.ssi.income.exclusions.general
**Label:** SSI flat general income exclusion

Flat amount of income excluded from SSI countable income.

**Type:** int

**Current value:** 20

---

### gov.ssa.ssi.income.exclusions.earned_share
**Label:** SSI earned income share excluded above flat exclusion

Share of earned income above the flat exclusion that is excluded from SSI countable income.

**Type:** float

**Current value:** 0.5

---

### gov.ssa.ssi.income.exclusions.earned
**Label:** SSI flat earned income exclusion

Flat amount of earned income excluded from SSI countable income.

**Type:** int

**Current value:** 65

---

### gov.ssa.ssi.income.sources.qualifying_quarters_threshold
**Label:** SSI qualifying quarters threshold

The US provides SSI to legal permanent residents with this minimum number of qualifying quarters of earnings.

**Type:** int

**Current value:** 40

---

### gov.ssa.ssi.eligibility.resources.limit.couple
**Label:** SSI resource limit for couples

SSI resource limit for couples.

**Type:** int

**Current value:** 3000

---

### gov.ssa.ssi.eligibility.resources.limit.individual
**Label:** SSI resource limit for individuals

SSI resource limit for individuals.

**Type:** int

**Current value:** 2000

---

### gov.ssa.ssi.eligibility.aged_threshold
**Label:** Age to qualify for Supplemental Security Income

Age to qualify for Supplemental Security Income.

**Type:** int

**Current value:** 65

---

### gov.ssa.uprating
**Label:** SSA uprating

The US indexes Social Security benefits (OASDI and SSI) according to this schedule, annually updating based on CPI-W in the third quarter of the prior year.

**Type:** float

**Current value:** 310.866

---

### gov.fcc.lifeline.amount.rural_tribal_supplement
**Label:** Lifeline supplement for rural Tribal areas

Lifeline supplement for rural Tribal areas

**Type:** int

**Current value:** 25

---

### gov.fcc.lifeline.amount.standard
**Label:** Lifeline maximum benefit

Maximum Lifeline benefit amount

**Type:** float

**Current value:** 9.25

---

### gov.fcc.lifeline.fpg_limit
**Label:** Lifeline maximum income as a percent of the poverty line

Maximum percent of the federal poverty guideline to be eligible for Lifeline

**Type:** float

**Current value:** 1.35

---

### gov.fcc.acp.amount.tribal
**Label:** Affordable Connectivity Program amount for households on Tribal lands

Maximum monthly Affordable Connectivity Program (ACP) amount for Tribal lands

**Type:** int

**Current value:** 0

---

### gov.fcc.acp.amount.standard
**Label:** Affordable Connectivity Program amount for households not on Tribal lands

Maximum monthly Affordable Connectivity Program (ACP) amount for non-Tribal lands

**Type:** int

**Current value:** 0

---

### gov.fcc.acp.fpg_limit
**Label:** Affordable Connectivity Program income limit as a percent of the poverty line

Maximum percent of the federal poverty guideline to be eligible for the Affordable Connectivity Program

**Type:** int

**Current value:** 2

---

### gov.doe.high_efficiency_electric_home_rebate.cap.total
**Label:** High efficiency electric home rebate total annual cap

The US caps high-efficiency home program rebates at this amount per year for appliance and non-appliance upgrades.

**Type:** int

**Current value:** 14000

---

### gov.doe.high_efficiency_electric_home_rebate.cap.heat_pump_water_heater
**Label:** High efficiency electric home rebate annual cap on electric heat pump water heaters

The US caps high-efficiency home program rebates at this amount per year for heat pump water heaters.

**Type:** int

**Current value:** 1750

---

### gov.doe.high_efficiency_electric_home_rebate.cap.insulation_air_sealing_ventilation
**Label:** High efficiency electric home rebate annual cap on insulation, air sealing, and ventilation

The US caps high-efficiency home program rebates at this amount per year for insulation, air sealing, and ventilation.

**Type:** int

**Current value:** 1600

---

### gov.doe.high_efficiency_electric_home_rebate.cap.electric_stove_cooktop_range_or_oven
**Label:** High efficiency electric home rebate annual cap on electric stoves, cooktops ranges, or ovens

The US caps high-efficiency home program rebates at this amount per year for electric stoves, cooktops, ranges, or ovens.

**Type:** int

**Current value:** 840

---

### gov.doe.high_efficiency_electric_home_rebate.cap.electric_heat_pump_clothes_dryer
**Label:** High efficiency electric home rebate annual cap on electric heat pump clothes dryers

The US caps high-efficiency home program rebates at this amount per year for heat pump clothes dryers.

**Type:** int

**Current value:** 840

---

### gov.doe.high_efficiency_electric_home_rebate.cap.electric_load_service_center_upgrade
**Label:** High efficiency electric home rebate annual cap on electric load service center upgrades

The US caps high-efficiency home program rebates at this amount per year for electric load service center upgrades.

**Type:** int

**Current value:** 4000

---

### gov.doe.high_efficiency_electric_home_rebate.cap.electric_wiring
**Label:** High efficiency electric home rebate annual cap on electric wiring

The US caps high-efficiency home program rebates at this amount per year for electric wiring.

**Type:** int

**Current value:** 2500

---

### gov.doe.high_efficiency_electric_home_rebate.cap.heat_pump
**Label:** High efficiency electric home rebate annual cap on electric heat pumps

The US caps high-efficiency home program rebates at this amount per year for heat pumps.

**Type:** int

**Current value:** 8000

---

### gov.doe.residential_efficiency_electrification_rebate.threshold.high
**Label:** Energy savings to qualify for a high residential efficiency and electrification rebate

The US limits high residential efficiency and electrification rebates to retrofits achieving at least this percentage of modeled energy savings.

**Type:** float

**Current value:** 0.35

---

### gov.doe.residential_efficiency_electrification_rebate.threshold.medium
**Label:** Energy savings to qualify for a medium residential efficiency and electrification rebate

The US limits medium residential efficiency and electrification rebates to retrofits achieving at least this percentage of modeled energy savings.

**Type:** float

**Current value:** 0.2

---

### gov.doe.residential_efficiency_electrification_rebate.threshold.low
**Label:** Energy savings to qualify for a residential efficiency and electrification rebate

The US limits residential efficiency and electrification rebates to retrofits achieving at least this percentage of modeled energy savings.

**Type:** float

**Current value:** 0.15

---

### gov.states.vt.tax.income.agi.exclusions.capital_gain.flat.cap
**Label:** Vermont flat capital gains exclusion cap

Vermont caps the flat capital gains exclusion at this amount.

**Type:** int

**Current value:** 5000

---

### gov.states.vt.tax.income.agi.exclusions.capital_gain.income_share_cap
**Label:** Vermont capital gains exclusion cap as fraction of taxable income

Vermont caps the net capital gains exclusion at this fraction of federal taxable income.

**Type:** float

**Current value:** 0.4

---

### gov.states.vt.tax.income.agi.exclusions.capital_gain.percentage.rate
**Label:** Vermont capital gains percentage exclusion calculation rate

Vermont multiplies the adjusted net capital gains by this rate under the capital gains percentage exclusion.

**Type:** float

**Current value:** 0.4

---

### gov.states.vt.tax.income.agi.exclusions.capital_gain.percentage.cap
**Label:** Vermont capital gains percentage exclusion max amount

Vermont caps the capital gains percentage exclusion at this amount.

**Type:** int

**Current value:** 350000

---

### gov.states.vt.tax.income.agi.retirement_income_exemption.divisor
**Label:** Vermont retirement income exemption divisor

Vermont divides the retirement income by this amount under the retirement income exemption.

**Type:** int

**Current value:** 10000

---

### gov.states.vt.tax.income.agi.retirement_income_exemption.csrs.amount
**Label:** Vermont CSRS retirement income exemption cap

Vermont caps the retirement income exemption from Civil Service Retirement System (CSRS) retirement system at this amount.

**Type:** int

**Current value:** 10000

---

### gov.states.vt.tax.income.agi.retirement_income_exemption.military_retirement.amount
**Label:** Vermont military retirement income exemption cap

Vermont caps the retirement income exemption from military retirement system at this amount.

**Type:** int

**Current value:** 10000

---

### gov.states.vt.tax.income.deductions.standard.additional
**Label:** Vermont additional aged or blind, head or spouse, standard deduction amount

Vermont provides this additional standard deduction amount for each aged or blind head or spouse.

**Type:** float

**Current value:** 1249.1944768925491

---

### gov.states.vt.tax.income.credits.elderly_or_disabled
**Label:** Vermont elderly or the disabled tax credit match

Vermont matches this fraction of the federal credit for elderly or the disabled.

**Type:** float

**Current value:** 0.24

---

### gov.states.vt.tax.income.credits.renter.fmr_rate
**Label:** Vermont renter credit fair market rent rate

Vermont provides a renter credit of this fraction of fair market rent.

**Type:** float

**Current value:** 0.1

---

### gov.states.vt.tax.income.credits.renter.shared_residence_reduction
**Label:** Vermont renter credit shared rent fraction

Vermont reduces the renter credit by this fraction for filers who reside with people outside their filing unit.

**Type:** float

**Current value:** 0.5

---

### gov.states.vt.tax.income.credits.renter.countable_tax_exempt_ss_fraction
**Label:** Vermont renter credit non-taxable social security rate

Vermont counts this fraction of tax-exempt social security benefits as income for the renter credit.

**Type:** float

**Current value:** 0.75

---

### gov.states.vt.tax.income.credits.ctc.amount
**Label:** Vermont Child Tax Credit amount

Vermont provides this amount per qualifying child under the child tax credit.

**Type:** int

**Current value:** 1000

---

### gov.states.vt.tax.income.credits.ctc.reduction.increment
**Label:** Vermont Child Tax Credit reduction increment

Vermont reduces the child tax credit for each of these increments of adjusted gross income exceeding the threshold.

**Type:** int

**Current value:** 1000

---

### gov.states.vt.tax.income.credits.ctc.reduction.amount
**Label:** Vermont Child Tax Credit reduction amount

Vermont reduces the child tax credit by this amount for each increment of adjusted gross income exceeding the threshold.

**Type:** int

**Current value:** 20

---

### gov.states.vt.tax.income.credits.ctc.reduction.start
**Label:** Vermont Child Tax Credit reduction threshold

Vermont reduces the child tax credit for filers with adjusted gross income above this amount.

**Type:** int

**Current value:** 125000

---

### gov.states.vt.tax.income.credits.ctc.age_limit
**Label:** Vermont Child Tax Credit age limit

Vermont limits its child tax credit to children this age or younger.

**Type:** int

**Current value:** 5

---

### gov.states.vt.tax.income.credits.cdcc.rate
**Label:** Vermont child and dependent care credit match

Vermont matches this percent of the federal child and dependent care credit.

**Type:** float

**Current value:** 0.72

---

### gov.states.vt.tax.income.credits.cdcc.low_income.rate
**Label:** Vermont low-income child and dependent care credit match

Vermont matches this percent of the federal child and dependent care credit for low-income filers.

**Type:** float

**Current value:** 0.5

---

### gov.states.vt.tax.income.credits.eitc.match
**Label:** Vermont earned income tax credit match

Vermont matches this fraction of the federal earned income tax credit.

**Type:** float

**Current value:** 0.38

---

### gov.states.va.tax.income.subtractions.military_basic_pay.threshold
**Label:** Virginia military basic pay subtraction

Virginia provides a military basic pay subtraction up to this amount for military personnel stationed inside or outside Virginia.

**Type:** int

**Current value:** 15000

---

### gov.states.va.tax.income.subtractions.disability_income.amount
**Label:** Virginia disability income subtraction

Virginia provides a disability income subtraction up to this amount for personnel with permanent and total disability on federal return

**Type:** int

**Current value:** 20000

---

### gov.states.va.tax.income.subtractions.military_benefit.age_threshold
**Label:** Virginia military benefit subtraction age threshold

Virginia provides a military benefit subtraction for military personnel of this age or older.

**Type:** int

**Current value:** 55

---

### gov.states.va.tax.income.subtractions.military_benefit.amount
**Label:** Virginia military benefit subtraction amount

Virginia provides a military benefit subtraction up to this amount.

**Type:** int

**Current value:** 40000

---

### gov.states.va.tax.income.subtractions.military_benefit.availability
**Label:** Virginia military benefit subtraction age threshold availability

Virginia allows for the military benefit subtraction to be claimed regardless of age if this is true.

**Type:** bool

**Current value:** False

---

### gov.states.va.tax.income.subtractions.national_guard_pay.cap
**Label:** Virginia national guard pay subtraction cap

Virginia caps the national guard pay subtraction to this amount.

**Type:** int

**Current value:** 5500

---

### gov.states.va.tax.income.subtractions.age_deduction.age_minimum
**Label:** Age threshold for Virginia Age Deduction

Virginia allows an age deduction for taxpayers this age and older.

**Type:** int

**Current value:** 65

---

### gov.states.va.tax.income.subtractions.age_deduction.birth_year_limit_for_full_amount
**Label:** Birth year threshold for Virginia Age Deduction.

Virginia allows a full age deduction for taxpayers born before this year.

**Type:** int

**Current value:** 1939

---

### gov.states.va.tax.income.subtractions.age_deduction.amount
**Label:** Virginia age deduction amount

Virginia provides an age deduction of up to this amount.

**Type:** int

**Current value:** 12000

---

### gov.states.va.tax.income.subtractions.federal_state_employees.amount
**Label:** Virginia federal state employees subtraction

Virginia provides a federal state employees subtraction up to this amount for head and spouse who is a federal or state employee.

**Type:** int

**Current value:** 15000

---

### gov.states.va.tax.income.exemptions.aged_blind
**Label:** Virginia aged and blind exemption

Virginia provides an income tax exemption of this value for each aged and blind head or spouse in the filing unit.

**Type:** int

**Current value:** 800

---

### gov.states.va.tax.income.exemptions.personal
**Label:** Virginia personal exemption amount

Virginia provides an income tax exemption of this value for each person in the filing unit.

**Type:** int

**Current value:** 930

---

### gov.states.va.tax.income.exemptions.spouse_tax_adjustment.divisor
**Label:** Virginia spouse tax adjustment divisor

Virginia divides the taxable income by this amount when calculating the spouse tax adjustment.

**Type:** int

**Current value:** 2

---

### gov.states.va.tax.income.exemptions.spouse_tax_adjustment.cap
**Label:** Virginia spouse tax adjustment cap

Virginia caps the spouse tax adjustment at the following amount.

**Type:** int

**Current value:** 259

---

### gov.states.va.tax.income.credits.eitc.match.non_refundable
**Label:** Virginia non-refundable earned income tax credit match

Virginia matches this percent of the federal earned income tax credit as a non-refundable credit.

**Type:** float

**Current value:** 0.2

---

### gov.states.va.tax.income.credits.eitc.match.refundable
**Label:** Virginia refundable earned income tax credit match

Virginia matches this percent of the federal earned income tax credit as a refundable credit.

**Type:** float

**Current value:** 0.15

---

### gov.states.va.tax.income.credits.eitc.low_income_tax.base
**Label:** Virginia earned income tax credit low income credit base

Virginia multiplies the number of personal exemptions by this amount under the low income tax credit.

**Type:** int

**Current value:** 300

---

### gov.states.sc.tax.income.subtractions.retirement.subtract_military
**Label:** South Carolina choice to subtract survivors retirement deduction from military retirement deduction

South Carolina subtracts the survivors retirement deduction from the military retirement deduction if this is true.

**Type:** bool

**Current value:** False

---

### gov.states.sc.tax.income.deductions.net_capital_gain.rate
**Label:** South Carolina net capital gain deduction rate

South Carolina deducts this fraction of net capital gains from taxable income.

**Type:** float

**Current value:** 0.44

---

### gov.states.sc.tax.income.deductions.young_child.ineligible_age
**Label:** South Carolina young child deduction ineligible age

South Carolina limits its young child deduction to children below this age.

**Type:** int

**Current value:** 6

---

### gov.states.sc.tax.income.deductions.young_child.amount
**Label:** South Carolina young child deduction amount

South Carolina provides a young child deduction of this amount.

**Type:** int

**Current value:** 4610

---

### gov.states.sc.tax.income.exemptions.senior.age_threshold
**Label:** South Carolina senior exemption age threshold

South Carolina allows filers above this age to be eligible for the senior exemption.

**Type:** int

**Current value:** 65

---

### gov.states.sc.tax.income.exemptions.senior.amount
**Label:** South Carolina senior exemption amount

South Carolina provides the following senior exemption amount for self.

**Type:** int

**Current value:** 15000

---

### gov.states.sc.tax.income.exemptions.senior.spouse_amount
**Label:** South Carolina senior exemption spouse amount

South Carolina provides the following senior exemption amount for spouse.

**Type:** int

**Current value:** 15000

---

### gov.states.sc.tax.income.credits.cdcc.max_care_expense_year_offset
**Label:** Decoupled year offset for maximum CDCC expense cap

Decoupled year offset for maximum CDCC expense cap

**Type:** int

**Current value:** 0

---

### gov.states.sc.tax.income.credits.cdcc.rate
**Label:** South Carolina Child and Dependent Care Credit match

South Carolina matches this share of the federal Child and Dependent Care Credit.

**Type:** float

**Current value:** 0.07

---

### gov.states.sc.tax.income.credits.eitc.rate
**Label:** South Carolina EITC Rate

South Carolina matches the federal EITC at this rate.

**Type:** float

**Current value:** 1.25

---

### gov.states.ut.tax.income.rate
**Label:** Utah income tax rate

Utah taxes personal income at this flat rate.

**Type:** float

**Current value:** 0.0455

---

### gov.states.ut.tax.income.credits.at_home_parent.parent_max_earnings
**Label:** Utah at-home parent credit maximum earnings

Maximum earnings for the claimant to qualify for the Utah at-home parent credit.

**Type:** int

**Current value:** 3000

---

### gov.states.ut.tax.income.credits.at_home_parent.max_agi
**Label:** Utah at-home parent credit maximum AGI

Maximum adjusted gross income for a tax unit to qualify for the Utah at-home parent credit.

**Type:** int

**Current value:** 50000

---

### gov.states.ut.tax.income.credits.at_home_parent.max_child_age
**Label:** Utah at-home parent credit maximum child age

Maximum age for a child to quality for the Utah at-home parent credit.

**Type:** int

**Current value:** 1

---

### gov.states.ut.tax.income.credits.at_home_parent.amount
**Label:** Utah at-home parent credit amount

The amount of at-home credit per qualifying child.

**Type:** int

**Current value:** 100

---

### gov.states.ut.tax.income.credits.taxpayer.rate
**Label:** Utah taxpayer credit rate

The maximum taxpayer credit is this percentage of federal deductions plus the personal exemption.

**Type:** float

**Current value:** 0.06

---

### gov.states.ut.tax.income.credits.taxpayer.phase_out.rate
**Label:** Utah taxpayer credit phase-out rate

The Utah taxpayer credit reduces by this rate for each dollar of income above the phase-out threshold.

**Type:** float

**Current value:** 0.013

---

### gov.states.ut.tax.income.credits.taxpayer.personal_exemption
**Label:** Utah taxpayer credit personal exemption

This exemption is added to federal standard or itemized deductions for the taxpayer credit.

**Type:** float

**Current value:** 2108.4230257812505

---

### gov.states.ut.tax.income.credits.taxpayer.in_effect
**Label:** Utah additional qualifying dependent for personal exemption in effect

Utah provides an additional qualifying dependent personal exemption if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.ut.tax.income.credits.retirement.birth_year
**Label:** Utah retirement credit birth year

Utah limits the retirement credit to filers born in or before this year.

**Type:** int

**Current value:** 1952

---

### gov.states.ut.tax.income.credits.earned_income.rate
**Label:** Utah EITC match

Utah matches this percentage of the federal earned income tax credit.

**Type:** float

**Current value:** 0.2

---

### gov.states.ut.tax.income.credits.ctc.amount
**Label:** Utah child tax credit amount

Utah provides the following child tax credit amount, per eligible child.

**Type:** int

**Current value:** 1000

---

### gov.states.ut.tax.income.credits.ctc.reduction.rate
**Label:** Utah child tax credit reduction rate

Utah reduces the child tax credit by the following rate, based on state adjusted gross income and tax exempt interest income.

**Type:** float

**Current value:** 0.1

---

### gov.states.ga.tax.income.agi.exclusions.retirement.cap.younger
**Label:** Georgia retirement income exclusion younger cap

Georgia subtracts this lower retirement income amount for filers meeting the younger age threshold.

**Type:** int

**Current value:** 35000

---

### gov.states.ga.tax.income.agi.exclusions.retirement.cap.earned_income
**Label:** Georgia retirement exclusion earned income cap

Georgia limits the earned income portion of the retirement exclusion to the following amount.

**Type:** int

**Current value:** 4000

---

### gov.states.ga.tax.income.agi.exclusions.retirement.cap.older
**Label:** Georgia retirement income exclusion older cap

Georgia subtracts this higher retirement income amount for filers meeting the older age threshold.

**Type:** int

**Current value:** 65000

---

### gov.states.ga.tax.income.agi.exclusions.retirement.age_threshold.younger
**Label:** Georgia retirement income exclusion younger age threshold

Georgia allows filers to receive the lower retirement income exclusion amount at or above the following younger age threshold.

**Type:** int

**Current value:** 62

---

### gov.states.ga.tax.income.agi.exclusions.retirement.age_threshold.older
**Label:** Georgia retirement income exclusion older age threshold

Georgia allows filers to receive the higher retirement income exclusion amount at or above the following older age threshold.

**Type:** int

**Current value:** 65

---

### gov.states.ga.tax.income.agi.exclusions.military_retirement.age_limit
**Label:** Georgia military retirement income exclusion age limit

Georgia qualifies filers for the military retirement income exclusions below the following age.

**Type:** int

**Current value:** 62

---

### gov.states.ga.tax.income.agi.exclusions.military_retirement.additional.earned_income_threshold
**Label:** Georgia additional retirement exclusion earned income threshold

Georgia qualifies filers for the additional military retirement income exclusion with earned income above this threshold.

**Type:** int

**Current value:** 17500

---

### gov.states.ga.tax.income.agi.exclusions.military_retirement.additional.amount
**Label:** Georgia military retirement income exclusion additional amount

Georgia subtracts this additional amount of military retirement income exclusion from adjusted gross income.

**Type:** int

**Current value:** 17500

---

### gov.states.ga.tax.income.agi.exclusions.military_retirement.base
**Label:** Georgia military retirement income exclusion base amount

Georgia provides military retirement income exclusion for the age filer at this amount.

**Type:** int

**Current value:** 17500

---

### gov.states.ga.tax.income.deductions.standard.blind.head
**Label:** Georgia additional standard deduction for blind head

Georgia allows for this additional standard deduction for blind filers.

**Type:** int

**Current value:** 1300

---

### gov.states.ga.tax.income.deductions.standard.blind.spouse
**Label:** Georgia additional standard deduction for blind spouse

Georgia allows for this additional standard deduction for the blind spouse.

**Type:** int

**Current value:** 1300

---

### gov.states.ga.tax.income.deductions.standard.aged.amount.head
**Label:** Georgia additional standard deduction for aged head

Georgia provides this additional standard deduction for aged filers.

**Type:** int

**Current value:** 1300

---

### gov.states.ga.tax.income.deductions.standard.aged.amount.spouse
**Label:** Georgia additional standard deduction for aged spouse

Georgia provides this additional standard deduction for the aged spouse.

**Type:** int

**Current value:** 1300

---

### gov.states.ga.tax.income.deductions.standard.aged.age_threshold
**Label:** Georgia additional standard deduction age threshold

Georgia provides additional standard deduction for the taxpayer or spouse at or above the following age.

**Type:** int

**Current value:** 65

---

### gov.states.ga.tax.income.exemptions.dependent
**Label:** Georgia dependent exemption amount

Georgia issues the following exemption amount for each dependent.

**Type:** int

**Current value:** 4000

---

### gov.states.ga.tax.income.credits.low_income.supplement_age_eligibility
**Label:** Georgia low income credit supplement age eligibility

Georgia provides an additional exemption under the low income credit for head and spouse at or above this age threshold.

**Type:** int

**Current value:** 65

---

### gov.states.ga.tax.income.credits.cdcc.rate
**Label:** Georgia tax credits for qualified child and dependent care expenses

Georgia matches this percentage of the federal child and dependent care credit.

**Type:** float

**Current value:** 0.3

---

### gov.states.ms.tax.income.adjustments.self_employment.rate
**Label:** Mississippi self-employment tax adjustment rate

Mississippi subtracts this fraction of self-employment taxes from adjusted gross income.

**Type:** float

**Current value:** 0.5

---

### gov.states.ms.tax.income.adjustments.national_guard_or_reserve_pay.cap
**Label:** Mississippi national guard or reserve pay adjustment cap

Mississippi limits the national guard or reserve pay adjustment to the following amount.

**Type:** int

**Current value:** 15000

---

### gov.states.ms.tax.income.exemptions.blind.amount
**Label:** Mississippi blind exemption amount

Mississippi provides an exemption of this amount per blind filer or spouse.

**Type:** int

**Current value:** 1500

---

### gov.states.ms.tax.income.exemptions.dependents.amount
**Label:** Mississippi dependent exemption

Mississippi provides an exemption of this amount per dependent.

**Type:** int

**Current value:** 1500

---

### gov.states.ms.tax.income.exemptions.aged.age_threshold
**Label:** Mississippi senior exemption age threshold

Mississippi provides the aged exemption amount for aged filers or spouse at or above this age.

**Type:** int

**Current value:** 65

---

### gov.states.ms.tax.income.exemptions.aged.amount
**Label:** Mississippi aged exemption amount

Mississippi provides an exemption of this amount per aged filer or spouse.

**Type:** int

**Current value:** 1500

---

### gov.states.ms.tax.income.credits.cdcc.match
**Label:** Mississippi CDCC match

Mississippi matches this percentage of the federal child and dependent care credit.

**Type:** float

**Current value:** 0.25

---

### gov.states.ms.tax.income.credits.cdcc.income_limit
**Label:** Mississippi CDCC income limit

Mississippi limits the child and dependent care credit to filers with income below the following amount.

**Type:** int

**Current value:** 50000

---

### gov.states.mt.tax.income.subtractions.disability_income.age_threshold
**Label:** Montana disability income exclusion age limit

Montana limits the disability income exclusion to filers under this age.

**Type:** int

**Current value:** 65

---

### gov.states.mt.tax.income.subtractions.disability_income.cap
**Label:** Montana disability income exclusion cap

Montana caps the individual disability income exclusion at this amount.

**Type:** int

**Current value:** 5200

---

### gov.states.mt.tax.income.subtractions.tuition.cap
**Label:** Montana tuition subtraction cap

Montana caps the tuition subtraction at this maximum amount.

**Type:** int

**Current value:** 3000

---

### gov.states.mt.tax.income.deductions.standard.rate
**Label:** Montana standard deduction rate

Montana provides a standard deduction equal to this percentage of Montana adjusted gross income, subject to minimum and maximum values.

**Type:** float

**Current value:** 0.2

---

### gov.states.mt.tax.income.deductions.child_dependent_care_expense.age_limit
**Label:** Montana Child and Dependent Care Expense deduction age threshold

Montana limits the child and dependent care expense deduction to expenses for dependents who have a disability or are below this age.

**Type:** int

**Current value:** 15

---

### gov.states.mt.tax.income.main.capital_gains.in_effect
**Label:** Montana capital gains tax rate in effect

Montana taxes capital gains at a separate tax rate from other income if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.mt.tax.income.exemptions.interest.age_threshold
**Label:** Montana senior interest income exclusion age threshold

Montana partially excludes interest from adjusted gross income of filers and spouses at or above this age threshold.

**Type:** int

**Current value:** 65

---

### gov.states.mt.tax.income.exemptions.age_threshold
**Label:** Montana income tax aged exemption age threshold

Montana provides an additional tax exemption to filers this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.mt.tax.income.exemptions.amount
**Label:** Montana income tax exemption amount

Montana deducts this amount for each eligible exemption when computing taxable income.

**Type:** int

**Current value:** 2960

---

### gov.states.mt.tax.income.credits.elderly_homeowner_or_renter.net_household_income.standard_exclusion
**Label:** Montana elderly homeowner or renter credit net household income standard exclusion

Montana excludes this amount of net household income when computing net household income for elderly homeowner or renter credit.

**Type:** int

**Current value:** 12600

---

### gov.states.mt.tax.income.credits.elderly_homeowner_or_renter.age_threshold
**Label:** Montana elderly homeowner or renter credit age threshold

Montana limits the elderly homeowner or renter credit to filers of this age or older.

**Type:** int

**Current value:** 62

---

### gov.states.mt.tax.income.credits.elderly_homeowner_or_renter.rent_equivalent_tax_rate
**Label:** Montana elderly homeowner or renter credit rent equivalent rate

Montana counts this fraction of rent as property tax for its elderly homeowner or renter credit.

**Type:** float

**Current value:** 0.15

---

### gov.states.mt.tax.income.credits.elderly_homeowner_or_renter.cap
**Label:** Montana elderly homeowner or renter credit pre multiplier cap

Montana caps the pre-multiplier amount of the elderly homeowner or renter credit to this amount.

**Type:** int

**Current value:** 1150

---

### gov.states.mt.tax.income.credits.rebate.property.amount
**Label:** Montana property tax rebate amount

Montana provides the following property tax rebate amount.

**Type:** int

**Current value:** 675

---

### gov.states.mt.tax.income.credits.ctc.income_limit.investment
**Label:** Montana child tax credit investment income limit

Montana limits its child tax credit to filers with investment income below this amount.

**Type:** int

**Current value:** 10300

---

### gov.states.mt.tax.income.credits.ctc.income_limit.agi
**Label:** Montana child tax credit adjusted gross income limit

Montana limits its child tax credit to filers with federal adjusted gross income below this amount.

**Type:** int

**Current value:** 56000

---

### gov.states.mt.tax.income.credits.ctc.reduction.increment
**Label:** Montana child tax credit reduction increment

Montana reduces the child tax credit for each of these increments that a filer's adjusted gross income exceeds the threshold.

**Type:** int

**Current value:** 1000

---

### gov.states.mt.tax.income.credits.ctc.reduction.amount
**Label:** Montana child tax credit reduction amount

Montana reduces the child tax credit by this amount for each income increment.

**Type:** int

**Current value:** 90

---

### gov.states.mt.tax.income.credits.ctc.reduction.threshold
**Label:** Montana child tax credit reduction threshold

Montana reduces the child tax credit for filers with income above this income threshold.

**Type:** int

**Current value:** 50000

---

### gov.states.mt.tax.income.credits.capital_gain.percentage
**Label:** Montana capital gains credit rate

Montana provides a credit for this fraction of the filer's net capital gains.

**Type:** float

**Current value:** 0.02

---

### gov.states.mt.tax.income.credits.eitc.match
**Label:** Montana EITC match

Montana matches this fraction of the federal earned income tax credit.

**Type:** float

**Current value:** 0.1

---

### gov.states.mo.tax.income.deductions.mo_max_social_security_benefit
**Label:** Missouri max social security benefit

Missouri provides maximum amount of social security benefit.

**Type:** float

**Current value:** 48537.179835643285

---

### gov.states.mo.tax.income.deductions.business_income.rate
**Label:** Missouri business income deduction rate

Missouri caps the business income deduction at this percentage of total business income.

**Type:** float

**Current value:** 0.2

---

### gov.states.mo.tax.income.deductions.mo_max_private_pension
**Label:** Missouri maximum private pension amount

Missouri provides this maximum amount of private pension.

**Type:** int

**Current value:** 6000

---

### gov.states.mo.tax.income.minimum_taxable_income
**Label:** Missouri minimum taxable income

Missouri only levies tax on taxable income of at least this amount.

**Type:** int

**Current value:** 1273

---

### gov.states.mo.tax.income.credits.wftc.match
**Label:** Missouri EITC match

Missouri matches this percentage of the federal Earned Income Tax Credit under the Working Families Tax Credit.

**Type:** float

**Current value:** 0.2

---

### gov.states.mo.tax.income.credits.property_tax.income_offset.joint_renter
**Label:** Missouri income offset for married joint unit that paid some rent

Gross income offset for a married couple filing jointly who rent.

**Type:** int

**Current value:** 2000

---

### gov.states.mo.tax.income.credits.property_tax.income_offset.non_joint
**Label:** Missouri income offset for all tax units that did not file as married joint

Gross income offset for those not a married couple filing jointly.

**Type:** int

**Current value:** 0

---

### gov.states.mo.tax.income.credits.property_tax.income_offset.joint_owner
**Label:** Missouri income offset for married joint unit that owns house (and paid no rent)

Gross income offset for a married couple filing jointly who own.

**Type:** int

**Current value:** 4000

---

### gov.states.mo.tax.income.credits.property_tax.age_threshold
**Label:** Missouri property tax credit age threshold

Age threshold for qualification for the MO Property Tax Credit

**Type:** int

**Current value:** 65

---

### gov.states.mo.tax.income.credits.property_tax.phase_out.step
**Label:** Missouri property tax credit phaseout step size

Step size by which maximum MO property tax credit is phased out.

**Type:** int

**Current value:** 300

---

### gov.states.mo.tax.income.credits.property_tax.phase_out.rate
**Label:** Missouri property tax credit phaseout rate

Rate at which maximum MO property tax credit is phased out.

**Type:** float

**Current value:** 0.000625

---

### gov.states.mo.tax.income.credits.property_tax.phase_out.threshold
**Label:** Missouri property tax credit phaseout threshold

Net household income above which MO property tax credit is reduced.

**Type:** int

**Current value:** 14300

---

### gov.states.mo.tax.income.credits.property_tax.rent_property_tax_limit
**Label:** Missouri property tax credit limit for property renters

Maximum claimable property tax associated with a rented property.

**Type:** int

**Current value:** 750

---

### gov.states.mo.tax.income.credits.property_tax.property_tax_rent_ratio
**Label:** Missouri property tax credit property-tax-to-total-rent ratio

Ratio of property tax to total rent.

**Type:** float

**Current value:** 0.2

---

### gov.states.mo.tax.income.credits.property_tax.property_tax_limit
**Label:** Missouri property tax credit limit for property owners

Maximum claimable property tax associated with an owned property.

**Type:** int

**Current value:** 1100

---

### gov.states.mo.tax.income.credits.property_tax.aged_survivor_min_age
**Label:** Missouri property tax credit aged survivor minimum age

Minimum age for person with social security survivors benefits

**Type:** int

**Current value:** 60

---

### gov.states.ma.tax.income.rates.part_b
**Label:** Massachusetts main income tax rate

The tax rate on all taxable income that is not dividends or capital gains.

**Type:** float

**Current value:** 0.05

---

### gov.states.ma.tax.income.rates.part_a.capital_gains
**Label:** Massachusetts short-term capital gains tax rate

Massachusetts taxes Part A short-term capital gains at this rate.

**Type:** float

**Current value:** 0.085

---

### gov.states.ma.tax.income.rates.part_a.dividends
**Label:** Massachusetts dividend tax rate

The tax rate on Part A dividend income.

**Type:** float

**Current value:** 0.05

---

### gov.states.ma.tax.income.rates.part_c
**Label:** Massachusetts long-term capital gains rate

The tax rate on long-term capital gains.

**Type:** float

**Current value:** 0.05

---

### gov.states.ma.tax.income.deductions.rent.share
**Label:** Rent share for state income tax deduction

Share of rent that can be deducted from income for Massachusetts income tax.

**Type:** float

**Current value:** 0.5

---

### gov.states.ma.tax.income.deductions.public_retirement_contributions
**Label:** Massachusetts income tax pension contributions maximum deduction

Maximum pension contributions deductible per person for Massachusetts state income tax.

**Type:** int

**Current value:** 2000

---

### gov.states.ma.tax.income.capital_gains.long_term_collectibles_deduction
**Label:** MA Long-term capital gains on collectibles deduction rate

Percent of long-term capital gains on collectibles that is deductible from Part A (interest, dividends and short-term capital gains) gross income, after loss deductions.

**Type:** float

**Current value:** 0.5

---

### gov.states.ma.tax.income.capital_gains.deductible_against_interest_dividends
**Label:** MA income tax max capital gains deductible against interest or dividends

Maximum capital losses deductible against interest or dividends.

**Type:** int

**Current value:** 2000

---

### gov.states.ma.tax.income.exemptions.blind
**Label:** Massachusetts income tax blind exemption

Massachusetts income tax exemption per blind head or spouse.

**Type:** int

**Current value:** 2200

---

### gov.states.ma.tax.income.exemptions.dependent
**Label:** Massachusetts income tax dependent exemption

State income tax exemption per dependent.

**Type:** int

**Current value:** 1000

---

### gov.states.ma.tax.income.exemptions.aged.amount
**Label:** Massachusetts income tax aged exemption

Massachusetts income tax exemption per aged head or spouse.

**Type:** int

**Current value:** 700

---

### gov.states.ma.tax.income.exemptions.aged.age
**Label:** Massachusetts income tax aged exemption age threshold

Age threshold to be eligible for a Massachusetts income tax aged exemption

**Type:** int

**Current value:** 65

---

### gov.states.ma.tax.income.credits.dependent_care.dependent_cap
**Label:** Massachusetts dependent care credit dependent cap

Massachusetts dependent care credit maximum number of qualifying individuals.

**Type:** int

**Current value:** 2

---

### gov.states.ma.tax.income.credits.dependent_care.amount
**Label:** Massachusetts dependent care credit

Massachusetts dependent care credit amount per dependent

**Type:** int

**Current value:** 240

---

### gov.states.ma.tax.income.credits.dependent_care.in_effect
**Label:** Massachusetts Dependent Care Tax Credit in effect

Massachusetts provides the greater of the Dependent Tax Credit and the Dependent Care Tax Credit if this is true.

**Type:** bool

**Current value:** False

---

### gov.states.ma.tax.income.credits.limited_income_credit.income_limit
**Label:** Massachusetts limited income tax credit income limit

Maximum income for the Massachusetts Limited Income Credit, as a percentage of the AGI exempt limit.

**Type:** float

**Current value:** 1.75

---

### gov.states.ma.tax.income.credits.limited_income_credit.percent
**Label:** Massachusetts limited income tax credit percentage

Massachusetts limited income tax credit percentage.

**Type:** float

**Current value:** 0.1

---

### gov.states.ma.tax.income.credits.senior_circuit_breaker.amount.min_real_estate_tax
**Label:** Massachusetts Senior Circuit Breaker real estate tax threshold

Real estate taxes (or equivalent rents) over this percentage of income (for the MA SCB) increase the Massachusetts Senior Circuit Breaker credit.

**Type:** float

**Current value:** 0.1

---

### gov.states.ma.tax.income.credits.senior_circuit_breaker.amount.max
**Label:** Massachusetts Senior Circuit Breaker maximum payment

Maximum payment under the Massachusetts Senior Circuit Breaker credit.

**Type:** int

**Current value:** 2590

---

### gov.states.ma.tax.income.credits.senior_circuit_breaker.amount.rent_tax_share
**Label:** Massachusetts Senior Circuit Breaker rent tax share

Percentage of rent which is regarded as 'real estate tax payment' for the Massachusetts Senior Circuit Breaker.

**Type:** float

**Current value:** 0.25

---

### gov.states.ma.tax.income.credits.senior_circuit_breaker.eligibility.min_age
**Label:** Massachusetts Senior Circuit Breaker minimum age

Minimum age to qualify for the Massachusetts Senior Circuit Breaker credit.

**Type:** int

**Current value:** 65

---

### gov.states.ma.tax.income.credits.senior_circuit_breaker.eligibility.max_property_value
**Label:** Massachusetts Senior Circuit Breaker maximum property value

Maximum assessed property value for the Massachusetts Senior Circuit Breaker credit.

**Type:** int

**Current value:** 1025000

---

### gov.states.ma.tax.income.credits.covid_19_essential_employee_premium_pay_program.min_earnings
**Label:** Massachusetts COVID-19 Essential Employee Premium Pay Program minimum earnings

Minimum earned income to qualify for Massachusetts COVID-19 Essential Employee Premium Pay Program.

**Type:** int

**Current value:** 13500

---

### gov.states.ma.tax.income.credits.covid_19_essential_employee_premium_pay_program.amount
**Label:** Massachusetts COVID-19 Essential Employee Premium Pay Program amount

Amount of Massachusetts COVID-19 Essential Employee Premium Pay Program.

**Type:** int

**Current value:** 0

---

### gov.states.ma.tax.income.credits.covid_19_essential_employee_premium_pay_program.max_poverty_ratio
**Label:** Massachusetts COVID-19 Essential Employee Premium Pay Program maximum poverty ratio

Maximum poverty ratio to qualify for Massachusetts COVID-19 Essential Employee Premium Pay Program.

**Type:** int

**Current value:** 3

---

### gov.states.ma.tax.income.credits.dependent.dependent_cap
**Label:** Massachusetts child and dependent credit dependent cap

Massachusetts limits its child and dependent tax credit to this number of dependents.

**Type:** float

**Current value:** inf

---

### gov.states.ma.tax.income.credits.dependent.amount
**Label:** Massachusetts child and dependent credit amount

Massachusetts provides this amount for each dependent in its child and dependent credit.

**Type:** int

**Current value:** 440

---

### gov.states.ma.tax.income.credits.dependent.child_age_limit
**Label:** Massachusetts dependent credit child age limit

Age at which children no longer qualify for the Massachusetts dependent tax credit.

**Type:** int

**Current value:** 13

---

### gov.states.ma.tax.income.credits.dependent.elderly_age_limit
**Label:** Massachusetts dependent credit elderly age limit

Age at which elderly dependents qualify for the Massachusetts dependent tax credit.

**Type:** int

**Current value:** 65

---

### gov.states.ma.tax.income.credits.eitc.match
**Label:** Massachusetts EITC match

Massachusetts matches this fraction of the federal earned income credit.

**Type:** float

**Current value:** 0.4

---

### gov.states.ak.dor.permanent_fund_dividend
**Label:** Alaska taxable permanent fund dividend

Alaska provides this Permanent Fund Dividend amount.

**Type:** float

**Current value:** 1403.83

---

### gov.states.ak.dor.energy_relief
**Label:** Alaska energy relief

Alaska provides this one-time energy relief payment.

**Type:** float

**Current value:** 298.17

---

### gov.states.ky.tax.income.deductions.standard
**Label:** Kentucky standard deduction amount

Kentucky provides this standard deduction amount.

**Type:** int

**Current value:** 3270

---

### gov.states.ky.tax.income.rate
**Label:** Kentucky income tax rate

Kentucky taxes individual income at this rate.

**Type:** float

**Current value:** 0.04

---

### gov.states.ky.tax.income.exclusions.pension_income.threshold
**Label:** Kentucky income tax rate

Kentucky caps the pension income at this amount for most individuals.

**Type:** int

**Current value:** 31110

---

### gov.states.ky.tax.income.credits.personal.amount.blind
**Label:** Kentucky personal tax credits blind amount

Kentucky provides this personal tax credit for blind filers.

**Type:** int

**Current value:** 40

---

### gov.states.ky.tax.income.credits.personal.amount.military
**Label:** Kentucky personal tax credits military service amount

Kentucky provides this personal tax credit for filers who served in the military.

**Type:** int

**Current value:** 20

---

### gov.states.ky.tax.income.credits.tuition_tax.rate
**Label:** Kentucky tuition tax credit rate

Kentucky matches this fraction of the American Opportunity and the Lifetime Learning credits, for undergraduate education at Kentucky institutions.

**Type:** float

**Current value:** 0.25

---

### gov.states.ky.tax.income.credits.dependent_care_service.match
**Label:** Kentucky dependent care service credit rate

Kentucky matches the federal child and dependent care credit at the following rate for its dependent care service credit.

**Type:** float

**Current value:** 0.2

---

### gov.states.ky.tax.income.credits.family_size.family_size_cap
**Label:** Kentucky family size tax credit family size cap

Kentucky caps the family size at this number when calculating the poverty threshold for the family size tax credit.

**Type:** int

**Current value:** 4

---

### gov.states.al.tax.income.deductions.itemized.work_related_expense_rate
**Label:** Alabama work-related expense deduction rate

Alabama deducts work-related expense over this percentage of adjusted gross income.

**Type:** float

**Current value:** 0.02

---

### gov.states.al.tax.income.deductions.itemized.medical_expense.income_floor
**Label:** Alabama medical expenses deduction income floor

Alabama deducts medical expenses over this percentage of adjusted gross income.

**Type:** float

**Current value:** 0.04

---

### gov.states.al.tax.income.exemptions.retirement.age_threshold
**Label:** Alabama retirement exemption age threshold

Alabama provides the retirement exemption to filers at or above this age threshold.

**Type:** int

**Current value:** 65

---

### gov.states.al.tax.income.exemptions.retirement.cap
**Label:** Alabama retirement exemption cap

Alabama caps the retirement exemption at this amount.

**Type:** int

**Current value:** 6000

---

### gov.states.nh.tax.income.rate
**Label:** New Hampshire tax rate

New Hampshire taxes interest and dividends at this rate.

**Type:** float

**Current value:** 0.02

---

### gov.states.nh.tax.income.exemptions.amount.old_age_addition
**Label:** New Hampshire old age exemption amount

New Hampshire provides an old age exemption amount for filers of or above the age 65.

**Type:** int

**Current value:** 1200

---

### gov.states.nh.tax.income.exemptions.amount.disabled_addition
**Label:** New Hampshire disabled exemption amount

New Hampshire provided an exemption amount for disabled filers below the age of 65.

**Type:** int

**Current value:** 1200

---

### gov.states.nh.tax.income.exemptions.amount.blind_addition
**Label:** New Hampshire blind exemption

New Hampshire provides an exemption of this amount per blind filer.

**Type:** int

**Current value:** 1200

---

### gov.states.nh.tax.income.exemptions.disability_age_threshold
**Label:** New Hampshire disabled exemption age threshold

New Hampshire provides an exemption for disabled filers below this age.

**Type:** int

**Current value:** 65

---

### gov.states.nh.tax.income.exemptions.old_age_eligibility
**Label:** New Hampshire old age exemption eligibility

New Hampshire provides an exemption for taxpayers on or older than this age.

**Type:** int

**Current value:** 65

---

### gov.states.mn.tax.income.subtractions.elderly_disabled.agi_offset_extra
**Label:** Minnesota extra AGI offset in elderly/disabled subtraction calculations

Minnesota allows a subtraction from federal adjusted gross income to get its taxable income that is available to tax units with elderly or disabled heads or spouses that met certain eligibility conditions with this variable being extra offset against US AGI when there are two aged/disabled spouses in the tax unit.

**Type:** int

**Current value:** 3500

---

### gov.states.mn.tax.income.subtractions.elderly_disabled.net_agi_fraction
**Label:** Minnesota elderly/disabled subraction net AGI fraction

Minnesota allows a subtraction from federal adjusted gross income to get its taxable income that is available to tax units with elderly or disabled heads or spouses that met certain eligibility conditions with this variable being the fraction of net AGI that reduces the subtraction amount.

**Type:** float

**Current value:** 0.5

---

### gov.states.mn.tax.income.subtractions.elderly_disabled.minimum_age
**Label:** Minnesota elderly/disabled subtraction minimum age for age eligibility

Minnesota allows a subtraction from federal adjusted gross income to get its taxable income that is available to tax units with elderly or disabled heads or spouses that met certain eligibility conditions such as being at least this old to be considered age eligible.

**Type:** int

**Current value:** 65

---

### gov.states.mn.tax.income.subtractions.social_security.reduction.applies
**Label:** Minnesota social security subtraction reduction applies

Minnesota reduced the social security subtraction if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.mn.tax.income.subtractions.social_security.reduction.rate
**Label:** Minnesota social security subtraction reduction rate

Minnesota reduces the social security subtraction by this fraction for each increment of adjusted gross income.

**Type:** float

**Current value:** 0.1

---

### gov.states.mn.tax.income.subtractions.social_security.net_income_fraction
**Label:** Minnesota social security subtraction net income fraction

Minnesota allows subtraction from federal adjusted gross income of the lesser of US-taxable social security and an alternative amount with the complex calculation of the alternative subtraction amount including this fraction which is applied to a net income amout.

**Type:** float

**Current value:** 0.2

---

### gov.states.mn.tax.income.subtractions.social_security.total_benefit_fraction
**Label:** Minnesota social security subtraction total benefit fraction

Minnesota allows subtraction from federal adjusted gross income of the lesser of US-taxable social security and an alternative amount with the complex calculation of the alternative subtraction amount including this fraction which is applied to total social security benefits.

**Type:** float

**Current value:** 0.5

---

### gov.states.mn.tax.income.subtractions.pension_income.reduction.increment
**Label:** Minnesota public pension subtraction reduction increment

Minnesota reduces the public pension subtraction by this fraction for each increments of adjusted gross income.

**Type:** int

**Current value:** 2000

---

### gov.states.mn.tax.income.subtractions.pension_income.reduction.rate
**Label:** Minnesota public pension subtraction reduction rate

Minnesota reduces the public pension subtraction by this fraction for each increment of adjusted gross income.

**Type:** float

**Current value:** 0.1

---

### gov.states.mn.tax.income.subtractions.charity.threshold
**Label:** Minnesota charity subtraction threshold

Minnesota allows subtraction from federal adjusted gross income of a fraction of charitable contributions in excess of this threshold for tax units that do not itemize Minnesota deductions.

**Type:** int

**Current value:** 500

---

### gov.states.mn.tax.income.subtractions.charity.fraction
**Label:** Minnesota charity subtraction fraction

Minnesota allows subtraction from federal adjusted gross income of this fraction of charitable contributions in excess of a threshold for tax units that do not itemize Minnesota deductions.

**Type:** float

**Current value:** 0.5

---

### gov.states.mn.tax.income.amt.rate
**Label:** Minnesota AMT rate

Minnesota has an alternative income tax (AMT) the calculation of which involves this tax rate.

**Type:** float

**Current value:** 0.0675

---

### gov.states.mn.tax.income.deductions.itemized.reduction.alternate.income_threshold
**Label:** Minnesota itemized deduction alternate reduction income threshold

Minnesota reduces the itemized deductions by a flat rate for filers with adjusted gross income above this threshold.

**Type:** int

**Current value:** 1000000

---

### gov.states.mn.tax.income.deductions.itemized.reduction.alternate.rate
**Label:** Minnesota alternate itemized deduction reduction rate

Minnesota reduces the itemized deductions when federal adjusted gross income is above a threshold by applying this fraction to a subset of itemized deductions.

**Type:** float

**Current value:** 0.8

---

### gov.states.mn.tax.income.deductions.itemized.reduction.excess_agi_fraction.high
**Label:** Minnesota itemized deductions higher excess AGI fraction

Minnesota reduces itemized deductions by this fraction of the excess of adjusted gross income above the higher threshold.

**Type:** float

**Current value:** 0.1

---

### gov.states.mn.tax.income.deductions.itemized.reduction.excess_agi_fraction.low
**Label:** Minnesota itmeized deductions lower excess AGI fraction

Minnesota reduces itemized deductions by this fraction of the excess of adjusted gross income above the lower threshold.

**Type:** float

**Current value:** 0.03

---

### gov.states.mn.tax.income.deductions.itemized.alternate_reduction_applies
**Label:** Minnesota itemized deduction alternate reduction applies

Minnesota applies an alternate itemized deduction reduction if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.mn.tax.income.deductions.standard.reduction.alternate.income_threshold
**Label:** Minnesota standard deduction alternate reduction income threshold

Minnesota reduces the standard deduction by a flat rate for filers with adjusted gross income above this threshold.

**Type:** int

**Current value:** 1053750

---

### gov.states.mn.tax.income.deductions.standard.reduction.alternate.rate
**Label:** Minnesota fraction of subset of itemized deductions that can limit total itemized deductions

Minnesota reduces the standard deduction when federal adjusted gross income is above a threshold by applying this fraction to a subset of the standard deduction.

**Type:** float

**Current value:** 0.8

---

### gov.states.mn.tax.income.deductions.standard.reduction.excess_agi_fraction.high
**Label:** Minnesota standard deduction higher excess AGI fraction

Minnesota reduces the standard deduction by this fraction of the excess of adjusted gross income above the higher threshold.

**Type:** float

**Current value:** 0.1

---

### gov.states.mn.tax.income.deductions.standard.reduction.excess_agi_fraction.low
**Label:** Minnesota standard deduction lower excess AGI fraction

Minnesota reduces the standard deduction by this fraction of the excess of adjusted gross income above the lower threshold.

**Type:** float

**Current value:** 0.03

---

### gov.states.mn.tax.income.deductions.standard.reduction.alternate_reduction_applies
**Label:** Minnesota standard deduction alternate reduction applies

Minnesota applies an alternate standard deduction reduction if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.mn.tax.income.exemptions.agi_step_fraction
**Label:** Minnesota fraction of federal adjusted gross income steps above threshold that is used to limit exemptions

Minnesota limits exemptions when federal adjusted gross income is above a threshold by this fraction of AGI per step above the threshold.

**Type:** float

**Current value:** 0.02

---

### gov.states.mn.tax.income.credits.marriage.minimum_taxable_income
**Label:** Minnesota marriage credit minimum taxable income for eligibility

Minnesota provides a marriage credit for joint filers where their taxable income is at least this minimum amount.

**Type:** int

**Current value:** 44000

---

### gov.states.mn.tax.income.credits.marriage.minimum_individual_income
**Label:** Minnesota marriage credit minimum individual income for eligibility

Minnesota provides a marriage credit for joint filers where the lesser income of the two spouses is at least this minimum amount.

**Type:** int

**Current value:** 28000

---

### gov.states.mn.tax.income.credits.marriage.standard_deduction_fraction
**Label:** Minnesota marriage credit standard deduction fraction

Minnesota provides a marriage credit for joint filers the calculation of which involves this fraction of their standard deduction.

**Type:** float

**Current value:** 0.5

---

### gov.states.mn.tax.income.credits.marriage.maximum_amount
**Label:** Minnesota marriage credit minimum amount

Minnesota provides a marriage credit for joint filers where this is the maximum credit amount.

**Type:** float

**Current value:** 1857.4978743358774

---

### gov.states.mn.tax.income.credits.cwfc.wfc.additional.age_threshold
**Label:** Minnesota working family credit additional amount age threshold

Minnesota provides an additional working family credit amount for each qualifying child over this age threshold.

**Type:** int

**Current value:** 18

---

### gov.states.mn.tax.income.credits.cwfc.wfc.eligible.childless_adult_age.minimum
**Label:** Minnesota WFC minimum eligibility age for childless adults

Minnesota has a working family credit (WFC) for which childless adults must be at least this age and no more than a maximum age.

**Type:** int

**Current value:** 19

---

### gov.states.mn.tax.income.credits.cwfc.wfc.eligible.childless_adult_age.maximum
**Label:** Minnesota WFC maximum eligibility age for childless adults

Minnesota has a working family credit (WFC) for which childless adults must be at least a minimum age and no more than this age.

**Type:** int

**Current value:** 64

---

### gov.states.mn.tax.income.credits.cwfc.phase_out.rate.main
**Label:** Minnesota child and working families tax credit main phase-out rate

Minnesota phases the child and working families tax credit out at this rate, for filers without qualifying older children.

**Type:** float

**Current value:** 0.12

---

### gov.states.mn.tax.income.credits.cwfc.phase_out.rate.ctc_ineligible_with_qualifying_older_children
**Label:** Minnesota child and working families tax credit phase-out ctc ineligible with qualifying older children rate

Minnesota phases the child and working families tax credit out at this rate, for filers ineligible for the child tax credit with eligible older children.

**Type:** float

**Current value:** 0.09

---

### gov.states.mn.tax.income.credits.cwfc.phase_out.threshold.other
**Label:** Minnesota child and working families tax credit non-joint phase-out threshold

Minnesota phases the child and working families tax credit out over this threshold for non-joint filers with the larger of earned income or adjusted gross income.

**Type:** int

**Current value:** 29500

---

### gov.states.mn.tax.income.credits.cwfc.phase_out.threshold.joint
**Label:** Minnesota child and working families tax credit joint phase-out threshold

Minnesota phases the child and working families tax credit out over this threshold for joint filers with the larger of earned income or adjusted gross income.

**Type:** int

**Current value:** 35000

---

### gov.states.mn.tax.income.credits.cwfc.ctc.amount
**Label:** Minnesota child tax credit amount

Minnesota provides the following child tax credit amount for each qualifying child.

**Type:** int

**Current value:** 1920

---

### gov.states.mn.tax.income.credits.cdcc.maximum_dependents
**Label:** Minnesota CDCC maximum number of qualified dependents

Minnesota has a child/dependent care credit in which this is the maximum number of qualified dependents allowed.

**Type:** int

**Current value:** 2

---

### gov.states.mn.tax.income.credits.cdcc.child_age
**Label:** Minnesota CDCC dependent child age

Minnesota has a child/dependent care credit in which children under this age qualify as a dependent.

**Type:** int

**Current value:** 13

---

### gov.states.mn.tax.income.credits.cdcc.phaseout_rate
**Label:** Minnesota CDCC excess AGI phaseout rate

Minnesota has a child/dependent care credit which is phased out at this rate above a federal AGI threshold.

**Type:** float

**Current value:** 0.05

---

### gov.states.mn.tax.income.credits.cdcc.phaseout_threshold
**Label:** Minnesota CDCC phaseout threshold

Minnesota has a child/dependent care credit which begins to be phased out when federal AGI exceeds this threshold.

**Type:** int

**Current value:** 64320

---

### gov.states.mn.tax.income.credits.cdcc.separate_filers_excluded
**Label:** Minnesota CDCC separate filers excluded

Minnesota excludes separate filers from the dependent care credit if this is true.

**Type:** bool

**Current value:** False

---

### gov.states.mn.tax.income.credits.cdcc.maximum_expense
**Label:** Minnesota CDCC maximum allowed care expense per qualified dependent

Minnesota has a child/dependent care credit in which this is the maximum care expense allowed per qualified dependent.

**Type:** int

**Current value:** 3000

---

### gov.states.mi.tax.income.senior_age
**Label:** Michigan senior age threshold

Michigan defines "Senior citizen" as filers of this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.mi.tax.income.deductions.standard.tier_three.age_threshold
**Label:** Michigan tier three standard deduction age threshold

Michigan limits the tier three standard deduction to filers at or above this age threshold.

**Type:** int

**Current value:** 67

---

### gov.states.mi.tax.income.deductions.standard.tier_two.retirement_year
**Label:** Michigan retirement benefit tier three retirement age

Michigan limits the tier three pension benefit to filers who retired after this year.

**Type:** int

**Current value:** 2013

---

### gov.states.mi.tax.income.deductions.standard.tier_two.amount.increase
**Label:** Michigan increased tier two standard deduction amount

Michigan provides this increased tier two standard deduction amount.

**Type:** int

**Current value:** 15000

---

### gov.states.mi.tax.income.deductions.standard.tier_two.age_threshold
**Label:** Michigan additional standard deduction age threshold

Michigan limits the additional standard deduction to filers of this age or older.

**Type:** int

**Current value:** 67

---

### gov.states.mi.tax.income.deductions.interest_dividends_capital_gains.birth_year
**Label:** Michigan interest, dividends, and capital gains deduction birth year

Michigan provides a interest, dividends, and capital gains deduction to filers born prior to this year.

**Type:** int

**Current value:** 1946

---

### gov.states.mi.tax.income.deductions.retirement_benefits.expanded.rate
**Label:** Michigan expanded retirement and pension benefits rate

Michigan multiplies the reduced tier one deduction amount by this rate under the expanded retirement and pension benefits deduction.

**Type:** float

**Current value:** 0.75

---

### gov.states.mi.tax.income.deductions.retirement_benefits.expanded.availability
**Label:** Michigan expanded retirement and pension benefits deduction availability

Michigan allows for an expanded retirement and pension benefits deduction calculation if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.mi.tax.income.deductions.retirement_benefits.tier_three.ss_exempt.not_retired.amount
**Label:** Michigan non-retired tier three retirement and pension benefits deduction amount

Michigan provides this non-retired tier three retirement and pension benefits amount.

**Type:** int

**Current value:** 15000

---

### gov.states.mi.tax.income.deductions.retirement_benefits.tier_three.ss_exempt.retired.retirement_year
**Label:** Michigan tier three retirement benefit retirement year

Michigan limits the tier three pension benefit to filers, retired after this year.

**Type:** int

**Current value:** 2013

---

### gov.states.mi.tax.income.deductions.retirement_benefits.tier_one.birth_year
**Label:** Michigan tier one retirement and pension benefits birth year threshold

Michigan limits the tier one retirement and pension benefits addition to filers born before this year.

**Type:** int

**Current value:** 1946

---

### gov.states.mi.tax.income.rate
**Label:** Michigan income tax rate

Michigan taxes individual income at this rate.

**Type:** float

**Current value:** 0.0425

---

### gov.states.mi.tax.income.exemptions.disabled.amount.veteran
**Label:** Michigan disabled veteran exemption amount

Michigan provides this exemption amount for each disabled veteran in the household.

**Type:** int

**Current value:** 400

---

### gov.states.mi.tax.income.exemptions.disabled.amount.base
**Label:** Michigan disabled exemption base amount

Michigan provides this exemption amount for each disabled person or dependent in the household.

**Type:** int

**Current value:** 3100

---

### gov.states.mi.tax.income.exemptions.disabled.age_limit
**Label:** Michigan disabled exemption age limit

Michigan limits the disabled exemption to totally and permanently disabled filers under this age.

**Type:** int

**Current value:** 66

---

### gov.states.mi.tax.income.exemptions.personal
**Label:** Michigan exemption base amount

Michigan provides this exemption amount for the filer and spouse of the tax unit, each dependent, and each of the filers stillborn children.

**Type:** int

**Current value:** 5400

---

### gov.states.mi.tax.income.credits.home_heating.alternate.household_resources.rate
**Label:** Michigan home heating credit alternate household resource rate

Michigan provides a credit for this fraction of reduced heating costs less reduced adjusted household resources under the alternate home heating credit.

**Type:** float

**Current value:** 0.11

---

### gov.states.mi.tax.income.credits.home_heating.alternate.heating_costs.rate
**Label:** Michigan alternate home heating credit household resource rate

Michigan provides a credit for this fraction of reduced heating costs less reduced adjusted household resources under the alternate home heating credit.

**Type:** float

**Current value:** 0.7

---

### gov.states.mi.tax.income.credits.home_heating.alternate.heating_costs.cap
**Label:** Michigan alternate home heating credit heating costs cap

Michigan caps the total heating costs at this amount under the alternate home heating credit computation.

**Type:** int

**Current value:** 3500

---

### gov.states.mi.tax.income.credits.home_heating.additional_exemption.amount
**Label:** Michigan home heating additional base amount per additional exemption

Michigan increases the home heating base by this amount for each additional exemption.

**Type:** int

**Current value:** 198

---

### gov.states.mi.tax.income.credits.home_heating.additional_exemption.limit
**Label:** Michigan home heating credit additional exemption limit

Michigan increases the home heating credit base for each exemption over this number.

**Type:** int

**Current value:** 6

---

### gov.states.mi.tax.income.credits.home_heating.standard.included_heating_cost_rate
**Label:** Michigan standard home heating credit rate if rent includes heating

Michigan multiplies the standard home heating credit by this fraction if rent includes heating.

**Type:** float

**Current value:** 0.5

---

### gov.states.mi.tax.income.credits.home_heating.standard.reduction_rate
**Label:** Michigan standard home heating credit reduction rate

Michigan reduces the standard heating credit amount by this fraction of household resources.

**Type:** float

**Current value:** 0.035

---

### gov.states.mi.tax.income.credits.home_heating.standard.fpg_rate
**Label:** Michigan standard home heating credit federal poverty guidelines rate

Michigan limits the home heating credit to filers with household resources below this fraction of the federal poverty guidelines.

**Type:** float

**Current value:** 1.1

---

### gov.states.mi.tax.income.credits.home_heating.credit_percentage
**Label:** Michigan home heating credit percentage

Michigan provides a credit for this fraction of the greater of the standard and alternate home heating credit.

**Type:** float

**Current value:** 0.56

---

### gov.states.mi.tax.income.credits.homestead_property_tax.rate.senior.alternate
**Label:** Michigan alternate property tax senior credit alternate rate

Michigan provides senior renters with an alternate homestead property tax credit of this fraction of total household resources subtracted from total rent payments.

**Type:** float

**Current value:** 0.4

---

### gov.states.mi.tax.income.credits.homestead_property_tax.rate.non_senior_disabled
**Label:** Michigan homestead property tax non-disabled/senior credit rate

Michigan provides a maximum homestead property tax credit as this fraction of the excess of property taxes over the household resource exemption, for filers without a disabled or senior member.

**Type:** float

**Current value:** 0.6

---

### gov.states.mi.tax.income.credits.homestead_property_tax.exemption.non_senior_disabled
**Label:** Michigan homestead property tax credit non-disabled/senior exemption rate

Michigan subtracts this fraction of the household resources from the total household resources under the homestead property tax credit computation, for filers without a disabled or senior member.

**Type:** float

**Current value:** 0.032

---

### gov.states.mi.tax.income.credits.homestead_property_tax.rent_equivalization
**Label:** Michigan homestead property tax credit rent equivalization

Michigan multiplies the rent amount by this rate under the homestead property tax credit.

**Type:** float

**Current value:** 0.23

---

### gov.states.mi.tax.income.credits.homestead_property_tax.reduction.increment
**Label:** Michigan homestead property tax credit phase out increment

Michigan phases its homestead property tax credit out in these increments.

**Type:** int

**Current value:** 1000

---

### gov.states.mi.tax.income.credits.homestead_property_tax.reduction.rate
**Label:** Michigan household resources reduction rate phase out brackets

Michigan phases its homestead property tax credit at this rate multiple for each reduction increment.

**Type:** float

**Current value:** 0.1

---

### gov.states.mi.tax.income.credits.homestead_property_tax.reduction.start
**Label:** Michigan homestead property tax credit reduction start

Michigan phases its homestead property tax credit out for filers with household resources above this threshold.

**Type:** int

**Current value:** 58300

---

### gov.states.mi.tax.income.credits.homestead_property_tax.property_value_limit
**Label:** Michigan homestead property tax credit property value limit

Michigan limits the homestead property tax credit to filers with property value below this amount.

**Type:** int

**Current value:** 154400

---

### gov.states.mi.tax.income.credits.homestead_property_tax.cap
**Label:** Michigan homestead property tax credit cap

Michigan caps the homestead property tax credit at this amount.

**Type:** int

**Current value:** 1700

---

### gov.states.mi.tax.income.credits.eitc.match
**Label:** Michigan EITC match

Michigan matches this share of the federal Earned Income Tax Credit.

**Type:** float

**Current value:** 0.3

---

### gov.states.ok.tax.income.agi.subtractions.pension_limit
**Label:** Oklahoma limit on taxable pension benefit AGI subtraction per person

Oklahoma limit on taxable pension benefit AGI subtraction per person.

**Type:** int

**Current value:** 10000

---

### gov.states.ok.tax.income.agi.subtractions.military_retirement.floor
**Label:** Oklahoma military retirement benefit subtraction floor

Oklahoma provides a minimum military retirement benefit subtraction for this amount, not to exceed military retirement income.

**Type:** int

**Current value:** 0

---

### gov.states.ok.tax.income.agi.subtractions.military_retirement.rate
**Label:** Oklahoma military retirement exclusion rate

Oklahoma excludes this percentage of military retirement benefits under the retirement benefit subtraction.

**Type:** float

**Current value:** 1.0

---

### gov.states.ok.tax.income.deductions.itemized.limit
**Label:** Oklahoma itemized deduction limit

Oklahoma allows this maximum amount of itemized deductions.

**Type:** int

**Current value:** 17000

---

### gov.states.ok.tax.income.exemptions.special_age_minimum
**Label:** Oklahoma special exemption age minimum

Oklahoma provides a special exemption for people this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.ok.tax.income.exemptions.amount
**Label:** Oklahoma per-person exemption amount

Oklahoma provides this exemption amount per person.

**Type:** int

**Current value:** 1000

---

### gov.states.ok.tax.income.credits.property_tax.age_minimum
**Label:** Oklahoma property tax credit minimum age

Oklahoma limits its property tax credit to filers this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.ok.tax.income.credits.property_tax.income_limit
**Label:** Oklahoma property tax credit gross income limit

Oklahoma limits its property tax credit to filers with gross income below this amount.

**Type:** int

**Current value:** 12000

---

### gov.states.ok.tax.income.credits.property_tax.maximum_credit
**Label:** Oklahoma property tax credit maximum amount

Oklahoma provides a property tax credit up to this amount.

**Type:** int

**Current value:** 200

---

### gov.states.ok.tax.income.credits.property_tax.income_fraction
**Label:** Oklahoma property tax credit gross income fraction

Oklahoma provides a property tax credit of this percent of gross income.

**Type:** float

**Current value:** 0.01

---

### gov.states.ok.tax.income.credits.earned_income.eitc_fraction
**Label:** Oklahoma EITC match

Oklahoma matches this share of the federal Earned Income Tax Credit.

**Type:** float

**Current value:** 0.05

---

### gov.states.ok.tax.income.credits.sales_tax.age_minimum
**Label:** Oklahoma sales tax credit minimum age for second income limit

Oklahoma limits its sales tax credit to filers this age or above for the second income limit

**Type:** int

**Current value:** 65

---

### gov.states.ok.tax.income.credits.sales_tax.income_limit1
**Label:** Oklahoma sales tax credit gross income limit 1

Oklahoma applies this first gross income limit to the sales tax credit.

**Type:** int

**Current value:** 20000

---

### gov.states.ok.tax.income.credits.sales_tax.amount
**Label:** Oklahoma sales tax credit amount per exemption

Oklahoma provides a sales tax credit of this amount per exemption.

**Type:** int

**Current value:** 40

---

### gov.states.ok.tax.income.credits.sales_tax.income_limit2
**Label:** Oklahoma sales tax credit gross income limit 2

Oklahoma applies this second gross income limit to its sales tax credit.

**Type:** int

**Current value:** 50000

---

### gov.states.ok.tax.income.credits.child.agi_limit
**Label:** Oklahoma Child Care/Child Tax Credit income limit

Oklahoma limits its Child Care/Child Tax Credit to filers with federal AGI below this amount.

**Type:** int

**Current value:** 100000

---

### gov.states.ok.tax.income.credits.child.ctc_fraction
**Label:** Oklahoma CTC match

Oklahoma matches this percent of the federal Child Tax Credit.

**Type:** float

**Current value:** 0.05

---

### gov.states.ok.tax.income.credits.child.cdcc_fraction
**Label:** Oklahoma CDCC match

Oklahoma matches this percent of the federal Child and Dependent Care Credit.

**Type:** float

**Current value:** 0.2

---

### gov.states.ok.tax.use.rate
**Label:** Oklahoma use tax rate

Oklahoma levies a use tax at this percent of federal adjusted gross income.

**Type:** float

**Current value:** 0.00056

---

### gov.states.in.tax.income.deductions.military_service.max
**Label:** Indiana max military service deduction

Indiana provides up a military service deduction of up to this amount per person.

**Type:** int

**Current value:** 5000

---

### gov.states.in.tax.income.deductions.nonpublic_school.amount
**Label:** Indiana nonpublic school deduction

Indiana provides a deduction of this amount for qualified dependent children in private, parochial, or home school with unreimbursed expenses.

**Type:** int

**Current value:** 1000

---

### gov.states.in.tax.income.deductions.unemployment_compensation.reduced_agi_haircut
**Label:** Indiana haircut to reduced AGI for computing maximum unemployment compensation deduction

Indiana applies this haircut when reducing adjusted gross income for computing the maximum unemployment compensation deduction.

**Type:** float

**Current value:** 0.5

---

### gov.states.in.tax.income.agi_rate
**Label:** Indiana AGI tax rate

Indiana taxes Indiana adjusted gross income at this rate.

**Type:** float

**Current value:** 0.03

---

### gov.states.in.tax.income.exemptions.adoption.amount
**Label:** Indiana adopted children exemption additional amount

Indiana provides an additional exemption for eligible adopted dependents of this amount.

**Type:** int

**Current value:** 3000

---

### gov.states.in.tax.income.exemptions.aged_low_agi.amount
**Label:** Indiana exemptions additional amount for low AGI aged

Indiana provides this additional exemption amount for low-income aged filers.

**Type:** int

**Current value:** 500

---

### gov.states.in.tax.income.exemptions.qualifying_child.max_ages.student
**Label:** Indiana additional exemption age limit for students

Indiana considers as children people below this age when compute its additional exemption for student dependents.

**Type:** int

**Current value:** 23

---

### gov.states.in.tax.income.exemptions.qualifying_child.max_ages.non_student
**Label:** Indiana additional exemption age limit for non-students

Indiana considers as children people below this age when compute its additional exemption for non-student dependents.

**Type:** int

**Current value:** 18

---

### gov.states.in.tax.income.exemptions.aged_blind.amount
**Label:** Indiana exemptions additional amount for aged and or blind

Indiana provides this additional exemption amount for aged and/or blind filers.

**Type:** int

**Current value:** 1000

---

### gov.states.in.tax.income.exemptions.additional.amount
**Label:** Indiana exemptions additional amount for dependent children

Indiana provides this additional exemption amount for qualifying dependent children.

**Type:** int

**Current value:** 1500

---

### gov.states.in.tax.income.exemptions.base.amount
**Label:** Indiana exemptions base amount

Indiana provides this base exemption amount.

**Type:** int

**Current value:** 1000

---

### gov.states.in.tax.income.credits.earned_income.decoupled
**Label:** Whether IN EITC is decoupled from federal EITC

Indiana has a state EITC that is decoupled from the federal EITC if this parameter is true.

**Type:** bool

**Current value:** False

---

### gov.states.in.tax.income.credits.earned_income.childless.min_age
**Label:** Indiana EITC minimum age for childless eligibility

Indiana limits its earned income tax credit to filers this age or above if they have no children.

**Type:** int

**Current value:** 25

---

### gov.states.in.tax.income.credits.earned_income.childless.phase_out_rate
**Label:** Indiana EITC phase-out rate for childless credit in 2021

Indiana has a state EITC that used this phase-out rate for childless credit in 2021.

**Type:** int

**Current value:** 0

---

### gov.states.in.tax.income.credits.earned_income.childless.phase_in_rate
**Label:** Indiana EITC phase-in rate for childless credit in 2021

Indiana has a state EITC that used this phase-in rate for childless credit in 2021.

**Type:** int

**Current value:** 0

---

### gov.states.in.tax.income.credits.earned_income.childless.phase_out_start
**Label:** Indiana EITC phase-out start income for childless credit in 2021

Indiana has a state EITC that used this phase-out start income for childless credit in 2021.

**Type:** int

**Current value:** 0

---

### gov.states.in.tax.income.credits.earned_income.childless.max_age
**Label:** Indiana EITC maximum age for childless eligibility

Indiana limits its earned income tax credit to filers this age or below if they have no children.

**Type:** int

**Current value:** 64

---

### gov.states.in.tax.income.credits.earned_income.childless.maximum
**Label:** Indiana EITC maximum childless credit in 2021

Indiana has a state EITC that used this maximum childless credit in 2021.

**Type:** int

**Current value:** 0

---

### gov.states.in.tax.income.credits.earned_income.max_children
**Label:** IN EITC maximum allowable children

Indiana has a state EITC that recognizes at most this maximum number of eligible children.

**Type:** int

**Current value:** 3

---

### gov.states.in.tax.income.credits.earned_income.investment_income_limit
**Label:** Indiana EITC investment income limit

Indiana makes any taxpayer with investment income that exceeds this limit EITC ineligible.

**Type:** int

**Current value:** 3800

---

### gov.states.in.tax.income.credits.earned_income.match_rate
**Label:** Indiana federal-EITC match rate

Indiana matches this fraction of the federal earned income tax credit.

**Type:** float

**Current value:** 0.1

---

### gov.states.in.tax.income.credits.unified_elderly.min_age
**Label:** Indiana unified elderly tax credit minimum age for eligibility

Indiana allows filers at or above this age to receive the unified tax credit for the elderly.

**Type:** int

**Current value:** 65

---

### gov.states.co.tax.income.subtractions.charitable_contribution.adjustment
**Label:** Colorado charitable contributions subtraction adjustment

Colorado subtracts charitable contributions above this amount from the adjusted gross income of filers who do not itemize on their federal return.

**Type:** int

**Current value:** 500

---

### gov.states.co.tax.income.subtractions.pension.cap.younger
**Label:** Colorado capped pension and annuity income amount

Colorado allows a pension and annuity subtraction to get its net income that is capped at this amount.

**Type:** int

**Current value:** 20000

---

### gov.states.co.tax.income.subtractions.pension.cap.older
**Label:** Colorado capped pension and annuity income amount

Colorado allows a pension and annuity subtraction to get its net income that is capped at this amount.

**Type:** int

**Current value:** 24000

---

### gov.states.co.tax.income.subtractions.pension.social_security_subtraction_available
**Label:** Colorado social security subtraction available

Colorado separates Social Security income from pension income for the pension subtraction if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.co.tax.income.subtractions.pension.age_threshold.younger
**Label:** Colorado pension subtraction lower age threshold

Colorado limits its younger pension subtraction to filers below this age threshold.

**Type:** int

**Current value:** 55

---

### gov.states.co.tax.income.subtractions.pension.age_threshold.older
**Label:** Colorado pension subtraction upper age threshold

Colorado limits its older pension subtraction to filers above this age threshold.

**Type:** int

**Current value:** 65

---

### gov.states.co.tax.income.subtractions.military_retirement.age_threshold
**Label:** Colorado military retirement subtraction age threshold

Colorado limits its military retirement subtraction to filers below this age.

**Type:** int

**Current value:** 55

---

### gov.states.co.tax.income.subtractions.military_retirement.max_amount
**Label:** Colorado military retirement subtraction max amount

Colorado allows for this maximum military retirement subtraction for each eligible individual.

**Type:** int

**Current value:** 15000

---

### gov.states.co.tax.income.additions.federal_deductions.agi_threshold
**Label:** Colorado federal deductions add-back AGI threshold

Colorado adds back federal deductions for filers with adjusted gross income above this threshold.

**Type:** int

**Current value:** 300000

---

### gov.states.co.tax.income.additions.federal_deductions.itemized_only
**Label:** Colorado federal deduction addback itemized only

Whether the Colorado federal deductions addback is only itemized.

**Type:** bool

**Current value:** False

---

### gov.states.co.tax.income.rate
**Label:** Colorado income tax rate

Colorado taxes personal income at this flat rate.

**Type:** float

**Current value:** 0.044

---

### gov.states.co.tax.income.credits.income_qualified_senior_housing.income_threshold
**Label:** Colorado Income Qualified Senior Housing Tax Credit AGI threshold

Colorado provides the Income Qualified Senior Housing Tax Credit for filers with adjusted gross income at or below this threshold.

**Type:** int

**Current value:** 75000

---

### gov.states.co.tax.income.credits.income_qualified_senior_housing.reduction.increment
**Label:** Colorado income qualified senior housing income tax credit increment amount

Colorado reduces the income qualified senior housing income tax credit for each of these increments of adjusted gross income exceeding the threshold.

**Type:** int

**Current value:** 500

---

### gov.states.co.tax.income.credits.income_qualified_senior_housing.reduction.start
**Label:** Colorado personal income qualified senior housing income tax credit start

Colorado reduces the income qualified senior housing income tax credit for filers with adjusted gross income above this amount, based on filing status.

**Type:** int

**Current value:** 25499

---

### gov.states.co.tax.income.credits.income_qualified_senior_housing.age_limit
**Label:** Colorado Age Income-Qualified Senior Housing Tax Credit age threshold

Colorado provides the Income Qualified Senior Housing Tax Credit for filers' at or above this age threshold.

**Type:** int

**Current value:** 65

---

### gov.states.co.tax.income.credits.sales_tax_refund.amount.amount
**Label:** Colorado sales tax refund credit flat amount

Colorado provides a flat sales tax refund credit of this amount.

**Type:** int

**Current value:** 800

---

### gov.states.co.tax.income.credits.sales_tax_refund.amount.flat_amount_enabled
**Label:** Colorado sales tax refund credit flat amount enabled

Colorado allows for a flat sales tax refund credit if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.co.tax.income.credits.sales_tax_refund.age_threshold
**Label:** Colorado sales tax refund age threshold

Colorado limits its sales tax refund to filers this age or older.

**Type:** int

**Current value:** 18

---

### gov.states.co.tax.income.credits.family_affordability.amount
**Label:** Colorado family affordability tax credit young child amount

Colorado provides this family affordability tax credit base amount for each younger child.

**Type:** int

**Current value:** 3200

---

### gov.states.co.tax.income.credits.family_affordability.reduction.rate
**Label:** Colorado family affordability tax credit reduction rate

Colorado reduces the family affordability tax credit by this rate for each increment above the adjusted gross income threshold.

**Type:** float

**Current value:** 0.06875

---

### gov.states.co.tax.income.credits.ctc.ctc_matched_federal_credit
**Label:** Colorado child tax credit federal CTC match

Colorado matches a fraction of the federal child tax credit when this is true; otherwise, Colorado provides an amount based on income.

**Type:** bool

**Current value:** False

---

### gov.states.co.tax.income.credits.ctc.age_threshold
**Label:** Colorado child tax credit age threshold

Colorado issues the child tax credit to taxpayers with children below this age.

**Type:** int

**Current value:** 6

---

### gov.states.co.tax.income.credits.cdcc.low_income.federal_agi_threshold
**Label:** Colorado low-income child care expenses credit income threshold

Colorado limits the low-income child care expenses credit to filers with adjusted gross income up to this amount.

**Type:** int

**Current value:** 25000

---

### gov.states.co.tax.income.credits.cdcc.low_income.rate
**Label:** Colorado low income child care expense credit rate

Colorado matches up to this fraction of qualifying child care expenses in its low income child care expenses credit.

**Type:** float

**Current value:** 0.25

---

### gov.states.co.tax.income.credits.cdcc.low_income.child_age_threshold
**Label:** Colorado low-income child care expenses credit child age threshold

Colorado qualifies children for the low-income family child care expenses credit below this age threshold.

**Type:** int

**Current value:** 13

---

### gov.states.co.tax.income.credits.eitc.match
**Label:** Colorado EITC match

Colorado matches this fraction of the federal Earned Income Tax Credit.

**Type:** float

**Current value:** 0.35

---

### gov.states.co.ccap.re_determination.smi_rate
**Label:** Colorado Child Care Assistance Program household size state median income re-determination rate

Colorado limits its Child Care Assistance Program re-determination to households with income below this fraction of state median income.

**Type:** float

**Current value:** 0.85

---

### gov.states.co.ccap.entry.smi_rate
**Label:** Colorado Child Care Assistance Program household size state median income entry rate

Colorado limits its Child Care Assistance Program application to applicants with adjusted gross income lower than these rates of household size state median income.

**Type:** float

**Current value:** 0.85

---

### gov.states.co.ccap.implementing_month
**Label:** Colorado Child Care Assistance Program implementing month

Colorado Child Care Assistance Program annually implements in this month.

**Type:** int

**Current value:** 10

---

### gov.states.co.ccap.parent_fee.add_on
**Label:** Colorado Child Care Assistance Program parent fee add on rate

Colorado multiplies the number of additional eligible children by this amount under the Child Care Assistance Program to calculate add on parent fee.

**Type:** int

**Current value:** 15

---

### gov.states.co.ccap.disabled_age_limit
**Label:** Colorado Child Care Assistance Program disabled child age limit

Colorado limits its Child Care Assistance Program to disabled children below this age.

**Type:** int

**Current value:** 19

---

### gov.states.co.ccap.age_limit
**Label:** Colorado Child Care Assistance Program non-disabled child age limit

Colorado limits its Child Care Assistance Program to non-disabled children below this age.

**Type:** int

**Current value:** 13

---

### gov.states.co.ssa.oap.resources.couple
**Label:** Colorado OAP resource limit for couples

Colorado OAP resource limit for couples.

**Type:** int

**Current value:** 3000

---

### gov.states.co.ssa.oap.resources.single
**Label:** Colorado OAP resource limit for singles

Colorado OAP resource limit for singles.

**Type:** int

**Current value:** 2000

---

### gov.states.co.ssa.oap.grant_standard
**Label:** Colorado OAP grant standard

Grant Standard for OAP

**Type:** int

**Current value:** 1005

---

### gov.states.co.ssa.state_supplement.grant_standard
**Label:** Colorado State Supplement grant standard

Grant Standard for Colorado State Supplement

**Type:** int

**Current value:** 967

---

### gov.states.co.hcpf.chp.out_of_pocket
**Label:** Colorado CHP+ out of pocket maximum percent

Colorado limits its Child Health Plan Plus out of pocket expense to this fraction of income.

**Type:** float

**Current value:** 0.05

---

### gov.states.co.hcpf.chp.income_limit
**Label:** Colorado CHP+ maximum household income as percent of FPL

Colorado limits the Child Health Plan Plus to households with income up to this percentage of the federal poverty level.

**Type:** float

**Current value:** 2.65

---

### gov.states.co.cdhs.tanf.income.earned_exclusion.percent
**Label:** Colorado TANF earnings exclusion percent

Colorado excludes this share of earnings from TANF countable income, except for determining need for new applicants.

**Type:** float

**Current value:** 0.67

---

### gov.states.co.cdhs.tanf.income.earned_exclusion.flat
**Label:** Colorado TANF flat earnings exclusion

Colorado excludes this amount of earnings from TANF countable income when determining need for new applicants.

**Type:** int

**Current value:** 90

---

### gov.states.ca.cpuc.care.discount
**Label:** CARE poverty line threshold

California CARE recipient households recieve a discount on their energy expenses between 30 and 35%, ballparked here at 32.5% for simplicity.

**Type:** float

**Current value:** 0.325

---

### gov.states.ca.cpuc.care.eligibility.fpl_limit
**Label:** CARE poverty line threshold

California provides CARE eligibility to households with income below this percent of the (CARE-adjusted) poverty line.

**Type:** int

**Current value:** 2

---

### gov.states.ca.cpuc.fera.discount
**Label:** FERA poverty line threshold

California FERA recipient households recieve a discount on their energy expenses of 18%

**Type:** float

**Current value:** 0.18

---

### gov.states.ca.cpuc.fera.eligibility.minimum_household_size
**Label:** CARE poverty line threshold

Eligibility for California's FERA program requires a minimum household of this size to qualify.

**Type:** int

**Current value:** 3

---

### gov.states.ca.cpuc.fera.eligibility.fpl_limit
**Label:** FERA poverty line threshold

Eligibility for California's FERA program requires that a household make no more than this value times the poverty line.

**Type:** float

**Current value:** 2.5

---

### gov.states.ca.dhcs.ffyp.foster_care_age_minimum
**Label:** California Former Foster Youth Program foster care age minimum

California limits participation in the Former Foster Youth Program to individuals who were in foster care at this age or older.

**Type:** int

**Current value:** 18

---

### gov.states.ca.dhcs.ffyp.age_threshold
**Label:** California Former Foster Youth Program age limit

California limits participation in the Former Foster Youth Program to individuals below this age.

**Type:** int

**Current value:** 26

---

### gov.states.ca.cpi
**Label:** California income tax CPI uprating

California CPI (from the current year's June)

**Type:** float

**Current value:** 360.6750331608849

---

### gov.states.ca.tax.income.amt.tentative_min_tax_rate
**Label:** California tentative alternative minimum tax rate

California multiplies the alternative minimum tax by this rate to calculate the tentative alternative minimum tax.

**Type:** float

**Current value:** 0.07

---

### gov.states.ca.tax.income.deductions.itemized.limit.agi_fraction
**Label:** fraction of AGI used to compute CA itemized deductions limitation

Fraction of AGI used in CA itemized deduction limitation.

**Type:** float

**Current value:** 0.06

---

### gov.states.ca.tax.income.deductions.itemized.limit.ded_fraction
**Label:** California fraction of itemized deductions subject to limitation

Fraction of itemized deductions subject to CA limitation.

**Type:** float

**Current value:** 0.8

---

### gov.states.ca.tax.income.exemptions.dependent_amount
**Label:** California dependent exemption amount

California exempts this amount from taxable income per dependent.

**Type:** float

**Current value:** 473.6832028666453

---

### gov.states.ca.tax.income.exemptions.phase_out.amount
**Label:** California exemption phase out amount

California reduces its exemption by this amount for each increment of income exceeding the threshold.

**Type:** int

**Current value:** 6

---

### gov.states.ca.tax.income.exemptions.amount
**Label:** California income exemption amount

California exempts this amount from taxable income.

**Type:** float

**Current value:** 153.09934322587884

---

### gov.states.ca.tax.income.credits.young_child.ineligible_age
**Label:** California young child tax credit ineligible age

California limits the young child tax credit to filers with children below this age.

**Type:** int

**Current value:** 6

---

### gov.states.ca.tax.income.credits.young_child.phase_out.increment
**Label:** California young child tax credit phase out increment

California phases out its young child tax credit at a given amount per increment of this value.

**Type:** int

**Current value:** 100

---

### gov.states.ca.tax.income.credits.young_child.phase_out.amount
**Label:** California young child tax credit phase out amount

California phases out its young child tax credit at this amount per increment.

**Type:** float

**Current value:** 21.67

---

### gov.states.ca.tax.income.credits.young_child.phase_out.start
**Label:** California young child tax credit phase out start

California begins to phase out its young child tax credit at this income level.

**Type:** float

**Current value:** 27358.544380753356

---

### gov.states.ca.tax.income.credits.young_child.amount
**Label:** California young child tax credit amount

California provides a young child tax credit of this amount.

**Type:** float

**Current value:** 1185.7492757225784

---

### gov.states.ca.tax.income.credits.young_child.loss_threshold
**Label:** California Young Child Tax Credit loss threshold

California limits its Young Child Tax Credit to filers with losses not exceeding this value.

**Type:** float

**Current value:** 35553.983049005765

---

### gov.states.ca.tax.income.credits.earned_income.adjustment.factor
**Label:** CalEITC adjustment factor

California defines the following adjustment factor to the federal EITC in its annual Budget Act.

**Type:** float

**Current value:** 0.85

---

### gov.states.ca.tax.income.credits.earned_income.phase_out.final.end
**Label:** CalEITC max earnings

California limits CalEITC to filers with less than this amount of earnings.

**Type:** int

**Current value:** 31950

---

### gov.states.ca.tax.income.credits.earned_income.eligibility.age.max
**Label:** CalEITC max age

California limits CalEITC to filers below this age.

**Type:** float

**Current value:** inf

---

### gov.states.ca.tax.income.credits.earned_income.eligibility.age.min
**Label:** CalEITC minimum age

CalEITC is limited to filers this age and above.

**Type:** int

**Current value:** 18

---

### gov.states.ca.tax.income.credits.earned_income.eligibility.max_investment_income
**Label:** CalEITC investment income limit

California limits the CalEITC to filers with investment income below this threshold.

**Type:** float

**Current value:** 4915.308702555465

---

### gov.states.ca.tax.income.credits.foster_youth.phase_out.increment
**Label:** California foster youth credit phase out increment

California reduces the foster youth tax credit for each of these increments of earned income exceeding the threshold.

**Type:** int

**Current value:** 100

---

### gov.states.ca.tax.income.credits.foster_youth.phase_out.amount
**Label:** California foster youth tax credit phase out amount

California reduces the foster youth tax credit by this amount for each increment of earned income in excess of the phase-out threshold.

**Type:** float

**Current value:** 21.66

---

### gov.states.ca.tax.income.credits.foster_youth.phase_out.start
**Label:** California foster youth tax credit phase out start

California phases the foster youth tax credit out for filers with earned income above this threshold.

**Type:** float

**Current value:** 27358.544380753356

---

### gov.states.ca.calepa.carb.cvrp.increased_rebate.amount
**Label:** Amount of increased California CVRP rebate

Amount of the increased rebate for low- and moderate-income participants in California's Clean Vehicle Rebate Project, based on the date of purchase.

**Type:** int

**Current value:** 2500

---

### gov.states.ca.calepa.carb.cvrp.increased_rebate.fpl_limit
**Label:** Maximum FPL percent to qualify for an increased California CVRP rebate

Income limit as a percent of the federal poverty guideline to qualify for an increased rebate under California's Clean Vehicle Rebate Project.

**Type:** int

**Current value:** 4

---

### gov.states.ca.cdss.capi.payment_standard_offset.couple
**Label:** California CAPI couple payment standard offset

California reduces the Supplemental Security Income / State Supplemental Payment payment standard by this amount for couples when calculating the Cash Assistance Program for Immigrants.

**Type:** int

**Current value:** 20

---

### gov.states.ca.cdss.capi.payment_standard_offset.single
**Label:** California CAPI single payment standard offset

California reduces the Supplemental Security Income / State Supplemental Payment payment standard by this amount for single filers when calculating the Cash Assistance Program for Immigrants.

**Type:** int

**Current value:** 10

---

### gov.states.ca.cdss.capi.resources.vehicle.disregard
**Label:** California CAPI vehicle value disregard

California counts the value of a vehicle exceeding this threshold as resources for the Cash Assistance Program for Immigrants.

**Type:** int

**Current value:** 4500

---

### gov.states.ca.cdss.capi.resources.limit.couple
**Label:** California CAPI couple resource limit

California limits the Cash Assistance Program for Immigrants to couples with resources at or below this amount.

**Type:** int

**Current value:** 3000

---

### gov.states.ca.cdss.capi.resources.limit.single
**Label:** California CAPI single resource limit

California limits the Cash Assistance Program for Immigrants to single filers with resources at or below this amount.

**Type:** int

**Current value:** 2000

---

### gov.states.ca.cdss.state_supplement.payment_standard.blind.married.two_blind
**Label:** California state supplement blind allowance married two blind amount

California provides the following state supplement amount to married filers with two blind members who are both eligible.

**Type:** int

**Current value:** 1372

---

### gov.states.ca.cdss.state_supplement.payment_standard.blind.married.one_blind
**Label:** California state supplement blind allowance married one blind amount

California provides the following state supplement amount to married filers with one blind member who are both eligible.

**Type:** int

**Current value:** 1295

---

### gov.states.ca.cdss.state_supplement.payment_standard.blind.single
**Label:** California state supplement blind allowance single amount

California provides the following state supplement amount to single filers who are blind.

**Type:** int

**Current value:** 704

---

### gov.states.ca.cdss.state_supplement.payment_standard.allowance.medical_care_facility
**Label:** California state supplement medical care facility allowance amount

California provides the following state supplement allowance for filers receiving care in a medical facility.

**Type:** int

**Current value:** 42

---

### gov.states.ca.cdss.state_supplement.payment_standard.allowance.out_of_home_care
**Label:** California state supplement out-of-home care allowance amount

California provides the following state supplement allowance for filers in a nonmedical out-of-home care facility.

**Type:** int

**Current value:** 709

---

### gov.states.ca.cdss.state_supplement.payment_standard.allowance.food.married
**Label:** California state supplement food allowance married amount

California provides the following state supplement food allowance for married adults whose living arrangements prevents them from preparing their own meals.

**Type:** int

**Current value:** 136

---

### gov.states.ca.cdss.state_supplement.payment_standard.allowance.food.single
**Label:** California state supplement food allowance single amount

California provides the following state supplement food allowance for single adults whose living arrangements prevents them from preparing their own meals.

**Type:** int

**Current value:** 68

---

### gov.states.ca.cdss.state_supplement.payment_standard.aged_or_disabled.amount.married
**Label:** California state supplement aged or disabled allowance married amount

California provides the following state supplement amount to two eligible aged or disabled married filers.

**Type:** int

**Current value:** 1167

---

### gov.states.ca.cdss.state_supplement.payment_standard.aged_or_disabled.amount.single
**Label:** California state supplement aged or disabled allowance single amount

California provides the following state supplement amount to aged or disabled single filers.

**Type:** int

**Current value:** 630

---

### gov.states.ca.cdss.state_supplement.payment_standard.aged_or_disabled.age_threshold
**Label:** California state supplement aged or disabled age threshold

California provides a state supplement amount for dependents below this age threshold.

**Type:** int

**Current value:** 65

---

### gov.states.ca.cdss.state_supplement.payment_standard.dependent.amount
**Label:** California state supplement dependent amount

California provides the following state supplement amount for eligible dependents.

**Type:** int

**Current value:** 499

---

### gov.states.ca.cdss.state_supplement.payment_standard.dependent.age_limit
**Label:** California state supplement dependent age limit

California provides a state supplement amount for dependents below this age threshold.

**Type:** int

**Current value:** 18

---

### gov.states.ca.cdss.tanf.child_care.child_care_time.weekly_care.weekly_child_care_hours_threshold
**Label:** California CalWORKs weekly child care hours per week requirement

California CalWORKs weekly child care requires the corresponding weekly child care hours.

**Type:** int

**Current value:** 30

---

### gov.states.ca.cdss.tanf.child_care.child_care_time.hourly_care.daily_child_care_hours_limit
**Label:** California CalWORKs hourly child care hours per day limit

California CalWORKs hourly child care limits the following maximum daily child care hours.

**Type:** int

**Current value:** 6

---

### gov.states.ca.cdss.tanf.child_care.child_care_time.hourly_care.weekly_child_care_hours_limit
**Label:** California CalWORKs hourly child care hours per week limit

California CalWORKs hourly child care limits the following maximum weekly child care hours.

**Type:** int

**Current value:** 30

---

### gov.states.ca.cdss.tanf.child_care.child_care_time.monthly_care.child_care_weeks_requirement
**Label:** California CalWORKs monthly child care weeks per month requirement

California CalWORKs monthly child care requires the child care need occurs in every week of the month

**Type:** int

**Current value:** 4

---

### gov.states.ca.cdss.tanf.child_care.child_care_time.monthly_care.weekly_child_care_hours_threshold
**Label:** California CalWORKs monthly child care hours per week requirement

California CalWORKs monthly child care requires the corresponding weekly child care hours.

**Type:** int

**Current value:** 30

---

### gov.states.ca.cdss.tanf.child_care.child_care_time.daily_care.daily_child_care_hours_limit
**Label:** California CalWORKs daily child care hours per day limit

California CalWORKs daily child care limits the following minimum daily child care hours.

**Type:** int

**Current value:** 6

---

### gov.states.ca.cdss.tanf.child_care.child_care_time.daily_care.child_care_days_limit
**Label:** California CalWORKs daily child care days per month limit

California CalWORKs daily child care limits the following maximum number of days per month.

**Type:** int

**Current value:** 14

---

### gov.states.ca.cdss.tanf.child_care.eligibility.disabled_age_threshold
**Label:** California CalWORKs Child Care disabled age threshold

California provides the CalWORKs Child Care to disabled children below this age.

**Type:** int

**Current value:** 18

---

### gov.states.ca.cdss.tanf.child_care.eligibility.age_threshold
**Label:** California CalWORKs Child Care age threshold

California provides the CalWORKs Child Care to children below this age.

**Type:** int

**Current value:** 13

---

### gov.states.ca.cdss.tanf.child_care.rate_ceilings.exceptional_needs
**Label:** California CalWORKs Child Care Exceptional Needs Regional Market Rate Ceilings

California multiplies the child care reimbursement for Exceptional Needs under the CalWORKs Child Care by this factor.

**Type:** float

**Current value:** 1.2

---

### gov.states.ca.cdss.tanf.child_care.rate_ceilings.evening_or_weekend_II
**Label:** California CalWORKs Child Care Evening/Weekend (at least 10% but less than 50% of time) Regional Market Rate Ceilings

California multiplies the child care reimbursement for Evening/Weekend Care Ii under the CalWORKs Child Care by this factor.

**Type:** float

**Current value:** 1.125

---

### gov.states.ca.cdss.tanf.child_care.rate_ceilings.evening_or_weekend_I
**Label:** California CalWORKs Child Care Evening/Weekend (50% or more of time) Regional Market Rate Ceilings

California multiplies the child care reimbursement for Evening/Weekend Care I under the CalWORKs Child Care by this factor.

**Type:** float

**Current value:** 1.25

---

### gov.states.ca.cdss.tanf.child_care.rate_ceilings.severely_disabled
**Label:** California CalWORKs Child Care Severely Disabled Regional Market Rate Ceilings

California multiplies the child care reimbursement for Severely Disabled under the CalWORKs Child Care by this factor.

**Type:** float

**Current value:** 1.5

---

### gov.states.ca.cdss.tanf.child_care.rate_ceilings.age_threshold.lower
**Label:** California CalWORKs Child Care lower age threshold

California partition payment level based on age threshold.

**Type:** int

**Current value:** 2

---

### gov.states.ca.cdss.tanf.child_care.rate_ceilings.age_threshold.higher
**Label:** California CalWORKs Child Care lower age threshold

California partition payment level based on age threshold.

**Type:** int

**Current value:** 5

---

### gov.states.ca.cdss.tanf.cash.monthly_payment.max_au_size
**Label:** California CalWORKs maximum assistance unit size for payment standards

California CalWORKs provide the maximum monthly payment for the AU which is over this size.

**Type:** int

**Current value:** 10

---

### gov.states.ca.cdss.tanf.cash.resources.limit.vehicle
**Label:** California CalWORKs vehicle value limit

California limits CalWORKs to households with vehicle value below this amount.

**Type:** int

**Current value:** 32968

---

### gov.states.ca.cdss.tanf.cash.resources.limit.age_threshold
**Label:** California CalWORKs resource limit age threshold

California CalWORKs provides a higher resource limit to households with at least one person at or over this age.

**Type:** int

**Current value:** 60

---

### gov.states.ca.cdss.tanf.cash.resources.limit.with_elderly_or_disabled_member
**Label:** California CalWORKs resources limit for households with elderly or disabled people

California imposes this CalWORKs resource limit for households with an elderly or disabled member.

**Type:** int

**Current value:** 18206

---

### gov.states.ca.cdss.tanf.cash.resources.limit.without_elderly_or_disabled_member
**Label:** California CalWORKs resources limit for households without elderly or disabled people

California imposes this CalWORKs resource limit for households without an elderly or disabled member.

**Type:** int

**Current value:** 12137

---

### gov.states.ca.cdss.tanf.cash.income.monthly_limit.region1.additional
**Label:** California CalWORKs monthly income limit additional for region 1

California CalWORKs increases the income limit by this amount for each person above the max relevant AU size in Region 1.

**Type:** int

**Current value:** 34

---

### gov.states.ca.cdss.tanf.cash.income.monthly_limit.max_au_size
**Label:** California CalWORKs maximum assistance unit size for MBSAC

California provides an extra monthly income limit for the CalWORKS assistance unit over this size.

**Type:** int

**Current value:** 10

---

### gov.states.ca.cdss.tanf.cash.income.monthly_limit.region2.additional
**Label:** California CalWORKs monthly income limit additional for region 2

California CalWORKs increases the income limit by this amount for each person above the max relevant AU size in Region 2.

**Type:** int

**Current value:** 34

---

### gov.states.ca.cdss.tanf.cash.income.disregards.recipient.percentage
**Label:** California CalWORKs monthly percentage earnings exclusion

California disregards this percentage of monthly earned income when computing CalWORKS payments for recipients.

**Type:** float

**Current value:** 0.5

---

### gov.states.ca.cdss.tanf.cash.income.disregards.recipient.flat
**Label:** California CalWORKs flat monthly income exclusion for recipients

California disregards this amount of monthly income when computing CalWORKS payments for recipients.

**Type:** int

**Current value:** 600

---

### gov.states.ca.cdss.tanf.cash.income.disregards.applicant.flat
**Label:** California CalWORKs recipient flat earnings exclusion for applicants

California disregards this amount of monthly earned income when determining CalWORKS eligibility for new applicants.

**Type:** int

**Current value:** 450

---

### gov.states.ca.fcc.lifeline.max_amount
**Label:** California Lifeline maximum benefit

California provides the following maximum Lifeline benefit amount.

**Type:** int

**Current value:** 19

---

### gov.states.ca.fcc.lifeline.in_effect
**Label:** California Lifeline maximum benefit in effect

California provides a separate maximum Lifeline benefit amount if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.ca.infant.age_limit
**Label:** California infant age limit

California defines infants as children at or below this age threshold.

**Type:** int

**Current value:** 1

---

### gov.states.ca.foster_care.age_threshold
**Label:** California foster care minor dependent age threshold

California considers the foster child a minor dependent below the following age.

**Type:** int

**Current value:** 21

---

### gov.states.ia.tax.income.rates.by_filing_status.active
**Label:** Iowa post 2023 income tax structure applies

Iowa applies a new income tax rate structure if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.ia.tax.income.alternative_minimum_tax.rate
**Label:** Iowa alternative minimum tax rate

Iowa imposes an alternative minimum tax with this rate.

**Type:** float

**Current value:** 0.064

---

### gov.states.ia.tax.income.alternative_minimum_tax.in_effect
**Label:** Iowa alternative minimum tax availability

Iowa imposes an alternative minimum tax if this is true.

**Type:** bool

**Current value:** False

---

### gov.states.ia.tax.income.alternative_minimum_tax.fraction
**Label:** Iowa alternative minimum tax fraction

Iowa imposes an alternative minimum tax that uses this fraction.

**Type:** float

**Current value:** 0.25

---

### gov.states.ia.tax.income.deductions.itemized.applies_federal
**Label:** Iowa federal itemized deduction applies

Iowa applies the federal itemized deduction if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.ia.tax.income.deductions.qualified_business_income.fraction
**Label:** Iowa federal QBID fraction

Iowa allows a deduction of this fraction of the federal qualified buiness income deduction (QBID).

**Type:** float

**Current value:** 0.75

---

### gov.states.ia.tax.income.deductions.standard.applies_federal
**Label:** Iowa federal standard deduction applies

Iowa applies the federal standard deduction if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.ia.tax.income.tax_reduction.elderly_age
**Label:** Iowa elderly age threshold used in tax reduction worksheet

Iowa considers single tax units with head this age or older to be elderly in tax reduction worksheet calculations.

**Type:** int

**Current value:** 65

---

### gov.states.ia.tax.income.tax_reduction.threshold.elderly
**Label:** Iowa tax reduction worksheet modified income threshold for elderly

Iowa has a tax reduction worksheet for single tax units that uses this modified income threshold for the elderly.

**Type:** int

**Current value:** 24000

---

### gov.states.ia.tax.income.tax_reduction.threshold.nonelderly
**Label:** Iowa tax reduction worksheet modified income threshold for nonelderly

Iowa has a tax reduction worksheet for single tax units that uses this modified income threshold for the nonelderly.

**Type:** int

**Current value:** 9000

---

### gov.states.ia.tax.income.pension_exclusion.minimum_age
**Label:** Iowa pension exclusion minimum age for age eligibility

Iowa allows an exclusion of taxable pension income to get its net income that is available to elderly or disabled heads or spouses where elderly is defined as being at least this minimum age.

**Type:** int

**Current value:** 55

---

### gov.states.ia.tax.income.reportable_social_security.fraction
**Label:** Iowa reportable social security fraction

Iowa calculates reportable social security using this fraction.

**Type:** float

**Current value:** 0.5

---

### gov.states.ia.tax.income.tax_exempt.elderly_age
**Label:** Iowa elderly age threshold used in tax exemption calculations

Iowa considers tax units with head or spouse this age or older to be elderly in exempt from income taxation calculations.

**Type:** int

**Current value:** 65

---

### gov.states.ia.tax.income.tax_exempt.income_limit.single_elderly
**Label:** Iowa tax exemption income limit for nonelderly single tax units

Iowa considers single tax units with modified net income no greater than this limit to be exempt from income taxation.

**Type:** int

**Current value:** 24000

---

### gov.states.ia.tax.income.tax_exempt.income_limit.other_elderly
**Label:** Iowa tax exemption income limit for elderly nonsingle tax units

Iowa considers tax units other than singles with modified net income no greater than this limit to be exempt from income taxation.

**Type:** int

**Current value:** 32000

---

### gov.states.ia.tax.income.tax_exempt.income_limit.single_nonelderly
**Label:** Iowa tax exemption income limit for nonelderly single tax units

Iowa considers single tax units with modified net income no greater than this limit to be exempt from income taxation.

**Type:** int

**Current value:** 9000

---

### gov.states.ia.tax.income.tax_exempt.income_limit.other_nonelderly
**Label:** Iowa tax exemption income limit for nonelderly nonsingle tax units

Iowa considers tax units other than singles with modified net income no greater than this limit to be exempt from income taxation.

**Type:** int

**Current value:** 13500

---

### gov.states.ia.tax.income.married_filing_separately_on_same_return.availability
**Label:** Iowa married filing separately on the same return availability

Iowa allows married couples to file separately on the same tax return if this is true.

**Type:** bool

**Current value:** False

---

### gov.states.ia.tax.income.credits.exemption.elderly_age
**Label:** Iowa elderly age threshold used in additional exemption credit calculations

Iowa gives an additional exemption credit to a head or spouse who is at least this age.

**Type:** int

**Current value:** 65

---

### gov.states.ia.tax.income.credits.exemption.additional
**Label:** Iowa additional (elderly and/or blind) exemption amount

Iowa has an nonrefundable exemption credit in which each elderly and/blind head and spouse receive this additional exemption amount for each condition.

**Type:** int

**Current value:** 20

---

### gov.states.ia.tax.income.credits.exemption.dependent
**Label:** Iowa dependent exemption amount

Iowa has an nonrefundable exemption credit in which each tax unit dependent receives this dependent exemption amount.

**Type:** int

**Current value:** 40

---

### gov.states.ia.tax.income.credits.exemption.personal
**Label:** Iowa personal exemption amount

Iowa has an nonrefundable exemption credit in which each tax unit head and spouse receive this personal exemption amount.

**Type:** int

**Current value:** 40

---

### gov.states.ia.tax.income.credits.earned_income.fraction
**Label:** Iowa EITC fraction

Iowa provides an earned income tax credit (EITC) that is this fraction of the federal EITC amount.

**Type:** float

**Current value:** 0.15

---

### gov.states.ia.tax.income.alternate_tax.elderly_age
**Label:** Iowa alternate tax age threshold that determines deduction amount

Iowa allows an alternate tax for non-single filing units where the deduction varies depending on whether head or spouse age is at least this age.

**Type:** int

**Current value:** 65

---

### gov.states.ia.tax.income.alternate_tax.rate
**Label:** Iowa alternate tax rate

Iowa allows an alternate tax for non-single filing units that has this flat tax rate.

**Type:** float

**Current value:** 0.0853

---

### gov.states.ia.tax.income.alternate_tax.deduction.elderly
**Label:** Iowa deduction used in tax alternate tax calculations for elderly

Iowa has a alternate tax with this deduction against modified income for tax units with elderly head or spouse.

**Type:** int

**Current value:** 32000

---

### gov.states.ia.tax.income.alternate_tax.deduction.nonelderly
**Label:** Iowa deduction used in tax alternate tax calculations for nonelderly

Iowa has a alternate tax with this deduction against modified income for tax units without an elderly head or spouse.

**Type:** int

**Current value:** 13500

---

### gov.states.ct.tax.income.subtractions.pensions_or_annuity.rate
**Label:** Connecticut annuity and pension subtraction rate

Connecticut subtracts this fraction of annuity and pension income from adjusted gross income.

**Type:** int

**Current value:** 1

---

### gov.states.ct.tax.income.subtractions.social_security.combined_income_excess
**Label:** Connecticut combined income excess rate

Connecticut calculates this fraction of the combined income excess, which is then compared to a portion of taxable Social Security benefits, to determine the minimum as part of the social security benefit adjustment.

**Type:** float

**Current value:** 0.25

---

### gov.states.ct.tax.income.subtractions.social_security.rate.social_security
**Label:** Connecticut social security benefit adjustment rate

Connecticut multiplies the taxable social security amount by this rate under the social security benefit adjustment.

**Type:** float

**Current value:** 0.25

---

### gov.states.ct.tax.income.rebate.child_cap
**Label:** Connecticut tax rebate child cap

Connecticut caps the child for tax rebate at this number.

**Type:** int

**Current value:** 3

---

### gov.states.ct.tax.income.rebate.amount
**Label:** Connecticut child tax rebate amount

Connecticut provides a child tax rebate of this amount, for each eligible child.

**Type:** int

**Current value:** 250

---

### gov.states.ct.tax.income.rebate.reduction.increment
**Label:** Connecticut child tax rebate reduction increment

Connecticut reduces the child tax rebate amount for each of these increments of state adjusted gross income exceeding the threshold.

**Type:** int

**Current value:** 1000

---

### gov.states.ct.tax.income.rebate.reduction.rate
**Label:** Connecticut child tax rebate reduction rate

Connecticut reduces the personal exemption amount by this rate for each increment of state adjusted gross income exceeding the threshold.

**Type:** float

**Current value:** 0.1

---

### gov.states.ct.tax.income.exemptions.personal.reduction.increment
**Label:** Connecticut personal exemption reduction increment

Connecticut reduces the personal exemption amount for each of these increments of state adjusted gross income exceeding the threshold.

**Type:** int

**Current value:** 1000

---

### gov.states.ct.tax.income.exemptions.personal.reduction.amount
**Label:** Connecticut personal exemption reduction amount

Connecticut reduces the personal exemption amount by this amount for each increment of state adjusted gross income exceeding the threshold.

**Type:** int

**Current value:** 1000

---

### gov.states.ct.tax.income.credits.property_tax.age_threshold
**Label:** Connecticut property tax credit age threshold

Connecticut limits its property tax credit to filers at or above this age.

**Type:** int

**Current value:** 0

---

### gov.states.ct.tax.income.credits.property_tax.reduction.rate
**Label:** Connecticut Property Tax Credit reduction rate

Connecticut reduces its property tax credit by this percentage for each increment of state adjusted gross income exceeding the threshold.

**Type:** float

**Current value:** 0.15

---

### gov.states.ct.tax.income.credits.property_tax.cap
**Label:** Connecticut property tax credit cap

Connecticut caps the property tax credit at this amount.

**Type:** int

**Current value:** 300

---

### gov.states.ct.tax.income.credits.eitc.match
**Label:** Connecticut EITC match

Connecticut matches this percent of the federal earned income tax credit.

**Type:** float

**Current value:** 0.4

---

### gov.states.wv.tax.income.subtractions.social_security_benefits.rate
**Label:** West Virginia social security benefits subtraction rate

West Virginia subtracts this fraction of taxable social security benefits from adjusted gross income.

**Type:** int

**Current value:** 1

---

### gov.states.wv.tax.income.subtractions.public_pension.max_amount
**Label:** West Virginia public pension subtraction max amount

West Virginia provides a pension subtraction of up to this maximum amount.

**Type:** int

**Current value:** 2000

---

### gov.states.wv.tax.income.subtractions.senior_citizen_disability_deduction.age_threshold
**Label:** West Virginia senior citizen deduction age threshold

West Virginia limits the senior citizen deduction to filers this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.wv.tax.income.subtractions.senior_citizen_disability_deduction.cap
**Label:** West Virginia senior citizen or disability deduction cap

West Virginia caps the reduced adjusted gross income at this amount under the senior citizen or disability deduction.

**Type:** int

**Current value:** 8000

---

### gov.states.wv.tax.income.exemptions.base_personal
**Label:** West Virginia personal exemption

West Virginia provides an income tax exemption of this value for tax units with no exemptions claimed.

**Type:** int

**Current value:** 500

---

### gov.states.wv.tax.income.exemptions.homestead_exemption.max_amount
**Label:** West Virginia homestead exemption max amount

West Virginia provides a homestead exemption of up to this maximum amount.

**Type:** int

**Current value:** 20000

---

### gov.states.wv.tax.income.exemptions.personal
**Label:** West Virginia personal exemption

West Virginia provides an income tax exemption of this value for each person in the filing unit.

**Type:** int

**Current value:** 2000

---

### gov.states.wv.tax.income.credits.heptc.rate.fpg
**Label:** West Virginia homestead excess property tax credit poverty guidelines rate

West Virginia limits the homestead excess property tax credit to filers with adjusted gross income below this multiple of the federal poverty guidelines.

**Type:** int

**Current value:** 3

---

### gov.states.wv.tax.income.credits.heptc.rate.household_income
**Label:** West Virginia homestead excess property tax credit gross household income rate

West Virginia provides a homestead property tax credit for property taxes in excess of this fraction of gross household income less the amount of the senior citizen tax credit.

**Type:** float

**Current value:** 0.04

---

### gov.states.wv.tax.income.credits.heptc.cap
**Label:** West Virginia homestead excess property tax credit cap

West Virginia caps the homestead excess property tax credit at this amount.

**Type:** int

**Current value:** 1000

---

### gov.states.wv.tax.income.credits.sctc.max_amount
**Label:** West Virginia senior citizens tax credit max amount

West Virginia provides a senior citizens tax credit of up to this maximum amount.

**Type:** int

**Current value:** 20000

---

### gov.states.wv.tax.income.credits.sctc.fpg_percentage
**Label:** West Virginia senior citizens tax credit federal poverty guidelines percentage

West Virginia qualifies filers for the senior citizens tax credit with modified gross income below this percentage of the federal poverty guidelines.

**Type:** float

**Current value:** 1.5

---

### gov.states.wv.tax.income.credits.liftc.max_family_size
**Label:** West Virginia family size of low-income family tax credit max family size

West Virginia limits the number of eligible tax unit members for the low-income family tax credit to this amount.

**Type:** int

**Current value:** 8

---

### gov.states.ri.tax.income.agi.subtractions.taxable_retirement_income.cap
**Label:** Rhode Island taxable retirement income subtraction cap

Rhode Island subtracts up to this amount of taxable retirement income from adjusted gross income.

**Type:** int

**Current value:** 20000

---

### gov.states.ri.tax.income.agi.subtractions.social_security.limit.birth_year
**Label:** Rhode Island social security modification birth year threshold

Rhode Island allows social security modifications for taxpayers or spouses born on or before this date.

**Type:** int

**Current value:** 1957

---

### gov.states.ri.tax.income.deductions.standard.phase_out.percentage
**Label:** Rhode Island standard deduction phase out rate

Rhode Island phases out this percentage of its standard deduction for each increment by which their income exceeds the threshold.

**Type:** float

**Current value:** 0.2

---

### gov.states.ri.tax.income.exemption.reduction.rate
**Label:** Rhode Island exemption phase out rate

Rhode Island reduces the personal exemption amount by this rate, increased for each increment of state adjusted gross income exceeding the threshold.

**Type:** float

**Current value:** 0.2

---

### gov.states.ri.tax.income.credits.property_tax.rate.rent
**Label:** Rhode Island property tax credit rent rate

Rhode Island accounts for the following percentage of rent paid under the property tax credit.

**Type:** float

**Current value:** 0.2

---

### gov.states.ri.tax.income.credits.property_tax.age_threshold
**Label:** Rhode Island property tax credit age threshold

Rhode Island limits its property tax credit to filers this age or older, or who have a disability.

**Type:** int

**Current value:** 65

---

### gov.states.ri.tax.income.credits.child_tax_rebate.limit.age
**Label:** Rhode Island child tax rebate child age limit

Rhode Island limits its child tax rebate to children this age or younger.

**Type:** int

**Current value:** 18

---

### gov.states.ri.tax.income.credits.child_tax_rebate.limit.child
**Label:** Rhode Island child tax rebate child cap

Rhode Island caps the child tax rebate to this number of children.

**Type:** int

**Current value:** 3

---

### gov.states.ri.tax.income.credits.child_tax_rebate.amount
**Label:** Rhode Island child tax rebate amount

Rhode Island provides this child tax rebate amount for each eligible child.

**Type:** int

**Current value:** 250

---

### gov.states.ri.tax.income.credits.cdcc.rate
**Label:** Rhode Island CDCC match percent

Rhode Island matches the Federal Credit for child and dependent care expenses by this rate.

**Type:** float

**Current value:** 0.25

---

### gov.states.ri.tax.income.credits.eitc.match
**Label:** Rhode Island EITC match

Rhode Island matches this fraction of the federal earned income tax credit.

**Type:** float

**Current value:** 0.16

---

### gov.states.pa.dhs.tanf.resource_limit
**Label:** Pennsylvania TANF resource limit

Pennsylvania limits TANF benefits to households with resources at or below this amount.

**Type:** int

**Current value:** 1000

---

### gov.states.pa.dhs.tanf.cash_assistance.age_limit
**Label:** Pennsylvania TANF age eligibility

Pennsylvania limits TANF eligibility to people below this age, or students exactly this age.

**Type:** int

**Current value:** 18

---

### gov.states.pa.dhs.tanf.pregnancy_eligibility.age_limit
**Label:** Pennsylvania TANF age limitation for pregnant women with child receiving TANF

Pennsylvania has limitation for applying TANF to pregnant women above or equal to this age.

**Type:** int

**Current value:** 18

---

### gov.states.pa.tax.income.forgiveness.tax_back
**Label:** PA tax forgiveness percentage

Pennsylvania reduces its tax forgiveness by this percent per given amount of eligibility income.

**Type:** float

**Current value:** 0.1

---

### gov.states.pa.tax.income.forgiveness.dependent_rate
**Label:** PA tax forgiveness rate increase for each additional dependent

Pennsylvania increases the tax forgiveness eligibility income threshold by this amount for each dependent.

**Type:** int

**Current value:** 9500

---

### gov.states.pa.tax.income.forgiveness.base
**Label:** PA base eligibility income

Pennsylvania starts reducing its tax forgiveness when eligibility income exceeds this amount, or double for joint filers.

**Type:** int

**Current value:** 6500

---

### gov.states.pa.tax.income.forgiveness.rate_increment
**Label:** PA tax forgiveness rate decrease for each additional increment of eligibility income

Pennsylvania reduces its tax forgiveness by a given percent per this amount of eligibility income.

**Type:** int

**Current value:** 250

---

### gov.states.pa.tax.income.rate
**Label:** PA income tax rate

Pennsylvania taxes income at this rate.

**Type:** float

**Current value:** 0.0307

---

### gov.states.pa.tax.income.credits.cdcc.match
**Label:** Pennsylvania Child and Dependent Care Credit match

Pennsylvania matches this percentage of the federal Child and Dependent Care Credit.

**Type:** int

**Current value:** 1

---

### gov.states.pa.tax.use_tax.higher.rate.rest_of_pa
**Label:** Rest of PA Use Tax Rate

Pennsylvania levies a use tax at this percent of taxable income for residents outside Philadelphia and Allegheny County with taxable income over the higher threshold.

**Type:** float

**Current value:** 0.0003

---

### gov.states.pa.tax.use_tax.higher.rate.allegheny_county
**Label:** PA Allegheny County Use Tax Rate

Pennsylvania levies a use tax at this percent of taxable income for Allegheny County residents with taxable income over the higher threshold.

**Type:** float

**Current value:** 0.00035

---

### gov.states.pa.tax.use_tax.higher.rate.philadelphia_county
**Label:** PA Philadelphia Use Tax Rate

Pennsylvania levies a use tax at this percent of taxable income for Philadelphia residents with taxable income over the higher threshold.

**Type:** float

**Current value:** 0.0004

---

### gov.states.pa.tax.use_tax.higher.cap.rest_of_pa
**Label:** Rest of PA use tax cap

Pennsylvania caps the use tax at this amount for people outside Philadelphia and Allegheny County.

**Type:** int

**Current value:** 75

---

### gov.states.pa.tax.use_tax.higher.cap.allegheny_county
**Label:** PA Alleghney County use tax cap

Pennsylvania caps the use tax for Allegheny County at this amount.

**Type:** int

**Current value:** 88

---

### gov.states.pa.tax.use_tax.higher.cap.philadelphia_county
**Label:** PA Philadelphia use tax cap

Pennsylvania caps the use tax for Philadelphia at this amount.

**Type:** int

**Current value:** 100

---

### gov.states.pa.tax.use_tax.higher.threshold
**Label:** PA use Tax higher threshold

Pennsylvania moves to a percentage based use tax system at this threshold.

**Type:** int

**Current value:** 200000

---

### gov.states.nc.ncdhhs.tanf.need_standard.average_reduced_need_standard_thresold
**Label:** North Carolina TANF monthly minimum benefit

North Carolina disqualifies households from the Temporary Assistance for Needy Families program if their average per-person need standard, after subtracting income, falls below this amount.

**Type:** int

**Current value:** 25

---

### gov.states.nc.ncdhhs.tanf.need_standard.payment_percentage
**Label:** North Carolina TANF payment percentage

North Carolina provides this fraction of the difference between the need standard and household income for its Temporary Assistance for Needy Families program.

**Type:** float

**Current value:** 0.5

---

### gov.states.nc.ncdhhs.tanf.need_standard.age_limit
**Label:** North Carolina TANF program child age limit

North Carolina limits its Temporary Assistance for Needy Families program to children below this age.

**Type:** int

**Current value:** 18

---

### gov.states.nc.ncdhhs.tanf.need_standard.additional_person
**Label:** North Carolina TANF monthly income limit per additional person

North Carolina provides an additional need standard amount for each household member exceeding the maximum specified household size for its Temporary Assistance for Needy Families program.

**Type:** int

**Current value:** 50

---

### gov.states.nc.tax.income.deductions.military_retirement.minimum_years
**Label:** North Carolina minimum years serving in the military

North Carolina requires a filer to have served for at least this many years in the military to qualify for specific military retirement deductions, given the filer is not medically retired.

**Type:** int

**Current value:** 20

---

### gov.states.nc.tax.income.deductions.military_retirement.fraction
**Label:** North Carolina military retirement subtraction fraction

North Carolina subtracts this fraction of military retirement benefits from federal adjusted gross income.

**Type:** int

**Current value:** 1

---

### gov.states.nc.tax.income.rate
**Label:** North Carolina individual income tax rate

North Carolina taxes individual taxable income at this rate.

**Type:** float

**Current value:** 0.0425

---

### gov.states.nd.tax.income.taxable_income.subtractions.ltcg_fraction
**Label:** North Dakota fraction of long-term capital gains that can be subtracted from taxable income

North Dakota subtracts this fraction of long-term capital gains from US taxable income when calculating its taxable income.

**Type:** float

**Current value:** 0.4

---

### gov.states.nd.tax.income.taxable_income.subtractions.qdiv_fraction
**Label:** North Dakota fraction of qualified dividends that can be subtracted from taxable income

North Dakota subtracts this fraction of qualified dividends from US taxable income when calculating its taxable income.

**Type:** float

**Current value:** 0.4

---

### gov.states.nd.tax.income.credits.marriage_penalty.qualified_income_threshold
**Label:** North Dakota marriage-penalty credit qualified income threshold

North Dakota has a nonrefundable marriage-penalty credit for joint filers with smaller of head and spouse qualified income more than this amount.

**Type:** float

**Current value:** 47773.54182063854

---

### gov.states.nd.tax.income.credits.marriage_penalty.maximum
**Label:** North Dakota marriage-penalty credit maximum amount

North Dakota has a nonrefundable marriage-penalty credit for joint filers in which this is the maximum credit amount.

**Type:** float

**Current value:** 311.75549118970577

---

### gov.states.nd.tax.income.credits.marriage_penalty.taxable_income_threshold
**Label:** North Dakota marriage-penalty credit taxable income threshold

North Dakota has a nonrefundable marriage-penalty credit for joint filers with state taxable income more than this amount.

**Type:** float

**Current value:** 81319.30167750437

---

### gov.states.nd.tax.income.credits.resident_tax_relief.other_amount
**Label:** North Dakota resident-tax-relief credit amount for non-joint filing units

North Dakota had for 2021-2022 a nonrefundable resident-tax-relief credit of this amount for non-joint filing units.

**Type:** int

**Current value:** 0

---

### gov.states.nd.tax.income.credits.resident_tax_relief.joint_amount
**Label:** North Dakota resident-tax-relief credit amount for joint filing units

North Dakota had for 2021-2022 a nonrefundable resident-tax-relief credit of this amount for joint filing units.

**Type:** int

**Current value:** 0

---

### gov.states.nm.tax.income.rebates.property_tax.rent_rate
**Label:** New Mexico property tax rebate rent rate

New Mexico treats this percentage of rent as property tax for the property tax rebate.

**Type:** float

**Current value:** 0.06

---

### gov.states.nm.tax.income.rebates.property_tax.age_eligibility
**Label:** New Mexico property tax rebate age threshold

New Mexico provides the property tax rebate for filers at or above this age threshold.

**Type:** int

**Current value:** 65

---

### gov.states.nm.tax.income.rebates.property_tax.income_threshold
**Label:** New Mexico property tax rebate income threshold

New Mexico provides the property tax rebate for filers with income below this threshold.

**Type:** int

**Current value:** 16000

---

### gov.states.nm.tax.income.rebates.low_income.divisor
**Label:** New Mexico low income rebate divisor for married filing separately

New Mexico divides its low income comprehensive tax rebate by this number for married filing separately filers.

**Type:** int

**Current value:** 2

---

### gov.states.nm.tax.income.rebates.low_income.exemptions.blind
**Label:** New Mexico low income rebate blind exemption

New Mexico provides an additional exemption under the low income comprehensive tax rebate for blind filers.

**Type:** int

**Current value:** 1

---

### gov.states.nm.tax.income.deductions.net_capital_gains.uncapped_element_percent
**Label:** New Mexico net capital gain deduction uncapped element percent

New Mexico allows filers to deduct this percentage of their net capital gains, or an amount of it, whichever is greater.

**Type:** float

**Current value:** 0.4

---

### gov.states.nm.tax.income.exemptions.low_and_middle_income.max_amount
**Label:** New Mexico low- and middle-income exemption maximum amount

New Mexico provides this maximum low- and middle-income exemption amount.

**Type:** int

**Current value:** 2500

---

### gov.states.nm.tax.income.exemptions.unreimbursed_medical_care_expense.age_eligibility
**Label:** New Mexico medical care expense exemption age threshold

New Mexico provides the unreimbursed medical care expense exemption for filers at or above this age threshold.

**Type:** int

**Current value:** 65

---

### gov.states.nm.tax.income.exemptions.unreimbursed_medical_care_expense.amount
**Label:** New Mexico medical care expense exemption amount

New Mexico provides this amount under the unreimbursed medical care expense exemption.

**Type:** int

**Current value:** 3000

---

### gov.states.nm.tax.income.exemptions.unreimbursed_medical_care_expense.min_expenses
**Label:** New Mexico medical care expense exemption minimum expenses

New Mexico provides the unreimbursed medical care expense exemption for filers with expenses at or above this amount.

**Type:** int

**Current value:** 28000

---

### gov.states.nm.tax.income.exemptions.hundred_year.age_eligibility
**Label:** New Mexico hundred year exemption age threshold

New Mexico provides the hundred year exemption for filers at or above this age threshold.

**Type:** int

**Current value:** 100

---

### gov.states.nm.tax.income.exemptions.blind_and_aged.age_threshold
**Label:** New Mexico aged and blind exemption age threshold

New Mexico provides the aged or blind exemption for filers at or above this age threshold.

**Type:** int

**Current value:** 65

---

### gov.states.nm.tax.income.exemptions.armed_forces_retirement_pay.cap
**Label:** New Mexico armed forces retirement pay exemption cap

New Mexico exempts this amount of armed forces retirement pay.

**Type:** int

**Current value:** 30000

---

### gov.states.nm.tax.income.credits.unreimbursed_medical_care_expense.age_eligibility
**Label:** New Mexico medical care expense credit age threshold

New Mexico provides the unreimbursed medical care expense credit for filers at or above this age threshold.

**Type:** int

**Current value:** 65

---

### gov.states.nm.tax.income.credits.unreimbursed_medical_care_expense.amount
**Label:** New Mexico medical care expense credit amount

New Mexico provides this amount under the unreimbursed medical care expense credit.

**Type:** int

**Current value:** 2800

---

### gov.states.nm.tax.income.credits.unreimbursed_medical_care_expense.min_expenses
**Label:** New Mexico medical care expense credit minimum expenses

New Mexico provides the unreimbursed medical care expense credit for filers with expenses at or above this amount.

**Type:** int

**Current value:** 28000

---

### gov.states.nm.tax.income.credits.cdcc.age_eligible
**Label:** New Mexico credit for dependent day care child eligible age

New Mexico provides the credit for dependent day care for dependents below this age threshold.

**Type:** int

**Current value:** 15

---

### gov.states.nm.tax.income.credits.cdcc.divisor
**Label:** New Mexico credit for dependent day care separate divisor

New Mexico divides the credit for dependent day care for separate filers by this divisor.

**Type:** int

**Current value:** 2

---

### gov.states.nm.tax.income.credits.cdcc.rate
**Label:** New Mexico dependent day care credit rate

New Mexico matches up to this share of the federal Child and Dependent Care Credit for its Child Day Care Credit.

**Type:** float

**Current value:** 0.4

---

### gov.states.nm.tax.income.credits.cdcc.max_amount.per_child
**Label:** New Mexico credit for child and dependent care one dependent max amount

New Mexico provides up to this amount per child under its Child Day Care Credit.

**Type:** int

**Current value:** 480

---

### gov.states.nm.tax.income.credits.cdcc.max_amount.total
**Label:** New Mexico credit for child and dependent care max amount

New Mexico provides up to this total amount under its Child Day Care Credit.

**Type:** int

**Current value:** 1200

---

### gov.states.nm.tax.income.credits.cdcc.full_time_hours
**Label:** New Mexico credit for dependent day care full time hours

New Mexico provides the credit for child and dependent day care for filers with modified gross income based on these full time working hours.

**Type:** int

**Current value:** 40

---

### gov.states.nm.tax.income.credits.cdcc.income_limit_as_fraction_of_minimum_wage
**Label:** New Mexico CDCC MAGI limit as fraction of minimum wage

New Mexico provides the child and dependent day care credit for filers with modified gross income at or below this fraction of full-time minimum wage.

**Type:** int

**Current value:** 2

---

### gov.states.nm.tax.income.credits.eitc.match
**Label:** New Mexico EITC match

New Mexico matches this percentage of the federal Earned Income Tax Credit.

**Type:** float

**Current value:** 0.25

---

### gov.states.nm.tax.income.credits.eitc.eligibility.age.min
**Label:** New Mexico EITC minimum childless age

New Mexico limits Earned Income Tax Credit eligibility for filers without children to those this age or older.

**Type:** int

**Current value:** 18

---

### gov.states.nj.tax.income.deductions.property_tax.qualifying_rent_fraction
**Label:** New Jersey percent of rent considered property taxes

New Jersey considers this percent of rent paid property taxes.

**Type:** float

**Current value:** 0.18

---

### gov.states.nj.tax.income.deductions.property_tax.limit
**Label:** New Jersey property tax deduction/credit property tax limit

New Jersey allows for a property tax credit or deduction on up to this amount of paid property taxes.

**Type:** int

**Current value:** 15000

---

### gov.states.nj.tax.income.deductions.medical_expenses.rate
**Label:** New Jersey medical expense deduction rate

New Jersey deducts from taxable income the excess of medical expenses over this fraction of state adjusted gross income.

**Type:** float

**Current value:** 0.02

---

### gov.states.nj.tax.income.exclusions.retirement.other_retirement_income.earned_income_threshold
**Label:** NJ other retirement earned income exclusion threshold.

New Jersey filers with more than this amount of earned income are not eligible for other retirement exclusion.

**Type:** int

**Current value:** 3000

---

### gov.states.nj.tax.income.exclusions.retirement.age_threshold
**Label:** NJ pension/retirement exclusion and other retirement income exclusion qualifying age

Filers (and/or spouses) must be at or above this age to subtract retirement income from taxable income

**Type:** int

**Current value:** 62

---

### gov.states.nj.tax.income.exemptions.senior.age_threshold
**Label:** New Jersey senior exemption age threshold

New Jersey provides an additional exemption amount for filers above this age threshold.

**Type:** int

**Current value:** 65

---

### gov.states.nj.tax.income.exemptions.senior.amount
**Label:** New Jersey senior exemption amount

New Jersey provides this exemption amount per qualifying person.

**Type:** int

**Current value:** 1000

---

### gov.states.nj.tax.income.exemptions.dependents_attending_college.age_threshold
**Label:** New Jersey dependent attending college exemption age limit

New Jersey limits its exemption for dependents attending college to people below this age.

**Type:** int

**Current value:** 22

---

### gov.states.nj.tax.income.exemptions.dependents_attending_college.amount
**Label:** New Jersey dependent attending college exemption

New Jersey provides an exemption of this value per dependent attending colleges.

**Type:** int

**Current value:** 1000

---

### gov.states.nj.tax.income.exemptions.dependents.amount
**Label:** New Jersey dependent exemption

New Jersey provides an exemption of this value per dependent.

**Type:** int

**Current value:** 1500

---

### gov.states.nj.tax.income.exemptions.blind_or_disabled.amount
**Label:** New Jersey blind or disabled exemption

New Jersey provides an exemption of this amount per blind or disabled filer or spouse.

**Type:** int

**Current value:** 1000

---

### gov.states.nj.tax.income.credits.property_tax.age_threshold
**Label:** New Jersey property tax credit senior age threshold

New Jersey limits the property tax credit to filers of this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.nj.tax.income.credits.property_tax.amount
**Label:** New Jersey property tax credit amount

New Jersey offers a refundable property tax credit of this amount.

**Type:** int

**Current value:** 50

---

### gov.states.nj.tax.income.credits.ctc.age_limit
**Label:** New Jersey child tax credit age limit

New Jersey provides a child tax credit to filers for each dependent below this age.

**Type:** int

**Current value:** 6

---

### gov.states.nj.tax.income.credits.eitc.match
**Label:** New Jersey EITC match

New Jersey matches this fraction of the federal earned income tax credit.

**Type:** float

**Current value:** 0.4

---

### gov.states.nj.tax.income.credits.eitc.eligibility.age.min
**Label:** New Jersey EITC minimum childless age

New Jersey limits the earned income tax credit for filers without children to this age or older.

**Type:** int

**Current value:** 18

---

### gov.states.nj.njdhs.tanf.maximum_benefit.additional
**Label:** New Jersey TANF monthly maximum benefit per additional person

New Jersey limits its TANF program to households with this maximum benefit for people beyond size.

**Type:** int

**Current value:** 66

---

### gov.states.nj.njdhs.tanf.eligibility.resources.limit
**Label:** New Jersey TANF resource limit

New Jersey limits its TANF eligibility to households with up to this amount of resources.

**Type:** int

**Current value:** 2000

---

### gov.states.nj.njdhs.tanf.maximum_allowable_income.additional
**Label:** New Jersey TANF monthly income limit per additional person

New Jersey limits its TANF program to households with up to this income level for people beyond size.

**Type:** int

**Current value:** 99

---

### gov.states.nj.snap.amount
**Label:** New Jersey SNAP minimum allotment amount

New Jersey provides a minimum monthly SNAP allotment of this amount.

**Type:** int

**Current value:** 95

---

### gov.states.nj.snap.in_effect
**Label:** New Jersey SNAP minimum allotment in effect

New Jersey provides a separate SNAP minimum allotment amount if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.me.tax.income.agi.subtractions.pension_exclusion.cap
**Label:** Maine pension exclusion cap

Maine subtracts this amount from pensions and annuities included in federal AGI from Maine AGI.

**Type:** int

**Current value:** 35000

---

### gov.states.me.tax.income.credits.child_care.max_amount
**Label:** Maine child care credit amount refundable max

Maine provides up to this amount in its child care credit.

**Type:** int

**Current value:** 500

---

### gov.states.me.tax.income.credits.child_care.share_of_federal_credit.step_4
**Label:** Maine child care credit match for step 4 child care expenses

Maine matches this share of the federal child and dependent care credit for child care expenses that qualify as Step 4.

**Type:** float

**Current value:** 0.5

---

### gov.states.me.tax.income.credits.child_care.share_of_federal_credit.non_step_4
**Label:** Maine child care credit match for non-Step 4 child care expenses

Maine matches this share of the federal child and dependent care credit for child care expenses that don't qualify as Step 4.

**Type:** float

**Current value:** 0.25

---

### gov.states.me.tax.income.credits.fairness.property_tax.rate.income
**Label:** Maine property tax fairness credit income rate

Maine allows for a the property tax fairness credit amount which exceedes this rate of the filers income.

**Type:** float

**Current value:** 0.04

---

### gov.states.me.tax.income.credits.fairness.property_tax.rate.rent
**Label:** Maine property tax fairness credit income rate

Maine considers this percentage of the gross rent as rent constituting property taxes under the property tax fairness credit.

**Type:** float

**Current value:** 0.15

---

### gov.states.me.tax.income.credits.fairness.property_tax.dependent_count_threshold
**Label:** Maine property tax fairness credit dependent amount threshold

Maine assigns same amount of benefit base for household who have dependent of more than this value.

**Type:** int

**Current value:** 1

---

### gov.states.me.tax.income.credits.fairness.property_tax.benefit_base.head_of_household_one_child
**Label:** Maine property tax fairness credit benefit base for household with one child or joint filers with no child

Maine allows for this property tax fairness credit benefit base for head of household with one child or joint filers with no child

**Type:** int

**Current value:** 3000

---

### gov.states.me.tax.income.credits.fairness.property_tax.benefit_base.joint_or_head_of_household_multiple_children
**Label:** Maine property tax fairness credit benefit base for household with multiple children or joint filers with one child or more

Maine allows for this property tax fairness credit benefit base for head of household with multiple children or joint filers with one child or more.

**Type:** int

**Current value:** 3700

---

### gov.states.me.tax.income.credits.fairness.property_tax.benefit_base.single
**Label:** Maine property tax fairness credit benefit base for single filers

Maine allows for this property tax fairness credit benefit base for single filers

**Type:** int

**Current value:** 2300

---

### gov.states.me.tax.income.credits.fairness.property_tax.veterans_matched
**Label:** Maine additional credit for permanently and totally disabled veterans in effect

Maine provides additional credit for permanently and totally disabled veterans if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.me.tax.income.credits.dependent_exemption.phase_out.step
**Label:** Maine dependent exemption phaseout amount per phaseout increment

Maine reduces the dependent exemption credit by this amount for each increment in of Maine adjusted gross income above the threshold.

**Type:** float

**Current value:** 7.5

---

### gov.states.me.tax.income.credits.dependent_exemption.phase_out.increment
**Label:** Maine dependent exemption phaseout increment

Maine reduces the dependent exemption credit by an amount for each of these increments of Maine adjusted gross income exceeding the threshold.

**Type:** int

**Current value:** 1000

---

### gov.states.me.tax.income.credits.dependent_exemption.amount
**Label:** Maine dependent exemption credit amount

Maine provides up to this dependent exemption credit amount.

**Type:** int

**Current value:** 300

---

### gov.states.me.tax.income.credits.eitc.rate.with_qualifying_child
**Label:** Maine EITC percent

Maine matches this share of the federal EITC for filers with qualifying children.

**Type:** float

**Current value:** 0.25

---

### gov.states.me.tax.income.credits.eitc.rate.no_qualifying_child
**Label:** Maine EITC percent

Maine matches this share of the federal EITC for filers without qualifying children.

**Type:** float

**Current value:** 0.5

---

### gov.states.ar.tax.income.deductions.itemized.tuition.rate
**Label:** Arkansas post-secondary education deduction tuition expense rate

Arkansas calculates this rate of education tuition expenses under the post secondary eduction tuition deduction.

**Type:** float

**Current value:** 0.5

---

### gov.states.ar.tax.income.deductions.itemized.tuition.weighted_average_tuition.two_year_college
**Label:** Arkansas post secondary eduction tuition deduction two-year college weighted average tuition

Arkansas defines the weighted average tuition for four-year colleges at this amount under the post secondary education tuition deduction.

**Type:** int

**Current value:** 2405

---

### gov.states.ar.tax.income.deductions.itemized.tuition.weighted_average_tuition.technical_institutes
**Label:** Arkansas post secondary eduction tuition deduction technical institutes weighted average tuition

Arkansas defines the weighted average tuition for technical institutes at this amount under the post secondary education tuition deduction.

**Type:** int

**Current value:** 780

---

### gov.states.ar.tax.income.deductions.itemized.tuition.weighted_average_tuition.four_year_college
**Label:** Arkansas post secondary eduction tuition deduction four-year college weighted average tuition

Arkansas defines the weighted average tuition for four-year colleges at this amount under the post secondary education tuition deduction.

**Type:** int

**Current value:** 4819

---

### gov.states.ar.tax.income.gross_income.capital_gains.exempt.rate
**Label:** Arkansas long-term capital gains tax exempt rate

Arkansas exempts this percentage of long-term capital gains.

**Type:** float

**Current value:** 0.5

---

### gov.states.ar.tax.income.gross_income.capital_gains.exempt.cap
**Label:** Arkansas long-term capital gains tax exempt cap

Arkansas exempts all net capital gains in excess of this threshold.

**Type:** int

**Current value:** 10000000

---

### gov.states.ar.tax.income.exemptions.retirement_or_disability_benefits.cap
**Label:** Arkansas retirement or disability benefits exemption cap

Arkansas caps the retirement and benefit exemption at this amount.

**Type:** int

**Current value:** 6000

---

### gov.states.ar.tax.income.credits.personal.amount.disabled_dependent
**Label:** Arkansas disabled dependent personal tax credit amount

Arkansas provides this personal tax credit amount to each disabled dependent.

**Type:** int

**Current value:** 500

---

### gov.states.ar.tax.income.credits.personal.amount.base
**Label:** Arkansas personal tax credit base amount

Arkansas provides this base personal tax credit amount.

**Type:** int

**Current value:** 29

---

### gov.states.ar.tax.income.credits.personal.age_threshold
**Label:** Arkansas aged personal credit age threshold

Arkansas limits its aged personal credit to filers this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.ar.tax.income.credits.cdcc.match
**Label:** Arkansas household and dependents care credit match

Arkansas matches this percentage of the federal child and dependent care credit.

**Type:** float

**Current value:** 0.2

---

### gov.states.dc.dhs.tanf.resource_limit.lower_limit
**Label:** DC TANF resource limit for households without elderly or disabled people

DC limits TANF to households with up to this resource amount if they do not have elderly or disabled members.

**Type:** int

**Current value:** 2000

---

### gov.states.dc.dhs.tanf.resource_limit.higher_limit
**Label:** DC TANF resource limit for households with elderly or disabled people

DC limits TANF to households with up to this resource amount if they have elderly or disabled members.

**Type:** int

**Current value:** 3000

---

### gov.states.dc.dhs.tanf.resource_limit.elderly_age_threshold
**Label:** DC TANF resource limit threshold for an elderly

DC provide higher limit for resource amount to households have at least one elderly over 60.

**Type:** int

**Current value:** 60

---

### gov.states.dc.dhs.tanf.income.deductions.earned.percentage
**Label:** DC TANF earnings exclusion percent

DC excludes this share of earnings from TANF countable income, except for determining need for new applicants.

**Type:** float

**Current value:** 0.67

---

### gov.states.dc.dhs.tanf.income.deductions.earned.flat
**Label:** DC TANF flat earnings exclusion

DC excludes this amount of earnings from TANF countable income when determining need for new applicants.

**Type:** int

**Current value:** 160

---

### gov.states.dc.dhs.tanf.income.deductions.child_support
**Label:** DC TANF child support exclusion

DC excludes this amount of monthly child support when computing unearned income.

**Type:** int

**Current value:** 150

---

### gov.states.dc.dhs.snap.min_allotment.amount
**Label:** DC SNAP minimum allotment amount

DC provides the following monthly SNAP minimum allotment amount.

**Type:** int

**Current value:** 30

---

### gov.states.dc.dhs.snap.min_allotment.in_effect
**Label:** DC SNAP minimum allotment in effect

DC provides a separate SNAP minimum allotment amount if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.dc.tax.income.subtractions.disabled_exclusion.income_limit
**Label:** DC disabled exclusion income limit

DC allows an AGI subtraction for disabled persons who meet certain eligibility requirements and have household income below this limit.

**Type:** int

**Current value:** 100000

---

### gov.states.dc.tax.income.subtractions.disabled_exclusion.amount
**Label:** DC disabled exclusion amount

DC allows an AGI subtraction of this amount for disabled persons who meet certain eligibility requirements.

**Type:** int

**Current value:** 10000

---

### gov.states.dc.tax.income.additions.self_employment_loss.threshold
**Label:** DC AGI addition self-employment loss threshold

DC AGI excludes self-employment losses in excess of this threshold.

**Type:** int

**Current value:** 12000

---

### gov.states.dc.tax.income.deductions.itemized.phase_out.rate
**Label:** DC itemized deduction phase-out rate

DC phases out some itemized deductions at this rate on DC AGI above a threshold.

**Type:** float

**Current value:** 0.05

---

### gov.states.dc.tax.income.joint_separately_option
**Label:** Whether DC offers filing separate option to married-joint taxpayers

DC offers taxpayers who file married joint on federal return the option to file separately on DC return if this parameter is true.

**Type:** bool

**Current value:** True

---

### gov.states.dc.tax.income.snap.temporary_local_benefit.rate
**Label:** DC temporary local SNAP benefit rate

DC provides a temporary local SNAP benefit of this percentage of the maximum allotment.

**Type:** int

**Current value:** 0

---

### gov.states.dc.tax.income.credits.ptc.takeup
**Label:** DC property tax credit takeup rate

The share of eligible individuals who claim the DC property tax credit.

**Type:** float

**Current value:** 0.32

---

### gov.states.dc.tax.income.credits.ptc.rent_ratio
**Label:** DC property tax credit property tax to rent ratio

DC property tax credit assumes property taxes are this ratio to rent.

**Type:** float

**Current value:** 0.2

---

### gov.states.dc.tax.income.credits.ptc.min_elderly_age
**Label:** DC property tax minimum elderly age

DC property tax credit has a different credit rate for those this age or older.

**Type:** int

**Current value:** 70

---

### gov.states.dc.tax.income.credits.kccatc.max_age
**Label:** DC KCCATC maximum child age

DC keep child care affordable tax credit is for children this age or less.

**Type:** int

**Current value:** 3

---

### gov.states.dc.tax.income.credits.ctc.phase_out.increment
**Label:** DC Child Tax Credit phase-out increment

DC reduces the Child Tax Credit by a certain amount for each of this increment by which one's income exceeds the phase-out thresholds.

**Type:** int

**Current value:** 1000

---

### gov.states.dc.tax.income.credits.ctc.phase_out.amount
**Label:** DC Child Tax Credit phase-out amount

DC reduces the Child Tax Credit by this amount for each increment by which one's income exceeds the phase-out thresholds.

**Type:** int

**Current value:** 20

---

### gov.states.dc.tax.income.credits.ctc.amount
**Label:** DC Child Tax Credit amount

DC provides a Child Tax Credit of this amount per eligible child.

**Type:** int

**Current value:** 420

---

### gov.states.dc.tax.income.credits.ctc.child.child_cap
**Label:** DC Child Tax Credit child cap

DC limits the number of eligible children for the Child Tax Credit to this number.

**Type:** int

**Current value:** 3

---

### gov.states.dc.tax.income.credits.ctc.child.age_threshold
**Label:** DC Child Tax Credit child age threshold

DC provides a Child Tax Credit amount for children below this age.

**Type:** int

**Current value:** 6

---

### gov.states.dc.tax.income.credits.cdcc.match
**Label:** DC CDCC match rate

DC matches this share of the federal child/dependent care credit.

**Type:** float

**Current value:** 0.32

---

### gov.states.dc.tax.income.credits.eitc.with_children.match
**Label:** DC EITC match for filers with qualifying children

DC matches this percentage of the federal earned income tax credit for filers with qualifying children.

**Type:** float

**Current value:** 0.85

---

### gov.states.dc.tax.income.credits.eitc.without_children.phase_out.rate
**Label:** DC EITC phase-out rate for filers without qualifying children

DC phases out its EITC for filers without qualifying children at this rate for income above the threshold.

**Type:** float

**Current value:** 0.0848

---

### gov.states.dc.tax.income.credits.eitc.without_children.phase_out.start
**Label:** DC EITC phase-out threshold for filers without qualifying children

DC phases out its EITC for filers without qualifying children for income above this threshold.

**Type:** float

**Current value:** 23775.972791499233

---

### gov.states.md.tax.income.agi.subtractions.max_care_expense_year_offset
**Label:** Decoupled year offset for maximum CDCC expense cap

Decoupled year offset for maximum CDCC expense cap

**Type:** int

**Current value:** 0

---

### gov.states.md.tax.income.agi.subtractions.pension.min_age
**Label:** Maryland pension AGI subtraction minimum eligibility age

Maryland pension AGI subtraction minimum eligibility age

**Type:** int

**Current value:** 65

---

### gov.states.md.tax.income.agi.subtractions.pension.max_amount
**Label:** Maryland max pension AGI subtraction

Maryland provides the following maximum pension subtarction from adjusted gross income.

**Type:** int

**Current value:** 36200

---

### gov.states.md.tax.income.agi.subtractions.hundred_year.age_threshold
**Label:** Maryland hundred year subtraction age eligibility

Maryland limits the hundred year subtraction to individuals this age or older.

**Type:** int

**Current value:** 100

---

### gov.states.md.tax.income.agi.subtractions.hundred_year.amount
**Label:** Maryland hundred year subtraction amount

Maryland subtracts this amount from adjusted gross income under the hundred year subtraction.

**Type:** int

**Current value:** 100000

---

### gov.states.md.tax.income.agi.subtractions.max_two_income_subtraction
**Label:** MD max two-income AGI subtraction

Maryland maximum two-income AGI subtraction

**Type:** int

**Current value:** 1200

---

### gov.states.md.tax.income.deductions.standard.rate
**Label:** Maryland standard deduction as a percent of AGI

Maryland provides a standard deduction of this share of a filer's adjusted gross income.

**Type:** float

**Current value:** 0.15

---

### gov.states.md.tax.income.exemptions.blind
**Label:** Maryland income tax blind exemption

Maryland provides an exemption of this amount per blind head or spouse.

**Type:** int

**Current value:** 1000

---

### gov.states.md.tax.income.exemptions.aged.aged_dependent
**Label:** Maryland income tax aged dependent exemption

Maryland provides a tax exemption of this amount per aged dependent.

**Type:** int

**Current value:** 3200

---

### gov.states.md.tax.income.exemptions.aged.amount
**Label:** Maryland income tax aged exemption

Maryland provides a tax exemption of this amount per aged head or spouse.

**Type:** int

**Current value:** 1000

---

### gov.states.md.tax.income.exemptions.aged.age
**Label:** Maryland income tax aged exemption age threshold

Maryland provides an additional tax exemption to people of at least this age.

**Type:** int

**Current value:** 65

---

### gov.states.md.tax.income.credits.poverty_line.earned_income_share
**Label:** Maryland Poverty Line Credit rate

Maryland provides up to this share of earned income in its Poverty Line Credit.

**Type:** float

**Current value:** 0.05

---

### gov.states.md.tax.income.credits.ctc.agi_cap
**Label:** Maryland Child Tax Credit AGI cap

Maryland limits its Child Tax Credit to filers below this adjusted gross income.

**Type:** int

**Current value:** 15000

---

### gov.states.md.tax.income.credits.ctc.reduced_by_federal_credit
**Label:** Maryland CTC reduced by federal credit

Maryland reduces its child tax credit by the federal child tax credit amount when this is true.

**Type:** bool

**Current value:** False

---

### gov.states.md.tax.income.credits.ctc.amount
**Label:** Maryland Child Tax Credit amount per eligible child

Maryland's Child Tax Credit provides this amount to eligible children.

**Type:** int

**Current value:** 500

---

### gov.states.md.tax.income.credits.ctc.age_threshold.main
**Label:** Maryland Child Tax Credit main age limit

Maryland limits its Child Tax Credit to children below this age.

**Type:** int

**Current value:** 6

---

### gov.states.md.tax.income.credits.ctc.age_threshold.disabled
**Label:** Maryland Child Tax Credit disabled age limit

Maryland limits its Child Tax Credit to disabled children below this age.

**Type:** int

**Current value:** 17

---

### gov.states.md.tax.income.credits.cdcc.phase_out.percent
**Label:** Maryland CDCC phase-out percent

Maryland reduces its Child and Dependent Care Credit by this percentage for each increment of a filer's income above its phase-out start.

**Type:** float

**Current value:** 0.01

---

### gov.states.md.tax.income.credits.cdcc.percent
**Label:** Maryland percent of federal CDCC

Maryland matches up to this share of the federal Child and Dependent Care Credit.

**Type:** float

**Current value:** 0.32

---

### gov.states.md.tax.income.credits.senior_tax.age_eligibility
**Label:** Maryland Senior Tax Credit age eligibility

Maryland allows filers at or above this age to receive the senior tax credit.

**Type:** int

**Current value:** 65

---

### gov.states.md.tax.income.credits.senior_tax.amount.head_of_household
**Label:** Maryland Senior Tax Credit head of houshehold amount

Maryland provides this senior tax credit amount for head of household filers.

**Type:** int

**Current value:** 1750

---

### gov.states.md.tax.income.credits.senior_tax.amount.widow
**Label:** Maryland Senior Tax Credit widow(er) amount

Maryland provides this senior tax credit amount for widow(er) filers.

**Type:** int

**Current value:** 1750

---

### gov.states.md.tax.income.credits.senior_tax.amount.separate
**Label:** Maryland Senior Tax Credit separate amount

Maryland provides this senior tax credit amount for separate filers.

**Type:** int

**Current value:** 1000

---

### gov.states.md.tax.income.credits.senior_tax.amount.single
**Label:** Maryland Senior Tax Credit single amount

Maryland provides this senior tax credit amount for single filers.

**Type:** int

**Current value:** 1000

---

### gov.states.md.tax.income.credits.eitc.refundable.married_or_has_child.match
**Label:** Maryland refundable EITC match

Maryland matches this percent of the federal Earned Income Tax Credit as a refundable credit for filers who are not single and childless.

**Type:** float

**Current value:** 0.45

---

### gov.states.md.tax.income.credits.eitc.non_refundable.married_or_has_child.match
**Label:** Maryland non-refundable EITC match

Maryland matches this percent of the federal Earned Income Tax Credit for individuals with qualifying child or married couples filing jointly or separately with or without a qualifying child.

**Type:** float

**Current value:** 0.5

---

### gov.states.md.tax.income.credits.eitc.non_refundable.unmarried_childless.match
**Label:** Maryland childless EITC match

Maryland matches this percentage of the federal Earned Income Tax Credit to individuals without a qualifying child.

**Type:** int

**Current value:** 1

---

### gov.states.md.tax.income.credits.eitc.non_refundable.unmarried_childless.max_amount
**Label:** Maryland childless EITC maximum

Maryland provides up to this amount for its Earned Income Tax Credit to individuals without a qualifying child.

**Type:** float

**Current value:** inf

---

### gov.states.md.usda.snap.min_allotment.age_threshold
**Label:** Maryland SNAP age threshold for supplement minimum allotment

Maryland supplements the Supplemental Nutritional Assistant Program minimum allotment for households that include individuals this age or older.

**Type:** int

**Current value:** 62

---

### gov.states.md.usda.snap.min_allotment.amount
**Label:** Maryland SNAP minimum allotment amount

Maryland provides the following monthly SNAP minimum allotment amount.

**Type:** int

**Current value:** 40

---

### gov.states.md.usda.snap.min_allotment.in_effect
**Label:** Maryland SNAP minimum allotment in effect

Maryland provides a separate SNAP minimum allotment amount if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.md.tanf.income.deductions.earned.new
**Label:** Maryland TANF earnings exclusion percent for new enrollees

Maryland excludes this share of earnings from TANF countable earned income, for individuals not currently enrolled in TANF.

**Type:** float

**Current value:** 0.2

---

### gov.states.md.tanf.income.deductions.earned.not_self_employed
**Label:** Maryland TANF earnings exclusion percent for non-self-employed individuals

Maryland excludes this share of earnings from TANF countable earned income, for individuals without self employment income.

**Type:** float

**Current value:** 0.4

---

### gov.states.md.tanf.income.deductions.earned.self_employed
**Label:** Maryland TANF earnings exclusion percent for self-employed individuals

Maryland excludes this share of earnings from TANF countable earned income, for individuals with self employment income.

**Type:** float

**Current value:** 0.5

---

### gov.states.ks.tax.income.agi.subtractions.oasdi.agi_limit
**Label:** Kansas federal AGI limit for taxable social security AGI subtraction

Kansas limits its taxable OASDI subtraction to filers with AGI at or below this amount.

**Type:** float

**Current value:** inf

---

### gov.states.ks.tax.income.exemptions.consolidated.amount
**Label:** Kansas personal exemption consolidated amount

Kansas provides this exemption for each person in a filing unit, pre 2024.

**Type:** int

**Current value:** 2250

---

### gov.states.ks.tax.income.exemptions.disabled_veteran.in_effect
**Label:** Kansas additional exemptions for disabled veterans in effect

Kansas provides additional exemptions for disabled veterans if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.ks.tax.income.exemptions.disabled_veteran.base
**Label:** Kansas disabled veteran exemption amount

Kansas provides the following exemption amount for disabled veterans.

**Type:** int

**Current value:** 2250

---

### gov.states.ks.tax.income.exemptions.by_filing_status.dependent
**Label:** Kansas personal exemption by filing status dependent amount

Kansas provides this exemption amount for each dependent in a filing unit post 2024.

**Type:** int

**Current value:** 2320

---

### gov.states.ks.tax.income.exemptions.by_filing_status.in_effect
**Label:** Kansas person exemptions by filing status in effect

Kansas provides an updated personal exemption structure by filing status as well as a separate dependent exemption amount if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.ks.tax.income.exemptions.base
**Label:** Kansas personal exemption

Kansas provides the following exemption amount for each person in a filing unit.

**Type:** int

**Current value:** 2250

---

### gov.states.ks.tax.income.credits.eitc_fraction
**Label:** Kansas EITC match

Kansas matches this percentage of the federal EITC.

**Type:** float

**Current value:** 0.17

---

### gov.states.ks.tax.income.credits.cdcc_fraction
**Label:** Kansas CDCC match

Kansas matches this percentage of the federal Child and Dependent Care Credit.

**Type:** float

**Current value:** 0.5

---

### gov.states.ks.tax.income.credits.food_sales_tax.agi_limit
**Label:** Kansas food sales tax credit AGI limit

Kansas limits its food sales tax credit to filers with federal AGI below this amount.

**Type:** int

**Current value:** 30615

---

### gov.states.ks.tax.income.credits.food_sales_tax.child_age
**Label:** Kansas food sales tax credit adult age

Kansas considers people children for the purposes of the food sales tax credit if they are below this age.

**Type:** int

**Current value:** 18

---

### gov.states.ks.tax.income.credits.food_sales_tax.min_adult_age
**Label:** Kansas food sales tax credit adult age

Kansas limits its food sales tax credit to adults of this age and above.

**Type:** int

**Current value:** 55

---

### gov.states.ks.tax.income.credits.food_sales_tax.amount
**Label:** Kansas food sales tax credit amount

Kansas provides a food sales tax credit of this amount per qualifying exemption.

**Type:** int

**Current value:** 125

---

### gov.states.ne.tax.income.agi.subtractions.social_security.fraction
**Label:** fraction of taxable social security allowed as NE AGI subtraction when federal AGI is above threshold (fraction is 1.0 for others)

Fraction of taxable social security allowed as NE AGI subtraction when federal AGI is above threshold (fraction is 1.0 for others).

**Type:** int

**Current value:** 1

---

### gov.states.ne.tax.income.agi.subtractions.military_retirement.age_threshold
**Label:** Nebraska military retirement benefits age threshold

Nebraska limits the military retirement benefits to filers this age or older.

**Type:** int

**Current value:** 67

---

### gov.states.ne.tax.income.agi.subtractions.military_retirement.fraction
**Label:** Nebraska military retirement subtraction fraction

Nebraska subtracts this fraction of military retirement benefits from federal adjusted gross income.

**Type:** int

**Current value:** 1

---

### gov.states.ne.tax.income.deductions.standard.age_minimum
**Label:** Nebraska extra standard deduction age threshold

Nebraska limits its extra standard deduction to filers this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.ne.tax.income.exemptions.amount
**Label:** Nebraska per-person exemption amount

Nebraska per-person exemption amount

**Type:** float

**Current value:** 170.54220249750455

---

### gov.states.ne.tax.income.credits.ctc.refundable.age_threshold
**Label:** Nebraska refundable child tax credit age threshold

Nebraska limits the refundable child tax credit to children this age or younger.

**Type:** int

**Current value:** 5

---

### gov.states.ne.tax.income.credits.ctc.refundable.fpg_fraction
**Label:** Nebraska refundable child tax credit FPG limit

Nebraska limits the refundable child tax credit to filers with an total household income at or below this fraction of the federal poverty guideline.

**Type:** int

**Current value:** 1

---

### gov.states.ne.tax.income.credits.cdcc.refundable.match
**Label:** Nebraska refundable CDCC match

Nebraska matches this fraction of the federal child and dependent care credit as a refundable credit.

**Type:** int

**Current value:** 1

---

### gov.states.ne.tax.income.credits.cdcc.refundable.income_limit
**Label:** Nebraska CDCC refundability AGI limit

Nebraska provides the child and dependent care credit as a refundable credit to filers with federal adjusted gross income of this amount or less.

**Type:** int

**Current value:** 29000

---

### gov.states.ne.tax.income.credits.cdcc.refundable.reduction.increment
**Label:** Nebraska refundable CDCC reduction incrememnt

Nebraska reduces the refundable child and dependent tax credit match percentage for each of these increments of federal adjusted gross income exceeding the threshold.

**Type:** int

**Current value:** 1000

---

### gov.states.ne.tax.income.credits.cdcc.refundable.reduction.amount
**Label:** Nebraska refundable CDCC reduction amount

Nebraska reduces the refundable child and dependent tax credit match percentage by this amount for each increment of federal adjusted gross income exceeding the threshold.

**Type:** float

**Current value:** 0.1

---

### gov.states.ne.tax.income.credits.cdcc.refundable.reduction.start
**Label:** Nebraska refundable CDCC reduction start

Nebraska reduces the refundable child and dependent tax credit match percentage for filers with federal adjusted gross income above this amount.

**Type:** int

**Current value:** 22000

---

### gov.states.ne.tax.income.credits.cdcc.nonrefundable.fraction
**Label:** Nebraska nonrefundable CDCC match

Nebraska matches this fraction of the federal child and dependent care credit as a non-refundable credit.

**Type:** float

**Current value:** 0.25

---

### gov.states.ne.tax.income.credits.eitc.fraction
**Label:** Nebraska EITC match

Nebraska matches this fraction of the federal earned income tax credit.

**Type:** int

**Current value:** 1

---

### gov.states.ne.tax.income.credits.nonrefundable_adjust_limit
**Label:** Nebraska AGI adjustment limit

Nebraska limits the net adjusted gross income adjustments to this amount.

**Type:** int

**Current value:** 5000

---

### gov.states.ne.dhhs.child_care_subsidy.fpg_fraction.initial_eligibility
**Label:** Nebraska child care subsidy initial eligibility federal poverty guideline limit

Nebraska limits the child care subsidy to families with income at or below this fraction of the federal poverty guidelines for initial eligibility.

**Type:** float

**Current value:** 1.85

---

### gov.states.ne.dhhs.child_care_subsidy.fpg_fraction.fee_free_limit
**Label:** Nebraska child care subsidy federal poverty guideline limit threshold

Nebraska provides a fee-free child care subsidy to families with a income at or below this fraction of the federal poverty guidelines.

**Type:** int

**Current value:** 1

---

### gov.states.ne.dhhs.child_care_subsidy.rate
**Label:** Nebraska child care subsidy family fee rate

Nebraska obligates families participating in the child care subsidy program to pay childcare expenses of this fraction of income excess over federal poverty guidelines.

**Type:** float

**Current value:** 0.07

---

### gov.states.ne.dhhs.child_care_subsidy.age_threshold.special_needs
**Label:** Nebraska child care subsidy special needs age threshold

Nebraska limits the child care subsidy to children of this age or younger, requiring special needs care.

**Type:** int

**Current value:** 18

---

### gov.states.ne.dhhs.child_care_subsidy.age_threshold.base
**Label:** Nebraska child care subsidy base age threshold

Nebraska limits the child care subsidy to children of this age or younger, not requiring special needs care.

**Type:** int

**Current value:** 12

---

### gov.states.hi.tax.income.subtractions.military_pay.cap
**Label:** Hawaii military reserve or national guard duty pay exclusion cap

Hawaii caps the military reserve or Hawaii national guard duty pay exclusion at this amount.

**Type:** int

**Current value:** 7683

---

### gov.states.hi.tax.income.deductions.itemized.threshold.dependent
**Label:** Hawaii itemized deductions dependent threshold

Hawaii allows for itemized deductions for dependent filers with deductions above this amount.

**Type:** int

**Current value:** 500

---

### gov.states.hi.tax.income.alternative_tax.rate
**Label:** Hawaii alternative tax on capital gains rate

Hawaii taxes the excess of the eligible taxable income for the alternative capital gains over the total taxable income at this rate.

**Type:** float

**Current value:** 0.0725

---

### gov.states.hi.tax.income.alternative_tax.availability
**Label:** Hawaii alternative tax on capital gain availability

Hawaii allows for an alternative tax on capital gains calculation if this is true.

**Type:** bool

**Current value:** False

---

### gov.states.hi.tax.income.exemptions.disabled
**Label:** Hawaii disability exemption amount

Hawaii allows this exemption amount for each disabled head or spouse.

**Type:** int

**Current value:** 7000

---

### gov.states.hi.tax.income.exemptions.aged_threshold
**Label:** Hawaii aged exemption age threshold

Hawaii provides an additional exemption for filer heads and spouses this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.hi.tax.income.exemptions.base
**Label:** Hawaii exemption base amount

Hawaii provides this base exemption amount.

**Type:** int

**Current value:** 1144

---

### gov.states.hi.tax.income.credits.food_excise_tax.minor_child.support_proportion_threshold
**Label:** Hawaii Food/Excise Tax Credit minor child public agency support's proportion threshold

Hawaii allows for an additional food/excise credit amount for each minor child receiving more than this proportion of support from public agencies.

**Type:** float

**Current value:** 0.5

---

### gov.states.hi.tax.income.credits.food_excise_tax.minor_child.age_threshold
**Label:** Hawaii Food/Excise Tax Credit minor child age threshold

Hawaii extends an additional food/excise credit amount to filers with minor children below this age threshold.

**Type:** int

**Current value:** 18

---

### gov.states.hi.tax.income.credits.food_excise_tax.minor_child.amount
**Label:** Hawaii Food/Excise Tax Credit minor child amount

Hawaii provides this amount under the Food/Excise Tax Credit for each minor child receiving support from public agencies.

**Type:** int

**Current value:** 0

---

### gov.states.hi.tax.income.credits.food_excise_tax.minor_child.in_effect
**Label:** Hawaii Food/Excise Tax Credit minor child fixed amount in effect

Hawaii multiplies the number of minor children by a fixed amount, if this is true, under the Food/Excise Tax Credit.

**Type:** bool

**Current value:** False

---

### gov.states.hi.tax.income.credits.lihrtc.eligibility.agi_limit
**Label:** Hawaii low-income household renters credit AGI limit

Hawaii limits the tax credit for low-income household renters to filers with adjusted gross income below this amount.

**Type:** int

**Current value:** 30000

---

### gov.states.hi.tax.income.credits.lihrtc.eligibility.rent_threshold
**Label:** Hawaii tax credit for low-income household renters rent threshold

Hawaii limits the tax credit for low-income household renters to filers that paid more than this amount in rent.

**Type:** int

**Current value:** 1000

---

### gov.states.hi.tax.income.credits.lihrtc.amount
**Label:** Hawaii income tax credit for low-income household renters base amount

Hawaii extends this amount for each exemption under the income tax credit for low-income household renters.

**Type:** int

**Current value:** 50

---

### gov.states.hi.tax.income.credits.lihrtc.aged_age_threshold
**Label:** Hawaii low-income household renters credit age threshold

Hawaii counts filer heads and spouses as additional exemptions for the income tax credit for low-income household renters if they are this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.hi.tax.income.credits.eitc.match
**Label:** Hawaii EITC match rate

Hawaii matches this percent of the federal EITC.

**Type:** float

**Current value:** 0.4

---

### gov.states.de.tax.income.subtractions.exclusions.pension.military_retirement_exclusion_available
**Label:** Delaware military retirement exclusion available

Delaware allows for an exclusion of military retirement pay under the pension exclusion if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.de.tax.income.subtractions.exclusions.pension.cap.military
**Label:** Delaware military pension exclusion cap

Delaware caps the military pension income exclusion at this amount.

**Type:** int

**Current value:** 12500

---

### gov.states.de.tax.income.subtractions.exclusions.elderly_or_disabled.eligibility.age_threshold
**Label:** Delaware aged or disabled exclusion age threshold

Delaware qualifies filers above his age threshold to receive the aged or disabled exclusion.

**Type:** int

**Current value:** 60

---

### gov.states.de.tax.income.deductions.standard.additional.age_threshold
**Label:** Delaware additional aged deduction age eligibility

Delaware provides the aged deduction amount to filers at or above this age.

**Type:** int

**Current value:** 65

---

### gov.states.de.tax.income.deductions.standard.additional.amount
**Label:** Delaware aged deduction amount

Delaware provides this deduction amount for aged or blind filers.

**Type:** int

**Current value:** 2500

---

### gov.states.de.tax.income.credits.relief_rebate.amount
**Label:** Delaware relief rebate amount

Delaware provides a relief rebate of this amount to each adult in the household.

**Type:** int

**Current value:** 300

---

### gov.states.de.tax.income.credits.personal_credits.personal
**Label:** Delaware personal credits amount

Delaware provides this personal credit amount.

**Type:** int

**Current value:** 110

---

### gov.states.de.tax.income.credits.cdcc.match
**Label:** Delaware federal CDCC match

Delaware matches up to this share of the federal Child and Dependent Care Credit.

**Type:** float

**Current value:** 0.5

---

### gov.states.de.tax.income.credits.eitc.non_refundable
**Label:** Delaware non-refundable EITC match

Delaware matches this percent of the federal Earned Income Tax Credit as a non-refundable credit.

**Type:** float

**Current value:** 0.2

---

### gov.states.de.tax.income.credits.eitc.refundable
**Label:** Delaware refundable EITC match

Delaware matches this percent of the federal Earned Income Tax Credit as a refundable credit.

**Type:** float

**Current value:** 0.045

---

### gov.states.az.tax.income.subtractions.pension.public_pension_cap
**Label:** Arizona pension exclusion cap

Arizona caps the pension exclusion at this amount.

**Type:** int

**Current value:** 2500

---

### gov.states.az.tax.income.subtractions.capital_gains.rate
**Label:** Arizona long-term net capital gains subtraction rate

Arizona subtracts this fraction of long term capital gains from adjusted gross income.

**Type:** float

**Current value:** 0.25

---

### gov.states.az.tax.income.subtractions.military_retirement.max_amount
**Label:** Arizona military retirement subtraction max amount

Arizona caps the military retirement subtraction at this amount for each eligible individual.

**Type:** float

**Current value:** inf

---

### gov.states.az.tax.income.deductions.standard.increased.rate
**Label:** Arizona increased standard deduction for charitable contributions rate

Arizona increases the standard deduction by this fraction of charitable contributions that would have been allowed if the taxpayer elected to claim itemized deductions.

**Type:** float

**Current value:** 0.31

---

### gov.states.az.tax.income.exemptions.stillborn
**Label:** Arizona stillborn exemption amount

Arizona provides an exemption of this amount for each stillborn child.

**Type:** int

**Current value:** 2300

---

### gov.states.az.tax.income.exemptions.blind
**Label:** Arizona blind exemption amount

Arizona provides an exemption of this amount per blind filer or spouse.

**Type:** int

**Current value:** 1500

---

### gov.states.az.tax.income.exemptions.parent_grandparent.cost_rate
**Label:** Arizona parents and grandparents exemption cost rate

Arizona allows for the parent and grandparent exemptions if the filer paid care and support costs over this percentage of total costs.

**Type:** float

**Current value:** 0.5

---

### gov.states.az.tax.income.exemptions.parent_grandparent.min_age
**Label:** Arizona parents and grandparents exemption age threshold

Arizona extends the parents and grandparents exemption to filers this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.az.tax.income.exemptions.parent_grandparent.amount
**Label:** Arizona parents and grandparents exemption amount

Arizona provides an exemption of this amount per qualifying parent and grandparent.

**Type:** int

**Current value:** 10000

---

### gov.states.az.tax.income.credits.dependent_credit.reduction.percentage
**Label:** Arizona dependent tax credit reduction percentage

Arizona reduces the dependent tax credit amount by this percentage based on the federal adjusted gross income increments.

**Type:** float

**Current value:** 0.05

---

### gov.states.az.tax.income.credits.dependent_credit.reduction.increment
**Label:** Arizona dependent tax credit reduction increment

Arizona reduces the dependent tax credit amount in these increments of federal adjusted gross income.

**Type:** int

**Current value:** 1000

---

### gov.states.az.tax.income.credits.property_tax.age_threshold
**Label:** Arizona property tax credit age threshold

Arizona limits the property tax credit to filers of this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.az.tax.income.credits.increased_excise.max_amount
**Label:** Arizona increase excise tax credit max amount

Arizona allows for the following increase excise tax credit maximum amount.

**Type:** int

**Current value:** 100

---

### gov.states.az.tax.income.credits.increased_excise.amount
**Label:** Arizona increase excise tax credit amount

Arizona provides the following amount per personal or dependent exemption under the Increased Excise Tax Credit.

**Type:** int

**Current value:** 25

---

### gov.states.az.tax.income.credits.family_tax_credits.amount.per_person
**Label:** Arizona Family Income Tax Credit amount

Arizona provides the following family income tax credit amount per person.

**Type:** int

**Current value:** 40

---

### gov.states.az.tax.income.credits.family_tax_credits.income_limit.separate
**Label:** Arizona family tax credit separate maximum income

Arizona qualifies separate filers with income below this amount for the family tax credit.

**Type:** int

**Current value:** 10000

---

### gov.states.az.tax.income.credits.family_tax_credits.income_limit.single
**Label:** Arizona family tax credit single maximum income

Arizona qualifies single filers with income below this amount for the family tax credit.

**Type:** int

**Current value:** 10000

---

### gov.states.az.hhs.tanf.eligibility.age_threshold.student
**Label:** Arizona cash assistance student age threshold

Arizona limits the cash assistance to filers with student children below this age threshold.

**Type:** int

**Current value:** 19

---

### gov.states.az.hhs.tanf.eligibility.age_threshold.non_student
**Label:** Arizona cash assistance non-student age threshold

Arizona limits the cash assistance to filers with non-student children below this age threshold.

**Type:** int

**Current value:** 18

---

### gov.states.ny.otda.tanf.need_standard.additional
**Label:** New York TANF monthly income limit per additional person

New York limits its TANF program to households with up to this income level for people beyond size.

**Type:** int

**Current value:** 85

---

### gov.states.ny.otda.tanf.income.earned_income_deduction.percent
**Label:** New York TANF earned income deduction

New York excludes this percentage of earned income for the purposes of its TANF program.

**Type:** float

**Current value:** 0.5

---

### gov.states.ny.otda.tanf.income.earned_income_deduction.flat
**Label:** New York TANF flat earnings exclusion

New York excludes this amount of earned income for the purposes of its TANF program, after the percentage deduction.

**Type:** int

**Current value:** 150

---

### gov.states.ny.otda.tanf.eligibility.resources.lower_limit
**Label:** New York TANF resource limit for households without elderly people

New York limits its TANF eligibility to households with up to this amount of resources, if they have no elderly members.

**Type:** int

**Current value:** 2000

---

### gov.states.ny.otda.tanf.eligibility.resources.higher_resource_limit_age_threshold
**Label:** New York TANF asset limit elderly age

New York provide higher limit for amount of asset to households with family members over this age.

**Type:** int

**Current value:** 60

---

### gov.states.ny.otda.tanf.eligibility.resources.higher_limit
**Label:** New York TANF resource limit for households with elderly people

New York limits TANF to households with up to this resource amount if they have elderly members.

**Type:** int

**Current value:** 3000

---

### gov.states.ny.otda.tanf.grant_standard.additional
**Label:** New York TANF monthly income limit per additional person

New York limits its TANF grant standard to households with up to this income level for people beyond size.

**Type:** int

**Current value:** 85

---

### gov.states.ny.tax.income.college_tuition.cap
**Label:** New York allowable college tuition expenses cap

New York caps college tuition expenses at this amount per eligible student when calculating the credit and deduction.

**Type:** int

**Current value:** 10000

---

### gov.states.ny.tax.income.agi.subtractions.pension_exclusion.min_age
**Label:** New York pension exclusion minimum age

New York State residents over this age can make use of the NY State AGI exclusion for pensions and annuities.

**Type:** float

**Current value:** 59.5

---

### gov.states.ny.tax.income.agi.subtractions.pension_exclusion.cap
**Label:** New York pension exclusion cap

New York State residents can subtract this amount from pensions and annuities included in federal AGI from their NY State AGI.

**Type:** int

**Current value:** 20000

---

### gov.states.ny.tax.income.deductions.itemized.college_tuition.applicable_percentage
**Label:** New York college tuition deduction applicable percentage

New York provides an itemized deduction for this fraction of allowable college tuition expenses.

**Type:** int

**Current value:** 1

---

### gov.states.ny.tax.income.deductions.standard.dependent_elsewhere
**Label:** New York standard deduction for dependent filers

New York standard deduction for filers who can be claimed as a dependent elsewhere.

**Type:** int

**Current value:** 3100

---

### gov.states.ny.tax.income.supplemental.min_agi
**Label:** New York State supplemental tax minimum AGI

New York imposes the NY supplemental tax on filers with AGI over this amount.

**Type:** int

**Current value:** 107650

---

### gov.states.ny.tax.income.supplemental.phase_in_length
**Label:** New York State supplemental tax phase-in length

Each bracket of the New York supplemental tax phases in over this length.

**Type:** int

**Current value:** 50000

---

### gov.states.ny.tax.income.supplemental.in_effect
**Label:** New York supplemental tax availability

New York state provides a incremental benefit under the supplemental tax if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.ny.tax.income.exemptions.dependent
**Label:** New York dependent exemption amount

New York dependent exemption amount.

**Type:** int

**Current value:** 1000

---

### gov.states.ny.tax.income.credits.college_tuition.applicable_percentage
**Label:** New York college tuition credit applicable percentage

New York provides a credit for this fraction of allowable college tuition expenses, after applying the rate structure.

**Type:** int

**Current value:** 1

---

### gov.states.ny.tax.income.credits.solar_energy_systems_equipment.rate
**Label:** New York solar energy systems equipment credit rate

New York provides a credit for this fraction of total solar energy systems equipment expenditures.

**Type:** float

**Current value:** 0.25

---

### gov.states.ny.tax.income.credits.solar_energy_systems_equipment.cap
**Label:** New York solar energy systems equipment credit cap

New York caps the solar energy systems equipment credit at this amount.

**Type:** int

**Current value:** 5000

---

### gov.states.ny.tax.income.credits.real_property_tax.elderly_age
**Label:** New York real property tax credit elderly age

New York applies the maximum real property tax credit for the elderly at this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.ny.tax.income.credits.real_property_tax.rent_tax_equivalent
**Label:** New York real property tax rent equivalent

New York deems this percentage of rent as equivalent to property tax for the real property tax credit.

**Type:** float

**Current value:** 0.25

---

### gov.states.ny.tax.income.credits.real_property_tax.rate
**Label:** New York real property tax credit rate

New York credits this percentage of excess real property tax (or rent equivalent) from the New York State income tax as the real property tax credit.

**Type:** float

**Current value:** 0.5

---

### gov.states.ny.tax.income.credits.real_property_tax.max_agi
**Label:** New York real property tax credit maximum AGI

New York sets this maximum AGI for eligibility for the real property tax credit.

**Type:** int

**Current value:** 18000

---

### gov.states.ny.tax.income.credits.real_property_tax.max_rent
**Label:** New York real property tax maximum rent

New York disqualifies renters whose annual rent exceeds this value from receiving the real property tax credit.

**Type:** int

**Current value:** 5400

---

### gov.states.ny.tax.income.credits.real_property_tax.max_property_value
**Label:** New York real property tax credit maximum property value

New York disqualifies property owners who own property valued above this amount from receiving the real property tax credit.

**Type:** int

**Current value:** 85000

---

### gov.states.ny.tax.income.credits.ctc.amount.percent
**Label:** New York CTC share of federal credit

New York's Empire State Child Credit share of federal credit.

**Type:** float

**Current value:** 0.33

---

### gov.states.ny.tax.income.credits.ctc.amount.minimum
**Label:** New York CTC minimum amount

New York sets this minimum amount per child for its Empire State Child Credit.

**Type:** int

**Current value:** 100

---

### gov.states.ny.tax.income.credits.ctc.minimum_age
**Label:** NY CTC minimum age

New York provides the Empire State Child Credit for children this age or older.

**Type:** int

**Current value:** 0

---

### gov.states.ny.tax.income.credits.ctc.pre_tcja
**Label:** Use pre-TCJA parameters for the federal CTC

Whether the NY CTC uses pre-TCJA parameters to calculate the federal CTC.

**Type:** bool

**Current value:** True

---

### gov.states.ny.tax.income.credits.ctc.additional.min_credit_value
**Label:** New York additional Empire State Child Credit minimum credit

New York provides the additional Empire State Child Credit if the calculated credit value is at least this amount.

**Type:** int

**Current value:** 25

---

### gov.states.ny.tax.income.credits.cdcc.percentage.alternate.multiplier
**Label:** New York CDCC alternate maximum AGI

New York sets this minimum numerator for the alternate fraction for the CDCC.

**Type:** float

**Current value:** 0.1

---

### gov.states.ny.tax.income.credits.cdcc.percentage.alternate.max_agi
**Label:** New York CDCC alternate maximum AGI

New York filers with AGI under this amount use the alternate parameters.

**Type:** int

**Current value:** 40000

---

### gov.states.ny.tax.income.credits.cdcc.percentage.alternate.base_percentage
**Label:** New York CDCC alternate base percentage

New York sets this base percentage for the alternate fraction for the CDCC.

**Type:** float

**Current value:** 1.0

---

### gov.states.ny.tax.income.credits.cdcc.percentage.alternate.fraction.denominator
**Label:** New York CDCC alternate fraction denominator

New York sets this denominator for the alternate fraction for the CDCC.

**Type:** int

**Current value:** 15000

---

### gov.states.ny.tax.income.credits.cdcc.percentage.alternate.fraction.numerator.min
**Label:** New York CDCC alternate fraction numerator minimum

New York sets this minimum numerator for the alternate fraction for the CDCC.

**Type:** int

**Current value:** 15000

---

### gov.states.ny.tax.income.credits.cdcc.percentage.alternate.fraction.numerator.top
**Label:** New York CDCC alternate fraction numerator top

New York AGI is subtracted from this to determine the NY CDCC percentage under the alternate fraction.

**Type:** int

**Current value:** 40000

---

### gov.states.ny.tax.income.credits.cdcc.percentage.main.multiplier
**Label:** New York CDCC main maximum AGI

New York sets this minimum numerator for the main fraction for the CDCC.

**Type:** float

**Current value:** 0.8

---

### gov.states.ny.tax.income.credits.cdcc.percentage.main.base_percentage
**Label:** New York CDCC main base percentage

New York sets this base percentage for the main fraction for the CDCC.

**Type:** float

**Current value:** 0.2

---

### gov.states.ny.tax.income.credits.cdcc.percentage.main.fraction.denominator
**Label:** New York CDCC main fraction denominator

New York sets this denominator for the main fraction for the CDCC.

**Type:** int

**Current value:** 15000

---

### gov.states.ny.tax.income.credits.cdcc.percentage.main.fraction.numerator.min
**Label:** New York CDCC main fraction numerator minimum

New York sets this minimum numerator for the main fraction for the CDCC.

**Type:** int

**Current value:** 15000

---

### gov.states.ny.tax.income.credits.cdcc.percentage.main.fraction.numerator.top
**Label:** New York CDCC main fraction numerator top

New York AGI is subtracted from this to determine the NY CDCC percentage under the main fraction.

**Type:** int

**Current value:** 65000

---

### gov.states.ny.tax.income.credits.geothermal_energy_system.rate
**Label:** New York geothermal energy system equipment credit rate

New York provides a geothermal energy systems credit of this percentage of total solar geothermal systems equipment expenditures.

**Type:** float

**Current value:** 0.25

---

### gov.states.ny.tax.income.credits.geothermal_energy_system.cap
**Label:** New York geothermal energy system equipment credit cap

New York caps the geothermal energy system credit at this amount.

**Type:** int

**Current value:** 5000

---

### gov.states.ny.tax.income.credits.eitc.match
**Label:** New York EITC percent

New York matches this fraction of the federal Earned Income Tax Credit.

**Type:** float

**Current value:** 0.3

---

### gov.states.ny.tax.income.credits.eitc.supplemental_match
**Label:** New York supplemental EITC match

New York matches this fraction of the federal earned income tax credit in its supplemental EITC.

**Type:** int

**Current value:** 0

---

### gov.states.ny.nyserda.drive_clean.flat_rebate.msrp_threshold
**Label:** New York Drive Clean point-of-sale flat rebate MSRP threshold

New York provides a flat Drive Clean point-of-sale rebate for vehicles with base MSRP over this amount.

**Type:** int

**Current value:** 42000

---

### gov.states.ny.nyserda.drive_clean.flat_rebate.amount
**Label:** New York Drive Clean point-of-sale flat rebate MSRP amount

New York provides the following flat Drive Clean point-of-sale rebate vehicles with a base MSRP over a certain threshold.

**Type:** int

**Current value:** 500

---

### gov.states.id.tax.income.subtractions.aged_or_disabled.person_cap
**Label:** Idaho aged or disabled deduction maximum household members

Idaho limits the aged or disabled deduction to this number of people per filing unit.

**Type:** int

**Current value:** 3

---

### gov.states.id.tax.income.subtractions.aged_or_disabled.age_threshold
**Label:** Idaho development disabilities deduction age threshold

Idaho limits the aged or disabled deduction to filers this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.id.tax.income.subtractions.aged_or_disabled.support_fraction_threshold
**Label:** Idaho aged or disabled deduction support fraction threshold

Idaho limits its aged or disabled deduction to family members of filers for whom the filer pays more than this fraction of their care and support costs.

**Type:** float

**Current value:** 0.5

---

### gov.states.id.tax.income.subtractions.aged_or_disabled.amount
**Label:** Idaho aged or disabled deduction

Idaho subtracts this amount from adjusted gross income for each aged or disabled person in the taxpayer's household.

**Type:** int

**Current value:** 1000

---

### gov.states.id.tax.income.deductions.dependent_care_expenses.cap
**Label:** Idaho dependent care expense deduction cap amount

Idaho caps the household and dependent care expense deduction at the greater of the federal cap and this amount.

**Type:** int

**Current value:** 12000

---

### gov.states.id.tax.income.deductions.retirement_benefits.age_eligibility.main
**Label:** Idaho retirement benefit deduction age threshold

Idaho limits the retirement benefit deduction to filers this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.id.tax.income.deductions.retirement_benefits.age_eligibility.disabled
**Label:** Idaho retirement benefit deduction disabled age threshold

Idaho limits the retirement benefit deduction to disabled filers at or above this age threshold.

**Type:** int

**Current value:** 62

---

### gov.states.id.tax.income.deductions.capital_gains.percentage
**Label:** Idaho capital gains deduction percentage

Idaho allows filers to deduct this fraction of capital gains on qualified property sales.

**Type:** float

**Current value:** 0.6

---

### gov.states.id.tax.income.other_taxes.pbf.amount
**Label:** Idaho permanent building fund tax amount

Idaho levies a permanent building fund tax of this amount.

**Type:** int

**Current value:** 10

---

### gov.states.id.tax.income.credits.grocery.amount.base
**Label:** Idaho grocery credit amount

Idaho provides this amount under the grocery tax credit.

**Type:** int

**Current value:** 120

---

### gov.states.id.tax.income.credits.aged_or_disabled.person_cap
**Label:** Idaho aged or disabled credit maximum household members

Idaho limits the aged or disabled credit to this number of people per filing unit.

**Type:** int

**Current value:** 3

---

### gov.states.id.tax.income.credits.aged_or_disabled.age_threshold
**Label:** Idaho aged or disabled credit age threshold

Idaho limits the aged or disabled credit to filers this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.id.tax.income.credits.aged_or_disabled.support_fraction_threshold
**Label:** Idaho aged or disabled credit support fraction threshold

Idaho limits its aged or disabled credit to family members of filers for whom the filer pays more than this fraction of their care and support costs.

**Type:** float

**Current value:** 0.5

---

### gov.states.id.tax.income.credits.aged_or_disabled.amount
**Label:** Idaho aged or disabled credit

Idaho provides this credit for each aged or disabled person in the taxpayer's household.

**Type:** int

**Current value:** 100

---

### gov.states.id.tax.income.credits.ctc.amount
**Label:** Idaho child tax credit amount

Idaho provides this child tax credit amount for each qualifying child.

**Type:** int

**Current value:** 205

---

### gov.states.oh.tax.income.agi_threshold
**Label:** Ohio assigns minimum income threshold to pay individual income tax.

Ohio requires filers with this adjusted gross income or more to pay individual income tax.

**Type:** int

**Current value:** 26050

---

### gov.states.oh.tax.income.deductions.unreimbursed_medical_care_expenses.rate
**Label:** Ohio Unreimbursed Medical Care Expenses Deduction AGI threshold

Ohio deducts medical care expenses in excess of this fraction of federal adjusted gross income.

**Type:** float

**Current value:** 0.075

---

### gov.states.oh.tax.income.deductions.plan_529_contributions.cap
**Label:** Ohio 529 plan contribution deduction cap

Ohio caps the 529 plan contributions deduction to this amount.

**Type:** int

**Current value:** 4000

---

### gov.states.oh.tax.income.credits.retirement.pension_based.income_limit
**Label:** Ohio pension based retirement income credit retirement credit income limit

Ohio limits its pension based retirement income credit to filers with state adjusted gross income below this amount.

**Type:** int

**Current value:** 100000

---

### gov.states.oh.tax.income.credits.retirement.lump_sum.age_threshold
**Label:** Ohio lump sum retirement income credit age threshold

Ohio limits the lump sum retirement income credit to filers this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.oh.tax.income.credits.retirement.lump_sum.income_limit
**Label:** Ohio lump sum retirement income credit retirement credit income limit

Ohio limits its lump sum retirement income credit to filers with state adjusted gross income below this amount.

**Type:** int

**Current value:** 100000

---

### gov.states.oh.tax.income.credits.adoption.amount.max
**Label:** Ohio adoption credit maximum amount

Ohio issues the adoption credit of up to this maximum amount.

**Type:** int

**Current value:** 0

---

### gov.states.oh.tax.income.credits.adoption.amount.min
**Label:** Ohio adoption credit minimum amount

Ohio issues the adoption credit of this minimum amount.

**Type:** int

**Current value:** 0

---

### gov.states.oh.tax.income.credits.adoption.age_limit
**Label:** Ohio adoption credit child age limit

Ohio provides an adoption credit for children younger than this age.

**Type:** int

**Current value:** 18

---

### gov.states.oh.tax.income.credits.lump_sum_distribution.age_threshold
**Label:** Ohio Lump Sum Distribution Credit age threshold

Ohio limits the lump sum distribution credit to filers of this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.oh.tax.income.credits.lump_sum_distribution.income_limit
**Label:** Ohio lump sum distribution credit income limit

Ohio limits its lump sum distribution credit to filers with Ohio modified adjusted gross income below this amount.

**Type:** int

**Current value:** 100000

---

### gov.states.oh.tax.income.credits.lump_sum_distribution.base_amount
**Label:** Ohio lump sum distribution credit base amount

Ohio multiplies the filer's expected remaining life in years by the following amount when calculating the lump sum distribution credit.

**Type:** int

**Current value:** 50

---

### gov.states.oh.tax.income.credits.joint_filing.income_threshold
**Label:** Ohio joint filing credit income threshold

Ohio limits the joint filing credit to filers with head and spouse each having at least this adjusted gross income.

**Type:** int

**Current value:** 500

---

### gov.states.oh.tax.income.credits.joint_filing.cap
**Label:** Ohio joint filing credit cap

Ohio caps the joint filing credit at this amount.

**Type:** int

**Current value:** 650

---

### gov.states.oh.tax.income.credits.senior_citizen.age_threshold
**Label:** Ohio Senior Citizen Credit age threshold

Ohio provides the Senior Citizen Credit to filers at or above this age threshold.

**Type:** int

**Current value:** 65

---

### gov.states.oh.tax.income.credits.eitc.rate
**Label:** Ohio earned income credit rate

Ohio matches the federal earned income tax credit at this rate.

**Type:** float

**Current value:** 0.3

---

### gov.states.or.tax.income.deductions.standard.aged_or_blind.age
**Label:** Oregon standard deduction addition age threshold

Oregon provides a standard deduction addition at this age threshold.

**Type:** int

**Current value:** 65

---

### gov.states.or.tax.income.deductions.standard.claimable_as_dependent.earned_income_addition
**Label:** Oregon earned income addition if claimable as dependent

Oregon adds this to your earned income for you total standard deduction if you can be claimed as a dependent, up to the filing status maximum.

**Type:** int

**Current value:** 400

---

### gov.states.or.tax.income.deductions.standard.claimable_as_dependent.min
**Label:** Oregon minimum deduction if claimable as dependent

Oregon provides a minimum standard deduction of this amount for filers who are claimable as a dependent.

**Type:** float

**Current value:** 1357.820083578858

---

### gov.states.or.tax.income.credits.exemption.income_limit.disabled_child_dependent
**Label:** Oregon exemption credit income limit (disabled child dependent)

Oregon limits its disabled child exemption credit to filers with adjusted gross income below this threshold.

**Type:** int

**Current value:** 100000

---

### gov.states.or.tax.income.credits.exemption.income_limit.severely_disabled
**Label:** Oregon exemption credit income limit (severely disabled)

Oregon limits its severely disabled exemption credit to filers with adjusted gross income below this threshold.

**Type:** int

**Current value:** 100000

---

### gov.states.or.tax.income.credits.exemption.amount
**Label:** Oregon exemption amount

Oregon provides a nonrefundable tax credit of this amount per exemption.

**Type:** int

**Current value:** 236

---

### gov.states.or.tax.income.credits.wfhdc.age_range.young
**Label:** Oregon working family household and dependent care credit youngest qualifying individual young age threshold

Oregon assigns filers a percentage value when the youngest qualifying individual is below this young age threshold under the working family household and dependent care credit.

**Type:** int

**Current value:** 6

---

### gov.states.or.tax.income.credits.wfhdc.age_range.youngest
**Label:** Oregon working family household and dependent care credit youngest qualifying individual youngest age threshold

Oregon assigns filers a percentage value when the youngest qualifying individual is below this youngest age threshold under the working family household and dependent care credit.

**Type:** int

**Current value:** 3

---

### gov.states.or.tax.income.credits.wfhdc.age_range.oldest
**Label:** Oregon working family household and dependent care credit youngest qualifying individual oldest age threshold

Oregon assigns filers a percentage value when the youngest qualifying individual is below this oldest age threshold under the working family household and dependent care credit.

**Type:** int

**Current value:** 18

---

### gov.states.or.tax.income.credits.wfhdc.age_range.old
**Label:** Oregon working family household and dependent care credit youngest qualifying individual old age threshold

Oregon assigns filers a percentage value when the youngest qualifying individual is below this old age threshold under the working family household and dependent care credit.

**Type:** int

**Current value:** 13

---

### gov.states.or.tax.income.credits.wfhdc.fpg_limit
**Label:** Oregon working family household and dependent care credit federal poverty guidelines rate

Oregon limits the working family household and dependent care credit to filers with the greater of federal or state adjusted gross income below this percentage of the federal poverty guidelines.

**Type:** int

**Current value:** 3

---

### gov.states.or.tax.income.credits.wfhdc.child_age_limit
**Label:** Oregon working family household and dependent care credit child age threshold

Oregon qualifies children without disabilities for the working family household and dependent care credit at or below this age.

**Type:** int

**Current value:** 12

---

### gov.states.or.tax.income.credits.wfhdc.cap
**Label:** Oregon working family household and dependent care expense credit child and dependent care expense cap

Oregon caps the childcare expenses under the working family household and dependent care at this amount, for each dependent.

**Type:** int

**Current value:** 12000

---

### gov.states.or.tax.income.credits.wfhdc.min_tax_unit_size
**Label:** Oregon working family household and dependent care credit minimum household size

Oregon limits its working family household and dependent care credit to filers with at least this number of people.

**Type:** int

**Current value:** 2

---

### gov.states.or.tax.income.credits.retirement_income.percentage
**Label:** Oregon retirement income credit percentage

Oregon multplies the lesser of the retirement income base credit amount or the filers retirement income by the following percentage.

**Type:** float

**Current value:** 0.09

---

### gov.states.or.tax.income.credits.retirement_income.age_eligibility
**Label:** Oregon retirement income credit age eligiblity

Oregon qualifies filers for the retirement income credit at or above this age threshold.

**Type:** int

**Current value:** 62

---

### gov.states.or.tax.income.credits.ctc.ineligible_age
**Label:** Oregon Child Tax Credit ineligible age

Oregon provides this Child Tax Credit to children below this age.

**Type:** int

**Current value:** 6

---

### gov.states.or.tax.income.credits.ctc.child_limit
**Label:** Oregon Child Tax Credit child limit

Oregon caps its Child Tax Credit at this number of children per filer.

**Type:** int

**Current value:** 5

---

### gov.states.or.tax.income.credits.ctc.amount
**Label:** Oregon Child Tax Credit amount

Oregon provides this maximum Child Tax Credit per qualifying child.

**Type:** int

**Current value:** 1000

---

### gov.states.or.tax.income.credits.ctc.reduction.width
**Label:** Oregon Child Tax Credit phase-out width

Oregon reduces its Child Tax Credit over this income range exceeding the phase-out start.

**Type:** int

**Current value:** 5000

---

### gov.states.or.tax.income.credits.ctc.reduction.start
**Label:** Oregon Child Tax Credit phase-out start

Oregon reduces its Child Tax Credit for filers with Oregon adjusted gross income exceeding this amount.

**Type:** int

**Current value:** 25000

---

### gov.states.or.tax.income.credits.kicker.percent
**Label:** Oregon kicker rate

Oregon returns this portion of the filer's prior-year tax liability before credits via its kicker credit.

**Type:** float

**Current value:** 0.4428

---

### gov.states.or.tax.income.credits.eitc.old_child_age
**Label:** Oregon EITC young child age limit

Oregon defines young children as those up to this age for its Earned Income Tax Credit match.

**Type:** int

**Current value:** 3

---

### gov.states.or.tax.income.credits.eitc.match.no_young_child
**Label:** Oregon EITC match for filers with no young children

Oregon matches the federal Earned Income Tax Credit at this rate for filers with no young children.

**Type:** float

**Current value:** 0.09

---

### gov.states.or.tax.income.credits.eitc.match.has_young_child
**Label:** Oregon EITC match for filers with young children

Oregon matches the federal Earned Income Tax Credit at this rate for filers with young children.

**Type:** float

**Current value:** 0.12

---

### gov.states.or.fcc.lifeline.max_amount
**Label:** Oregon Lifeline maximum benefit

Oregon provides the following maximum Lifeline benefit amount.

**Type:** float

**Current value:** 15.25

---

### gov.states.or.fcc.lifeline.in_effect
**Label:** Oregon Lifeline maximum benefit in effect

Oregon provides a separate maximum Lifeline benefit amount if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.il.tax.income.exemption.dependent
**Label:** Illinois dependent exemption amount

Illinois provides the following exemption amount for each dependent.

**Type:** int

**Current value:** 2425

---

### gov.states.il.tax.income.exemption.aged_and_blind
**Label:** Illinois Senior & Blind Exemption

Illinois Senior & Blind Exemption Allowance

**Type:** int

**Current value:** 1000

---

### gov.states.il.tax.income.exemption.personal
**Label:** Illinois personal exemption amount

Illinois provides the following personal exemption allowance amount.

**Type:** int

**Current value:** 2875

---

### gov.states.il.tax.income.rate
**Label:** Illinois tax rate

Illinois Individual Income Tax Rates

**Type:** float

**Current value:** 0.0495

---

### gov.states.il.tax.income.credits.property_tax.rate
**Label:** Illinois Property Tax Credit Rate

Illinois provides a non-refundable credit for this fraction of property taxes.

**Type:** float

**Current value:** 0.05

---

### gov.states.il.tax.income.credits.ctc.amount
**Label:** Illinois Child Tax Credit amount

Illinois provides the following child tax credit amount for each individual child.

**Type:** int

**Current value:** 300

---

### gov.states.il.tax.income.credits.k12.rate
**Label:** Illinois K-12 Education Expense Credit Rate

Illinois provides a non-refundable credit for this fraction of K-12 education expenses.

**Type:** float

**Current value:** 0.25

---

### gov.states.il.tax.income.credits.k12.reduction
**Label:** Illinois K-12 Education Expense Credit Reduction

Illinois provides a non-refundable credit for a capped fraction of K-12 education expenses in excess of this amount.

**Type:** int

**Current value:** 250

---

### gov.states.il.tax.income.credits.k12.cap
**Label:** Illinois K-12 Education Expense Credit Cap

Illinois caps its K-12 Education Expense Credit at this amount.

**Type:** int

**Current value:** 750

---

### gov.states.il.tax.income.credits.eitc.match
**Label:** Illinois EITC match

Illinois matches this fraction of the federal Earned Income Tax Credit.

**Type:** float

**Current value:** 0.2

---

### gov.states.la.tax.income.deductions.federal_tax.availability
**Label:** Louisiana federal tax deduction availability

Louisiana allows for a federal tax deduction if this is true.

**Type:** bool

**Current value:** False

---

### gov.states.la.tax.income.deductions.itemized.excess_fraction
**Label:** Louisiana itemized deductions excess fraction

Louisiana subtracts this fraction of the excess of the either the federal itemized deductions or the medical expense deduction amount over the federal standard deduction from adjusted gross income.

**Type:** int

**Current value:** 1

---

### gov.states.la.tax.income.deductions.standard.applies
**Label:** Lousiana standard deduction applies

Louisiana applies a standard deduction and repeals personal exemptions, if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.la.tax.income.exempt_income.military_pay_exclusion.max_amount
**Label:** Louisiana military pay exclusion max amount

Louisiana allows for this maximum military pay exclusion amount.

**Type:** int

**Current value:** 50000

---

### gov.states.la.tax.income.exempt_income.reduction.in_effect
**Label:** Louisiana exempt adjusted gross income reduction in effect

Louisiana reduces the exempt adjusted gross income if this is true.

**Type:** bool

**Current value:** False

---

### gov.states.la.tax.income.exempt_income.disability.cap
**Label:** Louisiana disability income exemption cap

Louisiana caps the disability income exemption at this amount.

**Type:** int

**Current value:** 12000

---

### gov.states.la.tax.income.main.flat.applies
**Label:** Lousiana flat income tax rate applies

Louisiana applies a flat income tax rate if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.la.tax.income.main.flat.rate
**Label:** Louisiana flat income tax rate post 2024

Louisiana taxes income at this flat rate, post 2024.

**Type:** float

**Current value:** 0.03

---

### gov.states.la.tax.income.exemptions.blind
**Label:** Louisiana blind exemption amount

Louisiana reduces taxable income by this amount for each blind head or spouse.

**Type:** int

**Current value:** 1000

---

### gov.states.la.tax.income.exemptions.dependent
**Label:** Louisiana dependent exemption amount

Louisiana reduces taxable income by this amount for each dependent.

**Type:** int

**Current value:** 1000

---

### gov.states.la.tax.income.exemptions.widow
**Label:** Louisiana qualifying widow exemption amount

Louisiana reduces taxable income by this amount for each qualifying widow(er).

**Type:** int

**Current value:** 1000

---

### gov.states.la.tax.income.credits.school_readiness.age_threshold
**Label:** Louisiana school readiness tax credit child age threshold

Louisiana provides the school readiness tax credit to filers with children below this age threshold.

**Type:** int

**Current value:** 6

---

### gov.states.la.tax.income.credits.cdcc.non_refundable.upper_bracket_cap
**Label:** Louisiana non-refundable CDCC upper bracket cap

Louisiana limits its non-refundable child and dependent care credit to this maximum amount, for filers with income in the top bracket.

**Type:** int

**Current value:** 25

---

### gov.states.la.tax.income.credits.eitc.match
**Label:** Louisiana EITC match

Louisiana matches this percent of the federal EITC.

**Type:** float

**Current value:** 0.05

---

### gov.states.wi.tax.income.subtractions.childcare_expense.max_dependents
**Label:** Wisconsin maximum dependents for care expense AGI subtraction

Wisconsin recognizes this maximum number of dependents as eligible for care expense AGI subtraction.

**Type:** int

**Current value:** 2

---

### gov.states.wi.tax.income.subtractions.childcare_expense.max_amount
**Label:** Wisconsin maximum care expenses per dependent for AGI subtraction

Wisconsin subtracts from AGI this maximum of child and dependent care expenses per dependent.

**Type:** int

**Current value:** 3000

---

### gov.states.wi.tax.income.subtractions.unemployment_compensation.income_phase_out.rate
**Label:** Wisconsin income phase-out rate for unemployment compensation subtraction

Wisconsin uses this rate to phase-out income in calculation of unemployment compensation subtraction.

**Type:** float

**Current value:** 0.5

---

### gov.states.wi.tax.income.subtractions.retirement_income.min_age
**Label:** Wisconsin minimum age for retirement income subtraction

Wisconsin limits its retirement income subtraction to filers this age or older.

**Type:** int

**Current value:** 65

---

### gov.states.wi.tax.income.subtractions.retirement_income.max_amount
**Label:** Wisconsin maximum retirement income AGI subtraction per person

Wisconsin limits retirement income AGI subtraction to this maximum per person.

**Type:** int

**Current value:** 5000

---

### gov.states.wi.tax.income.subtractions.capital_gain.fraction
**Label:** Wisconsin fraction of capital gains subtracted from AGI

Wisconsin subtracts from AGI this fraction of long-term capital gains.

**Type:** float

**Current value:** 0.3

---

### gov.states.wi.tax.income.exemption.extra
**Label:** Wisconsin personal exemption additional amount

Wisconsin exemption includes this amount for each elderly taxpayer.

**Type:** int

**Current value:** 250

---

### gov.states.wi.tax.income.exemption.old_age
**Label:** Wisconsin personal exemption old age threshold

Wisconsin gives an extra exemption to head/spouse this age or more.

**Type:** int

**Current value:** 65

---

### gov.states.wi.tax.income.exemption.base
**Label:** Wisconsin personal exemption base amount

Wisconsin exemption includes this base amount.

**Type:** int

**Current value:** 700

---

### gov.states.wi.tax.income.credits.married_couple.max
**Label:** Wisconsin married couple credit cap

Wisconsin married couple credit is limited to this maximum.

**Type:** int

**Current value:** 480

---

### gov.states.wi.tax.income.credits.married_couple.rate
**Label:** Wisconsin married couple credit rate

Wisconsin married couple credit is calculated using this rate.

**Type:** float

**Current value:** 0.03

---

### gov.states.wi.tax.income.credits.childcare_expense.fraction
**Label:** Wisconsin CDCC fraction of federal CDCC

Wisconsin allows this faction of the federal child and dependent care credit as an AGI income subtraction.

**Type:** int

**Current value:** 1

---

### gov.states.wi.tax.income.credits.property_tax.max
**Label:** Wisconsin property tax credit limit

Wisconsin property tax credit is limited to this maximum.

**Type:** int

**Current value:** 300

---

### gov.states.wi.tax.income.credits.property_tax.rate
**Label:** Wisconsin property tax credit rate

Wisconsin propery tax credit is calculated using this rate.

**Type:** float

**Current value:** 0.12

---

### gov.states.wi.tax.income.credits.property_tax.rent_fraction
**Label:** Wisconsin property tax credit fraction of rent considered property tax

Wisconsin property tax credit considers property taxes to be this fraction of rent.

**Type:** float

**Current value:** 0.2

---

### gov.states.wi.tax.income.credits.earned_income.investment_income_limit
**Label:** Wisconsin EITC investment income limit

Wisconsin limits EITC eligibility to this investment income amount.

**Type:** int

**Current value:** 3800

---

### gov.states.wi.tax.income.credits.earned_income.apply_federal_investment_income_limit
**Label:** Wisconsin EITC apply federal investment income limit

Wisconsin applies the federal investment income limit for the earned income tax credit if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.wa.tax.income.in_effect
**Label:** Washington income tax rules in effect

Washington applies its income tax rules if this is true.

**Type:** bool

**Current value:** True

---

### gov.states.wa.tax.income.capital_gains.deductions.charitable.exemption
**Label:** Washington capital gains charitable contribution exemption

Washington capital gains charitable contribution exemption.

**Type:** int

**Current value:** 285000

---

### gov.states.wa.tax.income.capital_gains.deductions.charitable.cap
**Label:** Washington capital gains charitable contribution cap

Washington capital gains charitable contribution cap.

**Type:** int

**Current value:** 114000

---

### gov.states.wa.tax.income.capital_gains.deductions.standard
**Label:** Washington capital gains standard deduction

Washington capital gains standard deduction.

**Type:** int

**Current value:** 285000

---

### gov.states.wa.tax.income.capital_gains.rate
**Label:** Washington capital gains tax rate

Washington capital gains tax rate.

**Type:** float

**Current value:** 0.07

---

### gov.states.wa.tax.income.credits.working_families_tax_credit.min_amount
**Label:** Washington Working Families Tax Credit minimum amount

Washington Working Families Tax Credit minimum amount for those with nonzero benefit.

**Type:** int

**Current value:** 50

---

### gov.states.wa.dshs.tanf.eligibility.resources.limit
**Label:** Washington TANF resource limit

Washington limits its TANF eligibility to household withs up to this resource amount.

**Type:** int

**Current value:** 6000

---

### gov.bls.cpi.c_cpi_u
**Label:** Chained CPI-U

The Bureau of Labor Statistics estimates this Chained Consumer Price Index for All Urban Consumers.

**Type:** float

**Current value:** 173.7

---

### gov.bls.cpi.cpi_u
**Label:** CPI-U

The Bureau of Labor Statistics estimates this Consumer Price Index for All Urban Consumers.

**Type:** float

**Current value:** 311.2

---

### gov.bls.cpi.cpi_w
**Label:** CPI-W

The Bureau of Labor Statistics estimates this Consumer Price Index for Urban Wage Earners and Clerical Workers.

**Type:** float

**Current value:** 312.639

---

### gov.dol.minimum_wage
**Label:** Federal minimum wage

The US requires each employer to pay each of its employees the following federal minimum wage rate.

**Type:** float

**Current value:** 7.25

---

### gov.irs.vita.eligibility.income_limit
**Label:** VITA Program Income Limit

The IRS extends the Volunteer Income Tax Assistance (VITA) program to filers with gross income at or below this amount.

**Type:** int

**Current value:** 64000

---

### gov.irs.self_employment.social_security_rate
**Label:** Self-employment Social Security tax rate

Self-employment Social Security tax rate

**Type:** float

**Current value:** 0.124

---

### gov.irs.self_employment.net_earnings_exemption
**Label:** Self-employment net earnings exemption

Minimum self-employment net earnings to have to pay self-employment tax.

**Type:** int

**Current value:** 400

---

### gov.irs.self_employment.medicare_rate
**Label:** Self-employment Medicare tax rate

Self-employment Medicare tax rate.

**Type:** float

**Current value:** 0.029

---

### gov.irs.deductions.qbi.max.w2_wages.alt_rate
**Label:** Alternative QBID rate on W-2 wages

Alternative QBID cap rate on pass-through business W-2 wages paid. QBID is capped at this fraction of W-2 wages paid by the pass-through business plus some fraction of business property if pre-QBID taxable income is above the QBID thresholds and the alternative cap is higher than the main wage-only cap.

**Type:** float

**Current value:** 0.25

---

### gov.irs.deductions.qbi.max.w2_wages.rate
**Label:** QBID rate on W-2 wages

QBID cap rate on pass-through business W-2 wages paid.

**Type:** float

**Current value:** 0.5

---

### gov.irs.deductions.qbi.max.rate
**Label:** Qualified business income deduction rate

Pass-through qualified business income deduction rate.

**Type:** float

**Current value:** 0.2

---

### gov.irs.deductions.qbi.max.business_property.rate
**Label:** Alternative QBID rate on business property

Alternative QBID cap rate on pass-through business property owned

**Type:** float

**Current value:** 0.025

---

### gov.irs.deductions.itemized.limitation.agi_rate
**Label:** The US itemized deductions limitation fraction

The US limits itemized deductions to this fraction of the excess of adjusted gross income over the applicable amount.

**Type:** float

**Current value:** inf

---

### gov.irs.deductions.itemized.limitation.itemized_deduction_rate
**Label:** The US itemized deductions limitation rate

The US limits itemized deductions to this fraction of the amount of the itemized deductions otherwise allowable for such taxable year.

**Type:** float

**Current value:** inf

---

### gov.irs.deductions.itemized.casualty.floor
**Label:** Casualty expense deduction floor

Floor (as a fraction of AGI) for deductible casualty loss.

**Type:** float

**Current value:** 0.1

---

### gov.irs.deductions.itemized.casualty.active
**Label:** Casualty expense deduction active

Casualty expense deduction is active.

**Type:** bool

**Current value:** False

---

### gov.irs.deductions.itemized.reduction.rate.excess_agi
**Label:** IRS itemized deductions reduced adjusted gross income rate

IRS multiplies the excess of adjusted gross income over the applicable amount by this rate.

**Type:** int

**Current value:** 0

---

### gov.irs.deductions.itemized.reduction.rate.base
**Label:** IRS reduced itemized deductions base rate

IRS multiplies the excess of the total and reduced itemized deductions by this rate.

**Type:** int

**Current value:** 0

---

### gov.irs.deductions.itemized.medical.floor
**Label:** Medical expense deduction floor

Medical expenses over this percentage of AGI are deductible from taxable income.

**Type:** float

**Current value:** 0.075

---

### gov.irs.deductions.itemized.charity.ceiling.all
**Label:** Charitable deduction limit

Ceiling (as a decimal fraction of AGI) for all charitable contribution deductions.

**Type:** float

**Current value:** 0.6

---

### gov.irs.deductions.itemized.charity.ceiling.non_cash
**Label:** Non-cash charitable deduction limit

Ceiling (as a fraction of AGI) for noncash charitable contribution deductions.

**Type:** float

**Current value:** 0.3

---

### gov.irs.deductions.standard.aged_or_blind.age_threshold
**Label:** Aged standard deduction age

Age at which a person qualifies for the aged standard deduction addition

**Type:** int

**Current value:** 65

---

### gov.irs.income.amt.capital_gains.capital_gain_excess_tax_rate
**Label:** Alternative Minimum Tax capital gain excess tax rate

The IRS multiplies the taxable excess capital gain by this rate.

**Type:** float

**Current value:** 0.25

---

### gov.irs.income.exemption.traditional_distribution.age_threshold
**Label:** Traditional IRA distribution age threshold

The exemption for traditional IRA distributions is limited to filers above this age.

**Type:** float

**Current value:** 59.5

---

### gov.irs.income.disability_income_exclusion.amount
**Label:** Disability income reduction amount

IRS reduces the excludable disability income by this amount.

**Type:** int

**Current value:** 15000

---

### gov.irs.income.disability_income_exclusion.cap
**Label:** Disability exclusion cap

IRS caps the disability exclusion to this amount per disabled person.

**Type:** int

**Current value:** 5200

---

### gov.irs.gross_income.retirement_contributions.limit.401k
**Label:** 401(k) contribution limit

The US limits annual 401(k) contributions to this amount.

**Type:** int

**Current value:** 23000

---

### gov.irs.gross_income.retirement_contributions.limit.ira
**Label:** IRA contribution limit

The US limits annual IRA contributions to this amount.

**Type:** int

**Current value:** 7000

---

### gov.irs.gross_income.retirement_contributions.catch_up.limit.401k
**Label:** 401(k) catch-up amount

IRS limits the 401(k) contributions catch-up to this amount.

**Type:** int

**Current value:** 7500

---

### gov.irs.gross_income.retirement_contributions.catch_up.limit.ira
**Label:** IRA catch-up amount

The US allows for catch-up IRA contributions of this amount.

**Type:** int

**Current value:** 1000

---

### gov.irs.gross_income.retirement_contributions.catch_up.age_threshold
**Label:** Pension contribution catch-up age threshold

The US limits catch-up pension contributions to individuals this age or older.

**Type:** int

**Current value:** 50

---

### gov.irs.social_security.taxability.rate.additional
**Label:** Social Security benefit additional taxable rate

The IRS includes this additional portion of Social Security benefits in taxable income for filers whose modified adjusted gross income exceeds the additional threshold.

**Type:** float

**Current value:** 0.85

---

### gov.irs.social_security.taxability.rate.base
**Label:** Social Security benefit base taxable rate

The IRS includes this portion of Social Security benefits in taxable income for filers whose modified adjusted gross income is between the base and additional thresholds.

**Type:** float

**Current value:** 0.5

---

### gov.irs.social_security.taxability.threshold.adjusted_base.separate_cohabitating
**Label:** Social Security taxability additional threshold for cohabitating separate filers

The IRS taxes Social Security benefits at the additional rate, for cohabitating married filing separately filers with modified adjusted gross income above this threshold.

**Type:** int

**Current value:** 0

---

### gov.irs.social_security.taxability.threshold.base.separate_cohabitating
**Label:** Social Security taxability base threshold for cohabitating separate filers

The IRS taxes Social Security benefits at the base rate, for cohabitating married filing separately filers with modified adjusted gross income between this threshold and the respective additional threshold.

**Type:** int

**Current value:** 0

---

### gov.irs.tce.age_threshold
**Label:** TCE age threshold

IRS provides free tax assistance under the Tax Counseling for the Elderly (TCE) grant program for individuals this age or older.

**Type:** int

**Current value:** 60

---

### gov.irs.dependent.ineligible_age.student
**Label:** IRS student dependent age limit

The IRS permits filers to claim dependents who are full-time students if they are younger than this age at the end of the year.

**Type:** int

**Current value:** 24

---

### gov.irs.dependent.ineligible_age.non_student
**Label:** IRS non-student dependent age limit

The IRS permits filers to claim dependents who are non-students if they are younger than this age at the end of the year.

**Type:** int

**Current value:** 19

---

### gov.irs.uprating
**Label:** Uprating index for IRS tax parameters

Uprating index for IRS tax parameters (December 1999 = 100%).

**Type:** float

**Current value:** 172.57558333333336

---

### gov.irs.capital_gains.unrecaptured_s_1250_rate
**Label:** Tax rate on net un-recaptured Section 1250 gains.

Tax rate on net un-recaptured Section 1250 gains.

**Type:** float

**Current value:** 0.25

---

### gov.irs.capital_gains.other_cg_rate
**Label:** Other capital gain tax rate

Capital gains tax rate applying to special categories of gains (including small business stock and collectibles).

**Type:** float

**Current value:** 0.28

---

### gov.irs.payroll.medicare.rate.employee
**Label:** Employee-side Medicare tax rate

Employee-side Medicare FICA rate.

**Type:** float

**Current value:** 0.0145

---

### gov.irs.payroll.medicare.rate.employer
**Label:** Employer-side Medicare tax rate

Employer-side Medicare FICA rate.

**Type:** float

**Current value:** 0.0145

---

### gov.irs.payroll.medicare.additional.rate
**Label:** Additional Medicare Tax rate

Additional Medicare Tax rate (same for wages and self-employment earnings).

**Type:** float

**Current value:** 0.009

---

### gov.irs.payroll.social_security.rate.employee
**Label:** Employee-side Social Security tax rate

Employee-side Social Security payroll tax rate

**Type:** float

**Current value:** 0.062

---

### gov.irs.payroll.social_security.rate.employer
**Label:** Employer-side Social Security tax rate

Employer-side Social Security payroll tax rate

**Type:** float

**Current value:** 0.062

---

### gov.irs.payroll.social_security.cap
**Label:** Social Security earnings cap

Individual earnings below this amount are subjected to Social Security (OASDI) payroll tax. This parameter is indexed by the rate of growth in average wages, not by the price inflation rate.

**Type:** int

**Current value:** 176100

---

### gov.irs.credits.recovery_rebate_credit.caa.phase_out.rate
**Label:** CAA Recovery Rebate Credit phase-out rate

Phase-out rate for the CAA Recovery Rebate Credit.

**Type:** int

**Current value:** 0

---

### gov.irs.credits.recovery_rebate_credit.caa.max.adult
**Label:** CAA Recovery Rebate Credit maximum amount (non-dependent adults)

Maximum credit per non-dependent adult.

**Type:** int

**Current value:** 0

---

### gov.irs.credits.recovery_rebate_credit.caa.max.child
**Label:** CAA Recovery Rebate Credit maximum amount (dependent children)

Maximum credit per dependent child.

**Type:** int

**Current value:** 0

---

### gov.irs.credits.recovery_rebate_credit.arpa.max.dependent
**Label:** ARPA Recovery Rebate Credit maximum amount (dependent children)

Maximum credit per dependent.

**Type:** int

**Current value:** 0

---

### gov.irs.credits.recovery_rebate_credit.arpa.max.adult
**Label:** ARPA Recovery Rebate Credit maximum amount (non-dependent adults)

Maximum credit per non-dependent adult.

**Type:** int

**Current value:** 0

---

### gov.irs.credits.recovery_rebate_credit.cares.phase_out.rate
**Label:** CARES Recovery Rebate Credit phase-out rate

Phase-out rate for the CARES Recovery Rebate Credit.

**Type:** int

**Current value:** 0

---

### gov.irs.credits.recovery_rebate_credit.cares.max.adult
**Label:** CARES Recovery Rebate Credit maximum amount (non-dependent adults)

Maximum credit per non-dependent adult.

**Type:** int

**Current value:** 0

---

### gov.irs.credits.recovery_rebate_credit.cares.max.child
**Label:** CARES Recovery Rebate Credit maximum amount (dependent children)

Maximum credit per dependent child.

**Type:** int

**Current value:** 0

---

### gov.irs.credits.retirement_saving.age_threshold
**Label:** Retirement Savings Contributions Credit (Saver's Credit) age threshold

The IRS limits the saver's credit to taxpayers at or over to following age.

**Type:** int

**Current value:** 18

---

### gov.irs.credits.retirement_saving.contributions_cap
**Label:** Saver's Credit contributions cap

The IRS caps the qualifying contributions at the following amount under the saver's credit.

**Type:** int

**Current value:** 2000

---

### gov.irs.credits.estate.base
**Label:** Estate tax credit base exclusion amount

The IRS provides this base exclusion amount under the estate tax credit.

**Type:** int

**Current value:** 13990000

---

### gov.irs.credits.education.phase_out.start.single
**Label:** Education credits phase-out start (single filers)

Phase-out start for both the American Opportunity Credit and Lifetime Learning Credit on AGI.

**Type:** int

**Current value:** 80000

---

### gov.irs.credits.education.phase_out.start.joint
**Label:** Education credits phase-out start (joint filers)

Phase-out start for both the American Opportunity Credit and Lifetime Learning Credit on AGI.

**Type:** int

**Current value:** 160000

---

### gov.irs.credits.education.phase_out.length.single
**Label:** Education credits phase-out length (single filers)

Length of the phase-out for both the American Opportunity Credit and Lifetime Learning Credit on AGI (when excess income totals this amount, the credit is reduced to zero).

**Type:** int

**Current value:** 10000

---

### gov.irs.credits.education.phase_out.length.joint
**Label:** Education credits phase-out length (joint filers)

Length of the phase-out for both the American Opportunity Credit and Lifetime Learning Credit on AGI (when excess income totals this amount, the credit is reduced to zero).

**Type:** int

**Current value:** 20000

---

### gov.irs.credits.education.american_opportunity_credit.abolition
**Label:** American Opportunity Credit abolition

**Type:** bool

**Current value:** False

---

### gov.irs.credits.education.american_opportunity_credit.refundability
**Label:** American Opportunity Credit refundable percentage

Percentage of the American Opportunity Credit which is refundable.

**Type:** float

**Current value:** 0.4

---

### gov.irs.credits.education.lifetime_learning_credit.expense_limit
**Label:** Lifetime Learning Credit maximum expense

Maximum expenses for relief under the Lifetime Learning Credit

**Type:** int

**Current value:** 10000

---

### gov.irs.credits.education.lifetime_learning_credit.abolition
**Label:** Abolish the Lifetime Learning Credit

**Type:** bool

**Current value:** False

---

### gov.irs.credits.energy_efficient_home_improvement.rates.improvements
**Label:** Energy efficient home improvement credit rate on improvements

The IRS provides an energy efficient home improvement tax credit for this share of qualified energy efficiency improvements.

**Type:** float

**Current value:** 0.3

---

### gov.irs.credits.energy_efficient_home_improvement.rates.home_energy_audit
**Label:** Energy efficient home improvement credit rate on home energy audits

The IRS provides an energy efficient home improvement tax credit for this share of home energy audit expenditures.

**Type:** float

**Current value:** 0.3

---

### gov.irs.credits.energy_efficient_home_improvement.rates.property
**Label:** Energy efficient home improvement credit rate on property

The IRS provides an energy efficient home improvement tax credit for this share of residential energy property expenditures.

**Type:** float

**Current value:** 0.3

---

### gov.irs.credits.energy_efficient_home_improvement.cap.annual.energy_efficient_building_property
**Label:** Energy efficient home improvement credit cap on energy-efficient building property

The IRS caps energy efficient home improvement credits on energy efficient building property at this amount per year.

**Type:** int

**Current value:** 600

---

### gov.irs.credits.energy_efficient_home_improvement.cap.annual.total
**Label:** Energy efficient home improvement credit total cap

The IRS caps energy efficient total home improvement credits at this amount per year (the cap on heat pumps, heat pump water heaters, and biomass stoves and boilers supersedes this cap).

**Type:** int

**Current value:** 1200

---

### gov.irs.credits.energy_efficient_home_improvement.cap.annual.energy_efficient_central_air_conditioner
**Label:** Energy efficient home improvement credit cap on energy-efficient central air conditioners

The IRS caps energy efficient home improvement credits on energy efficient central air conditioners at this amount per year.

**Type:** float

**Current value:** inf

---

### gov.irs.credits.energy_efficient_home_improvement.cap.annual.heat_pump_heat_pump_water_heater_biomass_stove_boiler
**Label:** Energy efficient home improvement credit cap on heat pumps, heat pump water heaters, and biomass stoves and boilers

The IRS caps energy efficient home improvement credits on heat pumps, heat pump water heaters, and biomass stoves and boilers at this amount per year.

**Type:** int

**Current value:** 2000

---

### gov.irs.credits.energy_efficient_home_improvement.cap.annual.home_energy_audit
**Label:** Energy efficient home improvement credit cap on home energy audits

The IRS caps energy efficient home improvement credits on home energy audits at this amount per year.

**Type:** int

**Current value:** 150

---

### gov.irs.credits.energy_efficient_home_improvement.cap.annual.roof
**Label:** Energy efficient home improvement credit cap on roofs

The IRS caps energy efficient home improvement credits on roofs and roof material at this amount per year.

**Type:** float

**Current value:** inf

---

### gov.irs.credits.energy_efficient_home_improvement.cap.annual.qualified_furnace_or_hot_water_boiler
**Label:** Energy efficient home improvement credit cap on qualified furnaces or boilers

The IRS caps energy efficient home improvement credits on qualified natural gas, propane, or oil furnaces or hot water boilers at this amount per year.

**Type:** float

**Current value:** inf

---

### gov.irs.credits.energy_efficient_home_improvement.cap.annual.door
**Label:** Energy efficient home improvement credit cap on exterior doors

The IRS caps energy efficient home improvement credits on exterior doors at this amount per year.

**Type:** int

**Current value:** 500

---

### gov.irs.credits.energy_efficient_home_improvement.cap.annual.insulation_material
**Label:** Energy efficient home improvement credit cap on energy efficient insulation material

The IRS caps energy efficient home improvement credits on energy efficient insulation material at this amount per year.

**Type:** float

**Current value:** inf

---

### gov.irs.credits.energy_efficient_home_improvement.cap.annual.advanced_main_air_circulating_fan
**Label:** Energy efficient home improvement credit cap on advanced main air circulating fans

The IRS caps energy efficient home improvement credits on advance main air circulating fans at this amount per year.

**Type:** float

**Current value:** inf

---

### gov.irs.credits.energy_efficient_home_improvement.cap.annual.window
**Label:** Energy efficient home improvement credit cap on windows and skylights

The IRS caps energy efficient home improvement credits on energy efficient windows and skylights at this amount per year.

**Type:** int

**Current value:** 600

---

### gov.irs.credits.energy_efficient_home_improvement.cap.lifetime.total
**Label:** Energy efficient home improvement credit lifetime limit

The IRS caps lifetime energy efficient home improvement credits at this amount.

**Type:** float

**Current value:** inf

---

### gov.irs.credits.energy_efficient_home_improvement.cap.lifetime.window
**Label:** Energy efficient home improvement credit lifetime window limit

The IRS caps lifetime energy efficient home improvement credits on windows at this amount.

**Type:** float

**Current value:** inf

---

### gov.irs.credits.energy_efficient_home_improvement.in_effect
**Label:** Energy efficient home improvement tax credit in effect

The IRS provides the energy efficient home improvement tax credit when this is true.

**Type:** bool

**Current value:** True

---

### gov.irs.credits.clean_vehicle.new.critical_minerals.amount
**Label:** Credit for clean vehicles meeting the critical mineral requirement.

The IRS provides a credit of this amount to filers purchasing new clean vehicles meeting the critical mineral requirement.

**Type:** int

**Current value:** 3750

---

### gov.irs.credits.clean_vehicle.new.critical_minerals.threshold
**Label:** Share of clean vehicle battery critical minerals made in North America to qualify for credit

The IRS limits the new clean vehicle tax credit to vehicles with at least this share of battery critical minerals (by value) extracted or processed in a country with which the United States has a free trade agreement in effect, or recycled in North America.

**Type:** float

**Current value:** 0.6

---

### gov.irs.credits.clean_vehicle.new.eligibility.min_kwh
**Label:** Minimum kWh of battery capacity for new clean vehicle to be eligible for credit

The IRS limits the new clean vehicle credit to vehicles with at least this battery capacity, in kilowatt hours.

**Type:** int

**Current value:** 4

---

### gov.irs.credits.clean_vehicle.new.base_amount
**Label:** New clean vehicle credit base amount

The IRS sets the new clean vehicle credit at this base amount.

**Type:** int

**Current value:** 0

---

### gov.irs.credits.clean_vehicle.new.capacity_bonus.max
**Label:** New clean vehicle credit maximum amount for capacity bonus

The IRS caps its new clean vehicle credit capacity bonus at this amount.

**Type:** int

**Current value:** 0

---

### gov.irs.credits.clean_vehicle.new.capacity_bonus.amount
**Label:** New clean vehicle credit amount per excess kilowatt-hour

The IRS enhances its new clean vehicle credit with capacity bonus of this amount per kilowatt-hour in excess of the threshold.

**Type:** int

**Current value:** 0

---

### gov.irs.credits.clean_vehicle.new.capacity_bonus.kwh_threshold
**Label:** New clean vehicle credit kilowatt-hour threshold for battery capacity bonus

The IRS provides a capacity bonus for its new clean vehicle credit to filers purchasing vehicles with at least this battery capacity, in kilowatt hours.

**Type:** int

**Current value:** 5

---

### gov.irs.credits.clean_vehicle.new.battery_components.amount
**Label:** Credit for clean vehicles meeting the battery components requirement

The IRS provides a credit of this amount for filers purchasing new clean vehicles meeting the battery components requirement.

**Type:** int

**Current value:** 3750

---

### gov.irs.credits.clean_vehicle.new.battery_components.threshold
**Label:** Share of clean vehicle battery components made in North America to qualify for credit

The IRS limits its clean vehicle credit battery component amount to filers purchasing vehicles with this share of battery components (by value) made in North America.

**Type:** float

**Current value:** 0.6

---

### gov.irs.credits.clean_vehicle.used.amount.percent_of_sale_price
**Label:** Used clean vehicle credit as a percent of sale price

The IRS provides a tax credit for up to this percentage of a used clean vehicle's purchase price.

**Type:** float

**Current value:** 0.3

---

### gov.irs.credits.clean_vehicle.used.amount.max
**Label:** Maximum amount of used clean vehicle credit

The IRS caps the used clean vehicle credit at this amount.

**Type:** int

**Current value:** 4000

---

### gov.irs.credits.clean_vehicle.used.eligibility.sale_price_limit
**Label:** Sale price limit for used clean vehicle credit

The IRS limits the used clean vehicle credit to vehicle purchases below this threshold.

**Type:** int

**Current value:** 25000

---

### gov.irs.credits.residential_clean_energy.applicable_percentage
**Label:** Residential Clean Energy Credit applicable percentage

The IRS provides a tax credit for this share of qualifying residential clean energy expenditures.

**Type:** float

**Current value:** 0.3

---

### gov.irs.credits.residential_clean_energy.fuel_cell_cap_per_kw
**Label:** Residential Clean Energy Credit fuel cell cap per kilowatt

The IRS caps the tax credit for fuel cell property expenditures at this amount per kilowatt.

**Type:** int

**Current value:** 1000

---

### gov.irs.credits.ctc.refundable.individual_max
**Label:** Child tax credit refundable maximum amount

Maximum refundable amount of the CTC for qualifying children.

**Type:** int

**Current value:** 1700

---

### gov.irs.credits.ctc.refundable.phase_in.rate
**Label:** CTC refundable phase-in rate

Additional Child Tax Credit rate

**Type:** float

**Current value:** 0.15

---

### gov.irs.credits.ctc.refundable.phase_in.min_children_for_ss_taxes_minus_eitc
**Label:** Minimum children to consider Social Security taxes minus EITC in refundable CTC

Minimum number of qualifying children to increase the refundable Child Tax Credit by Social Security taxes minus the Earned Income Tax Credit.

**Type:** int

**Current value:** 3

---

### gov.irs.credits.ctc.refundable.phase_in.threshold
**Label:** CTC refundable phase-in threshold

Additional Child Tax Credit income threshold

**Type:** int

**Current value:** 2500

---

### gov.irs.credits.ctc.refundable.fully_refundable
**Label:** Fully refundable CTC

The IRS makes the Child Tax Credit fully refundable if this is true.

**Type:** bool

**Current value:** False

---

### gov.irs.credits.ctc.amount.adult_dependent
**Label:** Child tax credit for adult dependents

Maximum value of the CTC for adult dependents.

**Type:** int

**Current value:** 500

---

### gov.irs.credits.ctc.amount.arpa_expansion_cap_percent_of_threshold_diff
**Label:** ARPA CTC expansion cap as percent of threshold difference

The IRS caps the American Rescue Plan Act Child Tax Credit expansion by this percentage of the difference in phase-out thresholds between base and ARPA.

**Type:** float

**Current value:** 0.05

---

### gov.irs.credits.ctc.phase_out.increment
**Label:** CTC phase-out increment (ARPA)

The IRS reduces the American Rescue Plan Act Child Tax Credit expansion by a certain amount for each of this increment by which one's income exceeds the phase-out thresholds.

**Type:** int

**Current value:** 1000

---

### gov.irs.credits.ctc.phase_out.arpa.increment
**Label:** CTC phase-out increment

The IRS reduces the Child Tax Credit by a certain amount for each of this increment by which one's income exceeds the phase-out thresholds.

**Type:** int

**Current value:** 1000

---

### gov.irs.credits.ctc.phase_out.arpa.amount
**Label:** CTC phase-out amount (ARPA)

The IRS reduces the American Rescue Plan Act Child Tax Credit expansion by this amount for each increment by which one's income exceeds the phase-out thresholds.

**Type:** int

**Current value:** 50

---

### gov.irs.credits.ctc.phase_out.arpa.in_effect
**Label:** CTC ARPA phase-out in effect

The IRS adds a second phase-out when this is in effect.

**Type:** bool

**Current value:** False

---

### gov.irs.credits.ctc.phase_out.amount
**Label:** CTC phase-out amount

The IRS reduces the Child Tax Credit by this amount for each increment by which one's income exceeds the phase-out thresholds.

**Type:** int

**Current value:** 50

---

### gov.irs.credits.cdcc.max
**Label:** Maximum care expenses per dependent for CDCC.

Maximum child and dependent care expenses per dependent.

**Type:** int

**Current value:** 3000

---

### gov.irs.credits.cdcc.phase_out.second_start
**Label:** CDCC second phase-out start

Child & dependent care credit second phase-out start.

**Type:** float

**Current value:** inf

---

### gov.irs.credits.cdcc.phase_out.max
**Label:** CDCC maximum rate

Child and dependent care credit maximum percentage rate.

**Type:** float

**Current value:** 0.35

---

### gov.irs.credits.cdcc.phase_out.increment
**Label:** CDCC phase-out increment

Child and dependent care credit phase-out increment. Income after the phase-out start(s) reduce the CDCC applicable percentage by the rate for each full or partial increment.

**Type:** int

**Current value:** 2000

---

### gov.irs.credits.cdcc.phase_out.rate
**Label:** CDCC phase-out rate

Child and dependent care credit phase-out percentage rate. This is the reduction to the applicable percentage for each full or partial increment beyond which AGI exceeds the phase-out start(s).

**Type:** float

**Current value:** 0.01

---

### gov.irs.credits.cdcc.phase_out.min
**Label:** CDCC minimum rate

Child and dependent care credit phase-out percentage rate floor. The first phase-out does not reduce the childcare credit rate below this percentage.

**Type:** float

**Current value:** 0.2

---

### gov.irs.credits.cdcc.phase_out.start
**Label:** CDCC phase-out start

Child & dependent care credit phase-out AGI start.

**Type:** int

**Current value:** 15000

---

### gov.irs.credits.cdcc.eligibility.child_age
**Label:** CDCC dependent child maximum age

The age under which a child qualifies as a dependent for the CDCC.

**Type:** int

**Current value:** 13

---

### gov.irs.credits.cdcc.eligibility.max
**Label:** CDCC maximum dependents

Maximum number of dependents qualifiable for CDCC.

**Type:** int

**Current value:** 2

---

### gov.irs.credits.eitc.phase_out.joint_bonus[0].amount
**Label:** EITC phase-out start joint filer bonus (no children)

**Type:** int

**Current value:** 7110

---

### gov.irs.credits.eitc.phase_out.joint_bonus[1].amount
**Label:** EITC phase-out start joint filer bonus (with children)

**Type:** int

**Current value:** 7120

---

### gov.irs.credits.eitc.phase_out.max_investment_income
**Label:** EITC maximum investment income

Maximum investment income for EITC.

**Type:** int

**Current value:** 11950

---

### gov.irs.credits.eitc.eligibility.separate_filer
**Label:** EITC separate filers eligible

The US makes married filing separate filers eligible for the EITC when this is true.

**Type:** bool

**Current value:** True

---

### gov.irs.credits.eitc.eligibility.age.max
**Label:** EITC maximum childless age

The US limits EITC eligibility for filers without children to those below this age.

**Type:** int

**Current value:** 64

---

### gov.irs.credits.eitc.eligibility.age.min
**Label:** EITC minimum non-student childless age

The US limits EITC eligibility for non-student filers without children to those this age or older.

**Type:** int

**Current value:** 25

---

### gov.irs.credits.eitc.eligibility.age.min_student
**Label:** EITC minimum childless student age

The US limits EITC eligibility for students without children to those this age or older.

**Type:** int

**Current value:** 25

---

### gov.hhs.head_start.early_head_start.age_limit
**Label:** Early Head Start children age limit

The Administration for Children and Families limits the Early Head Start participants to children below this age limit.

**Type:** int

**Current value:** 3

---

### gov.hhs.medicare.eligibility.min_months_receiving_social_security_disability
**Label:** Minimum number of months of receiving social security disability for Medicare eligibility

Minimum number of months of receiving social security disability for Medicare eligibility.

**Type:** int

**Current value:** 24

---

### gov.hhs.medicare.eligibility.min_age
**Label:** Minimum age for age-based Medicare eligibility

Minimum age for age-based Medicare eligibility.

**Type:** int

**Current value:** 65

---

### gov.hhs.tanf.cash.eligibility.age_limit.student
**Label:** TANF minor child student age limit

The Temporary Assistance for Needy Families (TANF) program defines one of the qualifying criteria of a minor child as an individual who has not yet reached this age and is a full-time student in a secondary school (or an equivalent level of vocational or technical training).

**Type:** int

**Current value:** 19

---

### gov.hhs.tanf.cash.eligibility.age_limit.non_student
**Label:** TANF minor child non student age limit

The Temporary Assistance for Needy Families (TANF) program defines one of the qualifying criteria of a minor child as an individual who has not yet reached this age.

**Type:** int

**Current value:** 18

---

### gov.hhs.tanf.abolish_tanf
**Label:** Abolish TANF

Abolish TANF cash payments.

**Type:** bool

**Current value:** False

---

### gov.hhs.uprating
**Label:** Poverty line uprating

The US indexes the federal poverty guidelines according to this schedule, annually updating based on CPI-U in the calendar year.

**Type:** float

**Current value:** 312.6

---

### gov.hud.abolition
**Label:** Housing subsidy abolition

HUD stops providing housing subsidies when this is toggled.

**Type:** bool

**Current value:** False

---

### gov.hud.adjusted_income.deductions.elderly_disabled.amount
**Label:** HUD elderly or disabled deduction

HUD adjusted income elderly or disabled deduction

**Type:** int

**Current value:** 400

---

### gov.hud.adjusted_income.deductions.moop.threshold
**Label:** HUD medical expense deduction income threshold

Percent of annual income beyond which medical expenses are deducted from HUD adjusted income.

**Type:** float

**Current value:** 0.03

---

### gov.hud.adjusted_income.deductions.dependent.amount
**Label:** HUD dependent deduction

HUD adjusted income dependent deduction

**Type:** int

**Current value:** 480

---

### gov.hud.total_tenant_payment.income_share
**Label:** TTP Income Share

HUD total tenant payment share, monthly income

**Type:** float

**Current value:** 0.1

---

### gov.hud.total_tenant_payment.adjusted_income_share
**Label:** Total tenant payment adjusted income share

HUD total tenant payment as a share of adjusted monthly income

**Type:** float

**Current value:** 0.3

---

### gov.hud.elderly_age_threshold
**Label:** HUD elderly age threshold

HUD applies special rules to people this age or older.

**Type:** int

**Current value:** 62

---

