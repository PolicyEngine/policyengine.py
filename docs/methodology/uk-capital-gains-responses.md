---
title: "UK capital gains realisation response"
---

People choose when to realise capital gains, so a change in the tax on gains
changes the gains realised. policyengine-uk models this for every reform, and
policyengine.py uses the model's response as it is; it adds no response of its
own.

## The response

A reform scales each person's realised gains $G_0$ to

$$
G_1 = G_0 \left(\frac{1 - t_1}{1 - t_0}\right)^{e}
$$

where $t_0$ and $t_1$ are the person's marginal rates on gains under the
baseline's and the reform's rules, and $e$ is the elasticity with respect to
the retention rate $1 - t$.

- **How the rates are measured.** Both are measured at the person's gains
  before any response, with every behavioural response switched off, so their
  difference reflects the reform alone.
- **Schedules.** Each rate is share-weighted across the person's schedules
  (main rates, Business Asset Disposal Relief, residential property, carried
  interest).
- **Relief gains.** Gains qualifying for the relief respond at their own
  elasticity, the main one unless `separate_badr_elasticity` is set.

## The default

The default elasticity is 1.0, PolicyEngine's central assumption. It is the
value Advani, Lonsdale and Summers (2024, pp. 36–37) use for the medium-term
(five-year) effect of their reform package, and the range they consider, 0.5
to 2.0, gives the sensitivities. Its limits:

- **For rate changes alone it is low.** They reach 1.0 from about 1.5 by
  adjusting for their package's base changes (removing the uplift at death,
  charging gains on emigration) and for income shifted back into income tax.
  They expect a reform without those changes to have a higher elasticity,
  and so lower revenue (p. 37). policyengine-uk adds no income tax back, so
  for a change to rates alone the default overstates what a rate rise
  raises.
- **It is a medium-term value.** Responses soon after a reform are larger,
  and forestalling isn't modelled, so a first-year score is likely to
  understate the response.
- **Large rate rises.** Revenue from a single rate on gains peaks at
  $1 / (1 + e)$: 50% at the default, 40% at 1.5, 33% at 2.0 and about 22% at
  3.6. So the elasticity can decide whether a large rise raises or loses
  revenue, and the default can give the opposite sign to official costings.
- **Not their calculation.** policyengine-uk raises each person's ratio of
  marginal retention rates to the power $e$. CenTax apply one aggregate
  elasticity to the CGT base as a whole (pp. 32 and 37), and a person's
  marginal rate differs from an aggregate rate at any elasticity. Read
  linearly, their elasticity would also give the power's response at 1 but
  not at 0.5 or 2. So adopting 1.0 reproduces neither their revenue estimates
  nor their sensitivities.

The OBR's elasticities (3.6 for main-rate gains, 1.4 for relief gains) can be
set for comparison. They then compare elasticities, not the OBR's full
costing. The response scales the gains in the data, so a comparison in
pounds also mixes in any gap in the level of gains.

The model's default is 1.0 from policyengine-uk 2.134.0. Before, it was 0, so
reforms were costed statically unless a caller set an elasticity.

## When there is no response

- **No reform.** A simulation without a reform, and a reform's own baseline,
  apply their baseline's rules. Their rates would be equal, so policyengine-uk
  does not measure them and the response is zero.
- **No rate change.** A reform that doesn't change a person's marginal rate
  on gains leaves their gains alone. That includes a change to one band's
  rate for someone whose last pound of gains falls in another band. Until
  [policyengine-uk#2433](https://github.com/PolicyEngine/policyengine-uk/pull/2433)
  lands, the model can place gains in the higher band where the law puts
  them in the additional band, so a reform to only one of those two rates can
  respond where it shouldn't, or not respond where it should. Change both
  rates together to avoid it.
- **Marginal tax rates.** Marginal tax rates on earnings hold realised gains
  fixed: a pay rise is not a reform for the response to answer.

## Choosing another assumption

See [Reforms](../reforms.md#behavioural-responses-uk-capital-gains) for the
settings: static, sensitivities, the OBR comparison and the marginal tax rate
convention. Every UK run records the response it applied, so a result shows
the assumption it was calculated under (see
[The UK capital gains realisation response](../microsim.md#the-uk-capital-gains-realisation-response)).

## Interpreting results

- **Revenue.** Realised gains are part of household income, so with a
  response the change in household net income no longer equals the change in
  revenue. Read revenue from `gov_balance` or the taxes themselves.
- **Distributional results.** Household net income counts gains no longer
  realised as income lost, although they are deferred, not lost. So
  per-household impacts, income deciles and winners and losers show a CGT
  rise costing households more with the response than without it. Whether
  distributional measures should use gains before the response is an open
  methodology question.
- **Cross-effects.** Reforms to income tax bands or allowances can move
  marginal rates on gains, and so realised gains, even when CGT rates don't
  change.
