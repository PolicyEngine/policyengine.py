# Breakdown Parents with Labels - Complete Analysis

This document lists all 432 breakdown parents that have labels in policyengine-us.
For each parent, we show how labels are currently generated and how they could be improved.

**Total breakdown parents with labels:** 432
**Total child parameters covered:** 40,115

---

## Summary Table

| # | Parent Path | Label | Dimensions | Children |
|---|-------------|-------|------------|----------|
| 1 | `gov.states.nc.ncdhhs.scca.childcare_market_rates` | North Carolina SCCA program market rates | 2 | 12,896 |
| 2 | `gov.states.tx.twc.ccs.payment.rates` | Texas CCS maximum reimbursement rates by workforce board region | 5 | 8,064 |
| 3 | `gov.irs.deductions.itemized.salt_and_real_estate.state_sales_tax_table.tax` | Optional state sales tax table | 3 | 6,726 |
| 4 | `gov.aca.state_rating_area_cost` | Second Lowest Cost Silver Plan premiums by rating area | 2 | 3,953 |
| 5 | `gov.states.or.tax.income.credits.wfhdc.match` | Oregon working family household and dependent care credit credit rate | 2 | 186 |
| 6 | `gov.states.il.dhs.aabd.payment.utility.water` | Illinois AABD water allowance by area | 2 | 152 |
| 7 | `gov.states.il.dhs.aabd.payment.utility.metered_gas` | Illinois AABD metered gas allowance by area | 2 | 152 |
| 8 | `gov.states.il.dhs.aabd.payment.utility.electricity` | Illinois AABD electricity allowance by area | 2 | 152 |
| 9 | `gov.states.il.dhs.aabd.payment.utility.coal` | Illinois AABD coal allowance by area | 2 | 152 |
| 10 | `gov.states.il.dhs.aabd.payment.utility.cooking_fuel` | Illinois AABD cooking fuel allowance by area | 2 | 152 |
| 11 | `gov.states.il.dhs.aabd.payment.utility.bottled_gas` | Illinois AABD bottled gas allowance by area | 2 | 152 |
| 12 | `gov.states.il.dhs.aabd.payment.utility.fuel_oil` | Illinois AABD fuel oil allowance by area | 2 | 152 |
| 13 | `gov.states.dc.dhs.ccsp.reimbursement_rates` | DC CCSP reimbursement rates | 3 | 126 |
| 14 | `gov.states.vt.tax.income.credits.renter.income_limit_ami.fifty_percent` | Vermont partial renter credit income limit | 1 | 112 |
| 15 | `gov.states.vt.tax.income.credits.renter.income_limit_ami.thirty_percent` | Vermont full renter credit income limit | 1 | 112 |
| 16 | `gov.states.vt.tax.income.credits.renter.fair_market_rent` | Vermont fair market rent amount | 1 | 112 |
| 17 | `gov.states.dc.doee.liheap.payment.gas` | DC LIHEAP Gas payment | 3 | 80 |
| 18 | `gov.states.dc.doee.liheap.payment.electricity` | DC LIHEAP Electricity payment | 3 | 80 |
| 19 | `gov.usda.snap.max_allotment.main` | SNAP max allotment | 2 | 63 |
| 20 | `calibration.gov.aca.enrollment.state` | ACA enrollment by state | 1 | 59 |
| 21 | `calibration.gov.aca.spending.state` | Federal ACA spending by state | 1 | 59 |
| 22 | `calibration.gov.hhs.medicaid.enrollment.non_expansion_adults` | Non-expansion adults enrolled in Medicaid | 1 | 59 |
| 23 | `calibration.gov.hhs.medicaid.enrollment.aged` | Aged persons enrolled in Medicaid | 1 | 59 |
| 24 | `calibration.gov.hhs.medicaid.enrollment.expansion_adults` | Expansion adults enrolled in Medicaid | 1 | 59 |
| 25 | `calibration.gov.hhs.medicaid.enrollment.disabled` | Disabled persons enrolled in Medicaid | 1 | 59 |
| 26 | `calibration.gov.hhs.medicaid.enrollment.child` | Children enrolled in Medicaid | 1 | 59 |
| 27 | `calibration.gov.hhs.medicaid.spending.by_eligibility_group.non_expansion_adults` | Medicaid spending for non-expansion adult enrollees | 1 | 59 |
| 28 | `calibration.gov.hhs.medicaid.spending.by_eligibility_group.aged` | Medicaid spending for aged enrollees | 1 | 59 |
| 29 | `calibration.gov.hhs.medicaid.spending.by_eligibility_group.expansion_adults` | Medicaid spending for expansion adult enrollees | 1 | 59 |
| 30 | `calibration.gov.hhs.medicaid.spending.by_eligibility_group.disabled` | Medicaid spending for disabled enrollees | 1 | 59 |
| 31 | `calibration.gov.hhs.medicaid.spending.by_eligibility_group.child` | Medicaid spending for child enrollees | 1 | 59 |
| 32 | `calibration.gov.hhs.medicaid.spending.totals.state` | State Medicaid spending | 1 | 59 |
| 33 | `calibration.gov.hhs.medicaid.spending.totals.federal` | Federal Medicaid spending by state | 1 | 59 |
| 34 | `calibration.gov.hhs.cms.chip.enrollment.total` | Enrollment in all CHIP programs by state | 1 | 59 |
| 35 | `calibration.gov.hhs.cms.chip.enrollment.medicaid_expansion_chip` | Enrollment in Medicaid Expansion CHIP programs by state | 1 | 59 |
| 36 | `calibration.gov.hhs.cms.chip.enrollment.separate_chip` | Enrollment in Separate CHIP programs by state | 1 | 59 |
| 37 | `calibration.gov.hhs.cms.chip.spending.separate_chip.state` | State share of CHIP spending for separate CHIP programs and coverage of pregnant women | 1 | 59 |
| 38 | `calibration.gov.hhs.cms.chip.spending.separate_chip.total` | CHIP spending for separate CHIP programs and coverage of pregnant women | 1 | 59 |
| 39 | `calibration.gov.hhs.cms.chip.spending.separate_chip.federal` | Federal share of CHIP spending for separate CHIP programs and coverage of pregnant women | 1 | 59 |
| 40 | `calibration.gov.hhs.cms.chip.spending.medicaid_expansion_chip.state` | State share of CHIP spending for Medicaid-expansion populations | 1 | 59 |
| 41 | `calibration.gov.hhs.cms.chip.spending.medicaid_expansion_chip.total` | CHIP spending for Medicaid-expansion populations | 1 | 59 |
| 42 | `calibration.gov.hhs.cms.chip.spending.medicaid_expansion_chip.federal` | Federal share of CHIP spending for Medicaid-expansion populations | 1 | 59 |
| 43 | `calibration.gov.hhs.cms.chip.spending.total.state` | State share of total CHIP spending | 1 | 59 |
| 44 | `calibration.gov.hhs.cms.chip.spending.total.total` | Total CHIP spending | 1 | 59 |
| 45 | `calibration.gov.hhs.cms.chip.spending.total.federal` | Federal share of total CHIP spending | 1 | 59 |
| 46 | `calibration.gov.hhs.cms.chip.spending.program_admin.state` | State share of state program administration costs for CHIP | 1 | 59 |
| 47 | `calibration.gov.hhs.cms.chip.spending.program_admin.total` | Total state program administration costs for CHIP | 1 | 59 |
| 48 | `calibration.gov.hhs.cms.chip.spending.program_admin.federal` | Federal share of state program administration costs for CHIP | 1 | 59 |
| 49 | `gov.aca.enrollment.state` | ACA enrollment by state | 1 | 59 |
| 50 | `gov.aca.family_tier_states` | Family tier rating states | 1 | 59 |
| 51 | `gov.aca.spending.state` | Federal ACA spending by state | 1 | 59 |
| 52 | `gov.usda.snap.income.deductions.self_employment.rate` | SNAP self-employment simplified deduction rate | 1 | 59 |
| 53 | `gov.usda.snap.income.deductions.self_employment.expense_based_deduction_applies` | SNAP self-employment expense-based deduction applies | 1 | 59 |
| 54 | `gov.usda.snap.income.deductions.excess_shelter_expense.homeless.available` | SNAP homeless shelter deduction available | 1 | 59 |
| 55 | `gov.usda.snap.income.deductions.child_support` | SNAP child support gross income deduction | 1 | 59 |
| 56 | `gov.usda.snap.income.deductions.utility.single.water` | SNAP standard utility allowance for water expenses | 1 | 59 |
| 57 | `gov.usda.snap.income.deductions.utility.single.electricity` | SNAP standard utility allowance for electricity expenses | 1 | 59 |
| 58 | `gov.usda.snap.income.deductions.utility.single.trash` | SNAP standard utility allowance for trash expenses | 1 | 59 |
| 59 | `gov.usda.snap.income.deductions.utility.single.sewage` | SNAP standard utility allowance for sewage expenses | 1 | 59 |
| 60 | `gov.usda.snap.income.deductions.utility.single.gas_and_fuel` | SNAP standard utility allowance for gas and fuel expenses | 1 | 59 |
| 61 | `gov.usda.snap.income.deductions.utility.single.phone` | SNAP standard utility allowance for phone expenses | 1 | 59 |
| 62 | `gov.usda.snap.income.deductions.utility.always_standard` | SNAP States using SUA | 1 | 59 |
| 63 | `gov.usda.snap.income.deductions.utility.standard.main` | SNAP standard utility allowance | 1 | 59 |
| 64 | `gov.usda.snap.income.deductions.utility.limited.active` | SNAP Limited Utility Allowance active | 1 | 59 |
| 65 | `gov.usda.snap.income.deductions.utility.limited.main` | SNAP limited utility allowance | 1 | 59 |
| 66 | `gov.usda.snap.emergency_allotment.in_effect` | SNAP emergency allotment in effect | 1 | 59 |
| 67 | `gov.hhs.head_start.spending` | Head Start state-level spending amount | 1 | 59 |
| 68 | `gov.hhs.head_start.enrollment` | Head Start state-level enrollment | 1 | 59 |
| 69 | `gov.hhs.head_start.early_head_start.spending` | Early Head Start state-level funding amount | 1 | 59 |
| 70 | `gov.hhs.head_start.early_head_start.enrollment` | Early Head Start state-level enrollment | 1 | 59 |
| 71 | `gov.hhs.medicaid.eligibility.undocumented_immigrant` | Medicaid undocumented immigrant eligibility | 1 | 59 |
| 72 | `gov.hhs.medicaid.eligibility.categories.young_child.income_limit` | Medicaid young child income limit | 1 | 59 |
| 73 | `gov.hhs.medicaid.eligibility.categories.senior_or_disabled.income.limit.couple` | Medicaid senior or disabled income limit (couple) | 1 | 59 |
| 74 | `gov.hhs.medicaid.eligibility.categories.senior_or_disabled.income.limit.individual` | Medicaid senior or disabled income limit (individual) | 1 | 59 |
| 75 | `gov.hhs.medicaid.eligibility.categories.senior_or_disabled.income.disregard.couple` | Medicaid senior or disabled income disregard (couple) | 1 | 59 |
| 76 | `gov.hhs.medicaid.eligibility.categories.senior_or_disabled.income.disregard.individual` | Medicaid senior or disabled income disregard (individual) | 1 | 59 |
| 77 | `gov.hhs.medicaid.eligibility.categories.senior_or_disabled.assets.limit.couple` | Medicaid senior or disabled asset limit (couple) | 1 | 59 |
| 78 | `gov.hhs.medicaid.eligibility.categories.senior_or_disabled.assets.limit.individual` | Medicaid senior or disabled asset limit (individual) | 1 | 59 |
| 79 | `gov.hhs.medicaid.eligibility.categories.young_adult.income_limit` | Medicaid pregnant income limit | 1 | 59 |
| 80 | `gov.hhs.medicaid.eligibility.categories.older_child.income_limit` | Medicaid older child income limit | 1 | 59 |
| 81 | `gov.hhs.medicaid.eligibility.categories.parent.income_limit` | Medicaid parent income limit | 1 | 59 |
| 82 | `gov.hhs.medicaid.eligibility.categories.pregnant.income_limit` | Medicaid pregnant income limit | 1 | 59 |
| 83 | `gov.hhs.medicaid.eligibility.categories.pregnant.postpartum_coverage` | Medicaid postpartum coverage | 1 | 59 |
| 84 | `gov.hhs.medicaid.eligibility.categories.ssi_recipient.is_covered` | Medicaid covers all SSI recipients | 1 | 59 |
| 85 | `gov.hhs.medicaid.eligibility.categories.infant.income_limit` | Medicaid infant income limit | 1 | 59 |
| 86 | `gov.hhs.medicaid.eligibility.categories.adult.income_limit` | Medicaid adult income limit | 1 | 59 |
| 87 | `gov.hhs.chip.fcep.income_limit` | CHIP FCEP pregnant income limit | 1 | 59 |
| 88 | `gov.hhs.chip.pregnant.income_limit` | CHIP pregnant income limit | 1 | 59 |
| 89 | `gov.hhs.chip.child.income_limit` | CHIP child income limit | 1 | 59 |
| 90 | `gov.hhs.medicare.savings_programs.eligibility.asset.applies` | MSP asset test applies | 1 | 59 |
| 91 | `gov.hhs.tanf.non_cash.income_limit.gross` | SNAP BBCE gross income limit | 1 | 59 |
| 92 | `gov.states.ma.dta.ssp.amount` | Massachusetts SSP payment amount | 3 | 48 |
| 93 | `gov.states.ma.eec.ccfa.reimbursement_rates.center_based.school_age` | Massachusetts CCFA center-based school age reimbursement rates | 3 | 48 |
| 94 | `gov.contrib.additional_tax_bracket.bracket.thresholds` | Individual income tax rate thresholds | 2 | 40 |
| 95 | `gov.usda.snap.income.deductions.standard` | SNAP standard deduction | 2 | 36 |
| 96 | `gov.irs.income.bracket.thresholds` | Individual income tax rate thresholds | 2 | 35 |
| 97 | `gov.states.ma.eec.ccfa.copay.fee_level.fee_percentages` | Massachusetts CCFA fee percentage by fee level | 1 | 29 |
| 98 | `gov.states.pa.dhs.tanf.standard_of_need.amount` | Pennsylvania TANF Standard of Need by county group | 1 | 24 |
| 99 | `gov.states.pa.dhs.tanf.family_size_allowance.amount` | Pennsylvania TANF family size allowance by county group | 1 | 24 |
| 100 | `gov.states.ma.doer.liheap.standard.amount.non_subsidized` | Massachusetts LIHEAP homeowners and non subsidized housing payment amount | 2 | 21 |
| 101 | `gov.states.ma.doer.liheap.standard.amount.subsidized` | Massachusetts LIHEAP subsidized housing payment amount | 2 | 21 |
| 102 | `gov.states.mn.dcyf.mfip.transitional_standard.amount` | Minnesota MFIP Transitional Standard amount | 1 | 20 |
| 103 | `gov.states.dc.dhs.tanf.standard_payment.amount` | DC TANF standard payment amount | 1 | 20 |
| 104 | `gov.hud.ami_limit.family_size` | HUD area median income limit | 2 | 20 |
| 105 | `gov.states.ut.dwf.fep.standard_needs_budget.amount` | Utah FEP Standard Needs Budget (SNB) | 1 | 19 |
| 106 | `gov.states.ut.dwf.fep.payment_standard.amount` | Utah FEP maximum benefit amount | 1 | 19 |
| 107 | `gov.states.mo.dss.tanf.standard_of_need.amount` | Missouri TANF standard of need | 1 | 19 |
| 108 | `gov.states.ar.dhs.tea.payment_standard.amount` | Arkansas TEA payment standard amount | 1 | 19 |
| 109 | `gov.usda.school_meals.amount.nslp` | National School Lunch Program value | 2 | 18 |
| 110 | `gov.usda.school_meals.amount.sbp` | School Breakfast Program value | 2 | 18 |
| 111 | `gov.contrib.harris.capital_gains.thresholds` | Harris capital gains tax rate thresholds | 2 | 15 |
| 112 | `gov.states.oh.odjfs.owf.payment_standard.amounts` | Ohio Works First payment standard amounts | 1 | 15 |
| 113 | `gov.states.nc.ncdhhs.tanf.need_standard.main` | North Carolina TANF monthly need standard | 1 | 14 |
| 114 | `gov.states.ma.eec.ccfa.copay.fee_level.income_ratio_increments` | Massachusetts CCFA income ratio increments by household size | 1 | 13 |
| 115 | `gov.states.ma.eec.ccfa.reimbursement_rates.head_start_partner_and_kindergarten` | Massachusetts CCFA head start partner and kindergarten reimbursement rates | 2 | 12 |
| 116 | `gov.states.ma.eec.ccfa.reimbursement_rates.center_based.early_education` | Massachusetts CCFA center-based early education reimbursement rates | 2 | 12 |
| 117 | `gov.hhs.fpg` | Federal poverty guidelines | 2 | 12 |
| 118 | `gov.states.ga.dfcs.tanf.financial_standards.family_maximum.base` | Georgia TANF family maximum base amount | 1 | 11 |
| 119 | `gov.states.ga.dfcs.tanf.financial_standards.standard_of_need.base` | Georgia TANF standard of need base amount | 1 | 11 |
| 120 | `gov.usda.snap.income.deductions.utility.standard.by_household_size.amount` | SNAP SUAs by household size | 2 | 10 |
| 121 | `gov.usda.snap.income.deductions.utility.limited.by_household_size.amount` | SNAP LUAs by household size | 2 | 10 |
| 122 | `gov.states.ms.dhs.tanf.need_standard.amount` | Mississippi TANF need standard amount | 1 | 10 |
| 123 | `gov.states.in.fssa.tanf.standard_of_need.amount` | Indiana TANF standard of need amount | 1 | 10 |
| 124 | `gov.states.ca.cdss.tanf.cash.monthly_payment.region1.exempt` | California CalWORKs monthly payment level - exempt map region 1 | 1 | 10 |
| 125 | `gov.states.ca.cdss.tanf.cash.monthly_payment.region1.non_exempt` | California CalWORKs monthly payment level - non-exempt map region 1 | 1 | 10 |
| 126 | `gov.states.ca.cdss.tanf.cash.monthly_payment.region2.exempt` | California CalWORKs monthly payment level - exempt map region 2 | 1 | 10 |
| 127 | `gov.states.ca.cdss.tanf.cash.monthly_payment.region2.non_exempt` | California CalWORKs monthly payment level - non-exempt map region 2 | 1 | 10 |
| 128 | `gov.states.ca.cdss.tanf.cash.income.monthly_limit.region1.main` | California CalWORKs monthly income limit for region 1 | 1 | 10 |
| 129 | `gov.states.ca.cdss.tanf.cash.income.monthly_limit.region2.main` | California CalWORKs monthly income limit for region 2 | 1 | 10 |
| 130 | `gov.states.ks.dcf.tanf.payment_standard.amount` | Kansas TANF payment standard amount | 1 | 10 |
| 131 | `gov.states.ne.dhhs.adc.benefit.standard_of_need.amount` | Nebraska ADC standard of need | 1 | 10 |
| 132 | `gov.states.id.tafi.work_incentive_table.amount` | Idaho TAFI work incentive table amount | 1 | 10 |
| 133 | `gov.states.or.odhs.tanf.income.countable_income_limit.amount` | Oregon TANF countable income limit | 1 | 10 |
| 134 | `gov.states.or.odhs.tanf.income.adjusted_income_limit.amount` | Oregon TANF adjusted income limit | 1 | 10 |
| 135 | `gov.states.or.odhs.tanf.payment_standard.amount` | Oregon TANF payment standard | 1 | 10 |
| 136 | `gov.states.wa.dshs.tanf.income.limit` | Washington TANF maximum gross earned income limit | 1 | 10 |
| 137 | `gov.states.wa.dshs.tanf.payment_standard.amount` | Washington TANF payment standard | 1 | 10 |
| 138 | `gov.contrib.additional_tax_bracket.bracket.rates` | Individual income tax rates | 1 | 8 |
| 139 | `gov.states.ma.dta.tcap.eaedc.standard_assistance.amount.additional` | Massachusetts EAEDC standard assistance additional amount | 1 | 8 |
| 140 | `gov.states.ma.dta.tcap.eaedc.standard_assistance.amount.base` | Massachusetts EAEDC standard assistance base amount | 1 | 8 |
| 141 | `gov.states.nj.njdhs.tanf.maximum_benefit.main` | New Jersey TANF monthly maximum benefit | 1 | 8 |
| 142 | `gov.states.nj.njdhs.tanf.maximum_allowable_income.main` | New Jersey TANF monthly maximum allowable income | 1 | 8 |
| 143 | `gov.states.il.dhs.aabd.payment.personal_allowance.bedfast` | Illinois AABD bedfast applicant personal allowance | 1 | 8 |
| 144 | `gov.states.il.dhs.aabd.payment.personal_allowance.active` | Illinois AABD active applicant personal allowance | 1 | 8 |
| 145 | `gov.usda.snap.income.deductions.excess_shelter_expense.cap` | SNAP maximum shelter deduction | 1 | 7 |
| 146 | `gov.states.ma.doer.liheap.hecs.amount.non_subsidized` | Massachusetts LIHEAP High Energy Cost Supplement payment for homeowners and non-subsidized housing applicants | 1 | 7 |
| 147 | `gov.states.ma.doer.liheap.hecs.amount.subsidized` | Massachusetts LIHEAP High Energy Cost Supplement payment for subsidized housing applicants | 1 | 7 |
| 148 | `gov.states.ky.dcbs.ktap.benefit.standard_of_need` | Kentucky K-TAP standard of need | 1 | 7 |
| 149 | `gov.states.ky.dcbs.ktap.benefit.payment_maximum` | Kentucky K-TAP payment maximum | 1 | 7 |
| 150 | `gov.irs.income.bracket.rates` | Individual income tax rates | 1 | 7 |
| 151 | `gov.aca.family_tier_ratings.ny` | ACA premium family tier multipliers - NY | 1 | 6 |
| 152 | `gov.aca.family_tier_ratings.vt` | ACA premium family tier multipliers - VT | 1 | 6 |
| 153 | `gov.usda.wic.nutritional_risk` | WIC nutritional risk | 1 | 6 |
| 154 | `gov.usda.wic.takeup` | WIC takeup rate | 1 | 6 |
| 155 | `gov.states.ma.doer.liheap.hecs.eligibility.prior_year_cost_threshold` | Massachusetts LIHEAP HECS payment threshold | 1 | 6 |
| 156 | `gov.states.ny.otda.tanf.need_standard.main` | New York TANF monthly income limit | 1 | 6 |
| 157 | `gov.states.ny.otda.tanf.grant_standard.main` | New York TANF monthly income limit | 1 | 6 |
| 158 | `calibration.gov.hhs.medicaid.totals.per_capita` | Per-capita Medicaid cost for other adults | 1 | 5 |
| 159 | `gov.territories.pr.tax.income.taxable_income.exemptions.personal` | Puerto Rico personal exemption amount | 1 | 5 |
| 160 | `gov.contrib.biden.budget_2025.capital_gains.income_threshold` | Threshold above which capital income is taxed as ordinary income | 1 | 5 |
| 161 | `gov.contrib.harris.lift.middle_class_tax_credit.phase_out.width` | Middle Class Tax Credit phase-out width | 1 | 5 |
| 162 | `gov.contrib.harris.lift.middle_class_tax_credit.phase_out.start` | Middle Class Tax Credit phase-out start | 1 | 5 |
| 163 | `gov.contrib.ubi_center.basic_income.agi_limit.amount` | Basic income AGI limit | 1 | 5 |
| 164 | `gov.contrib.ubi_center.basic_income.phase_out.end` | Basic income phase-out end | 1 | 5 |
| 165 | `gov.contrib.ubi_center.basic_income.phase_out.threshold` | Basic income phase-out threshold | 1 | 5 |
| 166 | `gov.contrib.ubi_center.flat_tax.exemption.agi` | Flat tax on AGI exemption amount | 1 | 5 |
| 167 | `gov.contrib.crfb.ss_credit.amount` | CRFB Social Security nonrefundable credit amount | 1 | 5 |
| 168 | `gov.contrib.local.nyc.stc.income_limit` | NYC School Tax Credit Income Limit | 1 | 5 |
| 169 | `gov.contrib.states.ri.dependent_exemption.phaseout.threshold` | Rhode Island dependent exemption phaseout threshold | 1 | 5 |
| 170 | `gov.contrib.states.ri.ctc.phaseout.threshold` | Rhode Island Child Tax Credit phaseout threshold | 1 | 5 |
| 171 | `gov.contrib.states.dc.property_tax.income_limit.non_elderly` | DC property tax credit non-elderly income limit | 1 | 5 |
| 172 | `gov.contrib.states.dc.property_tax.income_limit.elderly` | DC property tax credit elderly income limit | 1 | 5 |
| 173 | `gov.contrib.states.dc.property_tax.amount` | DC property tax credit amount | 1 | 5 |
| 174 | `gov.contrib.states.de.dependent_credit.phaseout.threshold` | Delaware dependent credit phaseout threshold | 1 | 5 |
| 175 | `gov.contrib.dc_kccatc.phase_out.threshold` | DC KCCATC phase-out threshold | 13 | 5 |
| 176 | `gov.contrib.congress.hawley.awra.phase_out.start` | American Worker Rebate Act phase-out start | 1 | 5 |
| 177 | `gov.contrib.congress.tlaib.end_child_poverty_act.filer_credit.phase_out.start` | End Child Poverty Act filer credit phase-out start | 1 | 5 |
| 178 | `gov.contrib.congress.tlaib.end_child_poverty_act.filer_credit.amount` | End Child Poverty Act filer credit amount | 1 | 5 |
| 179 | `gov.contrib.congress.tlaib.economic_dignity_for_all_agenda.end_child_poverty_act.filer_credit.phase_out.start` | Filer credit phase-out start | 1 | 5 |
| 180 | `gov.contrib.congress.tlaib.economic_dignity_for_all_agenda.end_child_poverty_act.filer_credit.amount` | Filer credit amount | 1 | 5 |
| 181 | `gov.contrib.congress.afa.ctc.phase_out.threshold.lower` | AFA CTC phase-out lower threshold | 1 | 5 |
| 182 | `gov.contrib.congress.afa.ctc.phase_out.threshold.higher` | AFA CTC phase-out higher threshold | 1 | 5 |
| 183 | `gov.local.ca.riv.general_relief.needs_standards.personal_needs` | Riverside County General Relief personal needs standard | 1 | 5 |
| 184 | `gov.local.ca.riv.general_relief.needs_standards.food` | Riverside County General Relief food needs standard | 1 | 5 |
| 185 | `gov.local.ca.riv.general_relief.needs_standards.housing` | Riverside County General Relief housing needs standard | 1 | 5 |
| 186 | `gov.local.ny.nyc.tax.income.credits.school.fixed.amount` | NYC School Tax Credit Fixed Amount | 1 | 5 |
| 187 | `gov.states.vt.tax.income.agi.retirement_income_exemption.social_security.reduction.end` | Vermont social security retirement income exemption income threshold | 1 | 5 |
| 188 | `gov.states.vt.tax.income.agi.retirement_income_exemption.social_security.reduction.start` | Vermont social security retirement income exemption reduction threshold | 1 | 5 |
| 189 | `gov.states.vt.tax.income.agi.retirement_income_exemption.csrs.reduction.end` | Vermont CSRS and military retirement income exemption income threshold | 1 | 5 |
| 190 | `gov.states.vt.tax.income.agi.retirement_income_exemption.csrs.reduction.start` | Vermont CSRS and military retirement income exemption reduction threshold | 1 | 5 |
| 191 | `gov.states.vt.tax.income.deductions.standard.base` | Vermont standard deduction | 1 | 5 |
| 192 | `gov.states.vt.tax.income.credits.cdcc.low_income.income_threshold` | Vermont low-income CDCC AGI limit | 1 | 5 |
| 193 | `gov.states.va.tax.income.subtractions.age_deduction.threshold` | Adjusted federal AGI threshold for VA taxpayers eligible for an age deduction | 1 | 5 |
| 194 | `gov.states.va.tax.income.deductions.itemized.applicable_amount` | Virginia itemized deduction applicable amount | 1 | 5 |
| 195 | `gov.states.va.tax.income.deductions.standard` | Virginia standard deduction | 1 | 5 |
| 196 | `gov.states.va.tax.income.rebate.amount` | Virginia rebate amount | 1 | 5 |
| 197 | `gov.states.va.tax.income.filing_requirement` | Virginia filing requirement | 1 | 5 |
| 198 | `gov.states.ut.tax.income.credits.ctc.reduction.start` | Utah child tax credit reduction start | 1 | 5 |
| 199 | `gov.states.ga.tax.income.deductions.standard.amount` | Georgia standard deduction amount | 1 | 5 |
| 200 | `gov.states.ga.tax.income.exemptions.personal.amount` | Georgia personal exemption amount | 1 | 5 |
| 201 | `gov.states.ga.tax.income.credits.surplus_tax_rebate.amount` | Georgia surplus tax rebate amount | 1 | 5 |
| 202 | `gov.states.ms.tax.income.deductions.standard.amount` | Mississippi standard deduction | 1 | 5 |
| 203 | `gov.states.ms.tax.income.exemptions.regular.amount` | Mississippi exemption | 1 | 5 |
| 204 | `gov.states.ms.tax.income.credits.charitable_contribution.cap` | Mississippi credit for contributions to foster organizations cap | 1 | 5 |
| 205 | `gov.states.mt.tax.income.deductions.itemized.federal_income_tax.cap` | Montana federal income tax deduction cap | 1 | 5 |
| 206 | `gov.states.mt.tax.income.deductions.standard.floor` | Montana minimum standard deduction | 1 | 5 |
| 207 | `gov.states.mt.tax.income.deductions.standard.cap` | Montana standard deduction max amount | 1 | 5 |
| 208 | `gov.states.mt.tax.income.social_security.amount.upper` | Montana social security benefits amount | 1 | 5 |
| 209 | `gov.states.mt.tax.income.social_security.amount.lower` | Montana social security benefits amount | 1 | 5 |
| 210 | `gov.states.mt.tax.income.main.capital_gains.rates.main` | Montana capital gains tax rate when nonqualified income exceeds threshold | 1 | 5 |
| 211 | `gov.states.mt.tax.income.main.capital_gains.threshold` | Montana capital gains tax threshold | 1 | 5 |
| 212 | `gov.states.mt.tax.income.exemptions.interest.cap` | Montana senior interest income exclusion cap | 1 | 5 |
| 213 | `gov.states.mt.tax.income.credits.rebate.amount` | Montana income tax rebate amount | 1 | 5 |
| 214 | `gov.states.mo.tax.income.deductions.federal_income_tax.cap` | Missouri federal income tax deduction caps | 1 | 5 |
| 215 | `gov.states.mo.tax.income.deductions.mo_private_pension_deduction_allowance` | Missouri private pension deduction allowance | 1 | 5 |
| 216 | `gov.states.mo.tax.income.deductions.social_security_and_public_pension.mo_ss_or_ssd_deduction_allowance` | Missouri social security or social security disability deduction allowance | 1 | 5 |
| 217 | `gov.states.mo.tax.income.deductions.social_security_and_public_pension.mo_public_pension_deduction_allowance` | Missouri Public Pension Deduction Allowance | 1 | 5 |
| 218 | `gov.states.mo.tax.income.deductions.social_security_and_public_pension.mo_ss_or_ssdi_exemption_threshold` | Missouri social security or social security disability income exemption threshold | 1 | 5 |
| 219 | `gov.states.ma.tax.income.deductions.rent.cap` | Massachusetts rental deduction cap. | 1 | 5 |
| 220 | `gov.states.ma.tax.income.exempt_status.limit.personal_exemption_added` | Massachusetts income tax exemption limit includes personal exemptions | 1 | 5 |
| 221 | `gov.states.ma.tax.income.exempt_status.limit.base` | AGI addition to limit to be exempt from Massachusetts income tax. | 1 | 5 |
| 222 | `gov.states.ma.tax.income.exemptions.interest.amount` | Massachusetts interest exemption | 1 | 5 |
| 223 | `gov.states.ma.tax.income.exemptions.personal` | Massachusetts income tax personal exemption | 1 | 5 |
| 224 | `gov.states.ma.tax.income.credits.senior_circuit_breaker.eligibility.max_income` | Massachusetts Senior Circuit Breaker maximum income | 1 | 5 |
| 225 | `gov.states.al.tax.income.deductions.standard.amount.max` | Alabama standard deduction maximum amount | 1 | 5 |
| 226 | `gov.states.al.tax.income.deductions.standard.amount.min` | Alabama standard deduction minimum amount | 1 | 5 |
| 227 | `gov.states.al.tax.income.deductions.standard.phase_out.increment` | Alabama standard deduction phase-out increment | 1 | 5 |
| 228 | `gov.states.al.tax.income.deductions.standard.phase_out.rate` | Alabama standard deduction phase-out rate | 1 | 5 |
| 229 | `gov.states.al.tax.income.deductions.standard.phase_out.threshold` | Alabama standard deduction phase-out threshold | 1 | 5 |
| 230 | `gov.states.al.tax.income.exemptions.personal` | Alabama personal exemption amount | 1 | 5 |
| 231 | `gov.states.nh.tax.income.exemptions.amount.base` | New Hampshire base exemption amount | 1 | 5 |
| 232 | `gov.states.mn.tax.income.subtractions.education_savings.cap` | Minnesota 529 plan contribution subtraction maximum | 1 | 5 |
| 233 | `gov.states.mn.tax.income.subtractions.elderly_disabled.agi_offset_base` | Minnesota base AGI offset in elderly/disabled subtraction calculations | 1 | 5 |
| 234 | `gov.states.mn.tax.income.subtractions.elderly_disabled.base_amount` | Minnesota base amount in elderly/disabled subtraction calculations | 1 | 5 |
| 235 | `gov.states.mn.tax.income.subtractions.social_security.alternative_amount` | Minnesota social security subtraction alternative subtraction amount | 1 | 5 |
| 236 | `gov.states.mn.tax.income.subtractions.social_security.reduction.start` | Minnesota social security subtraction reduction start | 1 | 5 |
| 237 | `gov.states.mn.tax.income.subtractions.social_security.income_amount` | Minnesota social security subtraction income amount | 1 | 5 |
| 238 | `gov.states.mn.tax.income.subtractions.pension_income.reduction.start` | Minnesota public pension income subtraction agi threshold | 1 | 5 |
| 239 | `gov.states.mn.tax.income.subtractions.pension_income.cap` | Minnesota public pension income subtraction cap | 1 | 5 |
| 240 | `gov.states.mn.tax.income.amt.fractional_income_threshold` | Minnesota fractional excess income threshold | 1 | 5 |
| 241 | `gov.states.mn.tax.income.amt.income_threshold` | Minnesota AMT taxable income threshold | 1 | 5 |
| 242 | `gov.states.mn.tax.income.deductions.itemized.reduction.agi_threshold.high` | Minnesota itemized deduction higher reduction AGI threshold | 1 | 5 |
| 243 | `gov.states.mn.tax.income.deductions.itemized.reduction.agi_threshold.low` | Minnesota itemized deduction lower reduction AGI threshold | 1 | 5 |
| 244 | `gov.states.mn.tax.income.deductions.standard.extra` | Minnesota extra standard deduction amount for each aged/blind head/spouse | 1 | 5 |
| 245 | `gov.states.mn.tax.income.deductions.standard.reduction.agi_threshold.high` | Minnesota standard deduction higher reduction AGI threshold | 1 | 5 |
| 246 | `gov.states.mn.tax.income.deductions.standard.reduction.agi_threshold.low` | Minnesota standard deduction lower reduction AGI threshold | 1 | 5 |
| 247 | `gov.states.mn.tax.income.deductions.standard.base` | Minnesota base standard deduction amount | 1 | 5 |
| 248 | `gov.states.mn.tax.income.exemptions.agi_threshold` | federal adjusted gross income threshold above which Minnesota exemptions are limited | 1 | 5 |
| 249 | `gov.states.mn.tax.income.exemptions.agi_step_size` | federal adjusted gross income step size used to limit Minnesota exemptions | 1 | 5 |
| 250 | `gov.states.mi.tax.income.deductions.standard.tier_three.amount` | Michigan tier three standard deduction amount | 1 | 5 |
| 251 | `gov.states.mi.tax.income.deductions.standard.tier_two.amount.base` | Michigan tier two standard deduction base | 1 | 5 |
| 252 | `gov.states.mi.tax.income.deductions.interest_dividends_capital_gains.amount` | Michigan interest, dividends, and capital gains deduction amount | 1 | 5 |
| 253 | `gov.states.mi.tax.income.deductions.retirement_benefits.tier_three.ss_exempt.retired.both_qualifying_amount` | Michigan tier three retirement and pension deduction both qualifying seniors | 1 | 5 |
| 254 | `gov.states.mi.tax.income.deductions.retirement_benefits.tier_three.ss_exempt.retired.single_qualifying_amount` | Michigan tier three retirement and pension deduction single qualifying senior amount | 1 | 5 |
| 255 | `gov.states.mi.tax.income.deductions.retirement_benefits.tier_one.amount` | Michigan tier one retirement and pension benefits amount | 1 | 5 |
| 256 | `gov.states.mi.tax.income.exemptions.dependent_on_other_return` | Michigan dependent on other return exemption amount | 1 | 5 |
| 257 | `gov.states.ok.tax.income.deductions.standard.amount` | Oklahoma standard deduction amount | 1 | 5 |
| 258 | `gov.states.ok.tax.income.exemptions.special_agi_limit` | Oklahoma special exemption federal AGI limit | 1 | 5 |
| 259 | `gov.states.in.tax.income.deductions.homeowners_property_tax.max` | Indiana max homeowner's property tax deduction | 1 | 5 |
| 260 | `gov.states.in.tax.income.deductions.renters.max` | Indiana max renter's deduction | 1 | 5 |
| 261 | `gov.states.in.tax.income.deductions.unemployment_compensation.agi_reduction` | Indiana AGI reduction for calculation of maximum unemployment compensation deduction | 1 | 5 |
| 262 | `gov.states.in.tax.income.exemptions.aged_low_agi.threshold` | Indiana low AGI aged exemption income limit | 1 | 5 |
| 263 | `gov.states.co.tax.income.subtractions.collegeinvest_contribution.max_amount` | Colorado CollegeInvest contribution subtraction max amount | 1 | 5 |
| 264 | `gov.states.co.tax.income.subtractions.able_contribution.cap` | Colorado ABLE contribution subtraction cap | 1 | 5 |
| 265 | `gov.states.co.tax.income.additions.federal_deductions.exemption` | Colorado itemized or standard deduction add back exemption | 1 | 5 |
| 266 | `gov.states.co.tax.income.additions.qualified_business_income_deduction.agi_threshold` | Colorado qualified business income deduction addback AGI threshold | 1 | 5 |
| 267 | `gov.states.co.tax.income.credits.income_qualified_senior_housing.reduction.max_amount` | Colorado income qualified senior housing income tax credit max amount | 1 | 5 |
| 268 | `gov.states.co.tax.income.credits.income_qualified_senior_housing.reduction.amount` | Colorado income qualified senior housing income tax credit reduction amount | 1 | 5 |
| 269 | `gov.states.co.tax.income.credits.sales_tax_refund.amount.multiplier` | Colorado sales tax refund filing status multiplier | 1 | 5 |
| 270 | `gov.states.co.tax.income.credits.family_affordability.reduction.threshold` | Colorado family affordability tax credit income-based reduction start | 1 | 5 |
| 271 | `gov.states.ca.tax.income.amt.exemption.amti.threshold.upper` | California alternative minimum tax exemption upper AMTI threshold | 1 | 5 |
| 272 | `gov.states.ca.tax.income.amt.exemption.amti.threshold.lower` | California alternative minimum tax exemption lower AMTI threshold | 1 | 5 |
| 273 | `gov.states.ca.tax.income.amt.exemption.amount` | California exemption amount | 1 | 5 |
| 274 | `gov.states.ca.tax.income.deductions.itemized.limit.agi_threshold` | California itemized deduction limitation threshold | 1 | 5 |
| 275 | `gov.states.ca.tax.income.deductions.standard.amount` | California standard deduction | 1 | 5 |
| 276 | `gov.states.ca.tax.income.exemptions.phase_out.increment` | California exemption phase out increment | 1 | 5 |
| 277 | `gov.states.ca.tax.income.exemptions.phase_out.start` | California exemption phase out start | 1 | 5 |
| 278 | `gov.states.ca.tax.income.exemptions.personal_scale` | California income personal exemption scaling factor | 1 | 5 |
| 279 | `gov.states.ca.tax.income.credits.renter.amount` | California renter tax credit amount | 1 | 5 |
| 280 | `gov.states.ca.tax.income.credits.renter.income_cap` | California renter tax credit AGI cap | 1 | 5 |
| 281 | `gov.states.ia.tax.income.alternative_minimum_tax.threshold` | Iowa alternative minimum tax threshold amount | 1 | 5 |
| 282 | `gov.states.ia.tax.income.alternative_minimum_tax.exemption` | Iowa alternative minimum tax exemption amount | 1 | 5 |
| 283 | `gov.states.ia.tax.income.deductions.standard.amount` | Iowa standard deduction amount | 1 | 5 |
| 284 | `gov.states.ia.tax.income.pension_exclusion.maximum_amount` | Iowa maximum pension exclusion amount | 1 | 5 |
| 285 | `gov.states.ia.tax.income.reportable_social_security.deduction` | Iowa reportable social security income deduction | 1 | 5 |
| 286 | `gov.states.ct.tax.income.subtractions.tuition.cap` | Connecticut state tuition subtraction max amount | 1 | 5 |
| 287 | `gov.states.ct.tax.income.subtractions.social_security.reduction_threshold` | Connecticut social security subtraction reduction threshold | 1 | 5 |
| 288 | `gov.states.ct.tax.income.add_back.increment` | Connecticut income tax phase out brackets | 1 | 5 |
| 289 | `gov.states.ct.tax.income.add_back.max_amount` | Connecticut income tax phase out max amount | 1 | 5 |
| 290 | `gov.states.ct.tax.income.add_back.amount` | Connecticut bottom income tax phase out amount | 1 | 5 |
| 291 | `gov.states.ct.tax.income.add_back.start` | Connecticut income tax phase out start | 1 | 5 |
| 292 | `gov.states.ct.tax.income.rebate.reduction.start` | Connecticut child tax rebate reduction start | 1 | 5 |
| 293 | `gov.states.ct.tax.income.exemptions.personal.max_amount` | Connecticut personal exemption max amount | 1 | 5 |
| 294 | `gov.states.ct.tax.income.exemptions.personal.reduction.start` | Connecticut personal exemption reduction start | 1 | 5 |
| 295 | `gov.states.ct.tax.income.credits.property_tax.reduction.increment` | Connecticut property tax reduction increment | 1 | 5 |
| 296 | `gov.states.ct.tax.income.credits.property_tax.reduction.start` | Connecticut Property Tax Credit reduction start | 1 | 5 |
| 297 | `gov.states.ct.tax.income.recapture.middle.increment` | Connecticut income tax recapture middle bracket increment | 1 | 5 |
| 298 | `gov.states.ct.tax.income.recapture.middle.max_amount` | Connecticut income tax recapture middle bracket max amount | 1 | 5 |
| 299 | `gov.states.ct.tax.income.recapture.middle.amount` | Connecticut income tax recapture middle bracket amount | 1 | 5 |
| 300 | `gov.states.ct.tax.income.recapture.middle.start` | Connecticut income tax recapture middle bracket start | 1 | 5 |
| 301 | `gov.states.ct.tax.income.recapture.high.increment` | Connecticut income tax recapture high bracket increment | 1 | 5 |
| 302 | `gov.states.ct.tax.income.recapture.high.max_amount` | Connecticut income tax recapture high bracket max amount | 1 | 5 |
| 303 | `gov.states.ct.tax.income.recapture.high.amount` | Connecticut income tax recapture high bracket increment | 1 | 5 |
| 304 | `gov.states.ct.tax.income.recapture.high.start` | Connecticut income tax recapture high bracket start | 1 | 5 |
| 305 | `gov.states.ct.tax.income.recapture.low.increment` | Connecticut income tax recapture low bracket increment | 1 | 5 |
| 306 | `gov.states.ct.tax.income.recapture.low.max_amount` | Connecticut income tax recapture low bracket max amount | 1 | 5 |
| 307 | `gov.states.ct.tax.income.recapture.low.amount` | Connecticut income tax recapture low bracket amount | 1 | 5 |
| 308 | `gov.states.ct.tax.income.recapture.low.start` | Connecticut income tax recapture low bracket start | 1 | 5 |
| 309 | `gov.states.wv.tax.income.subtractions.social_security_benefits.income_limit` | West Virginia social security benefits subtraction income limit | 1 | 5 |
| 310 | `gov.states.wv.tax.income.subtractions.low_income_earned_income.income_limit` | West Virginia low-income earned income exclusion income limit | 1 | 5 |
| 311 | `gov.states.wv.tax.income.subtractions.low_income_earned_income.amount` | West Virginia low-income earned income exclusion low-income earned income exclusion limit | 1 | 5 |
| 312 | `gov.states.wv.tax.income.credits.liftc.fpg_percent` | West Virginia low-income family tax credit MAGI limit | 1 | 5 |
| 313 | `gov.states.ri.tax.income.agi.subtractions.tuition_saving_program_contributions.cap` | Rhode Island tuition saving program contribution deduction cap | 1 | 5 |
| 314 | `gov.states.ri.tax.income.agi.subtractions.taxable_retirement_income.income_limit` | Rhode Island taxable retirement income subtraction income limit | 1 | 5 |
| 315 | `gov.states.ri.tax.income.agi.subtractions.social_security.limit.income` | Rhode Island social security subtraction income limit | 1 | 5 |
| 316 | `gov.states.ri.tax.income.deductions.standard.amount` | Rhode Island standard deduction amount | 1 | 5 |
| 317 | `gov.states.ri.tax.income.credits.child_tax_rebate.limit.income` | Rhode Island child tax rebate income limit | 1 | 5 |
| 318 | `gov.states.nc.tax.income.deductions.standard.amount` | North Carolina standard deduction amount | 1 | 5 |
| 319 | `gov.states.nm.tax.income.rebates.property_tax.max_amount` | New Mexico property tax rebate max amount | 1 | 5 |
| 320 | `gov.states.nm.tax.income.rebates.2021_income.supplemental.amount` | New Mexico supplemental 2021 income tax rebate amount | 1 | 5 |
| 321 | `gov.states.nm.tax.income.rebates.2021_income.additional.amount` | New Mexico additional 2021 income tax rebate amount | 1 | 5 |
| 322 | `gov.states.nm.tax.income.rebates.2021_income.main.income_limit` | New Mexico main 2021 income tax rebate income limit | 1 | 5 |
| 323 | `gov.states.nm.tax.income.rebates.2021_income.main.amount` | New Mexico main 2021 income tax rebate amount | 1 | 5 |
| 324 | `gov.states.nm.tax.income.deductions.certain_dependents.amount` | New Mexico deduction for certain dependents | 1 | 5 |
| 325 | `gov.states.nm.tax.income.exemptions.low_and_middle_income.income_limit` | New Mexico low- and middle-income exemption income limit | 1 | 5 |
| 326 | `gov.states.nm.tax.income.exemptions.low_and_middle_income.reduction.income_threshold` | New Mexico low- and middle-income exemption reduction threshold | 1 | 5 |
| 327 | `gov.states.nm.tax.income.exemptions.low_and_middle_income.reduction.rate` | New Mexico low- and middle-income exemption reduction rate | 1 | 5 |
| 328 | `gov.states.nm.tax.income.exemptions.social_security_income.income_limit` | New Mexico social security income exemption income limit | 1 | 5 |
| 329 | `gov.states.nj.tax.income.filing_threshold` | NJ filing threshold | 1 | 5 |
| 330 | `gov.states.nj.tax.income.exclusions.retirement.max_amount` | New Jersey pension/retirement maximum exclusion amount | 1 | 5 |
| 331 | `gov.states.nj.tax.income.exclusions.retirement.special_exclusion.amount` | NJ other retirement income special exclusion. | 1 | 5 |
| 332 | `gov.states.nj.tax.income.exemptions.regular.amount` | New Jersey Regular Exemption | 1 | 5 |
| 333 | `gov.states.nj.tax.income.credits.property_tax.income_limit` | New Jersey property tax credit income limit | 1 | 5 |
| 334 | `gov.states.me.tax.income.deductions.phase_out.width` | Maine standard/itemized deduction phase-out width | 1 | 5 |
| 335 | `gov.states.me.tax.income.deductions.phase_out.start` | Maine standard/itemized exemption phase-out start | 1 | 5 |
| 336 | `gov.states.me.tax.income.deductions.personal_exemption.phaseout.width` | Maine personal exemption phase-out width | 1 | 5 |
| 337 | `gov.states.me.tax.income.deductions.personal_exemption.phaseout.start` | Maine personal exemption phase-out start | 1 | 5 |
| 338 | `gov.states.me.tax.income.credits.relief_rebate.income_limit` | Maine Relief Rebate income limit | 1 | 5 |
| 339 | `gov.states.me.tax.income.credits.fairness.sales_tax.amount.base` | Maine sales tax fairness credit base amount | 1 | 5 |
| 340 | `gov.states.me.tax.income.credits.fairness.sales_tax.reduction.increment` | Maine sales tax fairness credit phase-out increment | 1 | 5 |
| 341 | `gov.states.me.tax.income.credits.fairness.sales_tax.reduction.amount` | Maine sales tax fairness credit phase-out amount | 1 | 5 |
| 342 | `gov.states.me.tax.income.credits.fairness.sales_tax.reduction.start` | Maine sales tax fairness credit phase-out start | 1 | 5 |
| 343 | `gov.states.me.tax.income.credits.dependent_exemption.phase_out.start` | Maine dependents exemption phase-out start | 1 | 5 |
| 344 | `gov.states.ar.tax.income.deductions.standard` | Arkansas standard deduction | 1 | 5 |
| 345 | `gov.states.ar.tax.income.gross_income.capital_gains.loss_cap` | Arkansas long-term capital gains tax loss cap | 1 | 5 |
| 346 | `gov.states.ar.tax.income.credits.inflationary_relief.max_amount` | Arkansas income-tax credit maximum amount | 1 | 5 |
| 347 | `gov.states.ar.tax.income.credits.inflationary_relief.reduction.increment` | Arkansas income reduction increment | 1 | 5 |
| 348 | `gov.states.ar.tax.income.credits.inflationary_relief.reduction.amount` | Arkansas inflation relief credit reduction amount | 1 | 5 |
| 349 | `gov.states.ar.tax.income.credits.inflationary_relief.reduction.start` | Arkansas inflation reduction credit reduction start | 1 | 5 |
| 350 | `gov.states.dc.tax.income.deductions.itemized.phase_out.start` | DC itemized deduction phase-out DC AGI start | 1 | 5 |
| 351 | `gov.states.dc.tax.income.credits.kccatc.income_limit` | DC KCCATC DC taxable income limit | 1 | 5 |
| 352 | `gov.states.dc.tax.income.credits.ctc.income_threshold` | DC Child Tax Credit taxable income threshold | 1 | 5 |
| 353 | `gov.states.md.tax.income.deductions.itemized.phase_out.threshold` | Maryland itemized deduction phase-out threshold | 1 | 5 |
| 354 | `gov.states.md.tax.income.deductions.standard.max` | Maryland maximum standard deduction | 1 | 5 |
| 355 | `gov.states.md.tax.income.deductions.standard.min` | Maryland minimum standard deduction | 1 | 5 |
| 356 | `gov.states.md.tax.income.deductions.standard.flat_deduction.amount` | Maryland standard deduction flat amount | 1 | 5 |
| 357 | `gov.states.md.tax.income.credits.cdcc.phase_out.increment` | Maryland CDCC phase-out increment | 1 | 5 |
| 358 | `gov.states.md.tax.income.credits.cdcc.phase_out.start` | Maryland CDCC phase-out start | 1 | 5 |
| 359 | `gov.states.md.tax.income.credits.cdcc.eligibility.agi_cap` | Maryland CDCC AGI cap | 1 | 5 |
| 360 | `gov.states.md.tax.income.credits.cdcc.eligibility.refundable_agi_cap` | Maryland refundable CDCC AGI cap | 1 | 5 |
| 361 | `gov.states.md.tax.income.credits.senior_tax.income_threshold` | Maryland Senior Tax Credit income threshold | 1 | 5 |
| 362 | `gov.states.ks.tax.income.rates.zero_tax_threshold` | KS zero-tax taxable-income threshold | 1 | 5 |
| 363 | `gov.states.ks.tax.income.deductions.standard.extra_amount` | Kansas extra standard deduction for elderly and blind | 1 | 5 |
| 364 | `gov.states.ks.tax.income.deductions.standard.base_amount` | Kansas base standard deduction | 1 | 5 |
| 365 | `gov.states.ne.tax.income.agi.subtractions.social_security.threshold` | Nebraska social security AGI subtraction threshold | 1 | 5 |
| 366 | `gov.states.ne.tax.income.deductions.standard.base_amount` | Nebraska standard deduction base amount | 1 | 5 |
| 367 | `gov.states.ne.tax.income.credits.school_readiness.amount.refundable` | Nebraska School Readiness credit refundable amount | 1 | 5 |
| 368 | `gov.states.hi.tax.income.deductions.itemized.threshold.deductions` | Hawaii itemized deductions deductions threshold | 13 | 5 |
| 369 | `gov.states.hi.tax.income.deductions.itemized.threshold.reduction` | Hawaii itemized deductions reduction threshold | 1 | 5 |
| 370 | `gov.states.hi.tax.income.deductions.standard.amount` | Hawaii standard deduction amount | 1 | 5 |
| 371 | `gov.states.de.tax.income.subtractions.exclusions.elderly_or_disabled.eligibility.agi_limit` | Delaware aged or disabled exclusion subtraction adjusted gross income limit | 1 | 5 |
| 372 | `gov.states.de.tax.income.subtractions.exclusions.elderly_or_disabled.eligibility.earned_income_limit` | Delaware aged or disabled exclusion earned income limit | 1 | 5 |
| 373 | `gov.states.de.tax.income.subtractions.exclusions.elderly_or_disabled.amount` | Delaware aged or disabled exclusion amount | 1 | 5 |
| 374 | `gov.states.de.tax.income.deductions.standard.amount` | Delaware Standard Deduction | 1 | 5 |
| 375 | `gov.states.az.tax.income.credits.charitable_contribution.ceiling.qualifying_organization` | Arizona charitable contribution credit cap | 1 | 5 |
| 376 | `gov.states.az.tax.income.credits.charitable_contribution.ceiling.qualifying_foster` | Arizona credit for contributions to foster organizations cap | 1 | 5 |
| 377 | `gov.states.az.tax.income.credits.dependent_credit.reduction.start` | Arizona dependent tax credit phase out start | 1 | 5 |
| 378 | `gov.states.az.tax.income.credits.increased_excise.income_threshold` | Arizona Increased Excise Tax Credit income threshold | 1 | 5 |
| 379 | `gov.states.az.tax.income.credits.family_tax_credits.amount.cap` | Arizona family tax credit maximum amount | 1 | 5 |
| 380 | `gov.states.ny.tax.income.deductions.standard.amount` | New York standard deduction | 1 | 5 |
| 381 | `gov.states.ny.tax.income.credits.ctc.post_2024.phase_out.threshold` | New York CTC post 2024 phase-out thresholds | 1 | 5 |
| 382 | `gov.states.id.tax.income.deductions.retirement_benefits.cap` | Idaho retirement benefit deduction cap | 1 | 5 |
| 383 | `gov.states.id.tax.income.credits.special_seasonal_rebate.floor` | Idaho special seasonal rebate floor | 1 | 5 |
| 384 | `gov.states.or.tax.income.deductions.standard.aged_or_blind.amount` | Oregon standard deduction addition for 65 or older or blind | 1 | 5 |
| 385 | `gov.states.or.tax.income.deductions.standard.amount` | Oregon standard deduction | 1 | 5 |
| 386 | `gov.states.or.tax.income.credits.exemption.income_limit.regular` | Oregon exemption credit income limit (regular) | 1 | 5 |
| 387 | `gov.states.or.tax.income.credits.retirement_income.income_threshold` | Oregon retirement income credit income threshold | 1 | 5 |
| 388 | `gov.states.or.tax.income.credits.retirement_income.base` | Oregon retirement income credit base | 1 | 5 |
| 389 | `gov.states.la.tax.income.deductions.standard.amount` | Louisiana standard deduction amount | 1 | 5 |
| 390 | `gov.states.la.tax.income.exemptions.personal` | Louisiana personal exemption amount | 1 | 5 |
| 391 | `gov.states.wi.tax.income.subtractions.retirement_income.max_agi` | Wisconsin retirement income subtraction maximum adjusted gross income | 1 | 5 |
| 392 | `gov.states.wi.dcf.works.placement.amount` | Wisconsin Works payment amount | 1 | 5 |
| 393 | `gov.irs.deductions.overtime_income.phase_out.start` | Overtime income exemption phase out start | 1 | 5 |
| 394 | `gov.irs.deductions.overtime_income.cap` | Overtime income exemption cap | 1 | 5 |
| 395 | `gov.irs.deductions.qbi.phase_out.start` | Qualified business income deduction phase-out start | 1 | 5 |
| 396 | `gov.irs.deductions.itemized.limitation.applicable_amount` | Itemized deductions applicable amount | 1 | 5 |
| 397 | `gov.irs.deductions.itemized.interest.mortgage.cap` | IRS home mortgage value cap | 13 | 5 |
| 398 | `gov.irs.deductions.itemized.reduction.agi_threshold` | IRS itemized deductions reduction threshold | 1 | 5 |
| 399 | `gov.irs.deductions.itemized.salt_and_real_estate.phase_out.threshold` | SALT deduction phase out threshold | 1 | 5 |
| 400 | `gov.irs.deductions.itemized.salt_and_real_estate.phase_out.floor.amount` | SALT deduction floor amount | 1 | 5 |
| 401 | `gov.irs.deductions.itemized.charity.non_itemizers_amount` | Charitable deduction amount for non-itemizers | 1 | 5 |
| 402 | `gov.irs.deductions.standard.aged_or_blind.amount` | Additional standard deduction for the blind and aged | 1 | 5 |
| 403 | `gov.irs.deductions.standard.amount` | Standard deduction | 1 | 5 |
| 404 | `gov.irs.deductions.auto_loan_interest.phase_out.start` | Auto loan interest deduction reduction start | 1 | 5 |
| 405 | `gov.irs.deductions.tip_income.phase_out.start` | Tip income exemption phase out start | 1 | 5 |
| 406 | `gov.irs.income.amt.multiplier` | AMT tax bracket multiplier | 1 | 5 |
| 407 | `gov.irs.gross_income.dependent_care_assistance_programs.reduction_amount` | IRS reduction amount from gross income for dependent care assistance | 13 | 5 |
| 408 | `gov.irs.ald.loss.capital.max` | Maximum capital loss deductible above-the-line | 1 | 5 |
| 409 | `gov.irs.ald.student_loan_interest.reduction.divisor` | Student loan interest deduction reduction divisor | 1 | 5 |
| 410 | `gov.irs.ald.student_loan_interest.reduction.start` | Student loan interest deduction amount | 1 | 5 |
| 411 | `gov.irs.ald.student_loan_interest.cap` | Student loan interest deduction cap | 1 | 5 |
| 412 | `gov.irs.social_security.taxability.threshold.adjusted_base.main` | Social Security taxability additional threshold | 13 | 5 |
| 413 | `gov.irs.social_security.taxability.threshold.base.main` | Social Security taxability base threshold | 13 | 5 |
| 414 | `gov.irs.credits.recovery_rebate_credit.caa.phase_out.threshold` | Second Recovery Rebate Credit phase-out starting threshold | 1 | 5 |
| 415 | `gov.irs.credits.recovery_rebate_credit.arpa.phase_out.threshold` | ARPA Recovery Rebate Credit phase-out starting threshold | 1 | 5 |
| 416 | `gov.irs.credits.recovery_rebate_credit.arpa.phase_out.length` | ARPA Recovery Rebate Credit phase-out length | 1 | 5 |
| 417 | `gov.irs.credits.recovery_rebate_credit.cares.phase_out.threshold` | CARES Recovery Rebate Credit phase-out starting threshold | 1 | 5 |
| 418 | `gov.irs.credits.retirement_saving.rate.threshold_adjustment` | Retirement Savings Contributions Credit (Saver's Credit) threshold adjustment rate | 1 | 5 |
| 419 | `gov.irs.credits.clean_vehicle.new.eligibility.income_limit` | Income limit for new clean vehicle credit | 1 | 5 |
| 420 | `gov.irs.credits.clean_vehicle.used.eligibility.income_limit` | Income limit for used clean vehicle credit | 1 | 5 |
| 421 | `gov.irs.credits.ctc.phase_out.threshold` | CTC phase-out threshold | 1 | 5 |
| 422 | `gov.irs.credits.cdcc.phase_out.amended_structure.second_start` | CDCC amended phase-out second start | 1 | 5 |
| 423 | `gov.hud.ami_limit.per_person_exceeding_4` | HUD area median income limit per person exceeding 4 | 1 | 5 |
| 424 | `gov.ed.pell_grant.sai.fpg_fraction.max_pell_limits` | Maximum Pell Grant income limits | 1 | 4 |
| 425 | `gov.states.az.tax.income.subtractions.college_savings.cap` | Arizona college savings plan subtraction cap | 1 | 4 |
| 426 | `gov.states.az.tax.income.deductions.standard.amount` | Arizona standard deduction | 1 | 4 |
| 427 | `gov.irs.credits.clean_vehicle.new.eligibility.msrp_limit` | MSRP limit for new clean vehicle credit | 1 | 4 |
| 428 | `gov.states.ma.eec.ccfa.reimbursement_rates.family_child_care.younger` | Massachusetts CCFA family child care younger child reimbursement rates | 1 | 3 |
| 429 | `gov.states.ma.eec.ccfa.reimbursement_rates.family_child_care.older` | Massachusetts CCFA family child care older child reimbursement rates | 1 | 3 |
| 430 | `gov.states.md.tax.income.credits.senior_tax.amount.joint` | Maryland Senior Tax Credit joint amount | 1 | 3 |
| 431 | `gov.states.il.idoa.bap.income_limit` | Illinois Benefit Access Program income limit | 1 | 3 |
| 432 | `gov.states.il.dhs.aabd.asset.disregard.base` | Illinois AABD asset disregard base amount | 1 | 2 |

---

## Detailed Analysis

### 1. `gov.states.nc.ncdhhs.scca.childcare_market_rates`

**Label:** North Carolina SCCA program market rates

**Breakdown dimensions:** `['county', 'range(1, 5)']`

**Child parameters:** 12,896

**Dimension analysis:**
- `county` → Variable/enum lookup (may or may not have labels)
- `range(1, 5)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.nc.ncdhhs.scca.childcare_market_rates.ALAMANCE_COUNTY_NC.1`
- Generated label: "North Carolina SCCA program market rates (ALAMANCE_COUNTY_NC, 1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[CHECK: county]', '[NEEDS: label for range(1, 5)]']`

---

### 2. `gov.states.tx.twc.ccs.payment.rates`

**Label:** Texas CCS maximum reimbursement rates by workforce board region

**Breakdown dimensions:** `['tx_ccs_workforce_board_region', 'tx_ccs_provider_type', 'tx_ccs_provider_rating', 'tx_ccs_child_age_category', 'tx_ccs_care_schedule']`

**Child parameters:** 8,064

**Dimension analysis:**
- `tx_ccs_workforce_board_region` → Variable/enum lookup (may or may not have labels)
- `tx_ccs_provider_type` → Variable/enum lookup (may or may not have labels)
- `tx_ccs_provider_rating` → Variable/enum lookup (may or may not have labels)
- `tx_ccs_child_age_category` → Variable/enum lookup (may or may not have labels)
- `tx_ccs_care_schedule` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.tx.twc.ccs.payment.rates.ALAMO.LCCC.REG.INFANT.FULL_TIME`
- Generated label: "Texas CCS maximum reimbursement rates by workforce board region (ALAMO, LCCC, REG, INFANT, FULL_TIME)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 3. `gov.irs.deductions.itemized.salt_and_real_estate.state_sales_tax_table.tax`

**Label:** Optional state sales tax table

**Breakdown dimensions:** `['state_code', 'range(1,7)', 'range(1,20)']`

**Child parameters:** 6,726

**Dimension analysis:**
- `state_code` → Enum lookup (state names)
- `range(1,7)` → **Raw numeric index (NO semantic label)**
- `range(1,20)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.irs.deductions.itemized.salt_and_real_estate.state_sales_tax_table.tax.AL.1.1`
- Generated label: "Optional state sales tax table (AL, 1, 1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['State', '[NEEDS: label for range(1,7)]', '[NEEDS: label for range(1,20)]']`

---

### 4. `gov.aca.state_rating_area_cost`

**Label:** Second Lowest Cost Silver Plan premiums by rating area

**Breakdown dimensions:** `['state_code', 'range(1, 68)']`

**Child parameters:** 3,953

**Dimension analysis:**
- `state_code` → Enum lookup (state names)
- `range(1, 68)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.aca.state_rating_area_cost.AK.1`
- Generated label: "Second Lowest Cost Silver Plan premiums by rating area (AK, 1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['State', '[NEEDS: label for range(1, 68)]']`

---

### 5. `gov.states.or.tax.income.credits.wfhdc.match`

**Label:** Oregon working family household and dependent care credit credit rate

**Breakdown dimensions:** `['list(range(0,30))', 'or_wfhdc_eligibility_category']`

**Child parameters:** 186

**Dimension analysis:**
- `list(range(0,30))` → **Raw numeric index (NO semantic label)**
- `or_wfhdc_eligibility_category` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.or.tax.income.credits.wfhdc.match.0.YOUNGEST`
- Generated label: "Oregon working family household and dependent care credit credit rate (0, YOUNGEST)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for list(range(0,30))]', '[CHECK: or_wfhdc_eligibility_category]']`

---

### 6. `gov.states.il.dhs.aabd.payment.utility.water`

**Label:** Illinois AABD water allowance by area

**Breakdown dimensions:** `['il_aabd_area', 'range(1,20)']`

**Child parameters:** 152

**Dimension analysis:**
- `il_aabd_area` → Variable/enum lookup (may or may not have labels)
- `range(1,20)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.il.dhs.aabd.payment.utility.water.AREA_1.1`
- Generated label: "Illinois AABD water allowance by area (AREA_1, 1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[CHECK: il_aabd_area]', '[NEEDS: label for range(1,20)]']`

---

### 7. `gov.states.il.dhs.aabd.payment.utility.metered_gas`

**Label:** Illinois AABD metered gas allowance by area

**Breakdown dimensions:** `['il_aabd_area', 'range(1,20)']`

**Child parameters:** 152

**Dimension analysis:**
- `il_aabd_area` → Variable/enum lookup (may or may not have labels)
- `range(1,20)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.il.dhs.aabd.payment.utility.metered_gas.AREA_1.1`
- Generated label: "Illinois AABD metered gas allowance by area (AREA_1, 1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[CHECK: il_aabd_area]', '[NEEDS: label for range(1,20)]']`

---

### 8. `gov.states.il.dhs.aabd.payment.utility.electricity`

**Label:** Illinois AABD electricity allowance by area

**Breakdown dimensions:** `['il_aabd_area', 'range(1,20)']`

**Child parameters:** 152

**Dimension analysis:**
- `il_aabd_area` → Variable/enum lookup (may or may not have labels)
- `range(1,20)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.il.dhs.aabd.payment.utility.electricity.AREA_1.1`
- Generated label: "Illinois AABD electricity allowance by area (AREA_1, 1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[CHECK: il_aabd_area]', '[NEEDS: label for range(1,20)]']`

---

### 9. `gov.states.il.dhs.aabd.payment.utility.coal`

**Label:** Illinois AABD coal allowance by area

**Breakdown dimensions:** `['il_aabd_area', 'range(1,20)']`

**Child parameters:** 152

**Dimension analysis:**
- `il_aabd_area` → Variable/enum lookup (may or may not have labels)
- `range(1,20)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.il.dhs.aabd.payment.utility.coal.AREA_1.1`
- Generated label: "Illinois AABD coal allowance by area (AREA_1, 1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[CHECK: il_aabd_area]', '[NEEDS: label for range(1,20)]']`

---

### 10. `gov.states.il.dhs.aabd.payment.utility.cooking_fuel`

**Label:** Illinois AABD cooking fuel allowance by area

**Breakdown dimensions:** `['il_aabd_area', 'range(1,20)']`

**Child parameters:** 152

**Dimension analysis:**
- `il_aabd_area` → Variable/enum lookup (may or may not have labels)
- `range(1,20)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.il.dhs.aabd.payment.utility.cooking_fuel.AREA_1.1`
- Generated label: "Illinois AABD cooking fuel allowance by area (AREA_1, 1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[CHECK: il_aabd_area]', '[NEEDS: label for range(1,20)]']`

---

### 11. `gov.states.il.dhs.aabd.payment.utility.bottled_gas`

**Label:** Illinois AABD bottled gas allowance by area

**Breakdown dimensions:** `['il_aabd_area', 'range(1,20)']`

**Child parameters:** 152

**Dimension analysis:**
- `il_aabd_area` → Variable/enum lookup (may or may not have labels)
- `range(1,20)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.il.dhs.aabd.payment.utility.bottled_gas.AREA_1.1`
- Generated label: "Illinois AABD bottled gas allowance by area (AREA_1, 1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[CHECK: il_aabd_area]', '[NEEDS: label for range(1,20)]']`

---

### 12. `gov.states.il.dhs.aabd.payment.utility.fuel_oil`

**Label:** Illinois AABD fuel oil allowance by area

**Breakdown dimensions:** `['il_aabd_area', 'range(1,20)']`

**Child parameters:** 152

**Dimension analysis:**
- `il_aabd_area` → Variable/enum lookup (may or may not have labels)
- `range(1,20)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.il.dhs.aabd.payment.utility.fuel_oil.AREA_1.1`
- Generated label: "Illinois AABD fuel oil allowance by area (AREA_1, 1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[CHECK: il_aabd_area]', '[NEEDS: label for range(1,20)]']`

---

### 13. `gov.states.dc.dhs.ccsp.reimbursement_rates`

**Label:** DC CCSP reimbursement rates

**Breakdown dimensions:** `['dc_ccsp_childcare_provider_category', 'dc_ccsp_child_category', 'dc_ccsp_schedule_type']`

**Child parameters:** 126

**Dimension analysis:**
- `dc_ccsp_childcare_provider_category` → Variable/enum lookup (may or may not have labels)
- `dc_ccsp_child_category` → Variable/enum lookup (may or may not have labels)
- `dc_ccsp_schedule_type` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.dc.dhs.ccsp.reimbursement_rates.CHILD_CENTER.INFANT_AND_TODDLER.FULL_TIME_TRADITIONAL`
- Generated label: "DC CCSP reimbursement rates (CHILD_CENTER, INFANT_AND_TODDLER, FULL_TIME_TRADITIONAL)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 14. `gov.states.vt.tax.income.credits.renter.income_limit_ami.fifty_percent`

**Label:** Vermont partial renter credit income limit

**Breakdown dimensions:** `['list(range(1,8))']`

**Child parameters:** 112

**Dimension analysis:**
- `list(range(1,8))` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.vt.tax.income.credits.renter.income_limit_ami.fifty_percent.1.ADDISON_COUNTY_VT`
- Generated label: "Vermont partial renter credit income limit (1, ADDISON_COUNTY_VT)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for list(range(1,8))]']`

---

### 15. `gov.states.vt.tax.income.credits.renter.income_limit_ami.thirty_percent`

**Label:** Vermont full renter credit income limit

**Breakdown dimensions:** `['list(range(1,8))']`

**Child parameters:** 112

**Dimension analysis:**
- `list(range(1,8))` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.vt.tax.income.credits.renter.income_limit_ami.thirty_percent.1.ADDISON_COUNTY_VT`
- Generated label: "Vermont full renter credit income limit (1, ADDISON_COUNTY_VT)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for list(range(1,8))]']`

---

### 16. `gov.states.vt.tax.income.credits.renter.fair_market_rent`

**Label:** Vermont fair market rent amount

**Breakdown dimensions:** `['list(range(1,9))']`

**Child parameters:** 112

**Dimension analysis:**
- `list(range(1,9))` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.vt.tax.income.credits.renter.fair_market_rent.1.ADDISON_COUNTY_VT`
- Generated label: "Vermont fair market rent amount (1, ADDISON_COUNTY_VT)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for list(range(1,9))]']`

---

### 17. `gov.states.dc.doee.liheap.payment.gas`

**Label:** DC LIHEAP Gas payment

**Breakdown dimensions:** `['dc_liheap_housing_type', 'range(1,11)', 'range(1,5)']`

**Child parameters:** 80

**Dimension analysis:**
- `dc_liheap_housing_type` → Variable/enum lookup (may or may not have labels)
- `range(1,11)` → **Raw numeric index (NO semantic label)**
- `range(1,5)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.dc.doee.liheap.payment.gas.MULTI_FAMILY.1.1`
- Generated label: "DC LIHEAP Gas payment (MULTI_FAMILY, 1, 1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[CHECK: dc_liheap_housing_type]', '[NEEDS: label for range(1,11)]', '[NEEDS: label for range(1,5)]']`

---

### 18. `gov.states.dc.doee.liheap.payment.electricity`

**Label:** DC LIHEAP Electricity payment

**Breakdown dimensions:** `['dc_liheap_housing_type', 'range(1,11)', 'range(1,5)']`

**Child parameters:** 80

**Dimension analysis:**
- `dc_liheap_housing_type` → Variable/enum lookup (may or may not have labels)
- `range(1,11)` → **Raw numeric index (NO semantic label)**
- `range(1,5)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.dc.doee.liheap.payment.electricity.MULTI_FAMILY.1.1`
- Generated label: "DC LIHEAP Electricity payment (MULTI_FAMILY, 1, 1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[CHECK: dc_liheap_housing_type]', '[NEEDS: label for range(1,11)]', '[NEEDS: label for range(1,5)]']`

---

### 19. `gov.usda.snap.max_allotment.main`

**Label:** SNAP max allotment

**Breakdown dimensions:** `['snap_region', 'range(1, 9)']`

**Child parameters:** 63

**Dimension analysis:**
- `snap_region` → Enum lookup
- `range(1, 9)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.usda.snap.max_allotment.main.CONTIGUOUS_US.0`
- Generated label: "SNAP max allotment (CONTIGUOUS_US, 0)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[CHECK: snap_region]', '[NEEDS: label for range(1, 9)]']`

---

### 20. `calibration.gov.aca.enrollment.state`

**Label:** ACA enrollment by state

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.aca.enrollment.state.AK`
- Generated label: "ACA enrollment by state (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 21. `calibration.gov.aca.spending.state`

**Label:** Federal ACA spending by state

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.aca.spending.state.AL`
- Generated label: "Federal ACA spending by state (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 22. `calibration.gov.hhs.medicaid.enrollment.non_expansion_adults`

**Label:** Non-expansion adults enrolled in Medicaid

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.medicaid.enrollment.non_expansion_adults.AL`
- Generated label: "Non-expansion adults enrolled in Medicaid (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 23. `calibration.gov.hhs.medicaid.enrollment.aged`

**Label:** Aged persons enrolled in Medicaid

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.medicaid.enrollment.aged.AL`
- Generated label: "Aged persons enrolled in Medicaid (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 24. `calibration.gov.hhs.medicaid.enrollment.expansion_adults`

**Label:** Expansion adults enrolled in Medicaid

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.medicaid.enrollment.expansion_adults.AL`
- Generated label: "Expansion adults enrolled in Medicaid (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 25. `calibration.gov.hhs.medicaid.enrollment.disabled`

**Label:** Disabled persons enrolled in Medicaid

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.medicaid.enrollment.disabled.AL`
- Generated label: "Disabled persons enrolled in Medicaid (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 26. `calibration.gov.hhs.medicaid.enrollment.child`

**Label:** Children enrolled in Medicaid

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.medicaid.enrollment.child.AL`
- Generated label: "Children enrolled in Medicaid (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 27. `calibration.gov.hhs.medicaid.spending.by_eligibility_group.non_expansion_adults`

**Label:** Medicaid spending for non-expansion adult enrollees

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.medicaid.spending.by_eligibility_group.non_expansion_adults.AK`
- Generated label: "Medicaid spending for non-expansion adult enrollees (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 28. `calibration.gov.hhs.medicaid.spending.by_eligibility_group.aged`

**Label:** Medicaid spending for aged enrollees

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.medicaid.spending.by_eligibility_group.aged.AL`
- Generated label: "Medicaid spending for aged enrollees (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 29. `calibration.gov.hhs.medicaid.spending.by_eligibility_group.expansion_adults`

**Label:** Medicaid spending for expansion adult enrollees

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.medicaid.spending.by_eligibility_group.expansion_adults.AL`
- Generated label: "Medicaid spending for expansion adult enrollees (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 30. `calibration.gov.hhs.medicaid.spending.by_eligibility_group.disabled`

**Label:** Medicaid spending for disabled enrollees

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.medicaid.spending.by_eligibility_group.disabled.AL`
- Generated label: "Medicaid spending for disabled enrollees (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 31. `calibration.gov.hhs.medicaid.spending.by_eligibility_group.child`

**Label:** Medicaid spending for child enrollees

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.medicaid.spending.by_eligibility_group.child.AK`
- Generated label: "Medicaid spending for child enrollees (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 32. `calibration.gov.hhs.medicaid.spending.totals.state`

**Label:** State Medicaid spending

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.medicaid.spending.totals.state.AK`
- Generated label: "State Medicaid spending (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 33. `calibration.gov.hhs.medicaid.spending.totals.federal`

**Label:** Federal Medicaid spending by state

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.medicaid.spending.totals.federal.AK`
- Generated label: "Federal Medicaid spending by state (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 34. `calibration.gov.hhs.cms.chip.enrollment.total`

**Label:** Enrollment in all CHIP programs by state

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.cms.chip.enrollment.total.AL`
- Generated label: "Enrollment in all CHIP programs by state (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 35. `calibration.gov.hhs.cms.chip.enrollment.medicaid_expansion_chip`

**Label:** Enrollment in Medicaid Expansion CHIP programs by state

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.cms.chip.enrollment.medicaid_expansion_chip.AL`
- Generated label: "Enrollment in Medicaid Expansion CHIP programs by state (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 36. `calibration.gov.hhs.cms.chip.enrollment.separate_chip`

**Label:** Enrollment in Separate CHIP programs by state

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.cms.chip.enrollment.separate_chip.AL`
- Generated label: "Enrollment in Separate CHIP programs by state (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 37. `calibration.gov.hhs.cms.chip.spending.separate_chip.state`

**Label:** State share of CHIP spending for separate CHIP programs and coverage of pregnant women

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.cms.chip.spending.separate_chip.state.AL`
- Generated label: "State share of CHIP spending for separate CHIP programs and coverage of pregnant women (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 38. `calibration.gov.hhs.cms.chip.spending.separate_chip.total`

**Label:** CHIP spending for separate CHIP programs and coverage of pregnant women

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.cms.chip.spending.separate_chip.total.AL`
- Generated label: "CHIP spending for separate CHIP programs and coverage of pregnant women (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 39. `calibration.gov.hhs.cms.chip.spending.separate_chip.federal`

**Label:** Federal share of CHIP spending for separate CHIP programs and coverage of pregnant women

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.cms.chip.spending.separate_chip.federal.AL`
- Generated label: "Federal share of CHIP spending for separate CHIP programs and coverage of pregnant women (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 40. `calibration.gov.hhs.cms.chip.spending.medicaid_expansion_chip.state`

**Label:** State share of CHIP spending for Medicaid-expansion populations

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.cms.chip.spending.medicaid_expansion_chip.state.AL`
- Generated label: "State share of CHIP spending for Medicaid-expansion populations (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 41. `calibration.gov.hhs.cms.chip.spending.medicaid_expansion_chip.total`

**Label:** CHIP spending for Medicaid-expansion populations

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.cms.chip.spending.medicaid_expansion_chip.total.AL`
- Generated label: "CHIP spending for Medicaid-expansion populations (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 42. `calibration.gov.hhs.cms.chip.spending.medicaid_expansion_chip.federal`

**Label:** Federal share of CHIP spending for Medicaid-expansion populations

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.cms.chip.spending.medicaid_expansion_chip.federal.AL`
- Generated label: "Federal share of CHIP spending for Medicaid-expansion populations (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 43. `calibration.gov.hhs.cms.chip.spending.total.state`

**Label:** State share of total CHIP spending

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.cms.chip.spending.total.state.AL`
- Generated label: "State share of total CHIP spending (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 44. `calibration.gov.hhs.cms.chip.spending.total.total`

**Label:** Total CHIP spending

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.cms.chip.spending.total.total.AL`
- Generated label: "Total CHIP spending (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 45. `calibration.gov.hhs.cms.chip.spending.total.federal`

**Label:** Federal share of total CHIP spending

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.cms.chip.spending.total.federal.AL`
- Generated label: "Federal share of total CHIP spending (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 46. `calibration.gov.hhs.cms.chip.spending.program_admin.state`

**Label:** State share of state program administration costs for CHIP

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.cms.chip.spending.program_admin.state.AL`
- Generated label: "State share of state program administration costs for CHIP (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 47. `calibration.gov.hhs.cms.chip.spending.program_admin.total`

**Label:** Total state program administration costs for CHIP

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.cms.chip.spending.program_admin.total.AL`
- Generated label: "Total state program administration costs for CHIP (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 48. `calibration.gov.hhs.cms.chip.spending.program_admin.federal`

**Label:** Federal share of state program administration costs for CHIP

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.cms.chip.spending.program_admin.federal.AL`
- Generated label: "Federal share of state program administration costs for CHIP (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 49. `gov.aca.enrollment.state`

**Label:** ACA enrollment by state

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.aca.enrollment.state.AK`
- Generated label: "ACA enrollment by state (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 50. `gov.aca.family_tier_states`

**Label:** Family tier rating states

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.aca.family_tier_states.AL`
- Generated label: "Family tier rating states (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 51. `gov.aca.spending.state`

**Label:** Federal ACA spending by state

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.aca.spending.state.AL`
- Generated label: "Federal ACA spending by state (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 52. `gov.usda.snap.income.deductions.self_employment.rate`

**Label:** SNAP self-employment simplified deduction rate

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.usda.snap.income.deductions.self_employment.rate.AK`
- Generated label: "SNAP self-employment simplified deduction rate (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 53. `gov.usda.snap.income.deductions.self_employment.expense_based_deduction_applies`

**Label:** SNAP self-employment expense-based deduction applies

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.usda.snap.income.deductions.self_employment.expense_based_deduction_applies.AK`
- Generated label: "SNAP self-employment expense-based deduction applies (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 54. `gov.usda.snap.income.deductions.excess_shelter_expense.homeless.available`

**Label:** SNAP homeless shelter deduction available

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.usda.snap.income.deductions.excess_shelter_expense.homeless.available.AK`
- Generated label: "SNAP homeless shelter deduction available (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 55. `gov.usda.snap.income.deductions.child_support`

**Label:** SNAP child support gross income deduction

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.usda.snap.income.deductions.child_support.AK`
- Generated label: "SNAP child support gross income deduction (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 56. `gov.usda.snap.income.deductions.utility.single.water`

**Label:** SNAP standard utility allowance for water expenses

**Breakdown dimensions:** `['snap_utility_region']`

**Child parameters:** 59

**Dimension analysis:**
- `snap_utility_region` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.usda.snap.income.deductions.utility.single.water.AK`
- Generated label: "SNAP standard utility allowance for water expenses (AK)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 57. `gov.usda.snap.income.deductions.utility.single.electricity`

**Label:** SNAP standard utility allowance for electricity expenses

**Breakdown dimensions:** `['snap_utility_region']`

**Child parameters:** 59

**Dimension analysis:**
- `snap_utility_region` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.usda.snap.income.deductions.utility.single.electricity.AK`
- Generated label: "SNAP standard utility allowance for electricity expenses (AK)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 58. `gov.usda.snap.income.deductions.utility.single.trash`

**Label:** SNAP standard utility allowance for trash expenses

**Breakdown dimensions:** `['snap_utility_region']`

**Child parameters:** 59

**Dimension analysis:**
- `snap_utility_region` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.usda.snap.income.deductions.utility.single.trash.AK`
- Generated label: "SNAP standard utility allowance for trash expenses (AK)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 59. `gov.usda.snap.income.deductions.utility.single.sewage`

**Label:** SNAP standard utility allowance for sewage expenses

**Breakdown dimensions:** `['snap_utility_region']`

**Child parameters:** 59

**Dimension analysis:**
- `snap_utility_region` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.usda.snap.income.deductions.utility.single.sewage.AK`
- Generated label: "SNAP standard utility allowance for sewage expenses (AK)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 60. `gov.usda.snap.income.deductions.utility.single.gas_and_fuel`

**Label:** SNAP standard utility allowance for gas and fuel expenses

**Breakdown dimensions:** `['snap_utility_region']`

**Child parameters:** 59

**Dimension analysis:**
- `snap_utility_region` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.usda.snap.income.deductions.utility.single.gas_and_fuel.AK`
- Generated label: "SNAP standard utility allowance for gas and fuel expenses (AK)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 61. `gov.usda.snap.income.deductions.utility.single.phone`

**Label:** SNAP standard utility allowance for phone expenses

**Breakdown dimensions:** `['snap_utility_region']`

**Child parameters:** 59

**Dimension analysis:**
- `snap_utility_region` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.usda.snap.income.deductions.utility.single.phone.AK`
- Generated label: "SNAP standard utility allowance for phone expenses (AK)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 62. `gov.usda.snap.income.deductions.utility.always_standard`

**Label:** SNAP States using SUA

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.usda.snap.income.deductions.utility.always_standard.AK`
- Generated label: "SNAP States using SUA (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 63. `gov.usda.snap.income.deductions.utility.standard.main`

**Label:** SNAP standard utility allowance

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.usda.snap.income.deductions.utility.standard.main.AK`
- Generated label: "SNAP standard utility allowance (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 64. `gov.usda.snap.income.deductions.utility.limited.active`

**Label:** SNAP Limited Utility Allowance active

**Breakdown dimensions:** `['snap_utility_region']`

**Child parameters:** 59

**Dimension analysis:**
- `snap_utility_region` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.usda.snap.income.deductions.utility.limited.active.AK`
- Generated label: "SNAP Limited Utility Allowance active (AK)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 65. `gov.usda.snap.income.deductions.utility.limited.main`

**Label:** SNAP limited utility allowance

**Breakdown dimensions:** `['snap_utility_region']`

**Child parameters:** 59

**Dimension analysis:**
- `snap_utility_region` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.usda.snap.income.deductions.utility.limited.main.AK`
- Generated label: "SNAP limited utility allowance (AK)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 66. `gov.usda.snap.emergency_allotment.in_effect`

**Label:** SNAP emergency allotment in effect

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.usda.snap.emergency_allotment.in_effect.AK`
- Generated label: "SNAP emergency allotment in effect (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 67. `gov.hhs.head_start.spending`

**Label:** Head Start state-level spending amount

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.head_start.spending.AK`
- Generated label: "Head Start state-level spending amount (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 68. `gov.hhs.head_start.enrollment`

**Label:** Head Start state-level enrollment

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.head_start.enrollment.AK`
- Generated label: "Head Start state-level enrollment (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 69. `gov.hhs.head_start.early_head_start.spending`

**Label:** Early Head Start state-level funding amount

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.head_start.early_head_start.spending.AK`
- Generated label: "Early Head Start state-level funding amount (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 70. `gov.hhs.head_start.early_head_start.enrollment`

**Label:** Early Head Start state-level enrollment

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.head_start.early_head_start.enrollment.AK`
- Generated label: "Early Head Start state-level enrollment (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 71. `gov.hhs.medicaid.eligibility.undocumented_immigrant`

**Label:** Medicaid undocumented immigrant eligibility

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.medicaid.eligibility.undocumented_immigrant.AL`
- Generated label: "Medicaid undocumented immigrant eligibility (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 72. `gov.hhs.medicaid.eligibility.categories.young_child.income_limit`

**Label:** Medicaid young child income limit

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.medicaid.eligibility.categories.young_child.income_limit.AK`
- Generated label: "Medicaid young child income limit (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 73. `gov.hhs.medicaid.eligibility.categories.senior_or_disabled.income.limit.couple`

**Label:** Medicaid senior or disabled income limit (couple)

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.medicaid.eligibility.categories.senior_or_disabled.income.limit.couple.AK`
- Generated label: "Medicaid senior or disabled income limit (couple) (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 74. `gov.hhs.medicaid.eligibility.categories.senior_or_disabled.income.limit.individual`

**Label:** Medicaid senior or disabled income limit (individual)

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.medicaid.eligibility.categories.senior_or_disabled.income.limit.individual.AK`
- Generated label: "Medicaid senior or disabled income limit (individual) (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 75. `gov.hhs.medicaid.eligibility.categories.senior_or_disabled.income.disregard.couple`

**Label:** Medicaid senior or disabled income disregard (couple)

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.medicaid.eligibility.categories.senior_or_disabled.income.disregard.couple.AL`
- Generated label: "Medicaid senior or disabled income disregard (couple) (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 76. `gov.hhs.medicaid.eligibility.categories.senior_or_disabled.income.disregard.individual`

**Label:** Medicaid senior or disabled income disregard (individual)

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.medicaid.eligibility.categories.senior_or_disabled.income.disregard.individual.AL`
- Generated label: "Medicaid senior or disabled income disregard (individual) (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 77. `gov.hhs.medicaid.eligibility.categories.senior_or_disabled.assets.limit.couple`

**Label:** Medicaid senior or disabled asset limit (couple)

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.medicaid.eligibility.categories.senior_or_disabled.assets.limit.couple.AL`
- Generated label: "Medicaid senior or disabled asset limit (couple) (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 78. `gov.hhs.medicaid.eligibility.categories.senior_or_disabled.assets.limit.individual`

**Label:** Medicaid senior or disabled asset limit (individual)

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.medicaid.eligibility.categories.senior_or_disabled.assets.limit.individual.AL`
- Generated label: "Medicaid senior or disabled asset limit (individual) (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 79. `gov.hhs.medicaid.eligibility.categories.young_adult.income_limit`

**Label:** Medicaid pregnant income limit

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.medicaid.eligibility.categories.young_adult.income_limit.AK`
- Generated label: "Medicaid pregnant income limit (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 80. `gov.hhs.medicaid.eligibility.categories.older_child.income_limit`

**Label:** Medicaid older child income limit

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.medicaid.eligibility.categories.older_child.income_limit.AK`
- Generated label: "Medicaid older child income limit (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 81. `gov.hhs.medicaid.eligibility.categories.parent.income_limit`

**Label:** Medicaid parent income limit

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.medicaid.eligibility.categories.parent.income_limit.AK`
- Generated label: "Medicaid parent income limit (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 82. `gov.hhs.medicaid.eligibility.categories.pregnant.income_limit`

**Label:** Medicaid pregnant income limit

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.medicaid.eligibility.categories.pregnant.income_limit.AK`
- Generated label: "Medicaid pregnant income limit (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 83. `gov.hhs.medicaid.eligibility.categories.pregnant.postpartum_coverage`

**Label:** Medicaid postpartum coverage

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.medicaid.eligibility.categories.pregnant.postpartum_coverage.AK`
- Generated label: "Medicaid postpartum coverage (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 84. `gov.hhs.medicaid.eligibility.categories.ssi_recipient.is_covered`

**Label:** Medicaid covers all SSI recipients

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.medicaid.eligibility.categories.ssi_recipient.is_covered.AK`
- Generated label: "Medicaid covers all SSI recipients (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 85. `gov.hhs.medicaid.eligibility.categories.infant.income_limit`

**Label:** Medicaid infant income limit

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.medicaid.eligibility.categories.infant.income_limit.AK`
- Generated label: "Medicaid infant income limit (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 86. `gov.hhs.medicaid.eligibility.categories.adult.income_limit`

**Label:** Medicaid adult income limit

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.medicaid.eligibility.categories.adult.income_limit.AK`
- Generated label: "Medicaid adult income limit (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 87. `gov.hhs.chip.fcep.income_limit`

**Label:** CHIP FCEP pregnant income limit

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.chip.fcep.income_limit.AK`
- Generated label: "CHIP FCEP pregnant income limit (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 88. `gov.hhs.chip.pregnant.income_limit`

**Label:** CHIP pregnant income limit

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.chip.pregnant.income_limit.AK`
- Generated label: "CHIP pregnant income limit (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 89. `gov.hhs.chip.child.income_limit`

**Label:** CHIP child income limit

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.chip.child.income_limit.AK`
- Generated label: "CHIP child income limit (AK)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 90. `gov.hhs.medicare.savings_programs.eligibility.asset.applies`

**Label:** MSP asset test applies

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.medicare.savings_programs.eligibility.asset.applies.AL`
- Generated label: "MSP asset test applies (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 91. `gov.hhs.tanf.non_cash.income_limit.gross`

**Label:** SNAP BBCE gross income limit

**Breakdown dimensions:** `['state_code']`

**Child parameters:** 59

**Dimension analysis:**
- `state_code` → Enum lookup (state names)

**Example - Current label generation:**
- Parameter: `gov.hhs.tanf.non_cash.income_limit.gross.AL`
- Generated label: "SNAP BBCE gross income limit (AL)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 92. `gov.states.ma.dta.ssp.amount`

**Label:** Massachusetts SSP payment amount

**Breakdown dimensions:** `['ma_state_living_arrangement', 'ssi_category', 'range(1, 3)']`

**Child parameters:** 48

**Dimension analysis:**
- `ma_state_living_arrangement` → Variable/enum lookup (may or may not have labels)
- `ssi_category` → Variable/enum lookup (may or may not have labels)
- `range(1, 3)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ma.dta.ssp.amount.FULL_COST.AGED.1`
- Generated label: "Massachusetts SSP payment amount (FULL_COST, AGED, 1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[CHECK: ma_state_living_arrangement]', '[CHECK: ssi_category]', '[NEEDS: label for range(1, 3)]']`

---

### 93. `gov.states.ma.eec.ccfa.reimbursement_rates.center_based.school_age`

**Label:** Massachusetts CCFA center-based school age reimbursement rates

**Breakdown dimensions:** `['ma_ccfa_region', 'ma_ccfa_child_age_category', 'ma_ccfa_schedule_type']`

**Child parameters:** 48

**Dimension analysis:**
- `ma_ccfa_region` → Variable/enum lookup (may or may not have labels)
- `ma_ccfa_child_age_category` → Variable/enum lookup (may or may not have labels)
- `ma_ccfa_schedule_type` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.ma.eec.ccfa.reimbursement_rates.center_based.school_age.WESTERN_CENTRAL_AND_SOUTHEAST.SCHOOL_AGE.BEFORE_ONLY`
- Generated label: "Massachusetts CCFA center-based school age reimbursement rates (WESTERN_CENTRAL_AND_SOUTHEAST, SCHOOL_AGE, BEFORE_ONLY)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 94. `gov.contrib.additional_tax_bracket.bracket.thresholds`

**Label:** Individual income tax rate thresholds

**Breakdown dimensions:** `['range(1, 8)', 'filing_status']`

**Child parameters:** 40

**Dimension analysis:**
- `range(1, 8)` → **Raw numeric index (NO semantic label)**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.additional_tax_bracket.bracket.thresholds.1.SINGLE`
- Generated label: "Individual income tax rate thresholds (1, SINGLE)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 8)]', 'Filing status']`

---

### 95. `gov.usda.snap.income.deductions.standard`

**Label:** SNAP standard deduction

**Breakdown dimensions:** `['state_group', 'range(1, 7)']`

**Child parameters:** 36

**Dimension analysis:**
- `state_group` → Variable/enum lookup (may or may not have labels)
- `range(1, 7)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.usda.snap.income.deductions.standard.CONTIGUOUS_US.1`
- Generated label: "SNAP standard deduction (CONTIGUOUS_US, 1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[CHECK: state_group]', '[NEEDS: label for range(1, 7)]']`

---

### 96. `gov.irs.income.bracket.thresholds`

**Label:** Individual income tax rate thresholds

**Breakdown dimensions:** `['range(1, 7)', 'filing_status']`

**Child parameters:** 35

**Dimension analysis:**
- `range(1, 7)` → **Raw numeric index (NO semantic label)**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.income.bracket.thresholds.1.SINGLE`
- Generated label: "Individual income tax rate thresholds (1, SINGLE)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 7)]', 'Filing status']`

---

### 97. `gov.states.ma.eec.ccfa.copay.fee_level.fee_percentages`

**Label:** Massachusetts CCFA fee percentage by fee level

**Breakdown dimensions:** `['range(1,29)']`

**Child parameters:** 29

**Dimension analysis:**
- `range(1,29)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ma.eec.ccfa.copay.fee_level.fee_percentages.0`
- Generated label: "Massachusetts CCFA fee percentage by fee level (0)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1,29)]']`

---

### 98. `gov.states.pa.dhs.tanf.standard_of_need.amount`

**Label:** Pennsylvania TANF Standard of Need by county group

**Breakdown dimensions:** `['pa_tanf_county_group']`

**Child parameters:** 24

**Dimension analysis:**
- `pa_tanf_county_group` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.pa.dhs.tanf.standard_of_need.amount.GROUP_1.1`
- Generated label: "Pennsylvania TANF Standard of Need by county group (GROUP_1, 1)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 99. `gov.states.pa.dhs.tanf.family_size_allowance.amount`

**Label:** Pennsylvania TANF family size allowance by county group

**Breakdown dimensions:** `['pa_tanf_county_group']`

**Child parameters:** 24

**Dimension analysis:**
- `pa_tanf_county_group` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.pa.dhs.tanf.family_size_allowance.amount.GROUP_1.1`
- Generated label: "Pennsylvania TANF family size allowance by county group (GROUP_1, 1)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 100. `gov.states.ma.doer.liheap.standard.amount.non_subsidized`

**Label:** Massachusetts LIHEAP homeowners and non subsidized housing payment amount

**Breakdown dimensions:** `['range(0,7)', 'ma_liheap_utility_category']`

**Child parameters:** 21

**Dimension analysis:**
- `range(0,7)` → **Raw numeric index (NO semantic label)**
- `ma_liheap_utility_category` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.ma.doer.liheap.standard.amount.non_subsidized.0.DELIVERABLE_FUEL`
- Generated label: "Massachusetts LIHEAP homeowners and non subsidized housing payment amount (0, DELIVERABLE_FUEL)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(0,7)]', '[CHECK: ma_liheap_utility_category]']`

---

### 101. `gov.states.ma.doer.liheap.standard.amount.subsidized`

**Label:** Massachusetts LIHEAP subsidized housing payment amount

**Breakdown dimensions:** `['range(1,6)', 'ma_liheap_utility_category']`

**Child parameters:** 21

**Dimension analysis:**
- `range(1,6)` → **Raw numeric index (NO semantic label)**
- `ma_liheap_utility_category` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.ma.doer.liheap.standard.amount.subsidized.0.DELIVERABLE_FUEL`
- Generated label: "Massachusetts LIHEAP subsidized housing payment amount (0, DELIVERABLE_FUEL)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1,6)]', '[CHECK: ma_liheap_utility_category]']`

---

### 102. `gov.states.mn.dcyf.mfip.transitional_standard.amount`

**Label:** Minnesota MFIP Transitional Standard amount

**Breakdown dimensions:** `['range(0, 20)']`

**Child parameters:** 20

**Dimension analysis:**
- `range(0, 20)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.mn.dcyf.mfip.transitional_standard.amount.1`
- Generated label: "Minnesota MFIP Transitional Standard amount (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(0, 20)]']`

---

### 103. `gov.states.dc.dhs.tanf.standard_payment.amount`

**Label:** DC TANF standard payment amount

**Breakdown dimensions:** `['range(0, 20)']`

**Child parameters:** 20

**Dimension analysis:**
- `range(0, 20)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.dc.dhs.tanf.standard_payment.amount.1`
- Generated label: "DC TANF standard payment amount (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(0, 20)]']`

---

### 104. `gov.hud.ami_limit.family_size`

**Label:** HUD area median income limit

**Breakdown dimensions:** `['hud_income_level', 'range(1, 5)']`

**Child parameters:** 20

**Dimension analysis:**
- `hud_income_level` → Variable/enum lookup (may or may not have labels)
- `range(1, 5)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.hud.ami_limit.family_size.MODERATE.1`
- Generated label: "HUD area median income limit (MODERATE, 1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[CHECK: hud_income_level]', '[NEEDS: label for range(1, 5)]']`

---

### 105. `gov.states.ut.dwf.fep.standard_needs_budget.amount`

**Label:** Utah FEP Standard Needs Budget (SNB)

**Breakdown dimensions:** `['range(1, 20)']`

**Child parameters:** 19

**Dimension analysis:**
- `range(1, 20)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ut.dwf.fep.standard_needs_budget.amount.1`
- Generated label: "Utah FEP Standard Needs Budget (SNB) (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 20)]']`

---

### 106. `gov.states.ut.dwf.fep.payment_standard.amount`

**Label:** Utah FEP maximum benefit amount

**Breakdown dimensions:** `['range(1, 20)']`

**Child parameters:** 19

**Dimension analysis:**
- `range(1, 20)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ut.dwf.fep.payment_standard.amount.1`
- Generated label: "Utah FEP maximum benefit amount (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 20)]']`

---

### 107. `gov.states.mo.dss.tanf.standard_of_need.amount`

**Label:** Missouri TANF standard of need

**Breakdown dimensions:** `['range(1, 20)']`

**Child parameters:** 19

**Dimension analysis:**
- `range(1, 20)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.mo.dss.tanf.standard_of_need.amount.1`
- Generated label: "Missouri TANF standard of need (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 20)]']`

---

### 108. `gov.states.ar.dhs.tea.payment_standard.amount`

**Label:** Arkansas TEA payment standard amount

**Breakdown dimensions:** `['range(1, 20)']`

**Child parameters:** 19

**Dimension analysis:**
- `range(1, 20)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ar.dhs.tea.payment_standard.amount.1`
- Generated label: "Arkansas TEA payment standard amount (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 20)]']`

---

### 109. `gov.usda.school_meals.amount.nslp`

**Label:** National School Lunch Program value

**Breakdown dimensions:** `['state_group', 'school_meal_tier']`

**Child parameters:** 18

**Dimension analysis:**
- `state_group` → Variable/enum lookup (may or may not have labels)
- `school_meal_tier` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.usda.school_meals.amount.nslp.CONTIGUOUS_US.PAID`
- Generated label: "National School Lunch Program value (CONTIGUOUS_US, PAID)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 110. `gov.usda.school_meals.amount.sbp`

**Label:** School Breakfast Program value

**Breakdown dimensions:** `['state_group', 'school_meal_tier']`

**Child parameters:** 18

**Dimension analysis:**
- `state_group` → Variable/enum lookup (may or may not have labels)
- `school_meal_tier` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.usda.school_meals.amount.sbp.CONTIGUOUS_US.PAID`
- Generated label: "School Breakfast Program value (CONTIGUOUS_US, PAID)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 111. `gov.contrib.harris.capital_gains.thresholds`

**Label:** Harris capital gains tax rate thresholds

**Breakdown dimensions:** `['range(1, 4)', 'filing_status']`

**Child parameters:** 15

**Dimension analysis:**
- `range(1, 4)` → **Raw numeric index (NO semantic label)**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.harris.capital_gains.thresholds.1.HEAD_OF_HOUSEHOLD`
- Generated label: "Harris capital gains tax rate thresholds (1, HEAD_OF_HOUSEHOLD)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 4)]', 'Filing status']`

---

### 112. `gov.states.oh.odjfs.owf.payment_standard.amounts`

**Label:** Ohio Works First payment standard amounts

**Breakdown dimensions:** `['range(1, 16)']`

**Child parameters:** 15

**Dimension analysis:**
- `range(1, 16)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.oh.odjfs.owf.payment_standard.amounts.1`
- Generated label: "Ohio Works First payment standard amounts (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 16)]']`

---

### 113. `gov.states.nc.ncdhhs.tanf.need_standard.main`

**Label:** North Carolina TANF monthly need standard

**Breakdown dimensions:** `['range(1, 15)']`

**Child parameters:** 14

**Dimension analysis:**
- `range(1, 15)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.nc.ncdhhs.tanf.need_standard.main.1`
- Generated label: "North Carolina TANF monthly need standard (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 15)]']`

---

### 114. `gov.states.ma.eec.ccfa.copay.fee_level.income_ratio_increments`

**Label:** Massachusetts CCFA income ratio increments by household size

**Breakdown dimensions:** `['range(1,13)']`

**Child parameters:** 13

**Dimension analysis:**
- `range(1,13)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ma.eec.ccfa.copay.fee_level.income_ratio_increments.0`
- Generated label: "Massachusetts CCFA income ratio increments by household size (0)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1,13)]']`

---

### 115. `gov.states.ma.eec.ccfa.reimbursement_rates.head_start_partner_and_kindergarten`

**Label:** Massachusetts CCFA head start partner and kindergarten reimbursement rates

**Breakdown dimensions:** `['ma_ccfa_region', 'ma_ccfa_schedule_type']`

**Child parameters:** 12

**Dimension analysis:**
- `ma_ccfa_region` → Variable/enum lookup (may or may not have labels)
- `ma_ccfa_schedule_type` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.ma.eec.ccfa.reimbursement_rates.head_start_partner_and_kindergarten.WESTERN_CENTRAL_AND_SOUTHEAST.BEFORE_ONLY`
- Generated label: "Massachusetts CCFA head start partner and kindergarten reimbursement rates (WESTERN_CENTRAL_AND_SOUTHEAST, BEFORE_ONLY)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 116. `gov.states.ma.eec.ccfa.reimbursement_rates.center_based.early_education`

**Label:** Massachusetts CCFA center-based early education reimbursement rates

**Breakdown dimensions:** `['ma_ccfa_region', 'ma_ccfa_child_age_category']`

**Child parameters:** 12

**Dimension analysis:**
- `ma_ccfa_region` → Variable/enum lookup (may or may not have labels)
- `ma_ccfa_child_age_category` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.ma.eec.ccfa.reimbursement_rates.center_based.early_education.WESTERN_CENTRAL_AND_SOUTHEAST.INFANT`
- Generated label: "Massachusetts CCFA center-based early education reimbursement rates (WESTERN_CENTRAL_AND_SOUTHEAST, INFANT)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 117. `gov.hhs.fpg`

**Label:** Federal poverty guidelines

**Breakdown dimensions:** `[['first_person', 'additional_person'], 'state_group']`

**Child parameters:** 12

**Dimension analysis:**
- `['first_person', 'additional_person']` → List of fixed keys
- `state_group` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.hhs.fpg.first_person.CONTIGUOUS_US`
- Generated label: "Federal poverty guidelines (first_person, CONTIGUOUS_US)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 118. `gov.states.ga.dfcs.tanf.financial_standards.family_maximum.base`

**Label:** Georgia TANF family maximum base amount

**Breakdown dimensions:** `['range(1, 12)']`

**Child parameters:** 11

**Dimension analysis:**
- `range(1, 12)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ga.dfcs.tanf.financial_standards.family_maximum.base.1`
- Generated label: "Georgia TANF family maximum base amount (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 12)]']`

---

### 119. `gov.states.ga.dfcs.tanf.financial_standards.standard_of_need.base`

**Label:** Georgia TANF standard of need base amount

**Breakdown dimensions:** `['range(1, 12)']`

**Child parameters:** 11

**Dimension analysis:**
- `range(1, 12)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ga.dfcs.tanf.financial_standards.standard_of_need.base.1`
- Generated label: "Georgia TANF standard of need base amount (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 12)]']`

---

### 120. `gov.usda.snap.income.deductions.utility.standard.by_household_size.amount`

**Label:** SNAP SUAs by household size

**Breakdown dimensions:** `[['NC'], 'range(1, 10)']`

**Child parameters:** 10

**Dimension analysis:**
- `['NC']` → List of fixed keys
- `range(1, 10)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.usda.snap.income.deductions.utility.standard.by_household_size.amount.NC.1`
- Generated label: "SNAP SUAs by household size (NC, 1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ["[NEEDS: label for ['NC']]", '[NEEDS: label for range(1, 10)]']`

---

### 121. `gov.usda.snap.income.deductions.utility.limited.by_household_size.amount`

**Label:** SNAP LUAs by household size

**Breakdown dimensions:** `[['NC'], 'range(1, 10)']`

**Child parameters:** 10

**Dimension analysis:**
- `['NC']` → List of fixed keys
- `range(1, 10)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.usda.snap.income.deductions.utility.limited.by_household_size.amount.NC.1`
- Generated label: "SNAP LUAs by household size (NC, 1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ["[NEEDS: label for ['NC']]", '[NEEDS: label for range(1, 10)]']`

---

### 122. `gov.states.ms.dhs.tanf.need_standard.amount`

**Label:** Mississippi TANF need standard amount

**Breakdown dimensions:** `['range(1, 11)']`

**Child parameters:** 10

**Dimension analysis:**
- `range(1, 11)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ms.dhs.tanf.need_standard.amount.1`
- Generated label: "Mississippi TANF need standard amount (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 11)]']`

---

### 123. `gov.states.in.fssa.tanf.standard_of_need.amount`

**Label:** Indiana TANF standard of need amount

**Breakdown dimensions:** `['range(1, 11)']`

**Child parameters:** 10

**Dimension analysis:**
- `range(1, 11)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.in.fssa.tanf.standard_of_need.amount.1`
- Generated label: "Indiana TANF standard of need amount (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 11)]']`

---

### 124. `gov.states.ca.cdss.tanf.cash.monthly_payment.region1.exempt`

**Label:** California CalWORKs monthly payment level - exempt map region 1

**Breakdown dimensions:** `['range(1, 11)']`

**Child parameters:** 10

**Dimension analysis:**
- `range(1, 11)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ca.cdss.tanf.cash.monthly_payment.region1.exempt.1`
- Generated label: "California CalWORKs monthly payment level - exempt map region 1 (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 11)]']`

---

### 125. `gov.states.ca.cdss.tanf.cash.monthly_payment.region1.non_exempt`

**Label:** California CalWORKs monthly payment level - non-exempt map region 1

**Breakdown dimensions:** `['range(1, 11)']`

**Child parameters:** 10

**Dimension analysis:**
- `range(1, 11)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ca.cdss.tanf.cash.monthly_payment.region1.non_exempt.1`
- Generated label: "California CalWORKs monthly payment level - non-exempt map region 1 (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 11)]']`

---

### 126. `gov.states.ca.cdss.tanf.cash.monthly_payment.region2.exempt`

**Label:** California CalWORKs monthly payment level - exempt map region 2

**Breakdown dimensions:** `['range(1, 11)']`

**Child parameters:** 10

**Dimension analysis:**
- `range(1, 11)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ca.cdss.tanf.cash.monthly_payment.region2.exempt.1`
- Generated label: "California CalWORKs monthly payment level - exempt map region 2 (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 11)]']`

---

### 127. `gov.states.ca.cdss.tanf.cash.monthly_payment.region2.non_exempt`

**Label:** California CalWORKs monthly payment level - non-exempt map region 2

**Breakdown dimensions:** `['range(1, 11)']`

**Child parameters:** 10

**Dimension analysis:**
- `range(1, 11)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ca.cdss.tanf.cash.monthly_payment.region2.non_exempt.1`
- Generated label: "California CalWORKs monthly payment level - non-exempt map region 2 (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 11)]']`

---

### 128. `gov.states.ca.cdss.tanf.cash.income.monthly_limit.region1.main`

**Label:** California CalWORKs monthly income limit for region 1

**Breakdown dimensions:** `['range(1, 11)']`

**Child parameters:** 10

**Dimension analysis:**
- `range(1, 11)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ca.cdss.tanf.cash.income.monthly_limit.region1.main.1`
- Generated label: "California CalWORKs monthly income limit for region 1 (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 11)]']`

---

### 129. `gov.states.ca.cdss.tanf.cash.income.monthly_limit.region2.main`

**Label:** California CalWORKs monthly income limit for region 2

**Breakdown dimensions:** `['range(1, 11)']`

**Child parameters:** 10

**Dimension analysis:**
- `range(1, 11)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ca.cdss.tanf.cash.income.monthly_limit.region2.main.1`
- Generated label: "California CalWORKs monthly income limit for region 2 (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 11)]']`

---

### 130. `gov.states.ks.dcf.tanf.payment_standard.amount`

**Label:** Kansas TANF payment standard amount

**Breakdown dimensions:** `['range(0, 10)']`

**Child parameters:** 10

**Dimension analysis:**
- `range(0, 10)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ks.dcf.tanf.payment_standard.amount.1`
- Generated label: "Kansas TANF payment standard amount (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(0, 10)]']`

---

### 131. `gov.states.ne.dhhs.adc.benefit.standard_of_need.amount`

**Label:** Nebraska ADC standard of need

**Breakdown dimensions:** `['range(1, 11)']`

**Child parameters:** 10

**Dimension analysis:**
- `range(1, 11)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ne.dhhs.adc.benefit.standard_of_need.amount.1`
- Generated label: "Nebraska ADC standard of need (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 11)]']`

---

### 132. `gov.states.id.tafi.work_incentive_table.amount`

**Label:** Idaho TAFI work incentive table amount

**Breakdown dimensions:** `['range(1, 11)']`

**Child parameters:** 10

**Dimension analysis:**
- `range(1, 11)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.id.tafi.work_incentive_table.amount.1`
- Generated label: "Idaho TAFI work incentive table amount (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 11)]']`

---

### 133. `gov.states.or.odhs.tanf.income.countable_income_limit.amount`

**Label:** Oregon TANF countable income limit

**Breakdown dimensions:** `['range(1, 11)']`

**Child parameters:** 10

**Dimension analysis:**
- `range(1, 11)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.or.odhs.tanf.income.countable_income_limit.amount.1`
- Generated label: "Oregon TANF countable income limit (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 11)]']`

---

### 134. `gov.states.or.odhs.tanf.income.adjusted_income_limit.amount`

**Label:** Oregon TANF adjusted income limit

**Breakdown dimensions:** `['range(1, 11)']`

**Child parameters:** 10

**Dimension analysis:**
- `range(1, 11)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.or.odhs.tanf.income.adjusted_income_limit.amount.1`
- Generated label: "Oregon TANF adjusted income limit (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 11)]']`

---

### 135. `gov.states.or.odhs.tanf.payment_standard.amount`

**Label:** Oregon TANF payment standard

**Breakdown dimensions:** `['range(1, 11)']`

**Child parameters:** 10

**Dimension analysis:**
- `range(1, 11)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.or.odhs.tanf.payment_standard.amount.1`
- Generated label: "Oregon TANF payment standard (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 11)]']`

---

### 136. `gov.states.wa.dshs.tanf.income.limit`

**Label:** Washington TANF maximum gross earned income limit

**Breakdown dimensions:** `['range(1, 11)']`

**Child parameters:** 10

**Dimension analysis:**
- `range(1, 11)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.wa.dshs.tanf.income.limit.1`
- Generated label: "Washington TANF maximum gross earned income limit (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 11)]']`

---

### 137. `gov.states.wa.dshs.tanf.payment_standard.amount`

**Label:** Washington TANF payment standard

**Breakdown dimensions:** `['range(1, 11)']`

**Child parameters:** 10

**Dimension analysis:**
- `range(1, 11)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.wa.dshs.tanf.payment_standard.amount.1`
- Generated label: "Washington TANF payment standard (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 11)]']`

---

### 138. `gov.contrib.additional_tax_bracket.bracket.rates`

**Label:** Individual income tax rates

**Breakdown dimensions:** `['range(1, 8)']`

**Child parameters:** 8

**Dimension analysis:**
- `range(1, 8)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.contrib.additional_tax_bracket.bracket.rates.1`
- Generated label: "Individual income tax rates (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 8)]']`

---

### 139. `gov.states.ma.dta.tcap.eaedc.standard_assistance.amount.additional`

**Label:** Massachusetts EAEDC standard assistance additional amount

**Breakdown dimensions:** `['ma_eaedc_living_arrangement']`

**Child parameters:** 8

**Dimension analysis:**
- `ma_eaedc_living_arrangement` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.ma.dta.tcap.eaedc.standard_assistance.amount.additional.A`
- Generated label: "Massachusetts EAEDC standard assistance additional amount (A)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 140. `gov.states.ma.dta.tcap.eaedc.standard_assistance.amount.base`

**Label:** Massachusetts EAEDC standard assistance base amount

**Breakdown dimensions:** `['ma_eaedc_living_arrangement']`

**Child parameters:** 8

**Dimension analysis:**
- `ma_eaedc_living_arrangement` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.ma.dta.tcap.eaedc.standard_assistance.amount.base.A`
- Generated label: "Massachusetts EAEDC standard assistance base amount (A)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 141. `gov.states.nj.njdhs.tanf.maximum_benefit.main`

**Label:** New Jersey TANF monthly maximum benefit

**Breakdown dimensions:** `['range(1, 9)']`

**Child parameters:** 8

**Dimension analysis:**
- `range(1, 9)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.nj.njdhs.tanf.maximum_benefit.main.1`
- Generated label: "New Jersey TANF monthly maximum benefit (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 9)]']`

---

### 142. `gov.states.nj.njdhs.tanf.maximum_allowable_income.main`

**Label:** New Jersey TANF monthly maximum allowable income

**Breakdown dimensions:** `['range(1, 9)']`

**Child parameters:** 8

**Dimension analysis:**
- `range(1, 9)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.nj.njdhs.tanf.maximum_allowable_income.main.1`
- Generated label: "New Jersey TANF monthly maximum allowable income (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 9)]']`

---

### 143. `gov.states.il.dhs.aabd.payment.personal_allowance.bedfast`

**Label:** Illinois AABD bedfast applicant personal allowance

**Breakdown dimensions:** `['range(1,9)']`

**Child parameters:** 8

**Dimension analysis:**
- `range(1,9)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.il.dhs.aabd.payment.personal_allowance.bedfast.1`
- Generated label: "Illinois AABD bedfast applicant personal allowance (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1,9)]']`

---

### 144. `gov.states.il.dhs.aabd.payment.personal_allowance.active`

**Label:** Illinois AABD active applicant personal allowance

**Breakdown dimensions:** `['range(1,9)']`

**Child parameters:** 8

**Dimension analysis:**
- `range(1,9)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.il.dhs.aabd.payment.personal_allowance.active.1`
- Generated label: "Illinois AABD active applicant personal allowance (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1,9)]']`

---

### 145. `gov.usda.snap.income.deductions.excess_shelter_expense.cap`

**Label:** SNAP maximum shelter deduction

**Breakdown dimensions:** `['snap_region']`

**Child parameters:** 7

**Dimension analysis:**
- `snap_region` → Enum lookup

**Example - Current label generation:**
- Parameter: `gov.usda.snap.income.deductions.excess_shelter_expense.cap.CONTIGUOUS_US`
- Generated label: "SNAP maximum shelter deduction (CONTIGUOUS_US)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 146. `gov.states.ma.doer.liheap.hecs.amount.non_subsidized`

**Label:** Massachusetts LIHEAP High Energy Cost Supplement payment for homeowners and non-subsidized housing applicants

**Breakdown dimensions:** `['range(0,7)']`

**Child parameters:** 7

**Dimension analysis:**
- `range(0,7)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ma.doer.liheap.hecs.amount.non_subsidized.0`
- Generated label: "Massachusetts LIHEAP High Energy Cost Supplement payment for homeowners and non-subsidized housing applicants (0)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(0,7)]']`

---

### 147. `gov.states.ma.doer.liheap.hecs.amount.subsidized`

**Label:** Massachusetts LIHEAP High Energy Cost Supplement payment for subsidized housing applicants

**Breakdown dimensions:** `['range(0,7)']`

**Child parameters:** 7

**Dimension analysis:**
- `range(0,7)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ma.doer.liheap.hecs.amount.subsidized.0`
- Generated label: "Massachusetts LIHEAP High Energy Cost Supplement payment for subsidized housing applicants (0)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(0,7)]']`

---

### 148. `gov.states.ky.dcbs.ktap.benefit.standard_of_need`

**Label:** Kentucky K-TAP standard of need

**Breakdown dimensions:** `['range(1, 8)']`

**Child parameters:** 7

**Dimension analysis:**
- `range(1, 8)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ky.dcbs.ktap.benefit.standard_of_need.1`
- Generated label: "Kentucky K-TAP standard of need (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 8)]']`

---

### 149. `gov.states.ky.dcbs.ktap.benefit.payment_maximum`

**Label:** Kentucky K-TAP payment maximum

**Breakdown dimensions:** `['range(1, 8)']`

**Child parameters:** 7

**Dimension analysis:**
- `range(1, 8)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ky.dcbs.ktap.benefit.payment_maximum.1`
- Generated label: "Kentucky K-TAP payment maximum (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 8)]']`

---

### 150. `gov.irs.income.bracket.rates`

**Label:** Individual income tax rates

**Breakdown dimensions:** `['range(1, 8)']`

**Child parameters:** 7

**Dimension analysis:**
- `range(1, 8)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.irs.income.bracket.rates.1`
- Generated label: "Individual income tax rates (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 8)]']`

---

### 151. `gov.aca.family_tier_ratings.ny`

**Label:** ACA premium family tier multipliers - NY

**Breakdown dimensions:** `['slcsp_family_tier_category']`

**Child parameters:** 6

**Dimension analysis:**
- `slcsp_family_tier_category` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.aca.family_tier_ratings.ny.ONE_ADULT`
- Generated label: "ACA premium family tier multipliers - NY (ONE_ADULT)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 152. `gov.aca.family_tier_ratings.vt`

**Label:** ACA premium family tier multipliers - VT

**Breakdown dimensions:** `['slcsp_family_tier_category']`

**Child parameters:** 6

**Dimension analysis:**
- `slcsp_family_tier_category` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.aca.family_tier_ratings.vt.ONE_ADULT`
- Generated label: "ACA premium family tier multipliers - VT (ONE_ADULT)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 153. `gov.usda.wic.nutritional_risk`

**Label:** WIC nutritional risk

**Breakdown dimensions:** `['wic_category']`

**Child parameters:** 6

**Dimension analysis:**
- `wic_category` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.usda.wic.nutritional_risk.PREGNANT`
- Generated label: "WIC nutritional risk (PREGNANT)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 154. `gov.usda.wic.takeup`

**Label:** WIC takeup rate

**Breakdown dimensions:** `['wic_category']`

**Child parameters:** 6

**Dimension analysis:**
- `wic_category` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.usda.wic.takeup.PREGNANT`
- Generated label: "WIC takeup rate (PREGNANT)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 155. `gov.states.ma.doer.liheap.hecs.eligibility.prior_year_cost_threshold`

**Label:** Massachusetts LIHEAP HECS payment threshold

**Breakdown dimensions:** `['ma_liheap_heating_type']`

**Child parameters:** 6

**Dimension analysis:**
- `ma_liheap_heating_type` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.ma.doer.liheap.hecs.eligibility.prior_year_cost_threshold.HEATING_OIL_AND_PROPANE`
- Generated label: "Massachusetts LIHEAP HECS payment threshold (HEATING_OIL_AND_PROPANE)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 156. `gov.states.ny.otda.tanf.need_standard.main`

**Label:** New York TANF monthly income limit

**Breakdown dimensions:** `['range(1, 7)']`

**Child parameters:** 6

**Dimension analysis:**
- `range(1, 7)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ny.otda.tanf.need_standard.main.1`
- Generated label: "New York TANF monthly income limit (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 7)]']`

---

### 157. `gov.states.ny.otda.tanf.grant_standard.main`

**Label:** New York TANF monthly income limit

**Breakdown dimensions:** `['range(1, 7)']`

**Child parameters:** 6

**Dimension analysis:**
- `range(1, 7)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ny.otda.tanf.grant_standard.main.1`
- Generated label: "New York TANF monthly income limit (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 7)]']`

---

### 158. `calibration.gov.hhs.medicaid.totals.per_capita`

**Label:** Per-capita Medicaid cost for other adults

**Breakdown dimensions:** `['medicaid_group']`

**Child parameters:** 5

**Dimension analysis:**
- `medicaid_group` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `calibration.gov.hhs.medicaid.totals.per_capita.NON_EXPANSION_ADULT`
- Generated label: "Per-capita Medicaid cost for other adults (NON_EXPANSION_ADULT)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 159. `gov.territories.pr.tax.income.taxable_income.exemptions.personal`

**Label:** Puerto Rico personal exemption amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.territories.pr.tax.income.taxable_income.exemptions.personal.SINGLE`
- Generated label: "Puerto Rico personal exemption amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 160. `gov.contrib.biden.budget_2025.capital_gains.income_threshold`

**Label:** Threshold above which capital income is taxed as ordinary income

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.biden.budget_2025.capital_gains.income_threshold.JOINT`
- Generated label: "Threshold above which capital income is taxed as ordinary income (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 161. `gov.contrib.harris.lift.middle_class_tax_credit.phase_out.width`

**Label:** Middle Class Tax Credit phase-out width

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.harris.lift.middle_class_tax_credit.phase_out.width.SINGLE`
- Generated label: "Middle Class Tax Credit phase-out width (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 162. `gov.contrib.harris.lift.middle_class_tax_credit.phase_out.start`

**Label:** Middle Class Tax Credit phase-out start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.harris.lift.middle_class_tax_credit.phase_out.start.SINGLE`
- Generated label: "Middle Class Tax Credit phase-out start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 163. `gov.contrib.ubi_center.basic_income.agi_limit.amount`

**Label:** Basic income AGI limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.ubi_center.basic_income.agi_limit.amount.SINGLE`
- Generated label: "Basic income AGI limit (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 164. `gov.contrib.ubi_center.basic_income.phase_out.end`

**Label:** Basic income phase-out end

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.ubi_center.basic_income.phase_out.end.SINGLE`
- Generated label: "Basic income phase-out end (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 165. `gov.contrib.ubi_center.basic_income.phase_out.threshold`

**Label:** Basic income phase-out threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.ubi_center.basic_income.phase_out.threshold.SINGLE`
- Generated label: "Basic income phase-out threshold (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 166. `gov.contrib.ubi_center.flat_tax.exemption.agi`

**Label:** Flat tax on AGI exemption amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.ubi_center.flat_tax.exemption.agi.HEAD_OF_HOUSEHOLD`
- Generated label: "Flat tax on AGI exemption amount (HEAD_OF_HOUSEHOLD)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 167. `gov.contrib.crfb.ss_credit.amount`

**Label:** CRFB Social Security nonrefundable credit amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.crfb.ss_credit.amount.JOINT`
- Generated label: "CRFB Social Security nonrefundable credit amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 168. `gov.contrib.local.nyc.stc.income_limit`

**Label:** NYC School Tax Credit Income Limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.local.nyc.stc.income_limit.SINGLE`
- Generated label: "NYC School Tax Credit Income Limit (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 169. `gov.contrib.states.ri.dependent_exemption.phaseout.threshold`

**Label:** Rhode Island dependent exemption phaseout threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.states.ri.dependent_exemption.phaseout.threshold.JOINT`
- Generated label: "Rhode Island dependent exemption phaseout threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 170. `gov.contrib.states.ri.ctc.phaseout.threshold`

**Label:** Rhode Island Child Tax Credit phaseout threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.states.ri.ctc.phaseout.threshold.JOINT`
- Generated label: "Rhode Island Child Tax Credit phaseout threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 171. `gov.contrib.states.dc.property_tax.income_limit.non_elderly`

**Label:** DC property tax credit non-elderly income limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.states.dc.property_tax.income_limit.non_elderly.JOINT`
- Generated label: "DC property tax credit non-elderly income limit (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 172. `gov.contrib.states.dc.property_tax.income_limit.elderly`

**Label:** DC property tax credit elderly income limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.states.dc.property_tax.income_limit.elderly.JOINT`
- Generated label: "DC property tax credit elderly income limit (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 173. `gov.contrib.states.dc.property_tax.amount`

**Label:** DC property tax credit amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.states.dc.property_tax.amount.JOINT`
- Generated label: "DC property tax credit amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 174. `gov.contrib.states.de.dependent_credit.phaseout.threshold`

**Label:** Delaware dependent credit phaseout threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.states.de.dependent_credit.phaseout.threshold.JOINT`
- Generated label: "Delaware dependent credit phaseout threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 175. `gov.contrib.dc_kccatc.phase_out.threshold`

**Label:** DC KCCATC phase-out threshold

**Breakdown dimensions:** `filing_status`

**Child parameters:** 5

**Dimension analysis:**
- `f` → Variable/enum lookup (may or may not have labels)
- `i` → Variable/enum lookup (may or may not have labels)
- `l` → Variable/enum lookup (may or may not have labels)
- `i` → Variable/enum lookup (may or may not have labels)
- `n` → Variable/enum lookup (may or may not have labels)
- `g` → Variable/enum lookup (may or may not have labels)
- `_` → Variable/enum lookup (may or may not have labels)
- `s` → Variable/enum lookup (may or may not have labels)
- `t` → Variable/enum lookup (may or may not have labels)
- `a` → Variable/enum lookup (may or may not have labels)
- `t` → Variable/enum lookup (may or may not have labels)
- `u` → Variable/enum lookup (may or may not have labels)
- `s` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.contrib.dc_kccatc.phase_out.threshold.SINGLE`
- Generated label: "DC KCCATC phase-out threshold (SINGLE)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 176. `gov.contrib.congress.hawley.awra.phase_out.start`

**Label:** American Worker Rebate Act phase-out start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.congress.hawley.awra.phase_out.start.SINGLE`
- Generated label: "American Worker Rebate Act phase-out start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 177. `gov.contrib.congress.tlaib.end_child_poverty_act.filer_credit.phase_out.start`

**Label:** End Child Poverty Act filer credit phase-out start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.congress.tlaib.end_child_poverty_act.filer_credit.phase_out.start.JOINT`
- Generated label: "End Child Poverty Act filer credit phase-out start (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 178. `gov.contrib.congress.tlaib.end_child_poverty_act.filer_credit.amount`

**Label:** End Child Poverty Act filer credit amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.congress.tlaib.end_child_poverty_act.filer_credit.amount.JOINT`
- Generated label: "End Child Poverty Act filer credit amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 179. `gov.contrib.congress.tlaib.economic_dignity_for_all_agenda.end_child_poverty_act.filer_credit.phase_out.start`

**Label:** Filer credit phase-out start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.congress.tlaib.economic_dignity_for_all_agenda.end_child_poverty_act.filer_credit.phase_out.start.JOINT`
- Generated label: "Filer credit phase-out start (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 180. `gov.contrib.congress.tlaib.economic_dignity_for_all_agenda.end_child_poverty_act.filer_credit.amount`

**Label:** Filer credit amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.congress.tlaib.economic_dignity_for_all_agenda.end_child_poverty_act.filer_credit.amount.JOINT`
- Generated label: "Filer credit amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 181. `gov.contrib.congress.afa.ctc.phase_out.threshold.lower`

**Label:** AFA CTC phase-out lower threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.congress.afa.ctc.phase_out.threshold.lower.SINGLE`
- Generated label: "AFA CTC phase-out lower threshold (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 182. `gov.contrib.congress.afa.ctc.phase_out.threshold.higher`

**Label:** AFA CTC phase-out higher threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.contrib.congress.afa.ctc.phase_out.threshold.higher.SINGLE`
- Generated label: "AFA CTC phase-out higher threshold (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 183. `gov.local.ca.riv.general_relief.needs_standards.personal_needs`

**Label:** Riverside County General Relief personal needs standard

**Breakdown dimensions:** `['range(1,6)']`

**Child parameters:** 5

**Dimension analysis:**
- `range(1,6)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.local.ca.riv.general_relief.needs_standards.personal_needs.1`
- Generated label: "Riverside County General Relief personal needs standard (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1,6)]']`

---

### 184. `gov.local.ca.riv.general_relief.needs_standards.food`

**Label:** Riverside County General Relief food needs standard

**Breakdown dimensions:** `['range(1,6)']`

**Child parameters:** 5

**Dimension analysis:**
- `range(1,6)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.local.ca.riv.general_relief.needs_standards.food.1`
- Generated label: "Riverside County General Relief food needs standard (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1,6)]']`

---

### 185. `gov.local.ca.riv.general_relief.needs_standards.housing`

**Label:** Riverside County General Relief housing needs standard

**Breakdown dimensions:** `['range(1,6)']`

**Child parameters:** 5

**Dimension analysis:**
- `range(1,6)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.local.ca.riv.general_relief.needs_standards.housing.1`
- Generated label: "Riverside County General Relief housing needs standard (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1,6)]']`

---

### 186. `gov.local.ny.nyc.tax.income.credits.school.fixed.amount`

**Label:** NYC School Tax Credit Fixed Amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.local.ny.nyc.tax.income.credits.school.fixed.amount.SINGLE`
- Generated label: "NYC School Tax Credit Fixed Amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 187. `gov.states.vt.tax.income.agi.retirement_income_exemption.social_security.reduction.end`

**Label:** Vermont social security retirement income exemption income threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.vt.tax.income.agi.retirement_income_exemption.social_security.reduction.end.JOINT`
- Generated label: "Vermont social security retirement income exemption income threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 188. `gov.states.vt.tax.income.agi.retirement_income_exemption.social_security.reduction.start`

**Label:** Vermont social security retirement income exemption reduction threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.vt.tax.income.agi.retirement_income_exemption.social_security.reduction.start.JOINT`
- Generated label: "Vermont social security retirement income exemption reduction threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 189. `gov.states.vt.tax.income.agi.retirement_income_exemption.csrs.reduction.end`

**Label:** Vermont CSRS and military retirement income exemption income threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.vt.tax.income.agi.retirement_income_exemption.csrs.reduction.end.JOINT`
- Generated label: "Vermont CSRS and military retirement income exemption income threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 190. `gov.states.vt.tax.income.agi.retirement_income_exemption.csrs.reduction.start`

**Label:** Vermont CSRS and military retirement income exemption reduction threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.vt.tax.income.agi.retirement_income_exemption.csrs.reduction.start.JOINT`
- Generated label: "Vermont CSRS and military retirement income exemption reduction threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 191. `gov.states.vt.tax.income.deductions.standard.base`

**Label:** Vermont standard deduction

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.vt.tax.income.deductions.standard.base.JOINT`
- Generated label: "Vermont standard deduction (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 192. `gov.states.vt.tax.income.credits.cdcc.low_income.income_threshold`

**Label:** Vermont low-income CDCC AGI limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.vt.tax.income.credits.cdcc.low_income.income_threshold.JOINT`
- Generated label: "Vermont low-income CDCC AGI limit (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 193. `gov.states.va.tax.income.subtractions.age_deduction.threshold`

**Label:** Adjusted federal AGI threshold for VA taxpayers eligible for an age deduction

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.va.tax.income.subtractions.age_deduction.threshold.JOINT`
- Generated label: "Adjusted federal AGI threshold for VA taxpayers eligible for an age deduction (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 194. `gov.states.va.tax.income.deductions.itemized.applicable_amount`

**Label:** Virginia itemized deduction applicable amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.va.tax.income.deductions.itemized.applicable_amount.JOINT`
- Generated label: "Virginia itemized deduction applicable amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 195. `gov.states.va.tax.income.deductions.standard`

**Label:** Virginia standard deduction

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.va.tax.income.deductions.standard.JOINT`
- Generated label: "Virginia standard deduction (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 196. `gov.states.va.tax.income.rebate.amount`

**Label:** Virginia rebate amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.va.tax.income.rebate.amount.JOINT`
- Generated label: "Virginia rebate amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 197. `gov.states.va.tax.income.filing_requirement`

**Label:** Virginia filing requirement

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.va.tax.income.filing_requirement.JOINT`
- Generated label: "Virginia filing requirement (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 198. `gov.states.ut.tax.income.credits.ctc.reduction.start`

**Label:** Utah child tax credit reduction start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ut.tax.income.credits.ctc.reduction.start.SINGLE`
- Generated label: "Utah child tax credit reduction start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 199. `gov.states.ga.tax.income.deductions.standard.amount`

**Label:** Georgia standard deduction amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ga.tax.income.deductions.standard.amount.JOINT`
- Generated label: "Georgia standard deduction amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 200. `gov.states.ga.tax.income.exemptions.personal.amount`

**Label:** Georgia personal exemption amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ga.tax.income.exemptions.personal.amount.JOINT`
- Generated label: "Georgia personal exemption amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 201. `gov.states.ga.tax.income.credits.surplus_tax_rebate.amount`

**Label:** Georgia surplus tax rebate amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ga.tax.income.credits.surplus_tax_rebate.amount.JOINT`
- Generated label: "Georgia surplus tax rebate amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 202. `gov.states.ms.tax.income.deductions.standard.amount`

**Label:** Mississippi standard deduction

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ms.tax.income.deductions.standard.amount.SINGLE`
- Generated label: "Mississippi standard deduction (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 203. `gov.states.ms.tax.income.exemptions.regular.amount`

**Label:** Mississippi exemption

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ms.tax.income.exemptions.regular.amount.SINGLE`
- Generated label: "Mississippi exemption (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 204. `gov.states.ms.tax.income.credits.charitable_contribution.cap`

**Label:** Mississippi credit for contributions to foster organizations cap

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ms.tax.income.credits.charitable_contribution.cap.JOINT`
- Generated label: "Mississippi credit for contributions to foster organizations cap (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 205. `gov.states.mt.tax.income.deductions.itemized.federal_income_tax.cap`

**Label:** Montana federal income tax deduction cap

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mt.tax.income.deductions.itemized.federal_income_tax.cap.JOINT`
- Generated label: "Montana federal income tax deduction cap (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 206. `gov.states.mt.tax.income.deductions.standard.floor`

**Label:** Montana minimum standard deduction

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mt.tax.income.deductions.standard.floor.JOINT`
- Generated label: "Montana minimum standard deduction (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 207. `gov.states.mt.tax.income.deductions.standard.cap`

**Label:** Montana standard deduction max amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mt.tax.income.deductions.standard.cap.JOINT`
- Generated label: "Montana standard deduction max amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 208. `gov.states.mt.tax.income.social_security.amount.upper`

**Label:** Montana social security benefits amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mt.tax.income.social_security.amount.upper.SINGLE`
- Generated label: "Montana social security benefits amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 209. `gov.states.mt.tax.income.social_security.amount.lower`

**Label:** Montana social security benefits amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mt.tax.income.social_security.amount.lower.SINGLE`
- Generated label: "Montana social security benefits amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 210. `gov.states.mt.tax.income.main.capital_gains.rates.main`

**Label:** Montana capital gains tax rate when nonqualified income exceeds threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mt.tax.income.main.capital_gains.rates.main.JOINT`
- Generated label: "Montana capital gains tax rate when nonqualified income exceeds threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 211. `gov.states.mt.tax.income.main.capital_gains.threshold`

**Label:** Montana capital gains tax threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mt.tax.income.main.capital_gains.threshold.JOINT`
- Generated label: "Montana capital gains tax threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 212. `gov.states.mt.tax.income.exemptions.interest.cap`

**Label:** Montana senior interest income exclusion cap

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mt.tax.income.exemptions.interest.cap.SINGLE`
- Generated label: "Montana senior interest income exclusion cap (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 213. `gov.states.mt.tax.income.credits.rebate.amount`

**Label:** Montana income tax rebate amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mt.tax.income.credits.rebate.amount.SINGLE`
- Generated label: "Montana income tax rebate amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 214. `gov.states.mo.tax.income.deductions.federal_income_tax.cap`

**Label:** Missouri federal income tax deduction caps

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mo.tax.income.deductions.federal_income_tax.cap.SINGLE`
- Generated label: "Missouri federal income tax deduction caps (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 215. `gov.states.mo.tax.income.deductions.mo_private_pension_deduction_allowance`

**Label:** Missouri private pension deduction allowance

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mo.tax.income.deductions.mo_private_pension_deduction_allowance.SINGLE`
- Generated label: "Missouri private pension deduction allowance (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 216. `gov.states.mo.tax.income.deductions.social_security_and_public_pension.mo_ss_or_ssd_deduction_allowance`

**Label:** Missouri social security or social security disability deduction allowance

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mo.tax.income.deductions.social_security_and_public_pension.mo_ss_or_ssd_deduction_allowance.SINGLE`
- Generated label: "Missouri social security or social security disability deduction allowance (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 217. `gov.states.mo.tax.income.deductions.social_security_and_public_pension.mo_public_pension_deduction_allowance`

**Label:** Missouri Public Pension Deduction Allowance

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mo.tax.income.deductions.social_security_and_public_pension.mo_public_pension_deduction_allowance.SINGLE`
- Generated label: "Missouri Public Pension Deduction Allowance (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 218. `gov.states.mo.tax.income.deductions.social_security_and_public_pension.mo_ss_or_ssdi_exemption_threshold`

**Label:** Missouri social security or social security disability income exemption threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mo.tax.income.deductions.social_security_and_public_pension.mo_ss_or_ssdi_exemption_threshold.SINGLE`
- Generated label: "Missouri social security or social security disability income exemption threshold (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 219. `gov.states.ma.tax.income.deductions.rent.cap`

**Label:** Massachusetts rental deduction cap.

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ma.tax.income.deductions.rent.cap.SINGLE`
- Generated label: "Massachusetts rental deduction cap. (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 220. `gov.states.ma.tax.income.exempt_status.limit.personal_exemption_added`

**Label:** Massachusetts income tax exemption limit includes personal exemptions

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ma.tax.income.exempt_status.limit.personal_exemption_added.SINGLE`
- Generated label: "Massachusetts income tax exemption limit includes personal exemptions (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 221. `gov.states.ma.tax.income.exempt_status.limit.base`

**Label:** AGI addition to limit to be exempt from Massachusetts income tax.

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ma.tax.income.exempt_status.limit.base.SINGLE`
- Generated label: "AGI addition to limit to be exempt from Massachusetts income tax. (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 222. `gov.states.ma.tax.income.exemptions.interest.amount`

**Label:** Massachusetts interest exemption

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ma.tax.income.exemptions.interest.amount.SINGLE`
- Generated label: "Massachusetts interest exemption (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 223. `gov.states.ma.tax.income.exemptions.personal`

**Label:** Massachusetts income tax personal exemption

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ma.tax.income.exemptions.personal.SINGLE`
- Generated label: "Massachusetts income tax personal exemption (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 224. `gov.states.ma.tax.income.credits.senior_circuit_breaker.eligibility.max_income`

**Label:** Massachusetts Senior Circuit Breaker maximum income

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ma.tax.income.credits.senior_circuit_breaker.eligibility.max_income.SINGLE`
- Generated label: "Massachusetts Senior Circuit Breaker maximum income (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 225. `gov.states.al.tax.income.deductions.standard.amount.max`

**Label:** Alabama standard deduction maximum amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.al.tax.income.deductions.standard.amount.max.JOINT`
- Generated label: "Alabama standard deduction maximum amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 226. `gov.states.al.tax.income.deductions.standard.amount.min`

**Label:** Alabama standard deduction minimum amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.al.tax.income.deductions.standard.amount.min.JOINT`
- Generated label: "Alabama standard deduction minimum amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 227. `gov.states.al.tax.income.deductions.standard.phase_out.increment`

**Label:** Alabama standard deduction phase-out increment

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.al.tax.income.deductions.standard.phase_out.increment.JOINT`
- Generated label: "Alabama standard deduction phase-out increment (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 228. `gov.states.al.tax.income.deductions.standard.phase_out.rate`

**Label:** Alabama standard deduction phase-out rate

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.al.tax.income.deductions.standard.phase_out.rate.JOINT`
- Generated label: "Alabama standard deduction phase-out rate (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 229. `gov.states.al.tax.income.deductions.standard.phase_out.threshold`

**Label:** Alabama standard deduction phase-out threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.al.tax.income.deductions.standard.phase_out.threshold.JOINT`
- Generated label: "Alabama standard deduction phase-out threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 230. `gov.states.al.tax.income.exemptions.personal`

**Label:** Alabama personal exemption amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.al.tax.income.exemptions.personal.SINGLE`
- Generated label: "Alabama personal exemption amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 231. `gov.states.nh.tax.income.exemptions.amount.base`

**Label:** New Hampshire base exemption amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.nh.tax.income.exemptions.amount.base.SINGLE`
- Generated label: "New Hampshire base exemption amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 232. `gov.states.mn.tax.income.subtractions.education_savings.cap`

**Label:** Minnesota 529 plan contribution subtraction maximum

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mn.tax.income.subtractions.education_savings.cap.JOINT`
- Generated label: "Minnesota 529 plan contribution subtraction maximum (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 233. `gov.states.mn.tax.income.subtractions.elderly_disabled.agi_offset_base`

**Label:** Minnesota base AGI offset in elderly/disabled subtraction calculations

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mn.tax.income.subtractions.elderly_disabled.agi_offset_base.JOINT`
- Generated label: "Minnesota base AGI offset in elderly/disabled subtraction calculations (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 234. `gov.states.mn.tax.income.subtractions.elderly_disabled.base_amount`

**Label:** Minnesota base amount in elderly/disabled subtraction calculations

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mn.tax.income.subtractions.elderly_disabled.base_amount.JOINT`
- Generated label: "Minnesota base amount in elderly/disabled subtraction calculations (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 235. `gov.states.mn.tax.income.subtractions.social_security.alternative_amount`

**Label:** Minnesota social security subtraction alternative subtraction amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mn.tax.income.subtractions.social_security.alternative_amount.JOINT`
- Generated label: "Minnesota social security subtraction alternative subtraction amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 236. `gov.states.mn.tax.income.subtractions.social_security.reduction.start`

**Label:** Minnesota social security subtraction reduction start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mn.tax.income.subtractions.social_security.reduction.start.JOINT`
- Generated label: "Minnesota social security subtraction reduction start (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 237. `gov.states.mn.tax.income.subtractions.social_security.income_amount`

**Label:** Minnesota social security subtraction income amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mn.tax.income.subtractions.social_security.income_amount.JOINT`
- Generated label: "Minnesota social security subtraction income amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 238. `gov.states.mn.tax.income.subtractions.pension_income.reduction.start`

**Label:** Minnesota public pension income subtraction agi threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mn.tax.income.subtractions.pension_income.reduction.start.JOINT`
- Generated label: "Minnesota public pension income subtraction agi threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 239. `gov.states.mn.tax.income.subtractions.pension_income.cap`

**Label:** Minnesota public pension income subtraction cap

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mn.tax.income.subtractions.pension_income.cap.JOINT`
- Generated label: "Minnesota public pension income subtraction cap (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 240. `gov.states.mn.tax.income.amt.fractional_income_threshold`

**Label:** Minnesota fractional excess income threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mn.tax.income.amt.fractional_income_threshold.JOINT`
- Generated label: "Minnesota fractional excess income threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 241. `gov.states.mn.tax.income.amt.income_threshold`

**Label:** Minnesota AMT taxable income threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mn.tax.income.amt.income_threshold.JOINT`
- Generated label: "Minnesota AMT taxable income threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 242. `gov.states.mn.tax.income.deductions.itemized.reduction.agi_threshold.high`

**Label:** Minnesota itemized deduction higher reduction AGI threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mn.tax.income.deductions.itemized.reduction.agi_threshold.high.JOINT`
- Generated label: "Minnesota itemized deduction higher reduction AGI threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 243. `gov.states.mn.tax.income.deductions.itemized.reduction.agi_threshold.low`

**Label:** Minnesota itemized deduction lower reduction AGI threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mn.tax.income.deductions.itemized.reduction.agi_threshold.low.JOINT`
- Generated label: "Minnesota itemized deduction lower reduction AGI threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 244. `gov.states.mn.tax.income.deductions.standard.extra`

**Label:** Minnesota extra standard deduction amount for each aged/blind head/spouse

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mn.tax.income.deductions.standard.extra.JOINT`
- Generated label: "Minnesota extra standard deduction amount for each aged/blind head/spouse (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 245. `gov.states.mn.tax.income.deductions.standard.reduction.agi_threshold.high`

**Label:** Minnesota standard deduction higher reduction AGI threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mn.tax.income.deductions.standard.reduction.agi_threshold.high.JOINT`
- Generated label: "Minnesota standard deduction higher reduction AGI threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 246. `gov.states.mn.tax.income.deductions.standard.reduction.agi_threshold.low`

**Label:** Minnesota standard deduction lower reduction AGI threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mn.tax.income.deductions.standard.reduction.agi_threshold.low.JOINT`
- Generated label: "Minnesota standard deduction lower reduction AGI threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 247. `gov.states.mn.tax.income.deductions.standard.base`

**Label:** Minnesota base standard deduction amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mn.tax.income.deductions.standard.base.JOINT`
- Generated label: "Minnesota base standard deduction amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 248. `gov.states.mn.tax.income.exemptions.agi_threshold`

**Label:** federal adjusted gross income threshold above which Minnesota exemptions are limited

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mn.tax.income.exemptions.agi_threshold.JOINT`
- Generated label: "federal adjusted gross income threshold above which Minnesota exemptions are limited (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 249. `gov.states.mn.tax.income.exemptions.agi_step_size`

**Label:** federal adjusted gross income step size used to limit Minnesota exemptions

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mn.tax.income.exemptions.agi_step_size.JOINT`
- Generated label: "federal adjusted gross income step size used to limit Minnesota exemptions (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 250. `gov.states.mi.tax.income.deductions.standard.tier_three.amount`

**Label:** Michigan tier three standard deduction amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mi.tax.income.deductions.standard.tier_three.amount.SINGLE`
- Generated label: "Michigan tier three standard deduction amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 251. `gov.states.mi.tax.income.deductions.standard.tier_two.amount.base`

**Label:** Michigan tier two standard deduction base

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mi.tax.income.deductions.standard.tier_two.amount.base.SINGLE`
- Generated label: "Michigan tier two standard deduction base (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 252. `gov.states.mi.tax.income.deductions.interest_dividends_capital_gains.amount`

**Label:** Michigan interest, dividends, and capital gains deduction amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mi.tax.income.deductions.interest_dividends_capital_gains.amount.SINGLE`
- Generated label: "Michigan interest, dividends, and capital gains deduction amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 253. `gov.states.mi.tax.income.deductions.retirement_benefits.tier_three.ss_exempt.retired.both_qualifying_amount`

**Label:** Michigan tier three retirement and pension deduction both qualifying seniors

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mi.tax.income.deductions.retirement_benefits.tier_three.ss_exempt.retired.both_qualifying_amount.SINGLE`
- Generated label: "Michigan tier three retirement and pension deduction both qualifying seniors (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 254. `gov.states.mi.tax.income.deductions.retirement_benefits.tier_three.ss_exempt.retired.single_qualifying_amount`

**Label:** Michigan tier three retirement and pension deduction single qualifying senior amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mi.tax.income.deductions.retirement_benefits.tier_three.ss_exempt.retired.single_qualifying_amount.SINGLE`
- Generated label: "Michigan tier three retirement and pension deduction single qualifying senior amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 255. `gov.states.mi.tax.income.deductions.retirement_benefits.tier_one.amount`

**Label:** Michigan tier one retirement and pension benefits amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mi.tax.income.deductions.retirement_benefits.tier_one.amount.SINGLE`
- Generated label: "Michigan tier one retirement and pension benefits amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 256. `gov.states.mi.tax.income.exemptions.dependent_on_other_return`

**Label:** Michigan dependent on other return exemption amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.mi.tax.income.exemptions.dependent_on_other_return.SINGLE`
- Generated label: "Michigan dependent on other return exemption amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 257. `gov.states.ok.tax.income.deductions.standard.amount`

**Label:** Oklahoma standard deduction amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ok.tax.income.deductions.standard.amount.JOINT`
- Generated label: "Oklahoma standard deduction amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 258. `gov.states.ok.tax.income.exemptions.special_agi_limit`

**Label:** Oklahoma special exemption federal AGI limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ok.tax.income.exemptions.special_agi_limit.JOINT`
- Generated label: "Oklahoma special exemption federal AGI limit (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 259. `gov.states.in.tax.income.deductions.homeowners_property_tax.max`

**Label:** Indiana max homeowner's property tax deduction

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.in.tax.income.deductions.homeowners_property_tax.max.SINGLE`
- Generated label: "Indiana max homeowner's property tax deduction (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 260. `gov.states.in.tax.income.deductions.renters.max`

**Label:** Indiana max renter's deduction

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.in.tax.income.deductions.renters.max.SINGLE`
- Generated label: "Indiana max renter's deduction (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 261. `gov.states.in.tax.income.deductions.unemployment_compensation.agi_reduction`

**Label:** Indiana AGI reduction for calculation of maximum unemployment compensation deduction

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.in.tax.income.deductions.unemployment_compensation.agi_reduction.SINGLE`
- Generated label: "Indiana AGI reduction for calculation of maximum unemployment compensation deduction (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 262. `gov.states.in.tax.income.exemptions.aged_low_agi.threshold`

**Label:** Indiana low AGI aged exemption income limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.in.tax.income.exemptions.aged_low_agi.threshold.SINGLE`
- Generated label: "Indiana low AGI aged exemption income limit (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 263. `gov.states.co.tax.income.subtractions.collegeinvest_contribution.max_amount`

**Label:** Colorado CollegeInvest contribution subtraction max amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.co.tax.income.subtractions.collegeinvest_contribution.max_amount.HEAD_OF_HOUSEHOLD`
- Generated label: "Colorado CollegeInvest contribution subtraction max amount (HEAD_OF_HOUSEHOLD)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 264. `gov.states.co.tax.income.subtractions.able_contribution.cap`

**Label:** Colorado ABLE contribution subtraction cap

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.co.tax.income.subtractions.able_contribution.cap.JOINT`
- Generated label: "Colorado ABLE contribution subtraction cap (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 265. `gov.states.co.tax.income.additions.federal_deductions.exemption`

**Label:** Colorado itemized or standard deduction add back exemption

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.co.tax.income.additions.federal_deductions.exemption.JOINT`
- Generated label: "Colorado itemized or standard deduction add back exemption (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 266. `gov.states.co.tax.income.additions.qualified_business_income_deduction.agi_threshold`

**Label:** Colorado qualified business income deduction addback AGI threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.co.tax.income.additions.qualified_business_income_deduction.agi_threshold.SINGLE`
- Generated label: "Colorado qualified business income deduction addback AGI threshold (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 267. `gov.states.co.tax.income.credits.income_qualified_senior_housing.reduction.max_amount`

**Label:** Colorado income qualified senior housing income tax credit max amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.co.tax.income.credits.income_qualified_senior_housing.reduction.max_amount.SINGLE`
- Generated label: "Colorado income qualified senior housing income tax credit max amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 268. `gov.states.co.tax.income.credits.income_qualified_senior_housing.reduction.amount`

**Label:** Colorado income qualified senior housing income tax credit reduction amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.co.tax.income.credits.income_qualified_senior_housing.reduction.amount.SINGLE`
- Generated label: "Colorado income qualified senior housing income tax credit reduction amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 269. `gov.states.co.tax.income.credits.sales_tax_refund.amount.multiplier`

**Label:** Colorado sales tax refund filing status multiplier

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.co.tax.income.credits.sales_tax_refund.amount.multiplier.HEAD_OF_HOUSEHOLD`
- Generated label: "Colorado sales tax refund filing status multiplier (HEAD_OF_HOUSEHOLD)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 270. `gov.states.co.tax.income.credits.family_affordability.reduction.threshold`

**Label:** Colorado family affordability tax credit income-based reduction start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.co.tax.income.credits.family_affordability.reduction.threshold.SINGLE`
- Generated label: "Colorado family affordability tax credit income-based reduction start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 271. `gov.states.ca.tax.income.amt.exemption.amti.threshold.upper`

**Label:** California alternative minimum tax exemption upper AMTI threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ca.tax.income.amt.exemption.amti.threshold.upper.JOINT`
- Generated label: "California alternative minimum tax exemption upper AMTI threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 272. `gov.states.ca.tax.income.amt.exemption.amti.threshold.lower`

**Label:** California alternative minimum tax exemption lower AMTI threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ca.tax.income.amt.exemption.amti.threshold.lower.JOINT`
- Generated label: "California alternative minimum tax exemption lower AMTI threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 273. `gov.states.ca.tax.income.amt.exemption.amount`

**Label:** California exemption amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ca.tax.income.amt.exemption.amount.JOINT`
- Generated label: "California exemption amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 274. `gov.states.ca.tax.income.deductions.itemized.limit.agi_threshold`

**Label:** California itemized deduction limitation threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ca.tax.income.deductions.itemized.limit.agi_threshold.JOINT`
- Generated label: "California itemized deduction limitation threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 275. `gov.states.ca.tax.income.deductions.standard.amount`

**Label:** California standard deduction

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ca.tax.income.deductions.standard.amount.JOINT`
- Generated label: "California standard deduction (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 276. `gov.states.ca.tax.income.exemptions.phase_out.increment`

**Label:** California exemption phase out increment

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ca.tax.income.exemptions.phase_out.increment.SINGLE`
- Generated label: "California exemption phase out increment (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 277. `gov.states.ca.tax.income.exemptions.phase_out.start`

**Label:** California exemption phase out start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ca.tax.income.exemptions.phase_out.start.SINGLE`
- Generated label: "California exemption phase out start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 278. `gov.states.ca.tax.income.exemptions.personal_scale`

**Label:** California income personal exemption scaling factor

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ca.tax.income.exemptions.personal_scale.SINGLE`
- Generated label: "California income personal exemption scaling factor (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 279. `gov.states.ca.tax.income.credits.renter.amount`

**Label:** California renter tax credit amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ca.tax.income.credits.renter.amount.SINGLE`
- Generated label: "California renter tax credit amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 280. `gov.states.ca.tax.income.credits.renter.income_cap`

**Label:** California renter tax credit AGI cap

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ca.tax.income.credits.renter.income_cap.SINGLE`
- Generated label: "California renter tax credit AGI cap (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 281. `gov.states.ia.tax.income.alternative_minimum_tax.threshold`

**Label:** Iowa alternative minimum tax threshold amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ia.tax.income.alternative_minimum_tax.threshold.JOINT`
- Generated label: "Iowa alternative minimum tax threshold amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 282. `gov.states.ia.tax.income.alternative_minimum_tax.exemption`

**Label:** Iowa alternative minimum tax exemption amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ia.tax.income.alternative_minimum_tax.exemption.JOINT`
- Generated label: "Iowa alternative minimum tax exemption amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 283. `gov.states.ia.tax.income.deductions.standard.amount`

**Label:** Iowa standard deduction amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ia.tax.income.deductions.standard.amount.JOINT`
- Generated label: "Iowa standard deduction amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 284. `gov.states.ia.tax.income.pension_exclusion.maximum_amount`

**Label:** Iowa maximum pension exclusion amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ia.tax.income.pension_exclusion.maximum_amount.JOINT`
- Generated label: "Iowa maximum pension exclusion amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 285. `gov.states.ia.tax.income.reportable_social_security.deduction`

**Label:** Iowa reportable social security income deduction

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ia.tax.income.reportable_social_security.deduction.JOINT`
- Generated label: "Iowa reportable social security income deduction (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 286. `gov.states.ct.tax.income.subtractions.tuition.cap`

**Label:** Connecticut state tuition subtraction max amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.subtractions.tuition.cap.SINGLE`
- Generated label: "Connecticut state tuition subtraction max amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 287. `gov.states.ct.tax.income.subtractions.social_security.reduction_threshold`

**Label:** Connecticut social security subtraction reduction threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.subtractions.social_security.reduction_threshold.SINGLE`
- Generated label: "Connecticut social security subtraction reduction threshold (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 288. `gov.states.ct.tax.income.add_back.increment`

**Label:** Connecticut income tax phase out brackets

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.add_back.increment.SINGLE`
- Generated label: "Connecticut income tax phase out brackets (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 289. `gov.states.ct.tax.income.add_back.max_amount`

**Label:** Connecticut income tax phase out max amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.add_back.max_amount.SINGLE`
- Generated label: "Connecticut income tax phase out max amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 290. `gov.states.ct.tax.income.add_back.amount`

**Label:** Connecticut bottom income tax phase out amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.add_back.amount.SINGLE`
- Generated label: "Connecticut bottom income tax phase out amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 291. `gov.states.ct.tax.income.add_back.start`

**Label:** Connecticut income tax phase out start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.add_back.start.SINGLE`
- Generated label: "Connecticut income tax phase out start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 292. `gov.states.ct.tax.income.rebate.reduction.start`

**Label:** Connecticut child tax rebate reduction start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.rebate.reduction.start.SINGLE`
- Generated label: "Connecticut child tax rebate reduction start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 293. `gov.states.ct.tax.income.exemptions.personal.max_amount`

**Label:** Connecticut personal exemption max amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.exemptions.personal.max_amount.SINGLE`
- Generated label: "Connecticut personal exemption max amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 294. `gov.states.ct.tax.income.exemptions.personal.reduction.start`

**Label:** Connecticut personal exemption reduction start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.exemptions.personal.reduction.start.SINGLE`
- Generated label: "Connecticut personal exemption reduction start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 295. `gov.states.ct.tax.income.credits.property_tax.reduction.increment`

**Label:** Connecticut property tax reduction increment

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.credits.property_tax.reduction.increment.SINGLE`
- Generated label: "Connecticut property tax reduction increment (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 296. `gov.states.ct.tax.income.credits.property_tax.reduction.start`

**Label:** Connecticut Property Tax Credit reduction start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.credits.property_tax.reduction.start.SINGLE`
- Generated label: "Connecticut Property Tax Credit reduction start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 297. `gov.states.ct.tax.income.recapture.middle.increment`

**Label:** Connecticut income tax recapture middle bracket increment

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.recapture.middle.increment.SINGLE`
- Generated label: "Connecticut income tax recapture middle bracket increment (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 298. `gov.states.ct.tax.income.recapture.middle.max_amount`

**Label:** Connecticut income tax recapture middle bracket max amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.recapture.middle.max_amount.SINGLE`
- Generated label: "Connecticut income tax recapture middle bracket max amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 299. `gov.states.ct.tax.income.recapture.middle.amount`

**Label:** Connecticut income tax recapture middle bracket amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.recapture.middle.amount.SINGLE`
- Generated label: "Connecticut income tax recapture middle bracket amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 300. `gov.states.ct.tax.income.recapture.middle.start`

**Label:** Connecticut income tax recapture middle bracket start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.recapture.middle.start.SINGLE`
- Generated label: "Connecticut income tax recapture middle bracket start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 301. `gov.states.ct.tax.income.recapture.high.increment`

**Label:** Connecticut income tax recapture high bracket increment

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.recapture.high.increment.SINGLE`
- Generated label: "Connecticut income tax recapture high bracket increment (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 302. `gov.states.ct.tax.income.recapture.high.max_amount`

**Label:** Connecticut income tax recapture high bracket max amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.recapture.high.max_amount.SINGLE`
- Generated label: "Connecticut income tax recapture high bracket max amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 303. `gov.states.ct.tax.income.recapture.high.amount`

**Label:** Connecticut income tax recapture high bracket increment

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.recapture.high.amount.SINGLE`
- Generated label: "Connecticut income tax recapture high bracket increment (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 304. `gov.states.ct.tax.income.recapture.high.start`

**Label:** Connecticut income tax recapture high bracket start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.recapture.high.start.SINGLE`
- Generated label: "Connecticut income tax recapture high bracket start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 305. `gov.states.ct.tax.income.recapture.low.increment`

**Label:** Connecticut income tax recapture low bracket increment

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.recapture.low.increment.SINGLE`
- Generated label: "Connecticut income tax recapture low bracket increment (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 306. `gov.states.ct.tax.income.recapture.low.max_amount`

**Label:** Connecticut income tax recapture low bracket max amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.recapture.low.max_amount.SINGLE`
- Generated label: "Connecticut income tax recapture low bracket max amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 307. `gov.states.ct.tax.income.recapture.low.amount`

**Label:** Connecticut income tax recapture low bracket amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.recapture.low.amount.SINGLE`
- Generated label: "Connecticut income tax recapture low bracket amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 308. `gov.states.ct.tax.income.recapture.low.start`

**Label:** Connecticut income tax recapture low bracket start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ct.tax.income.recapture.low.start.SINGLE`
- Generated label: "Connecticut income tax recapture low bracket start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 309. `gov.states.wv.tax.income.subtractions.social_security_benefits.income_limit`

**Label:** West Virginia social security benefits subtraction income limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.wv.tax.income.subtractions.social_security_benefits.income_limit.JOINT`
- Generated label: "West Virginia social security benefits subtraction income limit (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 310. `gov.states.wv.tax.income.subtractions.low_income_earned_income.income_limit`

**Label:** West Virginia low-income earned income exclusion income limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.wv.tax.income.subtractions.low_income_earned_income.income_limit.SINGLE`
- Generated label: "West Virginia low-income earned income exclusion income limit (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 311. `gov.states.wv.tax.income.subtractions.low_income_earned_income.amount`

**Label:** West Virginia low-income earned income exclusion low-income earned income exclusion limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.wv.tax.income.subtractions.low_income_earned_income.amount.SINGLE`
- Generated label: "West Virginia low-income earned income exclusion low-income earned income exclusion limit (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 312. `gov.states.wv.tax.income.credits.liftc.fpg_percent`

**Label:** West Virginia low-income family tax credit MAGI limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.wv.tax.income.credits.liftc.fpg_percent.SINGLE`
- Generated label: "West Virginia low-income family tax credit MAGI limit (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 313. `gov.states.ri.tax.income.agi.subtractions.tuition_saving_program_contributions.cap`

**Label:** Rhode Island tuition saving program contribution deduction cap

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ri.tax.income.agi.subtractions.tuition_saving_program_contributions.cap.SINGLE`
- Generated label: "Rhode Island tuition saving program contribution deduction cap (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 314. `gov.states.ri.tax.income.agi.subtractions.taxable_retirement_income.income_limit`

**Label:** Rhode Island taxable retirement income subtraction income limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ri.tax.income.agi.subtractions.taxable_retirement_income.income_limit.JOINT`
- Generated label: "Rhode Island taxable retirement income subtraction income limit (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 315. `gov.states.ri.tax.income.agi.subtractions.social_security.limit.income`

**Label:** Rhode Island social security subtraction income limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ri.tax.income.agi.subtractions.social_security.limit.income.JOINT`
- Generated label: "Rhode Island social security subtraction income limit (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 316. `gov.states.ri.tax.income.deductions.standard.amount`

**Label:** Rhode Island standard deduction amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ri.tax.income.deductions.standard.amount.SINGLE`
- Generated label: "Rhode Island standard deduction amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 317. `gov.states.ri.tax.income.credits.child_tax_rebate.limit.income`

**Label:** Rhode Island child tax rebate income limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ri.tax.income.credits.child_tax_rebate.limit.income.SINGLE`
- Generated label: "Rhode Island child tax rebate income limit (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 318. `gov.states.nc.tax.income.deductions.standard.amount`

**Label:** North Carolina standard deduction amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.nc.tax.income.deductions.standard.amount.SINGLE`
- Generated label: "North Carolina standard deduction amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 319. `gov.states.nm.tax.income.rebates.property_tax.max_amount`

**Label:** New Mexico property tax rebate max amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.nm.tax.income.rebates.property_tax.max_amount.JOINT`
- Generated label: "New Mexico property tax rebate max amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 320. `gov.states.nm.tax.income.rebates.2021_income.supplemental.amount`

**Label:** New Mexico supplemental 2021 income tax rebate amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.nm.tax.income.rebates.2021_income.supplemental.amount.JOINT`
- Generated label: "New Mexico supplemental 2021 income tax rebate amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 321. `gov.states.nm.tax.income.rebates.2021_income.additional.amount`

**Label:** New Mexico additional 2021 income tax rebate amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.nm.tax.income.rebates.2021_income.additional.amount.JOINT`
- Generated label: "New Mexico additional 2021 income tax rebate amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 322. `gov.states.nm.tax.income.rebates.2021_income.main.income_limit`

**Label:** New Mexico main 2021 income tax rebate income limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.nm.tax.income.rebates.2021_income.main.income_limit.JOINT`
- Generated label: "New Mexico main 2021 income tax rebate income limit (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 323. `gov.states.nm.tax.income.rebates.2021_income.main.amount`

**Label:** New Mexico main 2021 income tax rebate amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.nm.tax.income.rebates.2021_income.main.amount.JOINT`
- Generated label: "New Mexico main 2021 income tax rebate amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 324. `gov.states.nm.tax.income.deductions.certain_dependents.amount`

**Label:** New Mexico deduction for certain dependents

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.nm.tax.income.deductions.certain_dependents.amount.JOINT`
- Generated label: "New Mexico deduction for certain dependents (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 325. `gov.states.nm.tax.income.exemptions.low_and_middle_income.income_limit`

**Label:** New Mexico low- and middle-income exemption income limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.nm.tax.income.exemptions.low_and_middle_income.income_limit.JOINT`
- Generated label: "New Mexico low- and middle-income exemption income limit (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 326. `gov.states.nm.tax.income.exemptions.low_and_middle_income.reduction.income_threshold`

**Label:** New Mexico low- and middle-income exemption reduction threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.nm.tax.income.exemptions.low_and_middle_income.reduction.income_threshold.JOINT`
- Generated label: "New Mexico low- and middle-income exemption reduction threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 327. `gov.states.nm.tax.income.exemptions.low_and_middle_income.reduction.rate`

**Label:** New Mexico low- and middle-income exemption reduction rate

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.nm.tax.income.exemptions.low_and_middle_income.reduction.rate.JOINT`
- Generated label: "New Mexico low- and middle-income exemption reduction rate (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 328. `gov.states.nm.tax.income.exemptions.social_security_income.income_limit`

**Label:** New Mexico social security income exemption income limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.nm.tax.income.exemptions.social_security_income.income_limit.JOINT`
- Generated label: "New Mexico social security income exemption income limit (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 329. `gov.states.nj.tax.income.filing_threshold`

**Label:** NJ filing threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.nj.tax.income.filing_threshold.SINGLE`
- Generated label: "NJ filing threshold (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 330. `gov.states.nj.tax.income.exclusions.retirement.max_amount`

**Label:** New Jersey pension/retirement maximum exclusion amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.nj.tax.income.exclusions.retirement.max_amount.SINGLE`
- Generated label: "New Jersey pension/retirement maximum exclusion amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 331. `gov.states.nj.tax.income.exclusions.retirement.special_exclusion.amount`

**Label:** NJ other retirement income special exclusion.

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.nj.tax.income.exclusions.retirement.special_exclusion.amount.SINGLE`
- Generated label: "NJ other retirement income special exclusion. (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 332. `gov.states.nj.tax.income.exemptions.regular.amount`

**Label:** New Jersey Regular Exemption

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.nj.tax.income.exemptions.regular.amount.SINGLE`
- Generated label: "New Jersey Regular Exemption (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 333. `gov.states.nj.tax.income.credits.property_tax.income_limit`

**Label:** New Jersey property tax credit income limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.nj.tax.income.credits.property_tax.income_limit.SINGLE`
- Generated label: "New Jersey property tax credit income limit (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 334. `gov.states.me.tax.income.deductions.phase_out.width`

**Label:** Maine standard/itemized deduction phase-out width

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.me.tax.income.deductions.phase_out.width.SINGLE`
- Generated label: "Maine standard/itemized deduction phase-out width (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 335. `gov.states.me.tax.income.deductions.phase_out.start`

**Label:** Maine standard/itemized exemption phase-out start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.me.tax.income.deductions.phase_out.start.SINGLE`
- Generated label: "Maine standard/itemized exemption phase-out start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 336. `gov.states.me.tax.income.deductions.personal_exemption.phaseout.width`

**Label:** Maine personal exemption phase-out width

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.me.tax.income.deductions.personal_exemption.phaseout.width.SINGLE`
- Generated label: "Maine personal exemption phase-out width (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 337. `gov.states.me.tax.income.deductions.personal_exemption.phaseout.start`

**Label:** Maine personal exemption phase-out start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.me.tax.income.deductions.personal_exemption.phaseout.start.SINGLE`
- Generated label: "Maine personal exemption phase-out start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 338. `gov.states.me.tax.income.credits.relief_rebate.income_limit`

**Label:** Maine Relief Rebate income limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.me.tax.income.credits.relief_rebate.income_limit.SINGLE`
- Generated label: "Maine Relief Rebate income limit (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 339. `gov.states.me.tax.income.credits.fairness.sales_tax.amount.base`

**Label:** Maine sales tax fairness credit base amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.me.tax.income.credits.fairness.sales_tax.amount.base.SINGLE`
- Generated label: "Maine sales tax fairness credit base amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 340. `gov.states.me.tax.income.credits.fairness.sales_tax.reduction.increment`

**Label:** Maine sales tax fairness credit phase-out increment

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.me.tax.income.credits.fairness.sales_tax.reduction.increment.SINGLE`
- Generated label: "Maine sales tax fairness credit phase-out increment (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 341. `gov.states.me.tax.income.credits.fairness.sales_tax.reduction.amount`

**Label:** Maine sales tax fairness credit phase-out amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.me.tax.income.credits.fairness.sales_tax.reduction.amount.SINGLE`
- Generated label: "Maine sales tax fairness credit phase-out amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 342. `gov.states.me.tax.income.credits.fairness.sales_tax.reduction.start`

**Label:** Maine sales tax fairness credit phase-out start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.me.tax.income.credits.fairness.sales_tax.reduction.start.SINGLE`
- Generated label: "Maine sales tax fairness credit phase-out start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 343. `gov.states.me.tax.income.credits.dependent_exemption.phase_out.start`

**Label:** Maine dependents exemption phase-out start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.me.tax.income.credits.dependent_exemption.phase_out.start.SINGLE`
- Generated label: "Maine dependents exemption phase-out start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 344. `gov.states.ar.tax.income.deductions.standard`

**Label:** Arkansas standard deduction

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ar.tax.income.deductions.standard.JOINT`
- Generated label: "Arkansas standard deduction (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 345. `gov.states.ar.tax.income.gross_income.capital_gains.loss_cap`

**Label:** Arkansas long-term capital gains tax loss cap

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ar.tax.income.gross_income.capital_gains.loss_cap.JOINT`
- Generated label: "Arkansas long-term capital gains tax loss cap (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 346. `gov.states.ar.tax.income.credits.inflationary_relief.max_amount`

**Label:** Arkansas income-tax credit maximum amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ar.tax.income.credits.inflationary_relief.max_amount.JOINT`
- Generated label: "Arkansas income-tax credit maximum amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 347. `gov.states.ar.tax.income.credits.inflationary_relief.reduction.increment`

**Label:** Arkansas income reduction increment

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ar.tax.income.credits.inflationary_relief.reduction.increment.JOINT`
- Generated label: "Arkansas income reduction increment (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 348. `gov.states.ar.tax.income.credits.inflationary_relief.reduction.amount`

**Label:** Arkansas inflation relief credit reduction amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ar.tax.income.credits.inflationary_relief.reduction.amount.JOINT`
- Generated label: "Arkansas inflation relief credit reduction amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 349. `gov.states.ar.tax.income.credits.inflationary_relief.reduction.start`

**Label:** Arkansas inflation reduction credit reduction start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ar.tax.income.credits.inflationary_relief.reduction.start.JOINT`
- Generated label: "Arkansas inflation reduction credit reduction start (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 350. `gov.states.dc.tax.income.deductions.itemized.phase_out.start`

**Label:** DC itemized deduction phase-out DC AGI start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.dc.tax.income.deductions.itemized.phase_out.start.SINGLE`
- Generated label: "DC itemized deduction phase-out DC AGI start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 351. `gov.states.dc.tax.income.credits.kccatc.income_limit`

**Label:** DC KCCATC DC taxable income limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.dc.tax.income.credits.kccatc.income_limit.SINGLE`
- Generated label: "DC KCCATC DC taxable income limit (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 352. `gov.states.dc.tax.income.credits.ctc.income_threshold`

**Label:** DC Child Tax Credit taxable income threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.dc.tax.income.credits.ctc.income_threshold.SINGLE`
- Generated label: "DC Child Tax Credit taxable income threshold (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 353. `gov.states.md.tax.income.deductions.itemized.phase_out.threshold`

**Label:** Maryland itemized deduction phase-out threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.md.tax.income.deductions.itemized.phase_out.threshold.SINGLE`
- Generated label: "Maryland itemized deduction phase-out threshold (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 354. `gov.states.md.tax.income.deductions.standard.max`

**Label:** Maryland maximum standard deduction

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.md.tax.income.deductions.standard.max.JOINT`
- Generated label: "Maryland maximum standard deduction (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 355. `gov.states.md.tax.income.deductions.standard.min`

**Label:** Maryland minimum standard deduction

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.md.tax.income.deductions.standard.min.JOINT`
- Generated label: "Maryland minimum standard deduction (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 356. `gov.states.md.tax.income.deductions.standard.flat_deduction.amount`

**Label:** Maryland standard deduction flat amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.md.tax.income.deductions.standard.flat_deduction.amount.JOINT`
- Generated label: "Maryland standard deduction flat amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 357. `gov.states.md.tax.income.credits.cdcc.phase_out.increment`

**Label:** Maryland CDCC phase-out increment

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.md.tax.income.credits.cdcc.phase_out.increment.JOINT`
- Generated label: "Maryland CDCC phase-out increment (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 358. `gov.states.md.tax.income.credits.cdcc.phase_out.start`

**Label:** Maryland CDCC phase-out start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.md.tax.income.credits.cdcc.phase_out.start.JOINT`
- Generated label: "Maryland CDCC phase-out start (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 359. `gov.states.md.tax.income.credits.cdcc.eligibility.agi_cap`

**Label:** Maryland CDCC AGI cap

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.md.tax.income.credits.cdcc.eligibility.agi_cap.JOINT`
- Generated label: "Maryland CDCC AGI cap (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 360. `gov.states.md.tax.income.credits.cdcc.eligibility.refundable_agi_cap`

**Label:** Maryland refundable CDCC AGI cap

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.md.tax.income.credits.cdcc.eligibility.refundable_agi_cap.JOINT`
- Generated label: "Maryland refundable CDCC AGI cap (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 361. `gov.states.md.tax.income.credits.senior_tax.income_threshold`

**Label:** Maryland Senior Tax Credit income threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.md.tax.income.credits.senior_tax.income_threshold.JOINT`
- Generated label: "Maryland Senior Tax Credit income threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 362. `gov.states.ks.tax.income.rates.zero_tax_threshold`

**Label:** KS zero-tax taxable-income threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ks.tax.income.rates.zero_tax_threshold.JOINT`
- Generated label: "KS zero-tax taxable-income threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 363. `gov.states.ks.tax.income.deductions.standard.extra_amount`

**Label:** Kansas extra standard deduction for elderly and blind

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ks.tax.income.deductions.standard.extra_amount.JOINT`
- Generated label: "Kansas extra standard deduction for elderly and blind (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 364. `gov.states.ks.tax.income.deductions.standard.base_amount`

**Label:** Kansas base standard deduction

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ks.tax.income.deductions.standard.base_amount.JOINT`
- Generated label: "Kansas base standard deduction (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 365. `gov.states.ne.tax.income.agi.subtractions.social_security.threshold`

**Label:** Nebraska social security AGI subtraction threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ne.tax.income.agi.subtractions.social_security.threshold.JOINT`
- Generated label: "Nebraska social security AGI subtraction threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 366. `gov.states.ne.tax.income.deductions.standard.base_amount`

**Label:** Nebraska standard deduction base amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ne.tax.income.deductions.standard.base_amount.JOINT`
- Generated label: "Nebraska standard deduction base amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 367. `gov.states.ne.tax.income.credits.school_readiness.amount.refundable`

**Label:** Nebraska School Readiness credit refundable amount

**Breakdown dimensions:** `['range(1, 6)']`

**Child parameters:** 5

**Dimension analysis:**
- `range(1, 6)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.ne.tax.income.credits.school_readiness.amount.refundable.1`
- Generated label: "Nebraska School Readiness credit refundable amount (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 6)]']`

---

### 368. `gov.states.hi.tax.income.deductions.itemized.threshold.deductions`

**Label:** Hawaii itemized deductions deductions threshold

**Breakdown dimensions:** `filing_status`

**Child parameters:** 5

**Dimension analysis:**
- `f` → Variable/enum lookup (may or may not have labels)
- `i` → Variable/enum lookup (may or may not have labels)
- `l` → Variable/enum lookup (may or may not have labels)
- `i` → Variable/enum lookup (may or may not have labels)
- `n` → Variable/enum lookup (may or may not have labels)
- `g` → Variable/enum lookup (may or may not have labels)
- `_` → Variable/enum lookup (may or may not have labels)
- `s` → Variable/enum lookup (may or may not have labels)
- `t` → Variable/enum lookup (may or may not have labels)
- `a` → Variable/enum lookup (may or may not have labels)
- `t` → Variable/enum lookup (may or may not have labels)
- `u` → Variable/enum lookup (may or may not have labels)
- `s` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.hi.tax.income.deductions.itemized.threshold.deductions.SINGLE`
- Generated label: "Hawaii itemized deductions deductions threshold (SINGLE)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 369. `gov.states.hi.tax.income.deductions.itemized.threshold.reduction`

**Label:** Hawaii itemized deductions reduction threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.hi.tax.income.deductions.itemized.threshold.reduction.SINGLE`
- Generated label: "Hawaii itemized deductions reduction threshold (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 370. `gov.states.hi.tax.income.deductions.standard.amount`

**Label:** Hawaii standard deduction amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.hi.tax.income.deductions.standard.amount.JOINT`
- Generated label: "Hawaii standard deduction amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 371. `gov.states.de.tax.income.subtractions.exclusions.elderly_or_disabled.eligibility.agi_limit`

**Label:** Delaware aged or disabled exclusion subtraction adjusted gross income limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.de.tax.income.subtractions.exclusions.elderly_or_disabled.eligibility.agi_limit.JOINT`
- Generated label: "Delaware aged or disabled exclusion subtraction adjusted gross income limit (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 372. `gov.states.de.tax.income.subtractions.exclusions.elderly_or_disabled.eligibility.earned_income_limit`

**Label:** Delaware aged or disabled exclusion earned income limit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.de.tax.income.subtractions.exclusions.elderly_or_disabled.eligibility.earned_income_limit.JOINT`
- Generated label: "Delaware aged or disabled exclusion earned income limit (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 373. `gov.states.de.tax.income.subtractions.exclusions.elderly_or_disabled.amount`

**Label:** Delaware aged or disabled exclusion amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.de.tax.income.subtractions.exclusions.elderly_or_disabled.amount.JOINT`
- Generated label: "Delaware aged or disabled exclusion amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 374. `gov.states.de.tax.income.deductions.standard.amount`

**Label:** Delaware Standard Deduction

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.de.tax.income.deductions.standard.amount.JOINT`
- Generated label: "Delaware Standard Deduction (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 375. `gov.states.az.tax.income.credits.charitable_contribution.ceiling.qualifying_organization`

**Label:** Arizona charitable contribution credit cap

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.az.tax.income.credits.charitable_contribution.ceiling.qualifying_organization.JOINT`
- Generated label: "Arizona charitable contribution credit cap (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 376. `gov.states.az.tax.income.credits.charitable_contribution.ceiling.qualifying_foster`

**Label:** Arizona credit for contributions to foster organizations cap

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.az.tax.income.credits.charitable_contribution.ceiling.qualifying_foster.JOINT`
- Generated label: "Arizona credit for contributions to foster organizations cap (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 377. `gov.states.az.tax.income.credits.dependent_credit.reduction.start`

**Label:** Arizona dependent tax credit phase out start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.az.tax.income.credits.dependent_credit.reduction.start.SINGLE`
- Generated label: "Arizona dependent tax credit phase out start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 378. `gov.states.az.tax.income.credits.increased_excise.income_threshold`

**Label:** Arizona Increased Excise Tax Credit income threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.az.tax.income.credits.increased_excise.income_threshold.SINGLE`
- Generated label: "Arizona Increased Excise Tax Credit income threshold (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 379. `gov.states.az.tax.income.credits.family_tax_credits.amount.cap`

**Label:** Arizona family tax credit maximum amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.az.tax.income.credits.family_tax_credits.amount.cap.SINGLE`
- Generated label: "Arizona family tax credit maximum amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 380. `gov.states.ny.tax.income.deductions.standard.amount`

**Label:** New York standard deduction

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ny.tax.income.deductions.standard.amount.SINGLE`
- Generated label: "New York standard deduction (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 381. `gov.states.ny.tax.income.credits.ctc.post_2024.phase_out.threshold`

**Label:** New York CTC post 2024 phase-out thresholds

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.ny.tax.income.credits.ctc.post_2024.phase_out.threshold.SINGLE`
- Generated label: "New York CTC post 2024 phase-out thresholds (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 382. `gov.states.id.tax.income.deductions.retirement_benefits.cap`

**Label:** Idaho retirement benefit deduction cap

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.id.tax.income.deductions.retirement_benefits.cap.SINGLE`
- Generated label: "Idaho retirement benefit deduction cap (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 383. `gov.states.id.tax.income.credits.special_seasonal_rebate.floor`

**Label:** Idaho special seasonal rebate floor

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.id.tax.income.credits.special_seasonal_rebate.floor.SINGLE`
- Generated label: "Idaho special seasonal rebate floor (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 384. `gov.states.or.tax.income.deductions.standard.aged_or_blind.amount`

**Label:** Oregon standard deduction addition for 65 or older or blind

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.or.tax.income.deductions.standard.aged_or_blind.amount.JOINT`
- Generated label: "Oregon standard deduction addition for 65 or older or blind (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 385. `gov.states.or.tax.income.deductions.standard.amount`

**Label:** Oregon standard deduction

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.or.tax.income.deductions.standard.amount.JOINT`
- Generated label: "Oregon standard deduction (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 386. `gov.states.or.tax.income.credits.exemption.income_limit.regular`

**Label:** Oregon exemption credit income limit (regular)

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.or.tax.income.credits.exemption.income_limit.regular.JOINT`
- Generated label: "Oregon exemption credit income limit (regular) (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 387. `gov.states.or.tax.income.credits.retirement_income.income_threshold`

**Label:** Oregon retirement income credit income threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.or.tax.income.credits.retirement_income.income_threshold.JOINT`
- Generated label: "Oregon retirement income credit income threshold (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 388. `gov.states.or.tax.income.credits.retirement_income.base`

**Label:** Oregon retirement income credit base

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.or.tax.income.credits.retirement_income.base.JOINT`
- Generated label: "Oregon retirement income credit base (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 389. `gov.states.la.tax.income.deductions.standard.amount`

**Label:** Louisiana standard deduction amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.la.tax.income.deductions.standard.amount.SINGLE`
- Generated label: "Louisiana standard deduction amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 390. `gov.states.la.tax.income.exemptions.personal`

**Label:** Louisiana personal exemption amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.la.tax.income.exemptions.personal.SINGLE`
- Generated label: "Louisiana personal exemption amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 391. `gov.states.wi.tax.income.subtractions.retirement_income.max_agi`

**Label:** Wisconsin retirement income subtraction maximum adjusted gross income

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.states.wi.tax.income.subtractions.retirement_income.max_agi.SINGLE`
- Generated label: "Wisconsin retirement income subtraction maximum adjusted gross income (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 392. `gov.states.wi.dcf.works.placement.amount`

**Label:** Wisconsin Works payment amount

**Breakdown dimensions:** `['wi_works_placement']`

**Child parameters:** 5

**Dimension analysis:**
- `wi_works_placement` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.wi.dcf.works.placement.amount.CSJ`
- Generated label: "Wisconsin Works payment amount (CSJ)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 393. `gov.irs.deductions.overtime_income.phase_out.start`

**Label:** Overtime income exemption phase out start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.deductions.overtime_income.phase_out.start.JOINT`
- Generated label: "Overtime income exemption phase out start (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 394. `gov.irs.deductions.overtime_income.cap`

**Label:** Overtime income exemption cap

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.deductions.overtime_income.cap.JOINT`
- Generated label: "Overtime income exemption cap (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 395. `gov.irs.deductions.qbi.phase_out.start`

**Label:** Qualified business income deduction phase-out start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.deductions.qbi.phase_out.start.HEAD_OF_HOUSEHOLD`
- Generated label: "Qualified business income deduction phase-out start (HEAD_OF_HOUSEHOLD)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 396. `gov.irs.deductions.itemized.limitation.applicable_amount`

**Label:** Itemized deductions applicable amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.deductions.itemized.limitation.applicable_amount.JOINT`
- Generated label: "Itemized deductions applicable amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 397. `gov.irs.deductions.itemized.interest.mortgage.cap`

**Label:** IRS home mortgage value cap

**Breakdown dimensions:** `filing_status`

**Child parameters:** 5

**Dimension analysis:**
- `f` → Variable/enum lookup (may or may not have labels)
- `i` → Variable/enum lookup (may or may not have labels)
- `l` → Variable/enum lookup (may or may not have labels)
- `i` → Variable/enum lookup (may or may not have labels)
- `n` → Variable/enum lookup (may or may not have labels)
- `g` → Variable/enum lookup (may or may not have labels)
- `_` → Variable/enum lookup (may or may not have labels)
- `s` → Variable/enum lookup (may or may not have labels)
- `t` → Variable/enum lookup (may or may not have labels)
- `a` → Variable/enum lookup (may or may not have labels)
- `t` → Variable/enum lookup (may or may not have labels)
- `u` → Variable/enum lookup (may or may not have labels)
- `s` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.irs.deductions.itemized.interest.mortgage.cap.SINGLE`
- Generated label: "IRS home mortgage value cap (SINGLE)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 398. `gov.irs.deductions.itemized.reduction.agi_threshold`

**Label:** IRS itemized deductions reduction threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.deductions.itemized.reduction.agi_threshold.SINGLE`
- Generated label: "IRS itemized deductions reduction threshold (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 399. `gov.irs.deductions.itemized.salt_and_real_estate.phase_out.threshold`

**Label:** SALT deduction phase out threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.deductions.itemized.salt_and_real_estate.phase_out.threshold.SINGLE`
- Generated label: "SALT deduction phase out threshold (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 400. `gov.irs.deductions.itemized.salt_and_real_estate.phase_out.floor.amount`

**Label:** SALT deduction floor amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.deductions.itemized.salt_and_real_estate.phase_out.floor.amount.SINGLE`
- Generated label: "SALT deduction floor amount (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 401. `gov.irs.deductions.itemized.charity.non_itemizers_amount`

**Label:** Charitable deduction amount for non-itemizers

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.deductions.itemized.charity.non_itemizers_amount.JOINT`
- Generated label: "Charitable deduction amount for non-itemizers (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 402. `gov.irs.deductions.standard.aged_or_blind.amount`

**Label:** Additional standard deduction for the blind and aged

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.deductions.standard.aged_or_blind.amount.SINGLE`
- Generated label: "Additional standard deduction for the blind and aged (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 403. `gov.irs.deductions.standard.amount`

**Label:** Standard deduction

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.deductions.standard.amount.SINGLE`
- Generated label: "Standard deduction (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 404. `gov.irs.deductions.auto_loan_interest.phase_out.start`

**Label:** Auto loan interest deduction reduction start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.deductions.auto_loan_interest.phase_out.start.SINGLE`
- Generated label: "Auto loan interest deduction reduction start (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 405. `gov.irs.deductions.tip_income.phase_out.start`

**Label:** Tip income exemption phase out start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.deductions.tip_income.phase_out.start.JOINT`
- Generated label: "Tip income exemption phase out start (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 406. `gov.irs.income.amt.multiplier`

**Label:** AMT tax bracket multiplier

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.income.amt.multiplier.SINGLE`
- Generated label: "AMT tax bracket multiplier (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 407. `gov.irs.gross_income.dependent_care_assistance_programs.reduction_amount`

**Label:** IRS reduction amount from gross income for dependent care assistance

**Breakdown dimensions:** `filing_status`

**Child parameters:** 5

**Dimension analysis:**
- `f` → Variable/enum lookup (may or may not have labels)
- `i` → Variable/enum lookup (may or may not have labels)
- `l` → Variable/enum lookup (may or may not have labels)
- `i` → Variable/enum lookup (may or may not have labels)
- `n` → Variable/enum lookup (may or may not have labels)
- `g` → Variable/enum lookup (may or may not have labels)
- `_` → Variable/enum lookup (may or may not have labels)
- `s` → Variable/enum lookup (may or may not have labels)
- `t` → Variable/enum lookup (may or may not have labels)
- `a` → Variable/enum lookup (may or may not have labels)
- `t` → Variable/enum lookup (may or may not have labels)
- `u` → Variable/enum lookup (may or may not have labels)
- `s` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.irs.gross_income.dependent_care_assistance_programs.reduction_amount.SINGLE`
- Generated label: "IRS reduction amount from gross income for dependent care assistance (SINGLE)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 408. `gov.irs.ald.loss.capital.max`

**Label:** Maximum capital loss deductible above-the-line

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.ald.loss.capital.max.SINGLE`
- Generated label: "Maximum capital loss deductible above-the-line (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 409. `gov.irs.ald.student_loan_interest.reduction.divisor`

**Label:** Student loan interest deduction reduction divisor

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.ald.student_loan_interest.reduction.divisor.JOINT`
- Generated label: "Student loan interest deduction reduction divisor (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 410. `gov.irs.ald.student_loan_interest.reduction.start`

**Label:** Student loan interest deduction amount

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.ald.student_loan_interest.reduction.start.JOINT`
- Generated label: "Student loan interest deduction amount (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 411. `gov.irs.ald.student_loan_interest.cap`

**Label:** Student loan interest deduction cap

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.ald.student_loan_interest.cap.JOINT`
- Generated label: "Student loan interest deduction cap (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 412. `gov.irs.social_security.taxability.threshold.adjusted_base.main`

**Label:** Social Security taxability additional threshold

**Breakdown dimensions:** `filing_status`

**Child parameters:** 5

**Dimension analysis:**
- `f` → Variable/enum lookup (may or may not have labels)
- `i` → Variable/enum lookup (may or may not have labels)
- `l` → Variable/enum lookup (may or may not have labels)
- `i` → Variable/enum lookup (may or may not have labels)
- `n` → Variable/enum lookup (may or may not have labels)
- `g` → Variable/enum lookup (may or may not have labels)
- `_` → Variable/enum lookup (may or may not have labels)
- `s` → Variable/enum lookup (may or may not have labels)
- `t` → Variable/enum lookup (may or may not have labels)
- `a` → Variable/enum lookup (may or may not have labels)
- `t` → Variable/enum lookup (may or may not have labels)
- `u` → Variable/enum lookup (may or may not have labels)
- `s` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.irs.social_security.taxability.threshold.adjusted_base.main.SINGLE`
- Generated label: "Social Security taxability additional threshold (SINGLE)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 413. `gov.irs.social_security.taxability.threshold.base.main`

**Label:** Social Security taxability base threshold

**Breakdown dimensions:** `filing_status`

**Child parameters:** 5

**Dimension analysis:**
- `f` → Variable/enum lookup (may or may not have labels)
- `i` → Variable/enum lookup (may or may not have labels)
- `l` → Variable/enum lookup (may or may not have labels)
- `i` → Variable/enum lookup (may or may not have labels)
- `n` → Variable/enum lookup (may or may not have labels)
- `g` → Variable/enum lookup (may or may not have labels)
- `_` → Variable/enum lookup (may or may not have labels)
- `s` → Variable/enum lookup (may or may not have labels)
- `t` → Variable/enum lookup (may or may not have labels)
- `a` → Variable/enum lookup (may or may not have labels)
- `t` → Variable/enum lookup (may or may not have labels)
- `u` → Variable/enum lookup (may or may not have labels)
- `s` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.irs.social_security.taxability.threshold.base.main.SINGLE`
- Generated label: "Social Security taxability base threshold (SINGLE)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 414. `gov.irs.credits.recovery_rebate_credit.caa.phase_out.threshold`

**Label:** Second Recovery Rebate Credit phase-out starting threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.credits.recovery_rebate_credit.caa.phase_out.threshold.SINGLE`
- Generated label: "Second Recovery Rebate Credit phase-out starting threshold (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 415. `gov.irs.credits.recovery_rebate_credit.arpa.phase_out.threshold`

**Label:** ARPA Recovery Rebate Credit phase-out starting threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.credits.recovery_rebate_credit.arpa.phase_out.threshold.SINGLE`
- Generated label: "ARPA Recovery Rebate Credit phase-out starting threshold (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 416. `gov.irs.credits.recovery_rebate_credit.arpa.phase_out.length`

**Label:** ARPA Recovery Rebate Credit phase-out length

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.credits.recovery_rebate_credit.arpa.phase_out.length.SINGLE`
- Generated label: "ARPA Recovery Rebate Credit phase-out length (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 417. `gov.irs.credits.recovery_rebate_credit.cares.phase_out.threshold`

**Label:** CARES Recovery Rebate Credit phase-out starting threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.credits.recovery_rebate_credit.cares.phase_out.threshold.SINGLE`
- Generated label: "CARES Recovery Rebate Credit phase-out starting threshold (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 418. `gov.irs.credits.retirement_saving.rate.threshold_adjustment`

**Label:** Retirement Savings Contributions Credit (Saver's Credit) threshold adjustment rate

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.credits.retirement_saving.rate.threshold_adjustment.JOINT`
- Generated label: "Retirement Savings Contributions Credit (Saver's Credit) threshold adjustment rate (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 419. `gov.irs.credits.clean_vehicle.new.eligibility.income_limit`

**Label:** Income limit for new clean vehicle credit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.credits.clean_vehicle.new.eligibility.income_limit.JOINT`
- Generated label: "Income limit for new clean vehicle credit (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 420. `gov.irs.credits.clean_vehicle.used.eligibility.income_limit`

**Label:** Income limit for used clean vehicle credit

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.credits.clean_vehicle.used.eligibility.income_limit.JOINT`
- Generated label: "Income limit for used clean vehicle credit (JOINT)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 421. `gov.irs.credits.ctc.phase_out.threshold`

**Label:** CTC phase-out threshold

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.credits.ctc.phase_out.threshold.SINGLE`
- Generated label: "CTC phase-out threshold (SINGLE)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 422. `gov.irs.credits.cdcc.phase_out.amended_structure.second_start`

**Label:** CDCC amended phase-out second start

**Breakdown dimensions:** `['filing_status']`

**Child parameters:** 5

**Dimension analysis:**
- `filing_status` → Enum lookup (Single, Joint, etc.)

**Example - Current label generation:**
- Parameter: `gov.irs.credits.cdcc.phase_out.amended_structure.second_start.HEAD_OF_HOUSEHOLD`
- Generated label: "CDCC amended phase-out second start (HEAD_OF_HOUSEHOLD)"

**Suggested improvement:**
- ✓ Uses standard enums with known labels - current generation adequate

---

### 423. `gov.hud.ami_limit.per_person_exceeding_4`

**Label:** HUD area median income limit per person exceeding 4

**Breakdown dimensions:** `['hud_income_level']`

**Child parameters:** 5

**Dimension analysis:**
- `hud_income_level` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.hud.ami_limit.per_person_exceeding_4.MODERATE`
- Generated label: "HUD area median income limit per person exceeding 4 (MODERATE)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 424. `gov.ed.pell_grant.sai.fpg_fraction.max_pell_limits`

**Label:** Maximum Pell Grant income limits

**Breakdown dimensions:** `['pell_grant_household_type']`

**Child parameters:** 4

**Dimension analysis:**
- `pell_grant_household_type` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.ed.pell_grant.sai.fpg_fraction.max_pell_limits.DEPENDENT_SINGLE`
- Generated label: "Maximum Pell Grant income limits (DEPENDENT_SINGLE)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 425. `gov.states.az.tax.income.subtractions.college_savings.cap`

**Label:** Arizona college savings plan subtraction cap

**Breakdown dimensions:** `['az_filing_status']`

**Child parameters:** 4

**Dimension analysis:**
- `az_filing_status` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.az.tax.income.subtractions.college_savings.cap.SINGLE`
- Generated label: "Arizona college savings plan subtraction cap (SINGLE)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 426. `gov.states.az.tax.income.deductions.standard.amount`

**Label:** Arizona standard deduction

**Breakdown dimensions:** `['az_filing_status']`

**Child parameters:** 4

**Dimension analysis:**
- `az_filing_status` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.az.tax.income.deductions.standard.amount.JOINT`
- Generated label: "Arizona standard deduction (JOINT)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 427. `gov.irs.credits.clean_vehicle.new.eligibility.msrp_limit`

**Label:** MSRP limit for new clean vehicle credit

**Breakdown dimensions:** `['new_clean_vehicle_classification']`

**Child parameters:** 4

**Dimension analysis:**
- `new_clean_vehicle_classification` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.irs.credits.clean_vehicle.new.eligibility.msrp_limit.VAN`
- Generated label: "MSRP limit for new clean vehicle credit (VAN)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 428. `gov.states.ma.eec.ccfa.reimbursement_rates.family_child_care.younger`

**Label:** Massachusetts CCFA family child care younger child reimbursement rates

**Breakdown dimensions:** `['ma_ccfa_region']`

**Child parameters:** 3

**Dimension analysis:**
- `ma_ccfa_region` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.ma.eec.ccfa.reimbursement_rates.family_child_care.younger.WESTERN_CENTRAL_AND_SOUTHEAST`
- Generated label: "Massachusetts CCFA family child care younger child reimbursement rates (WESTERN_CENTRAL_AND_SOUTHEAST)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 429. `gov.states.ma.eec.ccfa.reimbursement_rates.family_child_care.older`

**Label:** Massachusetts CCFA family child care older child reimbursement rates

**Breakdown dimensions:** `['ma_ccfa_region']`

**Child parameters:** 3

**Dimension analysis:**
- `ma_ccfa_region` → Variable/enum lookup (may or may not have labels)

**Example - Current label generation:**
- Parameter: `gov.states.ma.eec.ccfa.reimbursement_rates.family_child_care.older.WESTERN_CENTRAL_AND_SOUTHEAST`
- Generated label: "Massachusetts CCFA family child care older child reimbursement rates (WESTERN_CENTRAL_AND_SOUTHEAST)"

**Suggested improvement:**
- ℹ️ Uses custom enum variables - verify they have display labels
- Consider adding `breakdown_labels` for clarity

---

### 430. `gov.states.md.tax.income.credits.senior_tax.amount.joint`

**Label:** Maryland Senior Tax Credit joint amount

**Breakdown dimensions:** `['range(0,2)']`

**Child parameters:** 3

**Dimension analysis:**
- `range(0,2)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.md.tax.income.credits.senior_tax.amount.joint.1`
- Generated label: "Maryland Senior Tax Credit joint amount (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(0,2)]']`

---

### 431. `gov.states.il.idoa.bap.income_limit`

**Label:** Illinois Benefit Access Program income limit

**Breakdown dimensions:** `['range(1, 4)']`

**Child parameters:** 3

**Dimension analysis:**
- `range(1, 4)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.il.idoa.bap.income_limit.1`
- Generated label: "Illinois Benefit Access Program income limit (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1, 4)]']`

---

### 432. `gov.states.il.dhs.aabd.asset.disregard.base`

**Label:** Illinois AABD asset disregard base amount

**Breakdown dimensions:** `['range(1,3)']`

**Child parameters:** 2

**Dimension analysis:**
- `range(1,3)` → **Raw numeric index (NO semantic label)**

**Example - Current label generation:**
- Parameter: `gov.states.il.dhs.aabd.asset.disregard.base.1`
- Generated label: "Illinois AABD asset disregard base amount (1)"

**Suggested improvement:**
- ⚠️ Has `range()` dimensions that need semantic labels
- Add `breakdown_labels` metadata with human-readable names
- Suggested: `breakdown_labels: ['[NEEDS: label for range(1,3)]']`

---
