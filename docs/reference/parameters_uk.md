# UK parameters

This page shows a list of available parameters for reforms for the UK model.

We exclude from this list:

* Some parameters without documentation (we're a large, fast-growing model maintained by a small team- we're working on it!)
* Abolition parameters, which mirror each household property and allow the user to set the value of the property to zero (these take the format `gov.abolitions.variable_name`) because these roughly triple the size of this list and are repetitive.
### calibration.uprating.equity_prices
**Label:** Equity prices

Equity prices (OBR forecast).

**Type:** int

**Current value:** 4291

---

### calibration.programs.fuel_duty.revenue
**Label:** Fuel duty revenues

Fuel duty revenues.

**Type:** int

**Current value:** 26621382708

---

### calibration.programs.capital_gains.total
**Label:** Total capital gains

Total capital gains by individuals.

**Type:** int

**Current value:** 79881000000

---

### calibration.programs.capital_gains.tax
**Label:** Capital Gains Tax revenue

Capital gains tax revenue.

**Type:** int

**Current value:** 16200000000

---

### household.wealth.financial_assets
**Label:** Financial assets

Financial assets of households.

**Type:** int

**Current value:** 7300000000000

---

### household.consumption.fuel.prices.diesel
**Label:** Price of diesel per litre

Average price of diesel per litre.

**Type:** float

**Current value:** 1.52

---

### household.consumption.fuel.prices.petrol
**Label:** Price of unleaded petrol per litre

Average price of unleaded petrol per litre, including fuel duty.

**Type:** float

**Current value:** 1.44

---

### household.poverty.absolute_poverty_threshold_bhc
**Label:** Absolute poverty threshold, before housing costs

Absolute poverty threshold for equivalised household net income, before housing costs

**Type:** float

**Current value:** 367.36108108108107

---

### household.poverty.absolute_poverty_threshold_ahc
**Label:** Absolute poverty threshold, after housing costs

Absolute poverty threshold for equivalised household net income, after housing costs.

**Type:** float

**Current value:** 314.75567567567566

---

### gov.indices.private_rent_index
**Label:** Private rental prices index

Index of private rental prices across the UK.

**Type:** float

**Current value:** 128.5577828397874

---

### gov.ons.rpi
**Label:** RPI

Retail Price Index (RPI) is a measure of inflation published by the Office for National Statistics.

**Type:** float

**Current value:** 377.5

---

### gov.social_security_scotland.pawhp.amount.lower
**Label:** PAWHP lower amount

**Type:** float

**Current value:** 205.04825538233115

---

### gov.social_security_scotland.pawhp.amount.higher
**Label:** PAWHP lower amount

**Type:** float

**Current value:** 307.5723830734967

---

### gov.social_security_scotland.pawhp.amount.base
**Label:** PAWHP base payment

Amount paid to non-benefit-claiming pensioners for the PAWHP.

**Type:** int

**Current value:** 100

---

### gov.social_security_scotland.pawhp.eligibility.state_pension_age_requirement
**Label:** PAWHP State Pension Age requirement

Whether individuals must be State Pension Age to qualify for the PAWHP.

**Type:** bool

**Current value:** True

---

### gov.social_security_scotland.pawhp.eligibility.require_benefits
**Label:** PAWHP means-tested benefits requirement

Whether receipt of means-tested benefits is required to qualify for the Winter Fuel Payment.

**Type:** bool

**Current value:** True

---

### gov.social_security_scotland.pawhp.eligibility.higher_age_requirement
**Label:** Winter Fuel Payment higher amount age requirement

Age requirement to qualify for the higher PAWHP.

**Type:** int

**Current value:** 80

---

### gov.ofgem.energy_price_guarantee
**Label:** Energy price guarantee

The capped default tariff energy price level for Ofgem's central household (2,900kWh per annum in electricity consumption, 12,000kWh per annum for gas). The Energy Price Cap subsidy reduces household bills to this level.

**Type:** int

**Current value:** 3000

---

### gov.ofgem.energy_price_cap
**Label:** Ofgem energy price level

The default tariff energy price for Ofgem's central household (2,900kWh per annum in electricity consumption, 12,000kWh per annum for gas). The Energy Price Cap subsidy reduces household energy bills by the difference between this amount and the subsity target parameter level.

**Type:** int

**Current value:** 2389

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

### gov.simulation.labor_supply_responses.substitution_elasticity
**Label:** Substitution elasticity of labor supply

Percent change in labor supply given a 1% change in the effective marginal wage. This applies only to employment income.

**Type:** int

**Current value:** 0

---

### gov.simulation.labor_supply_responses.income_elasticity
**Label:** Income elasticity of labor supply

Percent change in labor supply given a 1% change in disposable income. This applies only to employment income.

**Type:** int

**Current value:** 0

---

### gov.simulation.marginal_tax_rate_adults
**Label:** Number of adults to simulate a marginal tax rate for

Number of adults to simulate a marginal tax rate for, in each household.

**Type:** int

**Current value:** 2

---

### gov.simulation.capital_gains_responses.elasticity
**Label:** capital gains elasticity

Elasticity of capital gains with respect to the capital gains marginal tax rate.

**Type:** int

**Current value:** 0

---

### gov.simulation.private_school_vat.private_school_vat_basis
**Label:** private school tuition VAT basis

Effective percentage of private school tuition subject to VAT

**Type:** float

**Current value:** 0.75

---

### gov.simulation.private_school_vat.private_school_factor
**Label:** student polulation adjustment factor

student polulation adjustment factor, tested by Vahid

**Type:** float

**Current value:** 0.85

---

### gov.simulation.private_school_vat.private_school_fees
**Label:** mean annual private school fee

Mean annual private school fee

**Type:** float

**Current value:** 17210.75043630017

---

### gov.revenue_scotland.lbtt.residential.additional_residence_surcharge
**Label:** LBTT fixed rate increase for secondary residences

Increase in percentage rates for non-primary residence purchases.

**Type:** float

**Current value:** 0.06

---

### gov.benefit_uprating_cpi
**Label:** Benefit uprating index

Most recent September CPIH index value, updated for each uprating occurrence (2005=100)

**Type:** float

**Current value:** 153.44444444444443

---

### gov.contrib.conservatives.pensioner_personal_allowance
**Label:** personal allowance for pensioners

Personal Allowance for pensioners.

**Type:** int

**Current value:** 12570

---

### gov.contrib.conservatives.cb_hitc_household
**Label:** household-based High Income Tax Charge

Child Benefit HITC assesses the joint income of a household to determine the amount of Child Benefit that is repayable.

**Type:** bool

**Current value:** False

---

### gov.contrib.cps.marriage_tax_reforms.expanded_ma.remove_income_condition
**Label:** Remove MA high-income restrictions

Allow higher and additional rate taxpayers to claim the Marriage Allowance.

**Type:** bool

**Current value:** False

---

### gov.contrib.cps.marriage_tax_reforms.expanded_ma.max_child_age
**Label:** Expanded MA child age condition

Only expand the Marriage Allowance for couples with a child under this age (zero does not limit by child age).

**Type:** int

**Current value:** 0

---

### gov.contrib.cps.marriage_tax_reforms.expanded_ma.ma_rate
**Label:** Expanded Marriage Allowance rate

Marriage Allowance maximum rate for eligible couples.

**Type:** float

**Current value:** 0.1

---

### gov.contrib.cps.marriage_tax_reforms.marriage_neutral_it.neutralise_income_tax
**Label:** Marriage-neutral Income Tax

Allow couples to split their taxable income equally for Income Tax.

**Type:** bool

**Current value:** False

---

### gov.contrib.cps.marriage_tax_reforms.marriage_neutral_it.max_child_age
**Label:** Expanded MA child age condition

Only marriage-neutralise Income Tax for couples with a child under this age (zero does not limit by child age).

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.interactions.include_in_taxable_income
**Label:** Include basic income in taxable income

Include basic income as earned income in benefit means tests.

**Type:** bool

**Current value:** False

---

### gov.contrib.ubi_center.basic_income.interactions.withdraw_cb
**Label:** Withdraw Child Benefit from basic income recipients

Withdraw Child Benefit payments from basic income recipients.

**Type:** bool

**Current value:** False

---

### gov.contrib.ubi_center.basic_income.interactions.include_in_means_tests
**Label:** Include basic income in means tests

Include basic income as earned income in benefit means tests.

**Type:** bool

**Current value:** False

---

### gov.contrib.ubi_center.basic_income.amount.adult_age
**Label:** Adult basic income threshold

Age at which a person stops receiving the child basic income and begins receiving the adult basic income.

**Type:** int

**Current value:** 18

---

### gov.contrib.ubi_center.basic_income.amount.by_age.child
**Label:** Child basic income

Basic income payment to children.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.amount.by_age.working_age
**Label:** Working-age basic income

Basic income payment to working-age adults.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.amount.by_age.senior
**Label:** Senior basic income

Basic income payment to seniors (individuals over State Pension Age).

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.amount.child_min_age
**Label:** Child basic income minimum threshold

Minimum age for children to receive the child basic income.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.amount.flat
**Label:** Basic income

Flat per-person basic income amount.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.phase_out.individual.rate
**Label:** Basic income individual phase-out rate

Percentage of income over the phase-out threshold which is deducted from basic income payments.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.phase_out.individual.threshold
**Label:** Basic income individual phase-out threshold

Threshold for taxable income at which basic income is reduced.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.phase_out.household.rate
**Label:** Basic income household phase-out rate

Rate at which any remaining basic income (after individual phase-outs) is reduced over the household income threshold.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.phase_out.household.threshold
**Label:** Basic income household phase-out threshold

Threshold for household taxable income, after which any remaining basic income (after individual phase-outs) is reduced.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.wealth_tax[0].threshold
**Label:** First wealth tax threshold

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.wealth_tax[0].rate
**Label:** First wealth tax rate

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.wealth_tax[1].threshold
**Label:** Second wealth tax threshold

**Type:** int

**Current value:** 100000000

---

### gov.contrib.ubi_center.wealth_tax[1].rate
**Label:** Second wealth tax rate

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.wealth_tax[2].threshold
**Label:** Third wealth tax threshold

**Type:** int

**Current value:** 1000000000

---

### gov.contrib.ubi_center.wealth_tax[2].rate
**Label:** Third wealth tax rate

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.carbon_tax.consumer_incidence
**Label:** Carbon tax consumer incidence

Proportion of corporate carbon taxes which is passed on to consumers in the form of higher prices (as opposed to shareholders in the form of reduced profitability).

**Type:** float

**Current value:** 1.0

---

### gov.contrib.ubi_center.carbon_tax.rate
**Label:** Carbon tax

Price per tonne of carbon emissions

**Type:** float

**Current value:** 0.0

---

### gov.contrib.ubi_center.land_value_tax.rate
**Label:** Land value tax

Tax rate on the unimproved value of land

**Type:** float

**Current value:** 0.0

---

### gov.contrib.ubi_center.land_value_tax.household_rate
**Label:** Land value tax (households)

Tax rate on the unimproved value of land owned by households

**Type:** float

**Current value:** 0.0

---

### gov.contrib.ubi_center.land_value_tax.corporate_rate
**Label:** Land value tax (corporations)

Tax rate on the unimproved value of land owned by corporations

**Type:** float

**Current value:** 0.0

---

### gov.contrib.freeze_pension_credit
**Label:** Freeze Pension Credit

Freeze Pension Credit payments. Set all Pension Credit payments to what they are under baseline policy.

**Type:** bool

**Current value:** False

---

### gov.contrib.abolish_council_tax
**Label:** Abolish Council Tax

Abolish council tax payments (and council tax benefit).

**Type:** bool

**Current value:** False

---

### gov.contrib.labour.private_school_vat
**Label:** private school VAT rate

VAT rate applied to private schools.

**Type:** int

**Current value:** 0

---

### gov.contrib.benefit_uprating.non_sp
**Label:** Non-State Pension benefit uprating

Increase all non-State Pension benefits by this amount (this multiplies the end value, not the maximum amount).

**Type:** int

**Current value:** 0

---

### gov.contrib.benefit_uprating.all
**Label:** Benefit uprating

Increase all benefit values by this percentage.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.economy.energy_bills
**Label:** Change to energy spending

Raise energy spending by this percentage.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.economy.gdp_per_capita
**Label:** Change to GDP per capita

Raise all market incomes by this percentage.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.economy.transport
**Label:** Change to transport spending

Raise transport expenses by this percentage.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.economy.rent
**Label:** Change to rents

Raise rental expenses by this percentage.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.economy.interest_rates
**Label:** Change to interest rates

Raise the interest rate on mortgages by this percentage.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.employer_ni.employee_incidence
**Label:** Employer NI employee incidence

Fraction of employer NI that is borne by employees.

**Type:** int

**Current value:** 1

---

### gov.contrib.policyengine.employer_ni.exempt_employer_pension_contributions
**Label:** exempt employer pension contributions from employers' NI

Whether to exempt employer pension contributions from employer NI.

**Type:** bool

**Current value:** True

---

### gov.contrib.policyengine.employer_ni.consumer_incidence
**Label:** Employer NI consumer incidence

Fraction of (remaining after employee incidence) employer NI that is borne by consumers.

**Type:** float

**Current value:** 0.5

---

### gov.contrib.policyengine.employer_ni.capital_incidence
**Label:** Employer NI capital incidence

Fraction of (remaining after employee incidence) employer NI that is borne by capital.

**Type:** float

**Current value:** 0.5

---

### gov.contrib.policyengine.disable_simulated_benefits
**Label:** disable simulated benefits

Disable simulated benefits.

**Type:** bool

**Current value:** False

---

### gov.contrib.policyengine.budget.nhs
**Label:** NHS spending change (£bn)

Increase in NHS spending, distributed by income decile as estimated by the ONS Effects of Taxes and Benefits dataset.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.budget.consumer_incident_tax_change
**Label:** tax on consumers (£bn)

Tax increase incident on consumers.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.budget.education
**Label:** education spending change (£bn)

Increase in education, distributed by income decile as estimated by the ONS Effects of Taxes and Benefits dataset.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.budget.high_income_incident_tax_change
**Label:** high income incident tax change (£bn)

Tax rise for high income earners (functioning proportional to income over £100,000).

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.budget.other_public_spending
**Label:** general public spending change (£bn)

Increase in non-NHS, non-education public spending, distributed by income decile as estimated by the ONS Effects of Taxes and Benefits dataset.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.budget.corporate_incident_tax_change
**Label:** tax on capital (£bn)

Tax increase incident on owners of capital.

**Type:** int

**Current value:** 0

---

### gov.contrib.cec.state_pension_increase
**Label:** State Pension increase

Increase State Pension payments by this percentage.

**Type:** float

**Current value:** 0.0

---

### gov.contrib.cec.non_primary_residence_wealth_tax[0].threshold
**Label:** Wealth tax exemption on non-primary residence wealth

This much wealth is exempt from the wealth tax.

**Type:** int

**Current value:** 0

---

### gov.contrib.cec.non_primary_residence_wealth_tax[0].rate
**Label:** Wealth tax rate on non-primary residence wealth

This is the marginal rate of tax on wealth above the threshold.

**Type:** int

**Current value:** 0

---

### gov.contrib.abolish_state_pension
**Label:** Abolish State Pension

Remove all State Pension payments.

**Type:** bool

**Current value:** False

---

### gov.dwp.carers_allowance.rate
**Label:** Carer's Allowance rate

Weekly rate of Carer's Allowance.

**Type:** float

**Current value:** 83.29

---

### gov.dwp.carers_allowance.min_hours
**Label:** Carer's Allowance minimum hours

Minimum number of hours spent providing care to qualify for Carer's Allowance.

**Type:** int

**Current value:** 35

---

### gov.dwp.winter_fuel_payment.amount.lower
**Label:** Winter Fuel Payment lower amount

**Type:** int

**Current value:** 200

---

### gov.dwp.winter_fuel_payment.amount.higher
**Label:** Winter Fuel Payment higher amount

**Type:** int

**Current value:** 300

---

### gov.dwp.winter_fuel_payment.eligibility.state_pension_age_requirement
**Label:** Winter Fuel Payment State Pension Age requirement

Whether individuals must be State Pension Age to qualify for the Winter Fuel Payment.

**Type:** bool

**Current value:** True

---

### gov.dwp.winter_fuel_payment.eligibility.require_benefits
**Label:** Winter Fuel Payment means-tested benefits requirement

Whether receipt of means-tested benefits is required to qualify for the Winter Fuel Payment.

**Type:** bool

**Current value:** True

---

### gov.dwp.winter_fuel_payment.eligibility.higher_age_requirement
**Label:** Winter Fuel Payment higher amount age requitement

Age requirement to qualify for the higher Winter Fuel Payment.

**Type:** int

**Current value:** 80

---

### gov.dwp.carer_premium.couple
**Label:** Legacy benefit carer premium (two carers)

Carer premium for two qualifying carers for legacy benefits.

**Type:** float

**Current value:** 46.38

---

### gov.dwp.carer_premium.single
**Label:** Legacy benefit carer premium (one carer)

Carer premium for one qualifying carer, for legacy benefits.

**Type:** float

**Current value:** 46.38

---

### gov.dwp.sda.maximum
**Label:** Severe Disablement Allowance

Maximum Severe Disablement Allowance rate.

**Type:** float

**Current value:** 115.02

---

### gov.dwp.dla.self_care.middle
**Label:** DLA (self-care) (middle rate)

Middle rate for Disability Living Allowance (self-care component).

**Type:** float

**Current value:** 73.89

---

### gov.dwp.dla.self_care.lower
**Label:** DLA (self-care) (lower rate)

Lower rate for Disability Living Allowance (self-care component).

**Type:** float

**Current value:** 29.19

---

### gov.dwp.dla.self_care.higher
**Label:** DLA (self-care) (higher rate)

Higher rate for Disability Living Allowance (self-care component).

**Type:** float

**Current value:** 110.4

---

### gov.dwp.dla.mobility.lower
**Label:** DLA (mobility) (lower rate)

Lower rate for Disability Living Allowance (mobility component).

**Type:** float

**Current value:** 29.19

---

### gov.dwp.dla.mobility.higher
**Label:** DLA (mobility) (higher rate)

Higher rate for Disability Living Allowance (mobility component).

**Type:** float

**Current value:** 77.04

---

### gov.dwp.housing_benefit.allowances.lone_parent.younger
**Label:** Housing Benefit lone parent younger personal allowance

The following younger lone parent personal allowance is provided under the Housing Benefit.

**Type:** float

**Current value:** 72.92

---

### gov.dwp.housing_benefit.allowances.lone_parent.aged
**Label:** Housing Benefit lone parent aged personal allowance

Personal allowance for Housing Benefit for a lone parent over State Pension age.

**Type:** float

**Current value:** 239.2

---

### gov.dwp.housing_benefit.allowances.lone_parent.older
**Label:** Housing Benefit lone parent older personal allowance

The following older lone parent personal allowance is provided under the Housing Benefit.

**Type:** float

**Current value:** 92.04

---

### gov.dwp.housing_benefit.allowances.single.younger
**Label:** Housing Benefit single younger personal allowance

The following younger single person personal allowance is provided under the Housing Benefit.

**Type:** float

**Current value:** 72.92

---

### gov.dwp.housing_benefit.allowances.single.aged
**Label:** Housing Benefit single aged personal allowance

The following personal allowance amount is provided to single filers over the pension age under the Housing Benefit.

**Type:** float

**Current value:** 239.2

---

### gov.dwp.housing_benefit.allowances.single.older
**Label:** Housing Benefit single older personal allowance

The following older single person personal allowance is provided under the Housing Benefit.

**Type:** float

**Current value:** 92.04

---

### gov.dwp.housing_benefit.allowances.age_threshold.younger
**Label:** Housing Benefit allowance younger age threshold

A lower Housing Benefit allowance amount is provided if both members of a couple are below this age threshold.

**Type:** int

**Current value:** 18

---

### gov.dwp.housing_benefit.allowances.age_threshold.older
**Label:** Housing Benefit allowance older age threshold

A higher Houseing Benefit allowance amount is provided for filers over this age threshold.

**Type:** int

**Current value:** 25

---

### gov.dwp.housing_benefit.allowances.couple.younger
**Label:** Housing Benefit younger couple personal allowance

The following couple personal allowance is provided under the Housing Benefit, if both members are under the younger age threshold.

**Type:** float

**Current value:** 110.14

---

### gov.dwp.housing_benefit.allowances.couple.aged
**Label:** Housing Benefit aged couple personal allowance

The following couple personal allowance is provided under the Housing Benefit if at least one member is over the state pension age threshold.

**Type:** float

**Current value:** 357.98

---

### gov.dwp.housing_benefit.allowances.couple.older
**Label:** Housing Benefit older couple personal allowance

The following couple personal allowance is provided under the Housing Benefit, if at least one member is over the younger age threshold.

**Type:** float

**Current value:** 144.67

---

### gov.dwp.housing_benefit.non_dep_deduction.age_threshold
**Label:** Housing Benefit non dependent deduction age threshold

A non dependent deduction is provided under Housing Benefit for filers at or above this age threshold.

**Type:** int

**Current value:** 18

---

### gov.dwp.housing_benefit.means_test.withdrawal_rate
**Label:** Housing Benefit withdrawal rate

Withdrawal rate under the Housing Benefit.

**Type:** float

**Current value:** 0.65

---

### gov.dwp.housing_benefit.means_test.income_disregard.worker
**Label:** Housing Benefit worker earnings disregard

This amount of earnings is disreagrded for workers under the Housing Benefit.

**Type:** float

**Current value:** 51.18391608391608

---

### gov.dwp.housing_benefit.means_test.income_disregard.couple
**Label:** Housing Benefit couple earnings disregard

This amount of earnings is disreagrded for couples under the Housing Benefit.

**Type:** float

**Current value:** 13.796203796203795

---

### gov.dwp.housing_benefit.means_test.income_disregard.lone_parent
**Label:** Housing Benefit lone parent earnings disregard

This amount of earnings is disreagrded for lone parents under the Housing Benefit.

**Type:** float

**Current value:** 34.49050949050949

---

### gov.dwp.housing_benefit.means_test.income_disregard.single
**Label:** Housing Benefit single person earnings disregard

This amount of earnings is disreagrded for single filers under the Housing Benefit.

**Type:** float

**Current value:** 6.898101898101897

---

### gov.dwp.housing_benefit.means_test.income_disregard.worker_hours
**Label:** Housing Benefit worker element hours requirement

Filers can receive an additional income disregard amount if the meet the following averge weekly work hour quota under the Housing Benefit.

**Type:** int

**Current value:** 30

---

### gov.dwp.housing_benefit.takeup
**Label:** Housing Benefit take-up rate

Share of eligible Housing Benefit recipients that participate. By definition, this is 100%, because only current claimants are eligible (no new claims).

**Type:** float

**Current value:** 1.0

---

### gov.dwp.constant_attendance_allowance.exceptional_rate
**Label:** Constant Attendance Allowance exceptional rate

Exceptional rate for Constant Attendance Allowance

**Type:** float

**Current value:** 200.87272727272725

---

### gov.dwp.constant_attendance_allowance.full_day_rate
**Label:** Constant Attendance Allowance full day rate

Full day rate for Constant Attendance Allowance

**Type:** float

**Current value:** 100.43636363636362

---

### gov.dwp.constant_attendance_allowance.part_day_rate
**Label:** Constant Attendance Allowance part day rate

Part day rate for Constant Attendance Allowance

**Type:** float

**Current value:** 50.21818181818181

---

### gov.dwp.constant_attendance_allowance.intermediate_rate
**Label:** Constant Attendance Allowance intermediate rate

Intermediate rate for Constant Attendance Allowance

**Type:** float

**Current value:** 150.65454545454543

---

### gov.dwp.disability_premia.disability_single
**Label:** Legacy benefit disability premium (single)

Disability premium for a single person

**Type:** float

**Current value:** 48.217732267732266

---

### gov.dwp.disability_premia.severe_couple
**Label:** Legacy benefit severe disability premium (couple)

Severe disability premium for a couple where both are eligible

**Type:** float

**Current value:** 184.73116883116882

---

### gov.dwp.disability_premia.enhanced_couple
**Label:** Legacy benefit enhanced disability premium (couple)

Enhanced disability premium for a couple, invalid for Employment and Support Allowance

**Type:** float

**Current value:** 33.80069930069929

---

### gov.dwp.disability_premia.disability_couple
**Label:** Legacy benefit disability premium (couple)

Disability premium for a couple

**Type:** float

**Current value:** 68.7050949050949

---

### gov.dwp.disability_premia.severe_single
**Label:** Legacy benefit severe disability premium (single)

Severe disability premium for a single person

**Type:** float

**Current value:** 92.36558441558441

---

### gov.dwp.disability_premia.enhanced_single
**Label:** Legacy benefit enhanced disability premium (single)

Enhanced disability premium for a single person, invalid for Employment and Support Allowance

**Type:** float

**Current value:** 23.591508491508492

---

### gov.dwp.JSA.income.income_disregard_single
**Label:** Jobseeker's Allowance income disregard (single)

Threshold in income for a single person, above which the Jobseeker's Allowance amount is reduced

**Type:** float

**Current value:** 5.0

---

### gov.dwp.JSA.income.couple
**Label:** Income-based JSA (couple)

Weekly contributory Jobseeker's Allowance for couples

**Type:** float

**Current value:** 134.1653691813804

---

### gov.dwp.JSA.income.takeup
**Label:** Income-based Jobseeker's Allowance take-up rate

Share of eligible Income-based Jobseeker's Allowance recipients that participate

**Type:** float

**Current value:** 0.56

---

### gov.dwp.JSA.income.amount_18_24
**Label:** Income-based JSA (18-24)

Income-based Jobseeker's Allowance for persons aged 18-24

**Type:** float

**Current value:** 67.66456661316212

---

### gov.dwp.JSA.income.income_disregard_couple
**Label:** Jobseeker's Allowance income disregard (couple)

Threshold in income for a couple, above which the contributory Jobseeker's Allowance amount is reduced

**Type:** float

**Current value:** 10.0

---

### gov.dwp.JSA.income.amount_over_25
**Label:** Income-based JSA (over 25)

Income-based Jobseeker's Allowance for persons aged over 25

**Type:** float

**Current value:** 85.34269662921349

---

### gov.dwp.JSA.income.income_disregard_lone_parent
**Label:** Jobseeker's Allowance income disregard (lone parent)

Threshold in income for a lone parent, above which the contributory Jobseeker's Allowance amount is reduced

**Type:** float

**Current value:** 20.0

---

### gov.dwp.JSA.contrib.earn_disregard
**Label:** Jobseeker's Allowance earnings disregard

Threshold in earnings, above which the contributory Jobseeker's Allowance amount is reduced

**Type:** float

**Current value:** 5.0

---

### gov.dwp.JSA.contrib.amount_18_24
**Label:** Income-based JSA (18-24)

Income-based Jobseeker's Allowance for persons aged 18-24

**Type:** float

**Current value:** 61.05

---

### gov.dwp.JSA.contrib.pension_disregard
**Label:** Jobseeker's Allowance pension disregard

Threshold in occupational and personal pensions, above which the contributory Jobseeker's Allowance amount is reduced

**Type:** float

**Current value:** 50.0

---

### gov.dwp.JSA.contrib.amount_over_25
**Label:** Contributory JSA (over 25)

Contributory Jobseeker's Allowance for persons aged over 25

**Type:** float

**Current value:** 77.0

---

### gov.dwp.JSA.hours.couple
**Label:** Jobseeker's Allowance hours requirement (couple)

Hours requirement for joint claimants of Jobseeker's Allowance

**Type:** int

**Current value:** 24

---

### gov.dwp.JSA.hours.single
**Label:** Jobseeker's Allowance hours requirement (single)

Hours requirement for single claimants of Jobseeker's Allowance

**Type:** int

**Current value:** 16

---

### gov.dwp.universal_credit.takeup_rate
**Label:** Universal Credit take-up rate

Take-up rate of Universal Credit.

**Type:** float

**Current value:** 0.55

---

### gov.dwp.universal_credit.standard_allowance.amount.SINGLE_YOUNG
**Label:** Universal Credit single amount (under 25)

Standard allowance for single claimants under 25

**Type:** float

**Current value:** 316.98

---

### gov.dwp.universal_credit.standard_allowance.amount.SINGLE_OLD
**Label:** Universal Credit single amount (over 25)

Standard allowance for single claimants over 25.

**Type:** float

**Current value:** 400.14

---

### gov.dwp.universal_credit.standard_allowance.amount.COUPLE_YOUNG
**Label:** Universal Credit couple amount (both under 25)

Standard allowance for couples where both are under 25.

**Type:** float

**Current value:** 497.55

---

### gov.dwp.universal_credit.standard_allowance.amount.COUPLE_OLD
**Label:** Universal Credit couple amount (one over 25)

Standard allowance for couples where one is over 25.

**Type:** float

**Current value:** 628.1

---

### gov.dwp.universal_credit.standard_allowance.claimant_type.age_threshold
**Label:** Universal Credit standard allowance claimant type age threshold

A higher Universal Credit standard allowance is provided to claimants over this age threshold.

**Type:** int

**Current value:** 25

---

### gov.dwp.universal_credit.rollout_rate
**Label:** Universal Credit roll-out rate

Roll-out rate of Universal Credit

**Type:** int

**Current value:** 1

---

### gov.dwp.universal_credit.elements.housing.non_dep_deduction.age_threshold
**Label:** Universal Credit housing element non-dependent deduction age threshold

The non-dependent deduction is limited to filers over this age threshold under the housing element of the Universal Credit.

**Type:** int

**Current value:** 21

---

### gov.dwp.universal_credit.elements.housing.non_dep_deduction.amount
**Label:** Universal Credit housing element non-dependent deduction amount

Non-dependent deduction amount for the housing element of the Universal Credit.

**Type:** float

**Current value:** 93.77881959910913

---

### gov.dwp.universal_credit.elements.childcare.coverage_rate
**Label:** Universal Credit childcare element coverage rate

Proportion of childcare costs covered by Universal Credit.

**Type:** float

**Current value:** 0.85

---

### gov.dwp.universal_credit.elements.disabled.amount
**Label:** Universal Credit disability element amount

Limited capability for work-related activity element amount under the Universal Credit.

**Type:** float

**Current value:** 423.27

---

### gov.dwp.universal_credit.elements.carer.amount
**Label:** Universal Credit carer element amount

Carer element amount under the Universal Credit.

**Type:** float

**Current value:** 201.68

---

### gov.dwp.universal_credit.elements.child.limit.child_count
**Label:** Universal Credit child element child limit

Limit on the number of children for which the Universal Credit child element is payable.

**Type:** int

**Current value:** 2

---

### gov.dwp.universal_credit.elements.child.limit.start_year
**Label:** Universal Credit child element start year

A higher Universal Credit child element is payable for the first child if the child is born before this year.

**Type:** int

**Current value:** 2017

---

### gov.dwp.universal_credit.elements.child.first.higher_amount
**Label:** Universal Credit child element higher amount

Child element for the first child in Universal Credit.

**Type:** float

**Current value:** 339.0

---

### gov.dwp.universal_credit.elements.child.amount
**Label:** Universal Credit child element amount

The following child element is provided under the Universal Credit.

**Type:** float

**Current value:** 292.81

---

### gov.dwp.universal_credit.elements.child.disabled.amount
**Label:** Universal Credit disabled child element amount

The following disabled child element is provided under the Universal Credit.

**Type:** float

**Current value:** 158.76

---

### gov.dwp.universal_credit.elements.child.severely_disabled.amount
**Label:** Unversal Credit severely disabled element amount

Severely disabled child element of Universal Credit.

**Type:** float

**Current value:** 495.87

---

### gov.dwp.universal_credit.means_test.reduction_rate
**Label:** Universal Credit earned income reduction rate

Rate at which Universal Credit is reduced with earnings above the work allowance.

**Type:** float

**Current value:** 0.55

---

### gov.dwp.universal_credit.means_test.work_allowance.with_housing
**Label:** Universal Credit Work Allowance with housing support

Universal Credit Work Allowance if household receives housing support.

**Type:** int

**Current value:** 411

---

### gov.dwp.universal_credit.means_test.work_allowance.without_housing
**Label:** Universal Credit Work Allowance without housing support

Universal Credit Work Allowance if household does not receive housing support.

**Type:** int

**Current value:** 684

---

### gov.dwp.universal_credit.work_requirements.default_expected_hours
**Label:** Universal Credit minimum income floor expected weekly hours worked

Default expected hours worked per week for Universal Credit.

**Type:** int

**Current value:** 35

---

### gov.dwp.tax_credits.child_tax_credit.elements.dis_child_element
**Label:** CTC disabled child element

Child Tax Credit disabled child element

**Type:** int

**Current value:** 4240

---

### gov.dwp.tax_credits.child_tax_credit.elements.severe_dis_child_element
**Label:** CTC severely disabled child element

Child Tax Credit severely disabled child element

**Type:** float

**Current value:** 1584.935794542536

---

### gov.dwp.tax_credits.child_tax_credit.elements.child_element
**Label:** CTC child element

Child Tax Credit child element

**Type:** int

**Current value:** 3513

---

### gov.dwp.tax_credits.child_tax_credit.takeup
**Label:** Child Tax Credit take-up rate

Share of eligible Child Tax Credit recipients that participate. By definition, this is 100%, because only current claimants are eligible (no new claims).

**Type:** float

**Current value:** 1.0

---

### gov.dwp.tax_credits.min_benefit
**Label:** Tax credits minimum benefit

Tax credit amount below which tax credits are not paid

**Type:** int

**Current value:** 26

---

### gov.dwp.tax_credits.means_test.income_threshold
**Label:** Tax Credits income threshold

Yearly income threshold after which the Child Tax Credit is reduced for benefit units claiming Working Tax Credit

**Type:** int

**Current value:** 8080

---

### gov.dwp.tax_credits.means_test.income_threshold_CTC_only
**Label:** CTC income threshold

Income threshold for benefit units only entitled to Child Tax Credit

**Type:** int

**Current value:** 20335

---

### gov.dwp.tax_credits.working_tax_credit.elements.childcare_1
**Label:** Working Tax Credit childcare element one child amount

Working Tax Credit childcare element for one child

**Type:** float

**Current value:** 268.52777777777777

---

### gov.dwp.tax_credits.working_tax_credit.elements.couple
**Label:** WTC couple element

Working Tax Credit couple element

**Type:** int

**Current value:** 2542

---

### gov.dwp.tax_credits.working_tax_credit.elements.lone_parent
**Label:** WTC lone parent element

Working Tax Credit lone parent element

**Type:** int

**Current value:** 2542

---

### gov.dwp.tax_credits.working_tax_credit.elements.childcare_2
**Label:** Working Tax Credit childcare element two or more children amount

Working Tax Credit childcare element for two or more children

**Type:** float

**Current value:** 460.33333333333326

---

### gov.dwp.tax_credits.working_tax_credit.elements.severely_disabled
**Label:** WTC severe disability element

Working Tax Credit severe disability element

**Type:** int

**Current value:** 1734

---

### gov.dwp.tax_credits.working_tax_credit.elements.disabled
**Label:** WTC disability element

Working Tax Credit disability element

**Type:** int

**Current value:** 4001

---

### gov.dwp.tax_credits.working_tax_credit.elements.basic
**Label:** WTC basic element

Working Tax Credit basic element

**Type:** int

**Current value:** 2476

---

### gov.dwp.tax_credits.working_tax_credit.takeup
**Label:** Working Tax Credit take-up rate

Share of eligible Working Tax Credit recipients that participate. By definition, this is 100%, because only current claimants are eligible (no new claims).

**Type:** float

**Current value:** 1.0

---

### gov.dwp.state_pension.basic_state_pension.amount
**Label:** basic State Pension amount

Weekly amount paid to recipients of the basic State Pension.

**Type:** float

**Current value:** 172.38

---

### gov.dwp.state_pension.new_state_pension.active
**Label:** New State Pension active

Individuals who reach State Pension age while this parameter is true receive the New State Pension.

**Type:** bool

**Current value:** True

---

### gov.dwp.state_pension.new_state_pension.amount
**Label:** New State Pension amount

Weekly amount paid to recipients of the New State Pension.

**Type:** float

**Current value:** 224.96

---

### gov.dwp.pip.mobility.enhanced
**Label:** PIP (mobility) (enhanced rate)

Enhanced rate for Personal Independence Payment (mobility component).

**Type:** float

**Current value:** 77.04

---

### gov.dwp.pip.mobility.standard
**Label:** PIP (mobility) (standard rate)

Standard rate for Personal Independence Payment (mobility component).

**Type:** float

**Current value:** 29.19

---

### gov.dwp.pip.daily_living.enhanced
**Label:** PIP (daily living) (enhanced rate)

Enhanced rate for Personal Independence Payment (daily living component).

**Type:** float

**Current value:** 110.4

---

### gov.dwp.pip.daily_living.standard
**Label:** PIP (daily living) (standard rate)

Standard rate for Personal Independence Payment (daily living component).

**Type:** float

**Current value:** 73.89

---

### gov.dwp.ESA.income.income_disregard_single
**Label:** Income-based ESA single person earnings disregard

Threshold for income for a single person, above which the income-based Employment and Support Allowance amount is reduced

**Type:** float

**Current value:** 5.0

---

### gov.dwp.ESA.income.couple
**Label:** Income-based ESA personal allowance (couples)

Income-based Employment and Support Allowance personal allowance for couples

**Type:** float

**Current value:** 116.8

---

### gov.dwp.ESA.income.earn_disregard
**Label:** Income-based ESA earnings disregard

Earnings threshold above which the income-based Employment and Support Allowance amount is reduced

**Type:** float

**Current value:** 5.0

---

### gov.dwp.ESA.income.amount_18_24
**Label:** Income-based ESA personal allowance (18-24)

Income-based Employment and Support Allowance personal allowance for persons aged 18-24

**Type:** float

**Current value:** 58.9

---

### gov.dwp.ESA.income.pension_disregard
**Label:** Income-based ESA pension disregard

Threshold for occupational and personal pensions, above which the income-based Employment and Support Allowance amount is reduced

**Type:** float

**Current value:** 50.0

---

### gov.dwp.ESA.income.income_disregard_couple
**Label:** Income-based ESA couple earnings disregard

Threshold for income for a couple, above which the income-based Employment and Support Allowance amount is reduced

**Type:** float

**Current value:** 10.0

---

### gov.dwp.ESA.income.amount_over_25
**Label:** Income-based ESA personal allowance (over 25)

Income-based Employment and Support Allowance personal allowance for persons aged over 25

**Type:** float

**Current value:** 74.35

---

### gov.dwp.ESA.income.income_disregard_lone_parent
**Label:** Income-based ESA lone parent earnings disregard

Threshold for income for a lone parent, above which the income-based Employment and Support Allowance amount is reduced

**Type:** float

**Current value:** 20.0

---

### gov.dwp.IIDB.maximum
**Label:** Industrial Injuries Disablement Benefit maximum

Maximum weekly Industrial Injuries Disablement Benefit; amount varies in 10% increments

**Type:** int

**Current value:** 182

---

### gov.dwp.benefit_cap.single.in_london
**Label:** Benefit cap (single claimants, in London)

**Type:** int

**Current value:** 17255

---

### gov.dwp.benefit_cap.single.outside_london
**Label:** Benefit cap (single claimants, outside London)

**Type:** int

**Current value:** 15004

---

### gov.dwp.benefit_cap.non_single.in_london
**Label:** Benefit cap (family claimants, in London)

**Type:** int

**Current value:** 25753

---

### gov.dwp.benefit_cap.non_single.outside_london
**Label:** Benefit cap (family claimants, outside London)

**Type:** int

**Current value:** 22020

---

### gov.dwp.attendance_allowance.lower
**Label:** Attendance Allowance (lower rate)

Lower Attendance Allowance amount.

**Type:** float

**Current value:** 73.89

---

### gov.dwp.attendance_allowance.higher
**Label:** Attendance Allowance (higher rate)

Upper Attendance Allowance amount.

**Type:** float

**Current value:** 110.4

---

### gov.dwp.LHA.means_test.withdrawal_rate
**Label:** Housing Benefit (LHA) withdrawal rate

Withdrawal rate of Housing Benefit (LHA)

**Type:** float

**Current value:** 0.65

---

### gov.dwp.LHA.means_test.worker_income_disregard
**Label:** Housing Benefit (LHA) worker income disregard

Additional disregard in income for meeting the 16/30 hours requirement

**Type:** int

**Current value:** 30

---

### gov.dwp.LHA.means_test.income_disregard_single
**Label:** Housing Benefit (LHA) income disregard (single)

Threshold in income for a single person, above which the Housing Benefit (LHA) amount is reduced

**Type:** float

**Current value:** 5.0

---

### gov.dwp.LHA.means_test.earn_disregard
**Label:** Housing Benefit (LHA) earnings disregard

Threshold earnings, above which the Housing Benefit (LHA) is reduced

**Type:** float

**Current value:** 5.0

---

### gov.dwp.LHA.means_test.income_disregard_lone
**Label:** Housing Benefit (LHA) income disregard (lone parent)

Threshold in income for a lone parent, above which the Housing Benefit (LHA) amount is reduced

**Type:** float

**Current value:** 20.0

---

### gov.dwp.LHA.means_test.worker_hours
**Label:** LHA worker hours requirement

Default hours requirement for the Working-Tax-Credit-related worker element of Housing Benefit (LHA)

**Type:** int

**Current value:** 30

---

### gov.dwp.LHA.means_test.pension_disregard
**Label:** Housing Benefit (LHA) pension disregard

Threshold in occupational and personal pensions, above which the Housing Benefit (LHA) amount is reduced

**Type:** float

**Current value:** 50.0

---

### gov.dwp.LHA.means_test.income_disregard_couple
**Label:** Housing Benefit (LHA) income disregard (couple)

Threshold in income for a couple, above which the Housing Benefit (LHA) amount is reduced

**Type:** float

**Current value:** 10.0

---

### gov.dwp.LHA.means_test.income_disregard_lone_parent
**Label:** Housing Benefit (LHA) income disregard (lone parent)

Threshold in income for a lone parent, above which the Housing Benefit (LHA) amount is reduced

**Type:** float

**Current value:** 20.0

---

### gov.dwp.LHA.freeze
**Label:** LHA freeze

While this parameter is true, LHA rates are frozen in cash terms.

**Type:** bool

**Current value:** False

---

### gov.dwp.LHA.percentile
**Label:** LHA percentile

Local Housing Allowance rates are set at this percentile of private rents in the family's Broad Rental Market Area. This parameter does not apply if LHA is frozen.

**Type:** float

**Current value:** 0.3

---

### gov.dwp.income_support.amounts.amount_couples_age_gap
**Label:** Income Support applicable amount (couples, one under 18, one over 25)

Income Support applicable amount for couples in which one is under 18 and one over 25

**Type:** float

**Current value:** 102.57477522477521

---

### gov.dwp.income_support.amounts.amount_16_24
**Label:** Income Support applicable amount (single, 18-24)

Income Support applicable amount for single persons aged 18-24

**Type:** float

**Current value:** 81.25964035964034

---

### gov.dwp.income_support.amounts.amount_couples_16_17
**Label:** Income Support applicable amount (couples, both under 18)

Income Support applicable amount for couples both aged under 18

**Type:** float

**Current value:** 81.25964035964034

---

### gov.dwp.income_support.amounts.amount_lone_over_18
**Label:** Income Support applicable amount (lone parent, over 18)

Income Support applicable amount for lone parents aged over 18

**Type:** float

**Current value:** 102.57477522477521

---

### gov.dwp.income_support.amounts.amount_couples_over_18
**Label:** Income Support applicable amount (couples, both over 18)

Income Support applicable amount for couples aged over 18

**Type:** float

**Current value:** 161.1396603396603

---

### gov.dwp.income_support.amounts.amount_lone_16_17
**Label:** Income Support applicable amount (lone parent, under 18)

Income Support applicable amount for lone parents aged under 18

**Type:** float

**Current value:** 81.25964035964034

---

### gov.dwp.income_support.amounts.amount_over_25
**Label:** Income Support applicable amount (single, over 25)

Income Support applicable amount for single persons aged over 25

**Type:** float

**Current value:** 102.57477522477521

---

### gov.dwp.income_support.means_test.income_disregard_single
**Label:** Income Support income disregard (single)

Threshold in income for a single person, above which the Income Support amount is reduced

**Type:** float

**Current value:** 5.0

---

### gov.dwp.income_support.means_test.earn_disregard
**Label:** Income Support earnings disregard

Threshold in earnings, above which the Income Support amount is reduced

**Type:** float

**Current value:** 5.0

---

### gov.dwp.income_support.means_test.pension_disregard
**Label:** Income Support pension disregard

Threshold in occupational and personal pensions, above which the Income Support amount is reduced

**Type:** float

**Current value:** 50.0

---

### gov.dwp.income_support.means_test.income_disregard_couple
**Label:** Income Support income disregard (couples)

Threshold in income for a couple, above which the Income Support amount is reduced

**Type:** float

**Current value:** 10.0

---

### gov.dwp.income_support.means_test.income_disregard_lone_parent
**Label:** Income Support income disregard (lone parent)

Threshold in income for a lone parent, above which the Income Support amount is reduced

**Type:** float

**Current value:** 20.0

---

### gov.dwp.income_support.takeup
**Label:** Income Support take-up rate

Share of eligible Income Support recipients that participate. By definition, this is 100%, because only current claimants are eligible (no new claims).

**Type:** float

**Current value:** 1.0

---

### gov.dwp.pension_credit.income.pension_contributions_deduction
**Label:** Pension Credit pension contribution deduction

Percentage of pension contributions which are deductible from Pension Credit income.

**Type:** float

**Current value:** 0.5

---

### gov.dwp.pension_credit.savings_credit.rate.phase_in
**Label:** Savings Credit phase-in rate

The rate at which Savings Credit increases for income over the Savings Credit threshold.

**Type:** float

**Current value:** 0.6

---

### gov.dwp.pension_credit.savings_credit.rate.phase_out
**Label:** Savings Credit phase-out rate

The rate at which Savings Credit decreases for income over the Minimum Guarantee.

**Type:** float

**Current value:** 0.4

---

### gov.dwp.pension_credit.savings_credit.threshold.SINGLE
**Label:** Pension Credit savings credit income threshold (single)

**Type:** float

**Current value:** 193.02

---

### gov.dwp.pension_credit.savings_credit.threshold.COUPLE
**Label:** Pension Credit savings credit income threshold (couple)

**Type:** float

**Current value:** 306.34

---

### gov.dwp.pension_credit.guarantee_credit.severe_disability.addition
**Label:** Pension Credit severe disability addition

Addition to the Minimum Guarantee for each severely disabled adult.

**Type:** float

**Current value:** 76.91926163723917

---

### gov.dwp.pension_credit.guarantee_credit.carer.addition
**Label:** Pension Credit carer addition

Addition to the Minimum Guarantee for each claimant who is a carer.

**Type:** float

**Current value:** 46.37

---

### gov.dwp.pension_credit.guarantee_credit.child.disability.severe.addition
**Label:** Pension Credit severely disabled child addition

Addition to the Minimum Guarantee for each severely disabled child (above the child addition).

**Type:** float

**Current value:** 105.82494382022473

---

### gov.dwp.pension_credit.guarantee_credit.child.disability.addition
**Label:** Pension Credit disabled child addition

Addition to the Minimum Guarantee for each disabled child (above the child addition).

**Type:** float

**Current value:** 33.89324237560192

---

### gov.dwp.pension_credit.guarantee_credit.child.addition
**Label:** Pension Credit child addition

Addition to the Minimum Guarantee for each child.

**Type:** float

**Current value:** 62.45533707865169

---

### gov.dwp.pension_credit.takeup
**Label:** Pension Credit take-up rate

Share of eligible Pension Credit recipients that participate.

**Type:** float

**Current value:** 0.7

---

### gov.obr.inflation.food_beverages_and_tobacco
**Label:** Food and beverages inflation

OBR CPI category inflation projection for food, beverages and tobacco.

**Type:** float

**Current value:** 1.352

---

### gov.obr.inflation.utilities
**Label:** Utilities inflation

OBR CPI category inflation projection for utilities

**Type:** float

**Current value:** 1.365

---

### gov.dcms.bbc.tv_licence.evasion_rate
**Label:** TV licence fee evasion rate

Percent of households legally required to purchase a TV licence who evade the licence fee.

**Type:** float

**Current value:** 0.0725

---

### gov.dcms.bbc.tv_licence.discount.blind.discount
**Label:** Blind TV Licence discount

Percentage discount for qualifying blind licence holders.

**Type:** float

**Current value:** 0.5

---

### gov.dcms.bbc.tv_licence.discount.aged.discount
**Label:** Aged TV Licence discount

Percentage discount for qualifying aged households.

**Type:** int

**Current value:** 1

---

### gov.dcms.bbc.tv_licence.discount.aged.min_age
**Label:** Aged TV Licence discounted minimum age

Minimum age required to qualify for a TV licence discount.

**Type:** int

**Current value:** 75

---

### gov.dcms.bbc.tv_licence.discount.aged.must_claim_pc
**Label:** Aged TV licence Pension Credit requirement

Whether aged individuals must claim Pension Credit in order to qualify for a free TV licence.

**Type:** bool

**Current value:** True

---

### gov.dcms.bbc.tv_licence.colour
**Label:** TV Licence fee

Full TV licence for a colour TV, before any discounts are applied.

**Type:** float

**Current value:** 159.0

---

### gov.dcms.bbc.tv_licence.tv_ownership
**Label:** TV ownership rate

Percentage of households which own a TV.

**Type:** float

**Current value:** 0.9544

---

### gov.hmrc.fuel_duty.petrol_and_diesel
**Label:** Fuel duty rate (petrol and diesel)

Fuel duty rate per litre of petrol and diesel.

**Type:** float

**Current value:** 0.5795

---

### gov.hmrc.national_insurance.class_4.rates.additional
**Label:** NI Class 4 additional rate

The additional National Insurance rate paid above the Upper Profits Limit for self-employed profits

**Type:** float

**Current value:** 0.02

---

### gov.hmrc.national_insurance.class_4.rates.main
**Label:** NI Class 4 main rate

The main National Insurance rate paid between the Lower and Upper Profits Limits for self-employed profits

**Type:** float

**Current value:** 0.06

---

### gov.hmrc.national_insurance.class_4.thresholds.upper_profits_limit
**Label:** NI Upper Profits Limit

The Upper Profits Limit is the threshold at which self-employed earners pay the additional Class 4 National Insurance rate

**Type:** int

**Current value:** 50270

---

### gov.hmrc.national_insurance.class_4.thresholds.lower_profits_limit
**Label:** NI Lower Profits Limit

The Lower Profits Limit is the threshold at which self-employed earners pay the main Class 4 National Insurance rate

**Type:** float

**Current value:** 12887.282850779511

---

### gov.hmrc.national_insurance.class_2.flat_rate
**Label:** NI Class 2 Flat Rate

Flat rate National Insurance contribution for self-employed earners

**Type:** int

**Current value:** 0

---

### gov.hmrc.national_insurance.class_2.small_profits_threshold
**Label:** NI Class 2 Small Profits Threshold

Small profits National Insurance threshold for self-employed earners

**Type:** float

**Current value:** 7453.631621187801

---

### gov.hmrc.national_insurance.class_1.rates.employee.additional
**Label:** NI Class 1 additional rate

The Class 1 National Insurance additional rate is paid on employment earnings above the Upper Earnings Limit

**Type:** float

**Current value:** 0.0185

---

### gov.hmrc.national_insurance.class_1.rates.employee.main
**Label:** NI Class 1 main rate

The Class 1 National Insurance main rate is paid on employment earnings between the Primary Threshold and the Upper Earnings Limit

**Type:** float

**Current value:** 0.08

---

### gov.hmrc.national_insurance.class_1.rates.employer
**Label:** NI Employer rate

National Insurance contribution rate by employers on earnings above the Secondary Threshold

**Type:** float

**Current value:** 0.138

---

### gov.hmrc.national_insurance.class_1.thresholds.lower_earnings_limit
**Label:** NI Lower Earnings Limit

Lower earnings limit for National Insurance

**Type:** int

**Current value:** 123

---

### gov.hmrc.national_insurance.class_1.thresholds.primary_threshold
**Label:** NI Primary Threshold

The Primary Threshold is the lower bound for the main rate of Class 1 National Insurance

**Type:** float

**Current value:** 241.73

---

### gov.hmrc.national_insurance.class_1.thresholds.secondary_threshold
**Label:** NI Secondary Threshold

Secondary threshold for National Insurance

**Type:** int

**Current value:** 175

---

### gov.hmrc.national_insurance.class_1.thresholds.upper_earnings_limit
**Label:** NI Upper Earnings Limit

The Upper Earnings Limit is the upper bound for the main rate of Class 1 National Insurance

**Type:** float

**Current value:** 966.73

---

### gov.hmrc.stamp_duty.abolish
**Label:** Abolish SDLT

Abolish Stamp Duty Land Tax.

**Type:** bool

**Current value:** False

---

### gov.hmrc.stamp_duty.residential.purchase.additional.min
**Label:** Stamp Duty secondary residence minimum value

Minimum value for taxability of additional residential property

**Type:** int

**Current value:** 40000

---

### gov.hmrc.stamp_duty.residential.purchase.main.first.max
**Label:** Stamp Duty first home value limit

Maximum value for a first-property purchase to receive the Stamp Duty relief for first-time buyers. Increasing this value will underestimate the number of claims for FTBR, as the model will not add new claims.

**Type:** int

**Current value:** 500000

---

### gov.hmrc.stamp_duty.property_sale_rate
**Label:** percentage of properties sold

This percentage of properties are sold every year.

**Type:** float

**Current value:** 0.045

---

### gov.hmrc.income_tax.allowances.property_allowance
**Label:** Property Allowance

Amount of income from property untaxed per year

**Type:** int

**Current value:** 1000

---

### gov.hmrc.income_tax.allowances.marriage_allowance.takeup_rate
**Label:** Marriage Allowance take-up rate

Percentage of eligible couples who claim Marriage Allowance.

**Type:** int

**Current value:** 1

---

### gov.hmrc.income_tax.allowances.marriage_allowance.max
**Label:** Marriage Allowance maximum percentage

Maximum Marriage Allowance taxable income reduction, as a percentage of the full Personal Allowance

**Type:** float

**Current value:** 0.1

---

### gov.hmrc.income_tax.allowances.marriage_allowance.rounding_increment
**Label:** Marriage Allowance rounding increment

The Marriage Allowance is rounded up by this increment.

**Type:** int

**Current value:** 10

---

### gov.hmrc.income_tax.allowances.personal_allowance.reduction_rate
**Label:** Personal Allowance phase-out rate

Reduction rate for the Personal Allowance

**Type:** float

**Current value:** 0.5

---

### gov.hmrc.income_tax.allowances.personal_allowance.amount
**Label:** Personal allowance

The Personal Allowance is deducted from general income

**Type:** int

**Current value:** 12570

---

### gov.hmrc.income_tax.allowances.personal_allowance.maximum_ANI
**Label:** Personal Allowance phase-out threshold

Maximum adjusted net income before the Personal Allowance is reduced

**Type:** int

**Current value:** 100000

---

### gov.hmrc.income_tax.allowances.trading_allowance
**Label:** Trading Allowance

Amount of trading income untaxed per year

**Type:** int

**Current value:** 1000

---

### gov.hmrc.income_tax.allowances.dividend_allowance
**Label:** Dividend Allowance

Amount of dividend income untaxed per year

**Type:** int

**Current value:** 500

---

### gov.hmrc.income_tax.rates.uk[0].rate
**Label:** Basic rate

The basic rate is the first of three tax brackets on all income, after allowances are deducted

**Type:** float

**Current value:** 0.2

---

### gov.hmrc.income_tax.rates.uk[1].threshold
**Label:** Higher rate threshold

The lower threshold for the higher rate of income tax (and therefore the upper threshold of the basic rate)

**Type:** int

**Current value:** 37700

---

### gov.hmrc.income_tax.rates.uk[1].rate
**Label:** Higher rate

The higher rate is the middle tax bracket on earned income.

**Type:** float

**Current value:** 0.4

---

### gov.hmrc.income_tax.rates.uk[2].threshold
**Label:** Additional rate threshold

The lower threshold for the additional rate

**Type:** int

**Current value:** 125140

---

### gov.hmrc.income_tax.rates.uk[2].rate
**Label:** Additional rate

The additional rate is the highest tax bracket, with no upper bound

**Type:** float

**Current value:** 0.45

---

### gov.hmrc.income_tax.rates.uk[3].threshold
**Label:** Extra tax bracket threshold

The lower threshold for the extra bracket rate.

**Type:** int

**Current value:** 10000000

---

### gov.hmrc.income_tax.rates.uk[3].rate
**Label:** Extra tax bracket rate

An extra tax bracket.

**Type:** float

**Current value:** 0.45

---

### gov.hmrc.income_tax.rates.dividends[0].threshold
**Label:** Dividends basic rate threshold

**Type:** int

**Current value:** 0

---

### gov.hmrc.income_tax.rates.dividends[0].rate
**Label:** Dividends basic rate

**Type:** float

**Current value:** 0.0875

---

### gov.hmrc.income_tax.rates.dividends[1].threshold
**Label:** Dividends higher rate threshold

**Type:** int

**Current value:** 37500

---

### gov.hmrc.income_tax.rates.dividends[1].rate
**Label:** Dividends higher rate

**Type:** float

**Current value:** 0.3375

---

### gov.hmrc.income_tax.rates.dividends[2].threshold
**Label:** Dividends additional rate threshold

**Type:** int

**Current value:** 150000

---

### gov.hmrc.income_tax.rates.dividends[2].rate
**Label:** Dividends additional rate

**Type:** float

**Current value:** 0.3935

---

### gov.hmrc.income_tax.rates.dividends[3].threshold
**Label:** Extra dividend tax bracket threshold

The lower threshold for the extra dividend bracket rate.

**Type:** int

**Current value:** 10000000

---

### gov.hmrc.income_tax.rates.dividends[3].rate
**Label:** Extra dividend tax bracket rate

An extra dividend tax bracket.

**Type:** float

**Current value:** 0.3935

---

### gov.hmrc.income_tax.charges.CB_HITC.phase_out_end
**Label:** Child Benefit Tax Charge phase-out end

Income after which the Child Benefit is fully phased out

**Type:** int

**Current value:** 80000

---

### gov.hmrc.income_tax.charges.CB_HITC.phase_out_start
**Label:** Child Benefit Tax Charge phase-out threshold

Income after which the Child Benefit phases out

**Type:** int

**Current value:** 60000

---

### gov.hmrc.tax_free_childcare.minimum_weekly_hours
**Label:** Tax-free childcare weekly work hours minimum

HMRC limits tax-free childcare to benefit units in which each spouse earns at least the product of their minimum wage and this number of hours per week.

**Type:** int

**Current value:** 16

---

### gov.hmrc.tax_free_childcare.income.income_limit
**Label:** Tax-free childcare maximum adjusted income threshold

HMRC limits tax-free childcare eligibility to households where individual adjusted income does not exceed this yearly threshold.

**Type:** int

**Current value:** 100000

---

### gov.hmrc.tax_free_childcare.age.disability
**Label:** Tax-free childcare disability age limit

HMRC extends the tax-free childcare program eligibility to children with disabilities up to this age threshold.

**Type:** int

**Current value:** 17

---

### gov.hmrc.tax_free_childcare.age.standard
**Label:** Tax-free childcare standard age limit

HMRC extends the tax-free childcare program eligibility to children up to this age threshold.

**Type:** int

**Current value:** 12

---

### gov.hmrc.tax_free_childcare.contribution.standard_child
**Label:** Tax-free childcare standard yearly limit

HMRC provides tax-free childcare contribution up to this yearly amount for households with children under standard eligibility.

**Type:** int

**Current value:** 2000

---

### gov.hmrc.tax_free_childcare.contribution.disabled_child
**Label:** Tax-free childcare disabled child yearly limit

HMRC provides tax-free childcare contribution up to this yearly amount for households with disabled children.

**Type:** int

**Current value:** 4000

---

### gov.hmrc.vat.standard_rate
**Label:** VAT standard rate

The highest VAT rate, applicable to most goods and services.

**Type:** float

**Current value:** 0.2

---

### gov.hmrc.vat.reduced_rate
**Label:** VAT reduced rate

A reduced rate of VAT applicable to select goods and services (domestic fuel and power).

**Type:** float

**Current value:** 0.05

---

### gov.hmrc.cgt.additional_rate
**Label:** Capital Gains Tax additional rate

Capital gains tax rate on additional rate taxpayers. This parameter is under active development and reforms including it should not be cited.

**Type:** float

**Current value:** 0.2

---

### gov.hmrc.cgt.annual_exempt_amount
**Label:** Annual Exempt Amount

Annual Exempt Amount for individuals. This parameter is under active development and reforms including it should not be cited.

**Type:** float

**Current value:** 3075.723830734966

---

### gov.hmrc.cgt.higher_rate
**Label:** Capital Gains Tax higher rate

Capital gains tax rate on higher rate taxpayers. This parameter is under active development and reforms including it should not be cited.

**Type:** float

**Current value:** 0.2

---

### gov.hmrc.cgt.basic_rate
**Label:** Capital Gains Tax basic rate

Capital gains tax rate on basic rate taxpayers. This parameter is under active development and reforms including it should not be cited.

**Type:** float

**Current value:** 0.1

---

### gov.hmrc.child_benefit.amount.eldest
**Label:** Child Benefit (eldest)

Child Benefit amount for the eldest or only child

**Type:** float

**Current value:** 26.04

---

### gov.hmrc.child_benefit.amount.additional
**Label:** Child Benefit (additional)

Child Benefit amount for each additional child

**Type:** float

**Current value:** 17.24

---

### gov.hmrc.child_benefit.opt_out_rate
**Label:** Child Benefit HITC-liable opt-out rate

Percentage of fully HITC-liable families who opt out of Child Benefit.

**Type:** float

**Current value:** 0.23

---

### gov.hmrc.pensions.pension_contributions_relief_age_limit
**Label:** pension contributions relief age limit

The pensions contributions relief is limited to filers below this age threshold.

**Type:** int

**Current value:** 75

---

### gov.treasury.cost_of_living_support.pensioners.amount
**Label:** Payment to pensioner households

Payment to pensioner households receiving benefits.

**Type:** int

**Current value:** 0

---

### gov.treasury.cost_of_living_support.means_tested_households.amount
**Label:** Payment to households on means-tested benefits

Payment to households on means-tested benefits.

**Type:** int

**Current value:** 0

---

### gov.treasury.cost_of_living_support.disabled.amount
**Label:** Payment to households on disability benefits

Payment to households receiving disability benefits.

**Type:** int

**Current value:** 0

---

### gov.treasury.energy_bills_rebate.energy_bills_credit
**Label:** Energy bills credit

Credit on energy bills paid to households. This is modeled as a flat transfer to households.

**Type:** int

**Current value:** 0

---

### gov.treasury.energy_bills_rebate.council_tax_rebate.amount
**Label:** Council Tax rebate amount

Council Tax rebate paid to households in qualifying Council Tax bands under the Energy Bills Rebate.

**Type:** int

**Current value:** 0

---

### calibration.uprating.equity_prices
**Label:** Equity prices

Equity prices (OBR forecast).

**Type:** int

**Current value:** 4291

---

### calibration.programs.fuel_duty.revenue
**Label:** Fuel duty revenues

Fuel duty revenues.

**Type:** int

**Current value:** 26621382708

---

### calibration.programs.capital_gains.total
**Label:** Total capital gains

Total capital gains by individuals.

**Type:** int

**Current value:** 79881000000

---

### calibration.programs.capital_gains.tax
**Label:** Capital Gains Tax revenue

Capital gains tax revenue.

**Type:** int

**Current value:** 16200000000

---

### household.wealth.financial_assets
**Label:** Financial assets

Financial assets of households.

**Type:** int

**Current value:** 7300000000000

---

### household.consumption.fuel.prices.diesel
**Label:** Price of diesel per litre

Average price of diesel per litre.

**Type:** float

**Current value:** 1.52

---

### household.consumption.fuel.prices.petrol
**Label:** Price of unleaded petrol per litre

Average price of unleaded petrol per litre, including fuel duty.

**Type:** float

**Current value:** 1.44

---

### household.poverty.absolute_poverty_threshold_bhc
**Label:** Absolute poverty threshold, before housing costs

Absolute poverty threshold for equivalised household net income, before housing costs

**Type:** float

**Current value:** 367.36108108108107

---

### household.poverty.absolute_poverty_threshold_ahc
**Label:** Absolute poverty threshold, after housing costs

Absolute poverty threshold for equivalised household net income, after housing costs.

**Type:** float

**Current value:** 314.75567567567566

---

### gov.indices.private_rent_index
**Label:** Private rental prices index

Index of private rental prices across the UK.

**Type:** float

**Current value:** 128.5577828397874

---

### gov.ons.rpi
**Label:** RPI

Retail Price Index (RPI) is a measure of inflation published by the Office for National Statistics.

**Type:** float

**Current value:** 377.5

---

### gov.social_security_scotland.pawhp.amount.lower
**Label:** PAWHP lower amount

**Type:** float

**Current value:** 205.04825538233115

---

### gov.social_security_scotland.pawhp.amount.higher
**Label:** PAWHP lower amount

**Type:** float

**Current value:** 307.5723830734967

---

### gov.social_security_scotland.pawhp.amount.base
**Label:** PAWHP base payment

Amount paid to non-benefit-claiming pensioners for the PAWHP.

**Type:** int

**Current value:** 100

---

### gov.social_security_scotland.pawhp.eligibility.state_pension_age_requirement
**Label:** PAWHP State Pension Age requirement

Whether individuals must be State Pension Age to qualify for the PAWHP.

**Type:** bool

**Current value:** True

---

### gov.social_security_scotland.pawhp.eligibility.require_benefits
**Label:** PAWHP means-tested benefits requirement

Whether receipt of means-tested benefits is required to qualify for the Winter Fuel Payment.

**Type:** bool

**Current value:** True

---

### gov.social_security_scotland.pawhp.eligibility.higher_age_requirement
**Label:** Winter Fuel Payment higher amount age requirement

Age requirement to qualify for the higher PAWHP.

**Type:** int

**Current value:** 80

---

### gov.ofgem.energy_price_guarantee
**Label:** Energy price guarantee

The capped default tariff energy price level for Ofgem's central household (2,900kWh per annum in electricity consumption, 12,000kWh per annum for gas). The Energy Price Cap subsidy reduces household bills to this level.

**Type:** int

**Current value:** 3000

---

### gov.ofgem.energy_price_cap
**Label:** Ofgem energy price level

The default tariff energy price for Ofgem's central household (2,900kWh per annum in electricity consumption, 12,000kWh per annum for gas). The Energy Price Cap subsidy reduces household energy bills by the difference between this amount and the subsity target parameter level.

**Type:** int

**Current value:** 2389

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

### gov.simulation.labor_supply_responses.substitution_elasticity
**Label:** Substitution elasticity of labor supply

Percent change in labor supply given a 1% change in the effective marginal wage. This applies only to employment income.

**Type:** int

**Current value:** 0

---

### gov.simulation.labor_supply_responses.income_elasticity
**Label:** Income elasticity of labor supply

Percent change in labor supply given a 1% change in disposable income. This applies only to employment income.

**Type:** int

**Current value:** 0

---

### gov.simulation.marginal_tax_rate_adults
**Label:** Number of adults to simulate a marginal tax rate for

Number of adults to simulate a marginal tax rate for, in each household.

**Type:** int

**Current value:** 2

---

### gov.simulation.capital_gains_responses.elasticity
**Label:** capital gains elasticity

Elasticity of capital gains with respect to the capital gains marginal tax rate.

**Type:** int

**Current value:** 0

---

### gov.simulation.private_school_vat.private_school_vat_basis
**Label:** private school tuition VAT basis

Effective percentage of private school tuition subject to VAT

**Type:** float

**Current value:** 0.75

---

### gov.simulation.private_school_vat.private_school_factor
**Label:** student polulation adjustment factor

student polulation adjustment factor, tested by Vahid

**Type:** float

**Current value:** 0.85

---

### gov.simulation.private_school_vat.private_school_fees
**Label:** mean annual private school fee

Mean annual private school fee

**Type:** float

**Current value:** 17210.75043630017

---

### gov.revenue_scotland.lbtt.residential.additional_residence_surcharge
**Label:** LBTT fixed rate increase for secondary residences

Increase in percentage rates for non-primary residence purchases.

**Type:** float

**Current value:** 0.06

---

### gov.benefit_uprating_cpi
**Label:** Benefit uprating index

Most recent September CPIH index value, updated for each uprating occurrence (2005=100)

**Type:** float

**Current value:** 153.44444444444443

---

### gov.contrib.conservatives.pensioner_personal_allowance
**Label:** personal allowance for pensioners

Personal Allowance for pensioners.

**Type:** int

**Current value:** 12570

---

### gov.contrib.conservatives.cb_hitc_household
**Label:** household-based High Income Tax Charge

Child Benefit HITC assesses the joint income of a household to determine the amount of Child Benefit that is repayable.

**Type:** bool

**Current value:** False

---

### gov.contrib.cps.marriage_tax_reforms.expanded_ma.remove_income_condition
**Label:** Remove MA high-income restrictions

Allow higher and additional rate taxpayers to claim the Marriage Allowance.

**Type:** bool

**Current value:** False

---

### gov.contrib.cps.marriage_tax_reforms.expanded_ma.max_child_age
**Label:** Expanded MA child age condition

Only expand the Marriage Allowance for couples with a child under this age (zero does not limit by child age).

**Type:** int

**Current value:** 0

---

### gov.contrib.cps.marriage_tax_reforms.expanded_ma.ma_rate
**Label:** Expanded Marriage Allowance rate

Marriage Allowance maximum rate for eligible couples.

**Type:** float

**Current value:** 0.1

---

### gov.contrib.cps.marriage_tax_reforms.marriage_neutral_it.neutralise_income_tax
**Label:** Marriage-neutral Income Tax

Allow couples to split their taxable income equally for Income Tax.

**Type:** bool

**Current value:** False

---

### gov.contrib.cps.marriage_tax_reforms.marriage_neutral_it.max_child_age
**Label:** Expanded MA child age condition

Only marriage-neutralise Income Tax for couples with a child under this age (zero does not limit by child age).

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.interactions.include_in_taxable_income
**Label:** Include basic income in taxable income

Include basic income as earned income in benefit means tests.

**Type:** bool

**Current value:** False

---

### gov.contrib.ubi_center.basic_income.interactions.withdraw_cb
**Label:** Withdraw Child Benefit from basic income recipients

Withdraw Child Benefit payments from basic income recipients.

**Type:** bool

**Current value:** False

---

### gov.contrib.ubi_center.basic_income.interactions.include_in_means_tests
**Label:** Include basic income in means tests

Include basic income as earned income in benefit means tests.

**Type:** bool

**Current value:** False

---

### gov.contrib.ubi_center.basic_income.amount.adult_age
**Label:** Adult basic income threshold

Age at which a person stops receiving the child basic income and begins receiving the adult basic income.

**Type:** int

**Current value:** 18

---

### gov.contrib.ubi_center.basic_income.amount.by_age.child
**Label:** Child basic income

Basic income payment to children.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.amount.by_age.working_age
**Label:** Working-age basic income

Basic income payment to working-age adults.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.amount.by_age.senior
**Label:** Senior basic income

Basic income payment to seniors (individuals over State Pension Age).

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.amount.child_min_age
**Label:** Child basic income minimum threshold

Minimum age for children to receive the child basic income.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.amount.flat
**Label:** Basic income

Flat per-person basic income amount.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.phase_out.individual.rate
**Label:** Basic income individual phase-out rate

Percentage of income over the phase-out threshold which is deducted from basic income payments.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.phase_out.individual.threshold
**Label:** Basic income individual phase-out threshold

Threshold for taxable income at which basic income is reduced.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.phase_out.household.rate
**Label:** Basic income household phase-out rate

Rate at which any remaining basic income (after individual phase-outs) is reduced over the household income threshold.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.basic_income.phase_out.household.threshold
**Label:** Basic income household phase-out threshold

Threshold for household taxable income, after which any remaining basic income (after individual phase-outs) is reduced.

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.wealth_tax[0].threshold
**Label:** First wealth tax threshold

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.wealth_tax[0].rate
**Label:** First wealth tax rate

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.wealth_tax[1].threshold
**Label:** Second wealth tax threshold

**Type:** int

**Current value:** 100000000

---

### gov.contrib.ubi_center.wealth_tax[1].rate
**Label:** Second wealth tax rate

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.wealth_tax[2].threshold
**Label:** Third wealth tax threshold

**Type:** int

**Current value:** 1000000000

---

### gov.contrib.ubi_center.wealth_tax[2].rate
**Label:** Third wealth tax rate

**Type:** int

**Current value:** 0

---

### gov.contrib.ubi_center.carbon_tax.consumer_incidence
**Label:** Carbon tax consumer incidence

Proportion of corporate carbon taxes which is passed on to consumers in the form of higher prices (as opposed to shareholders in the form of reduced profitability).

**Type:** float

**Current value:** 1.0

---

### gov.contrib.ubi_center.carbon_tax.rate
**Label:** Carbon tax

Price per tonne of carbon emissions

**Type:** float

**Current value:** 0.0

---

### gov.contrib.ubi_center.land_value_tax.rate
**Label:** Land value tax

Tax rate on the unimproved value of land

**Type:** float

**Current value:** 0.0

---

### gov.contrib.ubi_center.land_value_tax.household_rate
**Label:** Land value tax (households)

Tax rate on the unimproved value of land owned by households

**Type:** float

**Current value:** 0.0

---

### gov.contrib.ubi_center.land_value_tax.corporate_rate
**Label:** Land value tax (corporations)

Tax rate on the unimproved value of land owned by corporations

**Type:** float

**Current value:** 0.0

---

### gov.contrib.freeze_pension_credit
**Label:** Freeze Pension Credit

Freeze Pension Credit payments. Set all Pension Credit payments to what they are under baseline policy.

**Type:** bool

**Current value:** False

---

### gov.contrib.abolish_council_tax
**Label:** Abolish Council Tax

Abolish council tax payments (and council tax benefit).

**Type:** bool

**Current value:** False

---

### gov.contrib.labour.private_school_vat
**Label:** private school VAT rate

VAT rate applied to private schools.

**Type:** int

**Current value:** 0

---

### gov.contrib.benefit_uprating.non_sp
**Label:** Non-State Pension benefit uprating

Increase all non-State Pension benefits by this amount (this multiplies the end value, not the maximum amount).

**Type:** int

**Current value:** 0

---

### gov.contrib.benefit_uprating.all
**Label:** Benefit uprating

Increase all benefit values by this percentage.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.economy.energy_bills
**Label:** Change to energy spending

Raise energy spending by this percentage.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.economy.gdp_per_capita
**Label:** Change to GDP per capita

Raise all market incomes by this percentage.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.economy.transport
**Label:** Change to transport spending

Raise transport expenses by this percentage.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.economy.rent
**Label:** Change to rents

Raise rental expenses by this percentage.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.economy.interest_rates
**Label:** Change to interest rates

Raise the interest rate on mortgages by this percentage.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.employer_ni.employee_incidence
**Label:** Employer NI employee incidence

Fraction of employer NI that is borne by employees.

**Type:** int

**Current value:** 1

---

### gov.contrib.policyengine.employer_ni.exempt_employer_pension_contributions
**Label:** exempt employer pension contributions from employers' NI

Whether to exempt employer pension contributions from employer NI.

**Type:** bool

**Current value:** True

---

### gov.contrib.policyengine.employer_ni.consumer_incidence
**Label:** Employer NI consumer incidence

Fraction of (remaining after employee incidence) employer NI that is borne by consumers.

**Type:** float

**Current value:** 0.5

---

### gov.contrib.policyengine.employer_ni.capital_incidence
**Label:** Employer NI capital incidence

Fraction of (remaining after employee incidence) employer NI that is borne by capital.

**Type:** float

**Current value:** 0.5

---

### gov.contrib.policyengine.disable_simulated_benefits
**Label:** disable simulated benefits

Disable simulated benefits.

**Type:** bool

**Current value:** False

---

### gov.contrib.policyengine.budget.nhs
**Label:** NHS spending change (£bn)

Increase in NHS spending, distributed by income decile as estimated by the ONS Effects of Taxes and Benefits dataset.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.budget.consumer_incident_tax_change
**Label:** tax on consumers (£bn)

Tax increase incident on consumers.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.budget.education
**Label:** education spending change (£bn)

Increase in education, distributed by income decile as estimated by the ONS Effects of Taxes and Benefits dataset.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.budget.high_income_incident_tax_change
**Label:** high income incident tax change (£bn)

Tax rise for high income earners (functioning proportional to income over £100,000).

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.budget.other_public_spending
**Label:** general public spending change (£bn)

Increase in non-NHS, non-education public spending, distributed by income decile as estimated by the ONS Effects of Taxes and Benefits dataset.

**Type:** int

**Current value:** 0

---

### gov.contrib.policyengine.budget.corporate_incident_tax_change
**Label:** tax on capital (£bn)

Tax increase incident on owners of capital.

**Type:** int

**Current value:** 0

---

### gov.contrib.cec.state_pension_increase
**Label:** State Pension increase

Increase State Pension payments by this percentage.

**Type:** float

**Current value:** 0.0

---

### gov.contrib.cec.non_primary_residence_wealth_tax[0].threshold
**Label:** Wealth tax exemption on non-primary residence wealth

This much wealth is exempt from the wealth tax.

**Type:** int

**Current value:** 0

---

### gov.contrib.cec.non_primary_residence_wealth_tax[0].rate
**Label:** Wealth tax rate on non-primary residence wealth

This is the marginal rate of tax on wealth above the threshold.

**Type:** int

**Current value:** 0

---

### gov.contrib.abolish_state_pension
**Label:** Abolish State Pension

Remove all State Pension payments.

**Type:** bool

**Current value:** False

---

### gov.dwp.carers_allowance.rate
**Label:** Carer's Allowance rate

Weekly rate of Carer's Allowance.

**Type:** float

**Current value:** 81.9

---

### gov.dwp.carers_allowance.min_hours
**Label:** Carer's Allowance minimum hours

Minimum number of hours spent providing care to qualify for Carer's Allowance.

**Type:** int

**Current value:** 35

---

### gov.dwp.winter_fuel_payment.amount.lower
**Label:** Winter Fuel Payment lower amount

**Type:** int

**Current value:** 200

---

### gov.dwp.winter_fuel_payment.amount.higher
**Label:** Winter Fuel Payment higher amount

**Type:** int

**Current value:** 300

---

### gov.dwp.winter_fuel_payment.eligibility.state_pension_age_requirement
**Label:** Winter Fuel Payment State Pension Age requirement

Whether individuals must be State Pension Age to qualify for the Winter Fuel Payment.

**Type:** bool

**Current value:** True

---

### gov.dwp.winter_fuel_payment.eligibility.require_benefits
**Label:** Winter Fuel Payment means-tested benefits requirement

Whether receipt of means-tested benefits is required to qualify for the Winter Fuel Payment.

**Type:** bool

**Current value:** True

---

### gov.dwp.winter_fuel_payment.eligibility.higher_age_requirement
**Label:** Winter Fuel Payment higher amount age requitement

Age requirement to qualify for the higher Winter Fuel Payment.

**Type:** int

**Current value:** 80

---

### gov.dwp.carer_premium.couple
**Label:** Legacy benefit carer premium (two carers)

Carer premium for two qualifying carers for legacy benefits.

**Type:** float

**Current value:** 45.6

---

### gov.dwp.carer_premium.single
**Label:** Legacy benefit carer premium (one carer)

Carer premium for one qualifying carer, for legacy benefits.

**Type:** float

**Current value:** 45.6

---

### gov.dwp.sda.maximum
**Label:** Severe Disablement Allowance

Maximum Severe Disablement Allowance rate.

**Type:** float

**Current value:** 113.1

---

### gov.dwp.dla.self_care.middle
**Label:** DLA (self-care) (middle rate)

Middle rate for Disability Living Allowance (self-care component).

**Type:** float

**Current value:** 72.65

---

### gov.dwp.dla.self_care.lower
**Label:** DLA (self-care) (lower rate)

Lower rate for Disability Living Allowance (self-care component).

**Type:** float

**Current value:** 28.7

---

### gov.dwp.dla.self_care.higher
**Label:** DLA (self-care) (higher rate)

Higher rate for Disability Living Allowance (self-care component).

**Type:** float

**Current value:** 108.55

---

### gov.dwp.dla.mobility.lower
**Label:** DLA (mobility) (lower rate)

Lower rate for Disability Living Allowance (mobility component).

**Type:** float

**Current value:** 28.7

---

### gov.dwp.dla.mobility.higher
**Label:** DLA (mobility) (higher rate)

Higher rate for Disability Living Allowance (mobility component).

**Type:** float

**Current value:** 75.75

---

### gov.dwp.housing_benefit.allowances.lone_parent.younger
**Label:** Housing Benefit lone parent younger personal allowance

The following younger lone parent personal allowance is provided under the Housing Benefit.

**Type:** float

**Current value:** 71.7

---

### gov.dwp.housing_benefit.allowances.lone_parent.aged
**Label:** Housing Benefit lone parent aged personal allowance

Personal allowance for Housing Benefit for a lone parent over State Pension age.

**Type:** float

**Current value:** 235.2

---

### gov.dwp.housing_benefit.allowances.lone_parent.older
**Label:** Housing Benefit lone parent older personal allowance

The following older lone parent personal allowance is provided under the Housing Benefit.

**Type:** float

**Current value:** 90.5

---

### gov.dwp.housing_benefit.allowances.single.younger
**Label:** Housing Benefit single younger personal allowance

The following younger single person personal allowance is provided under the Housing Benefit.

**Type:** float

**Current value:** 71.7

---

### gov.dwp.housing_benefit.allowances.single.aged
**Label:** Housing Benefit single aged personal allowance

The following personal allowance amount is provided to single filers over the pension age under the Housing Benefit.

**Type:** float

**Current value:** 235.2

---

### gov.dwp.housing_benefit.allowances.single.older
**Label:** Housing Benefit single older personal allowance

The following older single person personal allowance is provided under the Housing Benefit.

**Type:** float

**Current value:** 90.5

---

### gov.dwp.housing_benefit.allowances.age_threshold.younger
**Label:** Housing Benefit allowance younger age threshold

A lower Housing Benefit allowance amount is provided if both members of a couple are below this age threshold.

**Type:** int

**Current value:** 18

---

### gov.dwp.housing_benefit.allowances.age_threshold.older
**Label:** Housing Benefit allowance older age threshold

A higher Houseing Benefit allowance amount is provided for filers over this age threshold.

**Type:** int

**Current value:** 25

---

### gov.dwp.housing_benefit.allowances.couple.younger
**Label:** Housing Benefit younger couple personal allowance

The following couple personal allowance is provided under the Housing Benefit, if both members are under the younger age threshold.

**Type:** float

**Current value:** 108.3

---

### gov.dwp.housing_benefit.allowances.couple.aged
**Label:** Housing Benefit aged couple personal allowance

The following couple personal allowance is provided under the Housing Benefit if at least one member is over the state pension age threshold.

**Type:** int

**Current value:** 352

---

### gov.dwp.housing_benefit.allowances.couple.older
**Label:** Housing Benefit older couple personal allowance

The following couple personal allowance is provided under the Housing Benefit, if at least one member is over the younger age threshold.

**Type:** float

**Current value:** 142.25

---

### gov.dwp.housing_benefit.non_dep_deduction.age_threshold
**Label:** Housing Benefit non dependent deduction age threshold

A non dependent deduction is provided under Housing Benefit for filers at or above this age threshold.

**Type:** int

**Current value:** 18

---

### gov.dwp.housing_benefit.means_test.withdrawal_rate
**Label:** Housing Benefit withdrawal rate

Withdrawal rate under the Housing Benefit.

**Type:** float

**Current value:** 0.65

---

### gov.dwp.housing_benefit.means_test.income_disregard.worker
**Label:** Housing Benefit worker earnings disregard

This amount of earnings is disreagrded for workers under the Housing Benefit.

**Type:** float

**Current value:** 51.18391608391608

---

### gov.dwp.housing_benefit.means_test.income_disregard.couple
**Label:** Housing Benefit couple earnings disregard

This amount of earnings is disreagrded for couples under the Housing Benefit.

**Type:** float

**Current value:** 13.796203796203795

---

### gov.dwp.housing_benefit.means_test.income_disregard.lone_parent
**Label:** Housing Benefit lone parent earnings disregard

This amount of earnings is disreagrded for lone parents under the Housing Benefit.

**Type:** float

**Current value:** 34.49050949050949

---

### gov.dwp.housing_benefit.means_test.income_disregard.single
**Label:** Housing Benefit single person earnings disregard

This amount of earnings is disreagrded for single filers under the Housing Benefit.

**Type:** float

**Current value:** 6.898101898101897

---

### gov.dwp.housing_benefit.means_test.income_disregard.worker_hours
**Label:** Housing Benefit worker element hours requirement

Filers can receive an additional income disregard amount if the meet the following averge weekly work hour quota under the Housing Benefit.

**Type:** int

**Current value:** 30

---

### gov.dwp.housing_benefit.takeup
**Label:** Housing Benefit take-up rate

Share of eligible Housing Benefit recipients that participate. By definition, this is 100%, because only current claimants are eligible (no new claims).

**Type:** float

**Current value:** 1.0

---

### gov.dwp.constant_attendance_allowance.exceptional_rate
**Label:** Constant Attendance Allowance exceptional rate

Exceptional rate for Constant Attendance Allowance

**Type:** float

**Current value:** 200.87272727272725

---

### gov.dwp.constant_attendance_allowance.full_day_rate
**Label:** Constant Attendance Allowance full day rate

Full day rate for Constant Attendance Allowance

**Type:** float

**Current value:** 100.43636363636362

---

### gov.dwp.constant_attendance_allowance.part_day_rate
**Label:** Constant Attendance Allowance part day rate

Part day rate for Constant Attendance Allowance

**Type:** float

**Current value:** 50.21818181818181

---

### gov.dwp.constant_attendance_allowance.intermediate_rate
**Label:** Constant Attendance Allowance intermediate rate

Intermediate rate for Constant Attendance Allowance

**Type:** float

**Current value:** 150.65454545454543

---

### gov.dwp.disability_premia.disability_single
**Label:** Legacy benefit disability premium (single)

Disability premium for a single person

**Type:** float

**Current value:** 48.217732267732266

---

### gov.dwp.disability_premia.severe_couple
**Label:** Legacy benefit severe disability premium (couple)

Severe disability premium for a couple where both are eligible

**Type:** float

**Current value:** 184.73116883116882

---

### gov.dwp.disability_premia.enhanced_couple
**Label:** Legacy benefit enhanced disability premium (couple)

Enhanced disability premium for a couple, invalid for Employment and Support Allowance

**Type:** float

**Current value:** 33.80069930069929

---

### gov.dwp.disability_premia.disability_couple
**Label:** Legacy benefit disability premium (couple)

Disability premium for a couple

**Type:** float

**Current value:** 68.7050949050949

---

### gov.dwp.disability_premia.severe_single
**Label:** Legacy benefit severe disability premium (single)

Severe disability premium for a single person

**Type:** float

**Current value:** 92.36558441558441

---

### gov.dwp.disability_premia.enhanced_single
**Label:** Legacy benefit enhanced disability premium (single)

Enhanced disability premium for a single person, invalid for Employment and Support Allowance

**Type:** float

**Current value:** 23.591508491508492

---

### gov.dwp.JSA.income.income_disregard_single
**Label:** Jobseeker's Allowance income disregard (single)

Threshold in income for a single person, above which the Jobseeker's Allowance amount is reduced

**Type:** float

**Current value:** 5.0

---

### gov.dwp.JSA.income.couple
**Label:** Income-based JSA (couple)

Weekly contributory Jobseeker's Allowance for couples

**Type:** float

**Current value:** 134.1653691813804

---

### gov.dwp.JSA.income.takeup
**Label:** Income-based Jobseeker's Allowance take-up rate

Share of eligible Income-based Jobseeker's Allowance recipients that participate

**Type:** float

**Current value:** 0.56

---

### gov.dwp.JSA.income.amount_18_24
**Label:** Income-based JSA (18-24)

Income-based Jobseeker's Allowance for persons aged 18-24

**Type:** float

**Current value:** 67.66456661316212

---

### gov.dwp.JSA.income.income_disregard_couple
**Label:** Jobseeker's Allowance income disregard (couple)

Threshold in income for a couple, above which the contributory Jobseeker's Allowance amount is reduced

**Type:** float

**Current value:** 10.0

---

### gov.dwp.JSA.income.amount_over_25
**Label:** Income-based JSA (over 25)

Income-based Jobseeker's Allowance for persons aged over 25

**Type:** float

**Current value:** 85.34269662921349

---

### gov.dwp.JSA.income.income_disregard_lone_parent
**Label:** Jobseeker's Allowance income disregard (lone parent)

Threshold in income for a lone parent, above which the contributory Jobseeker's Allowance amount is reduced

**Type:** float

**Current value:** 20.0

---

### gov.dwp.JSA.contrib.earn_disregard
**Label:** Jobseeker's Allowance earnings disregard

Threshold in earnings, above which the contributory Jobseeker's Allowance amount is reduced

**Type:** float

**Current value:** 5.0

---

### gov.dwp.JSA.contrib.amount_18_24
**Label:** Income-based JSA (18-24)

Income-based Jobseeker's Allowance for persons aged 18-24

**Type:** float

**Current value:** 61.05

---

### gov.dwp.JSA.contrib.pension_disregard
**Label:** Jobseeker's Allowance pension disregard

Threshold in occupational and personal pensions, above which the contributory Jobseeker's Allowance amount is reduced

**Type:** float

**Current value:** 50.0

---

### gov.dwp.JSA.contrib.amount_over_25
**Label:** Contributory JSA (over 25)

Contributory Jobseeker's Allowance for persons aged over 25

**Type:** float

**Current value:** 77.0

---

### gov.dwp.JSA.hours.couple
**Label:** Jobseeker's Allowance hours requirement (couple)

Hours requirement for joint claimants of Jobseeker's Allowance

**Type:** int

**Current value:** 24

---

### gov.dwp.JSA.hours.single
**Label:** Jobseeker's Allowance hours requirement (single)

Hours requirement for single claimants of Jobseeker's Allowance

**Type:** int

**Current value:** 16

---

### gov.dwp.universal_credit.takeup_rate
**Label:** Universal Credit take-up rate

Take-up rate of Universal Credit.

**Type:** float

**Current value:** 0.55

---

### gov.dwp.universal_credit.standard_allowance.amount.SINGLE_YOUNG
**Label:** Universal Credit single amount (under 25)

Standard allowance for single claimants under 25

**Type:** float

**Current value:** 311.68

---

### gov.dwp.universal_credit.standard_allowance.amount.SINGLE_OLD
**Label:** Universal Credit single amount (over 25)

Standard allowance for single claimants over 25.

**Type:** float

**Current value:** 393.45

---

### gov.dwp.universal_credit.standard_allowance.amount.COUPLE_YOUNG
**Label:** Universal Credit couple amount (both under 25)

Standard allowance for couples where both are under 25.

**Type:** float

**Current value:** 489.23

---

### gov.dwp.universal_credit.standard_allowance.amount.COUPLE_OLD
**Label:** Universal Credit couple amount (one over 25)

Standard allowance for couples where one is over 25.

**Type:** float

**Current value:** 617.6

---

### gov.dwp.universal_credit.standard_allowance.claimant_type.age_threshold
**Label:** Universal Credit standard allowance claimant type age threshold

A higher Universal Credit standard allowance is provided to claimants over this age threshold.

**Type:** int

**Current value:** 25

---

### gov.dwp.universal_credit.rollout_rate
**Label:** Universal Credit roll-out rate

Roll-out rate of Universal Credit

**Type:** int

**Current value:** 1

---

### gov.dwp.universal_credit.elements.housing.non_dep_deduction.age_threshold
**Label:** Universal Credit housing element non-dependent deduction age threshold

The non-dependent deduction is limited to filers over this age threshold under the housing element of the Universal Credit.

**Type:** int

**Current value:** 21

---

### gov.dwp.universal_credit.elements.housing.non_dep_deduction.amount
**Label:** Universal Credit housing element non-dependent deduction amount

Non-dependent deduction amount for the housing element of the Universal Credit.

**Type:** float

**Current value:** 93.77881959910913

---

### gov.dwp.universal_credit.elements.childcare.coverage_rate
**Label:** Universal Credit childcare element coverage rate

Proportion of childcare costs covered by Universal Credit.

**Type:** float

**Current value:** 0.85

---

### gov.dwp.universal_credit.elements.disabled.amount
**Label:** Universal Credit disability element amount

Limited capability for work-related activity element amount under the Universal Credit.

**Type:** float

**Current value:** 416.19

---

### gov.dwp.universal_credit.elements.carer.amount
**Label:** Universal Credit carer element amount

Carer element amount under the Universal Credit.

**Type:** float

**Current value:** 198.31

---

### gov.dwp.universal_credit.elements.child.limit.child_count
**Label:** Universal Credit child element child limit

Limit on the number of children for which the Universal Credit child element is payable.

**Type:** int

**Current value:** 2

---

### gov.dwp.universal_credit.elements.child.limit.start_year
**Label:** Universal Credit child element start year

A higher Universal Credit child element is payable for the first child if the child is born before this year.

**Type:** int

**Current value:** 2017

---

### gov.dwp.universal_credit.elements.child.first.higher_amount
**Label:** Universal Credit child element higher amount

Child element for the first child in Universal Credit.

**Type:** float

**Current value:** 333.33

---

### gov.dwp.universal_credit.elements.child.amount
**Label:** Universal Credit child element amount

The following child element is provided under the Universal Credit.

**Type:** float

**Current value:** 287.92

---

### gov.dwp.universal_credit.elements.child.disabled.amount
**Label:** Universal Credit disabled child element amount

The following disabled child element is provided under the Universal Credit.

**Type:** float

**Current value:** 156.11

---

### gov.dwp.universal_credit.elements.child.severely_disabled.amount
**Label:** Unversal Credit severely disabled element amount

Severely disabled child element of Universal Credit.

**Type:** float

**Current value:** 487.58

---

### gov.dwp.universal_credit.means_test.reduction_rate
**Label:** Universal Credit earned income reduction rate

Rate at which Universal Credit is reduced with earnings above the work allowance.

**Type:** float

**Current value:** 0.55

---

### gov.dwp.universal_credit.means_test.work_allowance.with_housing
**Label:** Universal Credit Work Allowance with housing support

Universal Credit Work Allowance if household receives housing support.

**Type:** int

**Current value:** 404

---

### gov.dwp.universal_credit.means_test.work_allowance.without_housing
**Label:** Universal Credit Work Allowance without housing support

Universal Credit Work Allowance if household does not receive housing support.

**Type:** int

**Current value:** 673

---

### gov.dwp.universal_credit.work_requirements.default_expected_hours
**Label:** Universal Credit minimum income floor expected weekly hours worked

Default expected hours worked per week for Universal Credit.

**Type:** int

**Current value:** 35

---

### gov.dwp.tax_credits.child_tax_credit.elements.dis_child_element
**Label:** CTC disabled child element

Child Tax Credit disabled child element

**Type:** int

**Current value:** 4170

---

### gov.dwp.tax_credits.child_tax_credit.elements.severe_dis_child_element
**Label:** CTC severely disabled child element

Child Tax Credit severely disabled child element

**Type:** float

**Current value:** 1584.935794542536

---

### gov.dwp.tax_credits.child_tax_credit.elements.child_element
**Label:** CTC child element

Child Tax Credit child element

**Type:** int

**Current value:** 3455

---

### gov.dwp.tax_credits.child_tax_credit.takeup
**Label:** Child Tax Credit take-up rate

Share of eligible Child Tax Credit recipients that participate. By definition, this is 100%, because only current claimants are eligible (no new claims).

**Type:** float

**Current value:** 1.0

---

### gov.dwp.tax_credits.min_benefit
**Label:** Tax credits minimum benefit

Tax credit amount below which tax credits are not paid

**Type:** int

**Current value:** 26

---

### gov.dwp.tax_credits.means_test.income_threshold
**Label:** Tax Credits income threshold

Yearly income threshold after which the Child Tax Credit is reduced for benefit units claiming Working Tax Credit

**Type:** int

**Current value:** 7955

---

### gov.dwp.tax_credits.means_test.income_threshold_CTC_only
**Label:** CTC income threshold

Income threshold for benefit units only entitled to Child Tax Credit

**Type:** int

**Current value:** 19995

---

### gov.dwp.tax_credits.working_tax_credit.elements.childcare_1
**Label:** Working Tax Credit childcare element one child amount

Working Tax Credit childcare element for one child

**Type:** float

**Current value:** 268.52777777777777

---

### gov.dwp.tax_credits.working_tax_credit.elements.couple
**Label:** WTC couple element

Working Tax Credit couple element

**Type:** int

**Current value:** 2500

---

### gov.dwp.tax_credits.working_tax_credit.elements.lone_parent
**Label:** WTC lone parent element

Working Tax Credit lone parent element

**Type:** int

**Current value:** 2500

---

### gov.dwp.tax_credits.working_tax_credit.elements.childcare_2
**Label:** Working Tax Credit childcare element two or more children amount

Working Tax Credit childcare element for two or more children

**Type:** float

**Current value:** 460.33333333333326

---

### gov.dwp.tax_credits.working_tax_credit.elements.severely_disabled
**Label:** WTC severe disability element

Working Tax Credit severe disability element

**Type:** int

**Current value:** 1705

---

### gov.dwp.tax_credits.working_tax_credit.elements.disabled
**Label:** WTC disability element

Working Tax Credit disability element

**Type:** int

**Current value:** 3935

---

### gov.dwp.tax_credits.working_tax_credit.elements.basic
**Label:** WTC basic element

Working Tax Credit basic element

**Type:** int

**Current value:** 2435

---

### gov.dwp.tax_credits.working_tax_credit.takeup
**Label:** Working Tax Credit take-up rate

Share of eligible Working Tax Credit recipients that participate. By definition, this is 100%, because only current claimants are eligible (no new claims).

**Type:** float

**Current value:** 1.0

---

### gov.dwp.state_pension.basic_state_pension.amount
**Label:** basic State Pension amount

Weekly amount paid to recipients of the basic State Pension.

**Type:** float

**Current value:** 169.5

---

### gov.dwp.state_pension.new_state_pension.active
**Label:** New State Pension active

Individuals who reach State Pension age while this parameter is true receive the New State Pension.

**Type:** bool

**Current value:** True

---

### gov.dwp.state_pension.new_state_pension.amount
**Label:** New State Pension amount

Weekly amount paid to recipients of the New State Pension.

**Type:** float

**Current value:** 221.2

---

### gov.dwp.pip.mobility.enhanced
**Label:** PIP (mobility) (enhanced rate)

Enhanced rate for Personal Independence Payment (mobility component).

**Type:** float

**Current value:** 75.75

---

### gov.dwp.pip.mobility.standard
**Label:** PIP (mobility) (standard rate)

Standard rate for Personal Independence Payment (mobility component).

**Type:** float

**Current value:** 28.7

---

### gov.dwp.pip.daily_living.enhanced
**Label:** PIP (daily living) (enhanced rate)

Enhanced rate for Personal Independence Payment (daily living component).

**Type:** float

**Current value:** 108.55

---

### gov.dwp.pip.daily_living.standard
**Label:** PIP (daily living) (standard rate)

Standard rate for Personal Independence Payment (daily living component).

**Type:** float

**Current value:** 72.65

---

### gov.dwp.ESA.income.income_disregard_single
**Label:** Income-based ESA single person earnings disregard

Threshold for income for a single person, above which the income-based Employment and Support Allowance amount is reduced

**Type:** float

**Current value:** 5.0

---

### gov.dwp.ESA.income.couple
**Label:** Income-based ESA personal allowance (couples)

Income-based Employment and Support Allowance personal allowance for couples

**Type:** float

**Current value:** 116.8

---

### gov.dwp.ESA.income.earn_disregard
**Label:** Income-based ESA earnings disregard

Earnings threshold above which the income-based Employment and Support Allowance amount is reduced

**Type:** float

**Current value:** 5.0

---

### gov.dwp.ESA.income.amount_18_24
**Label:** Income-based ESA personal allowance (18-24)

Income-based Employment and Support Allowance personal allowance for persons aged 18-24

**Type:** float

**Current value:** 58.9

---

### gov.dwp.ESA.income.pension_disregard
**Label:** Income-based ESA pension disregard

Threshold for occupational and personal pensions, above which the income-based Employment and Support Allowance amount is reduced

**Type:** float

**Current value:** 50.0

---

### gov.dwp.ESA.income.income_disregard_couple
**Label:** Income-based ESA couple earnings disregard

Threshold for income for a couple, above which the income-based Employment and Support Allowance amount is reduced

**Type:** float

**Current value:** 10.0

---

### gov.dwp.ESA.income.amount_over_25
**Label:** Income-based ESA personal allowance (over 25)

Income-based Employment and Support Allowance personal allowance for persons aged over 25

**Type:** float

**Current value:** 74.35

---

### gov.dwp.ESA.income.income_disregard_lone_parent
**Label:** Income-based ESA lone parent earnings disregard

Threshold for income for a lone parent, above which the income-based Employment and Support Allowance amount is reduced

**Type:** float

**Current value:** 20.0

---

### gov.dwp.IIDB.maximum
**Label:** Industrial Injuries Disablement Benefit maximum

Maximum weekly Industrial Injuries Disablement Benefit; amount varies in 10% increments

**Type:** int

**Current value:** 182

---

### gov.dwp.benefit_cap.single.in_london
**Label:** Benefit cap (single claimants, in London)

**Type:** int

**Current value:** 16967

---

### gov.dwp.benefit_cap.single.outside_london
**Label:** Benefit cap (single claimants, outside London)

**Type:** int

**Current value:** 14753

---

### gov.dwp.benefit_cap.non_single.in_london
**Label:** Benefit cap (family claimants, in London)

**Type:** int

**Current value:** 25323

---

### gov.dwp.benefit_cap.non_single.outside_london
**Label:** Benefit cap (family claimants, outside London)

**Type:** int

**Current value:** 22020

---

### gov.dwp.attendance_allowance.lower
**Label:** Attendance Allowance (lower rate)

Lower Attendance Allowance amount.

**Type:** float

**Current value:** 72.65

---

### gov.dwp.attendance_allowance.higher
**Label:** Attendance Allowance (higher rate)

Upper Attendance Allowance amount.

**Type:** float

**Current value:** 108.55

---

### gov.dwp.LHA.means_test.withdrawal_rate
**Label:** Housing Benefit (LHA) withdrawal rate

Withdrawal rate of Housing Benefit (LHA)

**Type:** float

**Current value:** 0.65

---

### gov.dwp.LHA.means_test.worker_income_disregard
**Label:** Housing Benefit (LHA) worker income disregard

Additional disregard in income for meeting the 16/30 hours requirement

**Type:** int

**Current value:** 30

---

### gov.dwp.LHA.means_test.income_disregard_single
**Label:** Housing Benefit (LHA) income disregard (single)

Threshold in income for a single person, above which the Housing Benefit (LHA) amount is reduced

**Type:** float

**Current value:** 5.0

---

### gov.dwp.LHA.means_test.earn_disregard
**Label:** Housing Benefit (LHA) earnings disregard

Threshold earnings, above which the Housing Benefit (LHA) is reduced

**Type:** float

**Current value:** 5.0

---

### gov.dwp.LHA.means_test.income_disregard_lone
**Label:** Housing Benefit (LHA) income disregard (lone parent)

Threshold in income for a lone parent, above which the Housing Benefit (LHA) amount is reduced

**Type:** float

**Current value:** 20.0

---

### gov.dwp.LHA.means_test.worker_hours
**Label:** LHA worker hours requirement

Default hours requirement for the Working-Tax-Credit-related worker element of Housing Benefit (LHA)

**Type:** int

**Current value:** 30

---

### gov.dwp.LHA.means_test.pension_disregard
**Label:** Housing Benefit (LHA) pension disregard

Threshold in occupational and personal pensions, above which the Housing Benefit (LHA) amount is reduced

**Type:** float

**Current value:** 50.0

---

### gov.dwp.LHA.means_test.income_disregard_couple
**Label:** Housing Benefit (LHA) income disregard (couple)

Threshold in income for a couple, above which the Housing Benefit (LHA) amount is reduced

**Type:** float

**Current value:** 10.0

---

### gov.dwp.LHA.means_test.income_disregard_lone_parent
**Label:** Housing Benefit (LHA) income disregard (lone parent)

Threshold in income for a lone parent, above which the Housing Benefit (LHA) amount is reduced

**Type:** float

**Current value:** 20.0

---

### gov.dwp.LHA.freeze
**Label:** LHA freeze

While this parameter is true, LHA rates are frozen in cash terms.

**Type:** bool

**Current value:** False

---

### gov.dwp.LHA.percentile
**Label:** LHA percentile

Local Housing Allowance rates are set at this percentile of private rents in the family's Broad Rental Market Area. This parameter does not apply if LHA is frozen.

**Type:** float

**Current value:** 0.3

---

### gov.dwp.income_support.amounts.amount_couples_age_gap
**Label:** Income Support applicable amount (couples, one under 18, one over 25)

Income Support applicable amount for couples in which one is under 18 and one over 25

**Type:** float

**Current value:** 102.57477522477521

---

### gov.dwp.income_support.amounts.amount_16_24
**Label:** Income Support applicable amount (single, 18-24)

Income Support applicable amount for single persons aged 18-24

**Type:** float

**Current value:** 81.25964035964034

---

### gov.dwp.income_support.amounts.amount_couples_16_17
**Label:** Income Support applicable amount (couples, both under 18)

Income Support applicable amount for couples both aged under 18

**Type:** float

**Current value:** 81.25964035964034

---

### gov.dwp.income_support.amounts.amount_lone_over_18
**Label:** Income Support applicable amount (lone parent, over 18)

Income Support applicable amount for lone parents aged over 18

**Type:** float

**Current value:** 102.57477522477521

---

### gov.dwp.income_support.amounts.amount_couples_over_18
**Label:** Income Support applicable amount (couples, both over 18)

Income Support applicable amount for couples aged over 18

**Type:** float

**Current value:** 161.1396603396603

---

### gov.dwp.income_support.amounts.amount_lone_16_17
**Label:** Income Support applicable amount (lone parent, under 18)

Income Support applicable amount for lone parents aged under 18

**Type:** float

**Current value:** 81.25964035964034

---

### gov.dwp.income_support.amounts.amount_over_25
**Label:** Income Support applicable amount (single, over 25)

Income Support applicable amount for single persons aged over 25

**Type:** float

**Current value:** 102.57477522477521

---

### gov.dwp.income_support.means_test.income_disregard_single
**Label:** Income Support income disregard (single)

Threshold in income for a single person, above which the Income Support amount is reduced

**Type:** float

**Current value:** 5.0

---

### gov.dwp.income_support.means_test.earn_disregard
**Label:** Income Support earnings disregard

Threshold in earnings, above which the Income Support amount is reduced

**Type:** float

**Current value:** 5.0

---

### gov.dwp.income_support.means_test.pension_disregard
**Label:** Income Support pension disregard

Threshold in occupational and personal pensions, above which the Income Support amount is reduced

**Type:** float

**Current value:** 50.0

---

### gov.dwp.income_support.means_test.income_disregard_couple
**Label:** Income Support income disregard (couples)

Threshold in income for a couple, above which the Income Support amount is reduced

**Type:** float

**Current value:** 10.0

---

### gov.dwp.income_support.means_test.income_disregard_lone_parent
**Label:** Income Support income disregard (lone parent)

Threshold in income for a lone parent, above which the Income Support amount is reduced

**Type:** float

**Current value:** 20.0

---

### gov.dwp.income_support.takeup
**Label:** Income Support take-up rate

Share of eligible Income Support recipients that participate. By definition, this is 100%, because only current claimants are eligible (no new claims).

**Type:** float

**Current value:** 1.0

---

### gov.dwp.pension_credit.income.pension_contributions_deduction
**Label:** Pension Credit pension contribution deduction

Percentage of pension contributions which are deductible from Pension Credit income.

**Type:** float

**Current value:** 0.5

---

### gov.dwp.pension_credit.savings_credit.rate.phase_in
**Label:** Savings Credit phase-in rate

The rate at which Savings Credit increases for income over the Savings Credit threshold.

**Type:** float

**Current value:** 0.6

---

### gov.dwp.pension_credit.savings_credit.rate.phase_out
**Label:** Savings Credit phase-out rate

The rate at which Savings Credit decreases for income over the Minimum Guarantee.

**Type:** float

**Current value:** 0.4

---

### gov.dwp.pension_credit.savings_credit.threshold.SINGLE
**Label:** Pension Credit savings credit income threshold (single)

**Type:** float

**Current value:** 189.8

---

### gov.dwp.pension_credit.savings_credit.threshold.COUPLE
**Label:** Pension Credit savings credit income threshold (couple)

**Type:** float

**Current value:** 301.22

---

### gov.dwp.pension_credit.guarantee_credit.severe_disability.addition
**Label:** Pension Credit severe disability addition

Addition to the Minimum Guarantee for each severely disabled adult.

**Type:** float

**Current value:** 76.91926163723917

---

### gov.dwp.pension_credit.guarantee_credit.carer.addition
**Label:** Pension Credit carer addition

Addition to the Minimum Guarantee for each claimant who is a carer.

**Type:** float

**Current value:** 45.6

---

### gov.dwp.pension_credit.guarantee_credit.child.disability.severe.addition
**Label:** Pension Credit severely disabled child addition

Addition to the Minimum Guarantee for each severely disabled child (above the child addition).

**Type:** float

**Current value:** 105.82494382022473

---

### gov.dwp.pension_credit.guarantee_credit.child.disability.addition
**Label:** Pension Credit disabled child addition

Addition to the Minimum Guarantee for each disabled child (above the child addition).

**Type:** float

**Current value:** 33.89324237560192

---

### gov.dwp.pension_credit.guarantee_credit.child.addition
**Label:** Pension Credit child addition

Addition to the Minimum Guarantee for each child.

**Type:** float

**Current value:** 62.45533707865169

---

### gov.dwp.pension_credit.takeup
**Label:** Pension Credit take-up rate

Share of eligible Pension Credit recipients that participate.

**Type:** float

**Current value:** 0.7

---

### gov.obr.inflation.food_beverages_and_tobacco
**Label:** Food and beverages inflation

OBR CPI category inflation projection for food, beverages and tobacco.

**Type:** float

**Current value:** 1.352

---

### gov.obr.inflation.utilities
**Label:** Utilities inflation

OBR CPI category inflation projection for utilities

**Type:** float

**Current value:** 1.365

---

### gov.dcms.bbc.tv_licence.evasion_rate
**Label:** TV licence fee evasion rate

Percent of households legally required to purchase a TV licence who evade the licence fee.

**Type:** float

**Current value:** 0.0725

---

### gov.dcms.bbc.tv_licence.discount.blind.discount
**Label:** Blind TV Licence discount

Percentage discount for qualifying blind licence holders.

**Type:** float

**Current value:** 0.5

---

### gov.dcms.bbc.tv_licence.discount.aged.discount
**Label:** Aged TV Licence discount

Percentage discount for qualifying aged households.

**Type:** int

**Current value:** 1

---

### gov.dcms.bbc.tv_licence.discount.aged.min_age
**Label:** Aged TV Licence discounted minimum age

Minimum age required to qualify for a TV licence discount.

**Type:** int

**Current value:** 75

---

### gov.dcms.bbc.tv_licence.discount.aged.must_claim_pc
**Label:** Aged TV licence Pension Credit requirement

Whether aged individuals must claim Pension Credit in order to qualify for a free TV licence.

**Type:** bool

**Current value:** True

---

### gov.dcms.bbc.tv_licence.colour
**Label:** TV Licence fee

Full TV licence for a colour TV, before any discounts are applied.

**Type:** float

**Current value:** 159.0

---

### gov.dcms.bbc.tv_licence.tv_ownership
**Label:** TV ownership rate

Percentage of households which own a TV.

**Type:** float

**Current value:** 0.9544

---

### gov.hmrc.fuel_duty.petrol_and_diesel
**Label:** Fuel duty rate (petrol and diesel)

Fuel duty rate per litre of petrol and diesel.

**Type:** float

**Current value:** 0.5295

---

### gov.hmrc.national_insurance.class_4.rates.additional
**Label:** NI Class 4 additional rate

The additional National Insurance rate paid above the Upper Profits Limit for self-employed profits

**Type:** float

**Current value:** 0.02

---

### gov.hmrc.national_insurance.class_4.rates.main
**Label:** NI Class 4 main rate

The main National Insurance rate paid between the Lower and Upper Profits Limits for self-employed profits

**Type:** float

**Current value:** 0.06

---

### gov.hmrc.national_insurance.class_4.thresholds.upper_profits_limit
**Label:** NI Upper Profits Limit

The Upper Profits Limit is the threshold at which self-employed earners pay the additional Class 4 National Insurance rate

**Type:** int

**Current value:** 50270

---

### gov.hmrc.national_insurance.class_4.thresholds.lower_profits_limit
**Label:** NI Lower Profits Limit

The Lower Profits Limit is the threshold at which self-employed earners pay the main Class 4 National Insurance rate

**Type:** float

**Current value:** 12887.282850779511

---

### gov.hmrc.national_insurance.class_2.flat_rate
**Label:** NI Class 2 Flat Rate

Flat rate National Insurance contribution for self-employed earners

**Type:** int

**Current value:** 0

---

### gov.hmrc.national_insurance.class_2.small_profits_threshold
**Label:** NI Class 2 Small Profits Threshold

Small profits National Insurance threshold for self-employed earners

**Type:** float

**Current value:** 7453.631621187801

---

### gov.hmrc.national_insurance.class_1.rates.employee.additional
**Label:** NI Class 1 additional rate

The Class 1 National Insurance additional rate is paid on employment earnings above the Upper Earnings Limit

**Type:** float

**Current value:** 0.0185

---

### gov.hmrc.national_insurance.class_1.rates.employee.main
**Label:** NI Class 1 main rate

The Class 1 National Insurance main rate is paid on employment earnings between the Primary Threshold and the Upper Earnings Limit

**Type:** float

**Current value:** 0.08

---

### gov.hmrc.national_insurance.class_1.rates.employer
**Label:** NI Employer rate

National Insurance contribution rate by employers on earnings above the Secondary Threshold

**Type:** float

**Current value:** 0.138

---

### gov.hmrc.national_insurance.class_1.thresholds.lower_earnings_limit
**Label:** NI Lower Earnings Limit

Lower earnings limit for National Insurance

**Type:** int

**Current value:** 123

---

### gov.hmrc.national_insurance.class_1.thresholds.primary_threshold
**Label:** NI Primary Threshold

The Primary Threshold is the lower bound for the main rate of Class 1 National Insurance

**Type:** float

**Current value:** 241.73

---

### gov.hmrc.national_insurance.class_1.thresholds.secondary_threshold
**Label:** NI Secondary Threshold

Secondary threshold for National Insurance

**Type:** int

**Current value:** 175

---

### gov.hmrc.national_insurance.class_1.thresholds.upper_earnings_limit
**Label:** NI Upper Earnings Limit

The Upper Earnings Limit is the upper bound for the main rate of Class 1 National Insurance

**Type:** float

**Current value:** 966.73

---

### gov.hmrc.stamp_duty.abolish
**Label:** Abolish SDLT

Abolish Stamp Duty Land Tax.

**Type:** bool

**Current value:** False

---

### gov.hmrc.stamp_duty.residential.purchase.additional.min
**Label:** Stamp Duty secondary residence minimum value

Minimum value for taxability of additional residential property

**Type:** int

**Current value:** 40000

---

### gov.hmrc.stamp_duty.residential.purchase.main.first.max
**Label:** Stamp Duty first home value limit

Maximum value for a first-property purchase to receive the Stamp Duty relief for first-time buyers. Increasing this value will underestimate the number of claims for FTBR, as the model will not add new claims.

**Type:** int

**Current value:** 500000

---

### gov.hmrc.stamp_duty.property_sale_rate
**Label:** percentage of properties sold

This percentage of properties are sold every year.

**Type:** float

**Current value:** 0.045

---

### gov.hmrc.income_tax.allowances.property_allowance
**Label:** Property Allowance

Amount of income from property untaxed per year

**Type:** int

**Current value:** 1000

---

### gov.hmrc.income_tax.allowances.marriage_allowance.takeup_rate
**Label:** Marriage Allowance take-up rate

Percentage of eligible couples who claim Marriage Allowance.

**Type:** int

**Current value:** 1

---

### gov.hmrc.income_tax.allowances.marriage_allowance.max
**Label:** Marriage Allowance maximum percentage

Maximum Marriage Allowance taxable income reduction, as a percentage of the full Personal Allowance

**Type:** float

**Current value:** 0.1

---

### gov.hmrc.income_tax.allowances.marriage_allowance.rounding_increment
**Label:** Marriage Allowance rounding increment

The Marriage Allowance is rounded up by this increment.

**Type:** int

**Current value:** 10

---

### gov.hmrc.income_tax.allowances.personal_allowance.reduction_rate
**Label:** Personal Allowance phase-out rate

Reduction rate for the Personal Allowance

**Type:** float

**Current value:** 0.5

---

### gov.hmrc.income_tax.allowances.personal_allowance.amount
**Label:** Personal allowance

The Personal Allowance is deducted from general income

**Type:** int

**Current value:** 12570

---

### gov.hmrc.income_tax.allowances.personal_allowance.maximum_ANI
**Label:** Personal Allowance phase-out threshold

Maximum adjusted net income before the Personal Allowance is reduced

**Type:** int

**Current value:** 100000

---

### gov.hmrc.income_tax.allowances.trading_allowance
**Label:** Trading Allowance

Amount of trading income untaxed per year

**Type:** int

**Current value:** 1000

---

### gov.hmrc.income_tax.allowances.dividend_allowance
**Label:** Dividend Allowance

Amount of dividend income untaxed per year

**Type:** int

**Current value:** 500

---

### gov.hmrc.income_tax.rates.uk[0].rate
**Label:** Basic rate

The basic rate is the first of three tax brackets on all income, after allowances are deducted

**Type:** float

**Current value:** 0.2

---

### gov.hmrc.income_tax.rates.uk[1].threshold
**Label:** Higher rate threshold

The lower threshold for the higher rate of income tax (and therefore the upper threshold of the basic rate)

**Type:** int

**Current value:** 37700

---

### gov.hmrc.income_tax.rates.uk[1].rate
**Label:** Higher rate

The higher rate is the middle tax bracket on earned income.

**Type:** float

**Current value:** 0.4

---

### gov.hmrc.income_tax.rates.uk[2].threshold
**Label:** Additional rate threshold

The lower threshold for the additional rate

**Type:** int

**Current value:** 125140

---

### gov.hmrc.income_tax.rates.uk[2].rate
**Label:** Additional rate

The additional rate is the highest tax bracket, with no upper bound

**Type:** float

**Current value:** 0.45

---

### gov.hmrc.income_tax.rates.uk[3].threshold
**Label:** Extra tax bracket threshold

The lower threshold for the extra bracket rate.

**Type:** int

**Current value:** 10000000

---

### gov.hmrc.income_tax.rates.uk[3].rate
**Label:** Extra tax bracket rate

An extra tax bracket.

**Type:** float

**Current value:** 0.45

---

### gov.hmrc.income_tax.rates.dividends[0].threshold
**Label:** Dividends basic rate threshold

**Type:** int

**Current value:** 0

---

### gov.hmrc.income_tax.rates.dividends[0].rate
**Label:** Dividends basic rate

**Type:** float

**Current value:** 0.0875

---

### gov.hmrc.income_tax.rates.dividends[1].threshold
**Label:** Dividends higher rate threshold

**Type:** int

**Current value:** 37500

---

### gov.hmrc.income_tax.rates.dividends[1].rate
**Label:** Dividends higher rate

**Type:** float

**Current value:** 0.3375

---

### gov.hmrc.income_tax.rates.dividends[2].threshold
**Label:** Dividends additional rate threshold

**Type:** int

**Current value:** 150000

---

### gov.hmrc.income_tax.rates.dividends[2].rate
**Label:** Dividends additional rate

**Type:** float

**Current value:** 0.3935

---

### gov.hmrc.income_tax.rates.dividends[3].threshold
**Label:** Extra dividend tax bracket threshold

The lower threshold for the extra dividend bracket rate.

**Type:** int

**Current value:** 10000000

---

### gov.hmrc.income_tax.rates.dividends[3].rate
**Label:** Extra dividend tax bracket rate

An extra dividend tax bracket.

**Type:** float

**Current value:** 0.3935

---

### gov.hmrc.income_tax.charges.CB_HITC.phase_out_end
**Label:** Child Benefit Tax Charge phase-out end

Income after which the Child Benefit is fully phased out

**Type:** int

**Current value:** 80000

---

### gov.hmrc.income_tax.charges.CB_HITC.phase_out_start
**Label:** Child Benefit Tax Charge phase-out threshold

Income after which the Child Benefit phases out

**Type:** int

**Current value:** 60000

---

### gov.hmrc.tax_free_childcare.minimum_weekly_hours
**Label:** Tax-free childcare weekly work hours minimum

HMRC limits tax-free childcare to benefit units in which each spouse earns at least the product of their minimum wage and this number of hours per week.

**Type:** int

**Current value:** 16

---

### gov.hmrc.tax_free_childcare.income.income_limit
**Label:** Tax-free childcare maximum adjusted income threshold

HMRC limits tax-free childcare eligibility to households where individual adjusted income does not exceed this yearly threshold.

**Type:** int

**Current value:** 100000

---

### gov.hmrc.tax_free_childcare.age.disability
**Label:** Tax-free childcare disability age limit

HMRC extends the tax-free childcare program eligibility to children with disabilities up to this age threshold.

**Type:** int

**Current value:** 17

---

### gov.hmrc.tax_free_childcare.age.standard
**Label:** Tax-free childcare standard age limit

HMRC extends the tax-free childcare program eligibility to children up to this age threshold.

**Type:** int

**Current value:** 12

---

### gov.hmrc.tax_free_childcare.contribution.standard_child
**Label:** Tax-free childcare standard yearly limit

HMRC provides tax-free childcare contribution up to this yearly amount for households with children under standard eligibility.

**Type:** int

**Current value:** 2000

---

### gov.hmrc.tax_free_childcare.contribution.disabled_child
**Label:** Tax-free childcare disabled child yearly limit

HMRC provides tax-free childcare contribution up to this yearly amount for households with disabled children.

**Type:** int

**Current value:** 4000

---

### gov.hmrc.vat.standard_rate
**Label:** VAT standard rate

The highest VAT rate, applicable to most goods and services.

**Type:** float

**Current value:** 0.2

---

### gov.hmrc.vat.reduced_rate
**Label:** VAT reduced rate

A reduced rate of VAT applicable to select goods and services (domestic fuel and power).

**Type:** float

**Current value:** 0.05

---

### gov.hmrc.cgt.additional_rate
**Label:** Capital Gains Tax additional rate

Capital gains tax rate on additional rate taxpayers. This parameter is under active development and reforms including it should not be cited.

**Type:** float

**Current value:** 0.2

---

### gov.hmrc.cgt.annual_exempt_amount
**Label:** Annual Exempt Amount

Annual Exempt Amount for individuals. This parameter is under active development and reforms including it should not be cited.

**Type:** float

**Current value:** 3075.723830734966

---

### gov.hmrc.cgt.higher_rate
**Label:** Capital Gains Tax higher rate

Capital gains tax rate on higher rate taxpayers. This parameter is under active development and reforms including it should not be cited.

**Type:** float

**Current value:** 0.2

---

### gov.hmrc.cgt.basic_rate
**Label:** Capital Gains Tax basic rate

Capital gains tax rate on basic rate taxpayers. This parameter is under active development and reforms including it should not be cited.

**Type:** float

**Current value:** 0.1

---

### gov.hmrc.child_benefit.amount.eldest
**Label:** Child Benefit (eldest)

Child Benefit amount for the eldest or only child

**Type:** float

**Current value:** 25.6

---

### gov.hmrc.child_benefit.amount.additional
**Label:** Child Benefit (additional)

Child Benefit amount for each additional child

**Type:** float

**Current value:** 16.95

---

### gov.hmrc.child_benefit.opt_out_rate
**Label:** Child Benefit HITC-liable opt-out rate

Percentage of fully HITC-liable families who opt out of Child Benefit.

**Type:** float

**Current value:** 0.23

---

### gov.hmrc.pensions.pension_contributions_relief_age_limit
**Label:** pension contributions relief age limit

The pensions contributions relief is limited to filers below this age threshold.

**Type:** int

**Current value:** 75

---

### gov.treasury.cost_of_living_support.pensioners.amount
**Label:** Payment to pensioner households

Payment to pensioner households receiving benefits.

**Type:** int

**Current value:** 0

---

### gov.treasury.cost_of_living_support.means_tested_households.amount
**Label:** Payment to households on means-tested benefits

Payment to households on means-tested benefits.

**Type:** int

**Current value:** 0

---

### gov.treasury.cost_of_living_support.disabled.amount
**Label:** Payment to households on disability benefits

Payment to households receiving disability benefits.

**Type:** int

**Current value:** 0

---

### gov.treasury.energy_bills_rebate.energy_bills_credit
**Label:** Energy bills credit

Credit on energy bills paid to households. This is modeled as a flat transfer to households.

**Type:** int

**Current value:** 0

---

### gov.treasury.energy_bills_rebate.council_tax_rebate.amount
**Label:** Council Tax rebate amount

Council Tax rebate paid to households in qualifying Council Tax bands under the Energy Bills Rebate.

**Type:** int

**Current value:** 0

---

