# PSM Causal Effect Report

## Setup
- Treatment: `complaint_inspection` (0/1)
- Outcome: `future_incident` (0/1)
- Covariates: industry_risk, firm_size, prior_incidents, region_risk, safety_training_score
- Matching: 1-NN on propensity score with caliper 0.08

## Point Estimates
- ATT: -0.113040
- ATC: -0.107753
- ATE: -0.111028

## 95% Bootstrap CI
- ATT CI: [-0.16575740766869795, -0.08125829824788694]
- ATC CI: [-0.13429052471369154, -0.058075664315644294]
- ATE CI: [-0.1515743502806046, -0.08450572165243157]

## Match Quality
- ATT pairs: 2477
- ATC pairs: 1522
- Valid bootstrap draws: 80 / 80

## Interpretation
- Negative effect indicates complaint-driven inspections are associated with lower future incident probability.
- This version uses synthetic data for reproducibility and pipeline validation.

## TODO for Real Data
- Replace synthetic generation with `load_real_inspection_data()` once a real inspection table is provided.
