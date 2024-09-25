from policyengine_core.reforms import Reform
from .inequality_impact.inequality_impact import GiniCalculator, Top10PctShareCalculator, Top1PctShareCalculator
from .poverty_impact.regular_poverty.by_age.by_age import (
    ChildPoverty as RegularChildPoverty,
    AdultPoverty as RegularAdultPoverty,
    SeniorPoverty as RegularSeniorPoverty,
    AllPoverty as RegularAgeAllPoverty
)
from .poverty_impact.regular_poverty.by_gender.by_gender import (
    MalePoverty as RegularMalePoverty,
    FemalePoverty as RegularFemalePoverty,
    AllPoverty as RegularGenderAllPoverty
)
from .poverty_impact.deep_poverty.by_age.by_age import (
    ChildPoverty as DeepChildPoverty,
    AdultPoverty as DeepAdultPoverty,
    SeniorPoverty as DeepSeniorPoverty,
    AllPoverty as DeepAgeAllPoverty
)
from .poverty_impact.deep_poverty.by_gender.by_gender import (
    MalePoverty as DeepMalePoverty,
    FemalePoverty as DeepFemalePoverty,
    AllPoverty as DeepGenderAllPoverty
)

from .budgetary_impact.by_program.by_program import (
    IncomeTax, 
    NationalInsurance, 
    Vat, 
    CouncilTax, 
    FuelDuty, 
    TaxCredits, 
    UniversalCredit, 
    ChildBenefit, 
    StatePension, 
    PensionCredit
)



from .distributional_impact.by_income_decile.average.average import Average as AverageByIncome
from .distributional_impact.by_income_decile.relative.relative import Relative as RelativeByIncome

from .distributional_impact.by_wealth_decile.average.average import Average as AverageByWealth
from .distributional_impact.by_wealth_decile.relative.relative import Relative as RelativeByWealth

from .distributional_impact.by_income_decile.average.average import Average
from .distributional_impact.by_income_decile.relative.relative import Relative


from .budgetary_impact.overall.overall import (
    BudgetaryImpact, 
    BenefitSpendingImpact, 
    TaxRevenueImpact
)


from .labour_supply_impact.earnings.overall.relative.relative import IncomeLSR , SubstitutionLSR , NetLSRChange

from .labour_supply_impact.earnings.overall.absolute.absolute import (
    IncomeLSR as AbsoluteIncomeLSR,
    SubstitutionLSR as AbsoluteSubstitutionLSR,
    NetLSRChange as AbsoluteNetLSRChange
)

from .labour_supply_impact.earnings.by_decile.relative.substitution_effect.substitutional_effect import SubstitutionEffect
from .labour_supply_impact.earnings.by_decile.relative.income_effect.income_effect import IncomeEffect
from .labour_supply_impact.earnings.by_decile.relative.total.total import Total

from .labour_supply_impact.earnings.by_decile.absolute.substitution_effect.substitution_effect import SubstitutionEffect as AbsoluteSubstutionEffect
from .labour_supply_impact.earnings.by_decile.absolute.income_effect.income_effect import IncomeEffect as AbsoluteIncomeEffect
from .labour_supply_impact.earnings.by_decile.absolute.total.total import Total as AbsoluteTotal


from .winners_and_losers.by_income_decile.by_income_decile import ByIncomeDecile
from .winners_and_losers.by_wealth_decile.by_wealth_decile import ByWealthDecile


from typing import Dict, Type, Union

from policyengine.charts.inequality import InequalityImpactChart
from policyengine.charts.poverty.regular.by_age import RegularPovertyByAgeChart
from policyengine.charts.poverty.deep.by_age import DeepPovertyByAgeChart
from policyengine.charts.poverty.regular.by_gender import RegularPovertyByGenderChart
from policyengine.charts.poverty.deep.by_gender import DeepPovertyByGenderChart
from policyengine.charts.distributional_impact.by_income_decile.average import ByIncomeDecileAverageChart
from policyengine.charts.distributional_impact.by_income_decile.relative import ByIncomeDecileRelativeChart
from policyengine.charts.distributional_impact.by_wealth_decile.average import ByWealthDecileAverageChart
from policyengine.charts.distributional_impact.by_wealth_decile.relative import ByWealthDecileRelativeChart


class EconomicImpact:
    """
    A class to calculate economic impact metrics based on different reforms and countries.
    
    Attributes:
        reform (dict): Dictionary representing the reform parameters.
        country (str): Country code in lowercase ('uk' or 'us').
        dataset (str, optional): Dataset to be used for the simulation.
        Microsimulation (type): Class representing the microsimulation engine based on country.
        baseline (Microsimulation): Instance of Microsimulation for baseline scenario.
        reformed (Microsimulation): Instance of Microsimulation for reformed scenario based on given reform.
        metric_calculators (Dict[str, BaseMetricCalculator]): Dictionary mapping metric names to metric calculators.
    """
    
    def __init__(self, reform: dict, country: str, dataset: str = None) -> None:
        """
        Initialize EconomicImpact with reform parameters, country code, and optional dataset.
        
        Args:
            reform (dict): Dictionary representing the reform parameters.
            country (str): Country code in lowercase ('uk' or 'us').
            dataset (str, optional): Dataset to be used for the simulation. Defaults to None.
        """
        self.reform = reform
        self.country = country.lower()
        self.dataset = dataset
        self.Microsimulation = self._get_simulation_class()
        
        # Initialize baseline and reformed simulations
        self.baseline = self.Microsimulation(dataset=self.dataset)
        self.reformed = self.Microsimulation(reform=Reform.from_dict(self.reform, country_id=self.country), dataset=self.dataset)

        # Set up metric calculators
        self.metric_calculators: Dict[str, object] = {
            "budgetary/overall/budgetary_impact" : BudgetaryImpact(self.baseline, self.reformed),
            "budgetary/overall/benefit_spending_impact" : BenefitSpendingImpact(self.baseline, self.reformed),
            "budgetary/overall/tax_revenue_impact" : TaxRevenueImpact(self.baseline, self.reformed),
            "budgetary/by_program/income_tax" : IncomeTax(self.baseline, self.reformed),
            "budgetary/by_program/national_insurance" : NationalInsurance(self.baseline, self.reformed),
            "budgetary/by_program/vat" : Vat(self.baseline, self.reformed),
            "budgetary/by_program/council_tax" : CouncilTax(self.baseline, self.reformed),
            "budgetary/by_program/fuel_duty" : FuelDuty(self.baseline, self.reformed),
            "budgetary/by_program/tax_credits" : TaxCredits(self.baseline, self.reformed),
            "budgetary/by_program/universal_credits" : UniversalCredit(self.baseline, self.reformed),
            "budgetary/by_program/child_benefits" : ChildBenefit(self.baseline, self.reformed),
            "budgetary/by_program/state_pension" : StatePension(self.baseline, self.reformed),
            "budgetary/by_program/pension_credit" : PensionCredit(self.baseline, self.reformed),
            "inequality/gini": GiniCalculator(self.baseline, self.reformed),
            "inequality/top_1_pct_share": Top1PctShareCalculator(self.baseline, self.reformed),
            "inequality/top_10_pct_share": Top10PctShareCalculator(self.baseline, self.reformed),
            "poverty/regular/child": RegularChildPoverty(self.baseline, self.reformed),
            "poverty/regular/adult": RegularAdultPoverty(self.baseline, self.reformed),
            "poverty/regular/senior": RegularSeniorPoverty(self.baseline, self.reformed),
            "poverty/regular/age/all": RegularAgeAllPoverty(self.baseline, self.reformed),
            "poverty/regular/male": RegularMalePoverty(self.baseline, self.reformed),
            "poverty/regular/female": RegularFemalePoverty(self.baseline, self.reformed),
            "poverty/regular/gender/all": RegularGenderAllPoverty(self.baseline, self.reformed),
            "poverty/deep/child": DeepChildPoverty(self.baseline, self.reformed),
            "poverty/deep/adult": DeepAdultPoverty(self.baseline, self.reformed),
            "poverty/deep/senior": DeepSeniorPoverty(self.baseline, self.reformed),
            "poverty/deep/age/all": DeepAgeAllPoverty(self.baseline, self.reformed),
            "poverty/deep/male": DeepMalePoverty(self.baseline, self.reformed),
            "poverty/deep/female": DeepFemalePoverty(self.baseline, self.reformed),
            "poverty/deep/gender/all": DeepGenderAllPoverty(self.baseline, self.reformed),

            "labour_supply_impact/earnings/overall/relative/IncomeLSR" : IncomeLSR(self.baseline,self.reformed),
            "labour_supply_impact/earnings/overall/relative/SubstitutionLSR" : SubstitutionLSR(self.baseline,self.reformed),
            "labour_supply_impact/earnings/overall/relative/NetLSRChange" : NetLSRChange(self.baseline,self.reformed),
            "labour_supply_impact/earnings/overall/absolute/IncomeLSR" : AbsoluteIncomeLSR(self.baseline,self.reformed),
            "labour_supply_impact/earnings/overall/absolute/SubstitutionLSR" : AbsoluteSubstitutionLSR(self.baseline,self.reformed),
            "labour_supply_impact/earnings/overall/absolute/NetLSRChange" : AbsoluteNetLSRChange(self.baseline,self.reformed),
            "labour_supply_impact/earnings/by_decile/relative/IncomeEffect" : IncomeEffect(self.baseline,self.reformed),
            "labour_supply_impact/earnings/by_decile/relative/SubstitutionEffect" : SubstitutionEffect(self.baseline,self.reformed),
            "labour_supply_impact/earnings/by_decile/relative/Total" : Total(self.baseline,self.reformed),
            "labour_supply_impact/earnings/by_decile/absolute/income_effect" : AbsoluteIncomeEffect(self.baseline,self.reformed),
            "labour_supply_impact/earnings/by_decile/absolute/substitution_effect" : AbsoluteSubstutionEffect(self.baseline,self.reformed),
            "labour_supply_impact/earnings/by_decile/absolute/total" : AbsoluteTotal(self.baseline,self.reformed),


            "distributional/by_income/average": AverageByIncome(self.baseline, self.reformed),
            "distributional/by_income/relative": RelativeByIncome(self.baseline, self.reformed),
            "distributional/by_wealth/average": AverageByWealth(self.baseline, self.reformed),
            "distributional/by_wealth/relative": RelativeByWealth(self.baseline, self.reformed),

            "distributional/by_income/average": Average(self.baseline, self.reformed),
            "distributional/by_income/relative": Relative(self.baseline, self.reformed),

            "winners_and_losers/by_income_decile": ByIncomeDecile(self.baseline, self.reformed),
            "winners_and_losers/by_wealth_decile": ByWealthDecile(self.baseline, self.reformed),

        }


        self.chart_generators: Dict[str, Type] = {
            "inequality": InequalityImpactChart,
            "poverty/regular/by_age": RegularPovertyByAgeChart,
            "poverty/regular/by_gender": RegularPovertyByGenderChart,
            "poverty/deep/by_age": DeepPovertyByAgeChart,
            "poverty/deep/by_gender": DeepPovertyByGenderChart,
            "distributional/by_income/average": ByIncomeDecileAverageChart,
            "distributional/by_income/relative": ByIncomeDecileRelativeChart,
            "distributional/by_wealth/average": ByWealthDecileAverageChart,
            "distributional/by_wealth/relative": ByWealthDecileRelativeChart
        }

        self.composite_metrics: Dict[str, Dict[str, str]] = {
            "inequality": {
                "Gini index": "inequality/gini",
                "Top 1% share": "inequality/top_1_pct_share",
                "Top 10% share": "inequality/top_10_pct_share",
            },
            "poverty/regular/by_age": {
                "Child": "poverty/regular/child",
                "Adult": "poverty/regular/adult",
                "Senior":"poverty/regular/senior",
                "All": "poverty/regular/age/all"
            },
            "poverty/regular/by_gender": {
                "Male": "poverty/regular/male",
                "Female": "poverty/regular/female",
                "All": "poverty/regular/gender/all"
            },
            "poverty/deep/by_age": {
                "Child": "poverty/deep/child",
                "Adult": "poverty/deep/adult",
                "Senior":"poverty/deep/senior",
                "All": "poverty/deep/age/all"
            },
            "poverty/deep/by_gender": {
                "Male": "poverty/deep/male",
                "Female": "poverty/deep/female",
                "All": "poverty/deep/gender/all"
            }
        }

        self.metric_results: Dict[str, any] = {}

    def _get_simulation_class(self) -> type:
        """
        Get the appropriate Microsimulation class based on the country code.
        
        Returns:
            type: Microsimulation class based on the country.
        
        Raises:
            ValueError: If the country is not supported ('uk' or 'us').
        """
        if self.country == "uk":
            from policyengine_uk import Microsimulation
        elif self.country == "us":
            from policyengine_us import Microsimulation
        else:
            raise ValueError(f"Unsupported country: {self.country}")
        return Microsimulation

    def calculate(self, metric: str) -> dict:
        """
        Calculate the specified economic impact metric.
        
        Args:
            metric (str): Name of the metric to calculate ("inequality/gini", "inequality/top_1_pct_share", "inequality/top_10_pct_share").
        
        Returns:
            dict: Dictionary containing metric values ("baseline", "reform", "change").
        
        Raises:
            ValueError: If the metric is unknown.
        """
        if metric not in self.metric_calculators:
            raise ValueError(f"Unknown metric: {metric}")
        
        if metric not in self.metric_results:
            result = self.metric_calculators[metric].calculate()
            self.metric_results[metric] = result
        
        return self.metric_results[metric]

    def _calculate_composite_metric(self, metric: str) -> dict:
        if metric not in self.composite_metrics:
            raise ValueError(f"Unknown composite metric: {metric}")
        
        composite_data = {}
        for key, sub_metric in self.composite_metrics[metric].items():
            composite_data[key] = self.calculate(sub_metric)
        
        return composite_data

    def chart(self, metric: str) -> dict:
        if metric in self.composite_metrics:
            data = self._calculate_composite_metric(metric)
        elif metric in self.chart_generators:
            data = self.calculate(metric)
        else:
            raise ValueError(f"Unknown metric for charting: {metric}")

        chart_generator = self.chart_generators.get(metric)
        if not chart_generator:
            raise ValueError(f"No chart generator found for metric: {metric}")

        return chart_generator(self.country,data=data).generate_chart_data()

    def add_metric(self, metric: str, calculator: object, chart_generator: Type = None):
        self.metric_calculators[metric] = calculator
        if chart_generator:
            self.chart_generators[metric] = chart_generator

    def add_composite_metric(self, name: str, components: Dict[str, str], chart_generator: Type):
        self.composite_metrics[name] = components
        self.chart_generators[name] = chart_generator