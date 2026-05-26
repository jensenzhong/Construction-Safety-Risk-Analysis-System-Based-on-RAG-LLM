import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


DEFAULT_COVARIATES = [
    "industry_risk",
    "firm_size",
    "prior_incidents",
    "region_risk",
    "safety_training_score",
]


@dataclass
class MatchResult:
    source_index: int
    matched_index: int
    source_pscore: float
    matched_pscore: float
    abs_diff: float


@dataclass
class EffectEstimate:
    att: float
    atc: float
    ate: float
    n_att_pairs: int
    n_atc_pairs: int


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def simulate_data(n_samples: int = 6000, seed: int = 42) -> pd.DataFrame:
    """Generate reproducible synthetic inspection-level data for PSM demonstration."""
    rng = np.random.default_rng(seed)

    industry_risk = rng.beta(2.4, 2.1, n_samples)
    region_risk = rng.beta(2.0, 2.3, n_samples)
    firm_size = np.exp(rng.normal(4.1, 0.85, n_samples))

    prior_incidents = rng.poisson(0.5 + 2.5 * industry_risk + 0.6 * region_risk)
    safety_training_score = np.clip(
        rng.normal(70 - 18 * industry_risk - 8 * region_risk, 11, n_samples),
        5,
        100,
    )

    prior_norm = np.clip(prior_incidents / 10.0, 0.0, 2.0)
    training_norm = safety_training_score / 100.0
    size_norm = (np.log(firm_size) - np.log(firm_size).mean()) / (np.log(firm_size).std() + 1e-9)

    treatment_logit = (
        -0.25
        + 1.5 * industry_risk
        + 1.0 * prior_norm
        + 0.8 * region_risk
        - 1.1 * training_norm
        + 0.25 * size_norm
    )
    treatment_prob = _sigmoid(treatment_logit)
    complaint_inspection = rng.binomial(1, treatment_prob)

    # True treatment effect is negative: complaint-driven inspections reduce future incident risk.
    treatment_effect = -0.60
    outcome_logit = (
        -1.90
        + 1.6 * industry_risk
        + 1.1 * prior_norm
        + 0.7 * region_risk
        - 1.2 * training_norm
        + 0.20 * size_norm
        + treatment_effect * complaint_inspection
    )
    outcome_prob = _sigmoid(outcome_logit)
    future_incident = rng.binomial(1, outcome_prob)

    df = pd.DataFrame(
        {
            "complaint_inspection": complaint_inspection.astype(int),
            "future_incident": future_incident.astype(int),
            "industry_risk": industry_risk.astype(float),
            "firm_size": firm_size.astype(float),
            "prior_incidents": prior_incidents.astype(float),
            "region_risk": region_risk.astype(float),
            "safety_training_score": safety_training_score.astype(float),
        }
    )
    return df


def load_real_inspection_data(csv_path: Optional[Path]) -> pd.DataFrame:
    """
    Load a real inspection table.

    TODO:
    Replace synthetic simulation with actual complaint-driven inspection data
    once the real inspection table is available.
    """
    if csv_path is None:
        raise ValueError("csv_path must be provided when loading real inspection data.")

    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Real inspection dataset not found: {path}")

    df = pd.read_csv(path)
    required_cols = set(DEFAULT_COVARIATES + ["complaint_inspection", "future_incident"])
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Real inspection dataset missing required columns: {missing}")

    return df[list(required_cols)].copy()


def estimate_propensity_scores(
    df: pd.DataFrame,
    covariates: List[str],
    treatment_col: str = "complaint_inspection",
) -> np.ndarray:
    x = df[covariates].astype(float).to_numpy()
    t = df[treatment_col].astype(int).to_numpy()

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("logit", LogisticRegression(max_iter=2000, solver="lbfgs")),
        ]
    )
    model.fit(x, t)
    scores = model.predict_proba(x)[:, 1]
    return scores


def _match_direction(
    df: pd.DataFrame,
    propensity_col: str,
    treatment_col: str,
    source_treatment_value: int,
    caliper: float,
) -> List[MatchResult]:
    src_idx = df.index[df[treatment_col] == source_treatment_value].to_numpy()
    tgt_idx = df.index[df[treatment_col] != source_treatment_value].to_numpy()

    if len(src_idx) == 0 or len(tgt_idx) == 0:
        return []

    src_scores = df.loc[src_idx, propensity_col].to_numpy()
    tgt_scores = df.loc[tgt_idx, propensity_col].to_numpy()

    matches: List[MatchResult] = []
    for s_idx, s_score in zip(src_idx, src_scores):
        diffs = np.abs(tgt_scores - s_score)
        best_pos = int(np.argmin(diffs))
        best_diff = float(diffs[best_pos])
        if best_diff > caliper:
            continue
        m_idx = int(tgt_idx[best_pos])
        matches.append(
            MatchResult(
                source_index=int(s_idx),
                matched_index=m_idx,
                source_pscore=float(s_score),
                matched_pscore=float(tgt_scores[best_pos]),
                abs_diff=best_diff,
            )
        )

    return matches


def _estimate_effect_from_matches(
    df: pd.DataFrame,
    matches: List[MatchResult],
    outcome_col: str,
    source_is_treated: bool,
) -> float:
    if not matches:
        return float("nan")

    src_vals = np.array([df.at[m.source_index, outcome_col] for m in matches], dtype=float)
    m_vals = np.array([df.at[m.matched_index, outcome_col] for m in matches], dtype=float)

    if source_is_treated:
        # ATT = E[Y(1)-Y(0) | T=1]
        effects = src_vals - m_vals
    else:
        # ATC = E[Y(1)-Y(0) | T=0]
        effects = m_vals - src_vals

    return float(np.mean(effects))


def _build_matched_sample(
    df: pd.DataFrame,
    att_matches: List[MatchResult],
    atc_matches: List[MatchResult],
    treatment_col: str,
    outcome_col: str,
) -> pd.DataFrame:
    rows: List[Dict] = []

    pair_id = 0
    for m in att_matches:
        pair_id += 1
        rows.append(
            {
                "pair_id": pair_id,
                "pair_type": "ATT",
                "treated_index": int(m.source_index),
                "control_index": int(m.matched_index),
                "treated_outcome": int(df.at[m.source_index, outcome_col]),
                "control_outcome": int(df.at[m.matched_index, outcome_col]),
                "treated_pscore": float(m.source_pscore),
                "control_pscore": float(m.matched_pscore),
                "abs_pscore_diff": float(m.abs_diff),
            }
        )

    for m in atc_matches:
        pair_id += 1
        rows.append(
            {
                "pair_id": pair_id,
                "pair_type": "ATC",
                "treated_index": int(m.matched_index),
                "control_index": int(m.source_index),
                "treated_outcome": int(df.at[m.matched_index, outcome_col]),
                "control_outcome": int(df.at[m.source_index, outcome_col]),
                "treated_pscore": float(m.matched_pscore),
                "control_pscore": float(m.source_pscore),
                "abs_pscore_diff": float(m.abs_diff),
            }
        )

    return pd.DataFrame(rows)


def _estimate_once(
    df: pd.DataFrame,
    covariates: List[str],
    treatment_col: str,
    outcome_col: str,
    caliper: float,
) -> Tuple[EffectEstimate, pd.DataFrame, List[MatchResult], List[MatchResult]]:
    working = df.copy().reset_index(drop=True)
    pscore = estimate_propensity_scores(working, covariates, treatment_col=treatment_col)
    working["propensity_score"] = pscore

    att_matches = _match_direction(
        working,
        propensity_col="propensity_score",
        treatment_col=treatment_col,
        source_treatment_value=1,
        caliper=caliper,
    )
    atc_matches = _match_direction(
        working,
        propensity_col="propensity_score",
        treatment_col=treatment_col,
        source_treatment_value=0,
        caliper=caliper,
    )

    if not att_matches or not atc_matches:
        raise ValueError(
            f"Insufficient matches under caliper={caliper}. "
            f"att_matches={len(att_matches)}, atc_matches={len(atc_matches)}"
        )

    att = _estimate_effect_from_matches(
        working,
        matches=att_matches,
        outcome_col=outcome_col,
        source_is_treated=True,
    )
    atc = _estimate_effect_from_matches(
        working,
        matches=atc_matches,
        outcome_col=outcome_col,
        source_is_treated=False,
    )

    treated_rate = float(working[treatment_col].mean())
    ate = float(treated_rate * att + (1.0 - treated_rate) * atc)

    estimate = EffectEstimate(
        att=float(att),
        atc=float(atc),
        ate=float(ate),
        n_att_pairs=len(att_matches),
        n_atc_pairs=len(atc_matches),
    )
    return estimate, working, att_matches, atc_matches


def _bootstrap_ci(values: List[float]) -> List[Optional[float]]:
    if not values:
        return [None, None]
    arr = np.array(values, dtype=float)
    return [float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))]


def estimate_effects(
    df: pd.DataFrame,
    covariates: Optional[List[str]] = None,
    treatment_col: str = "complaint_inspection",
    outcome_col: str = "future_incident",
    caliper: float = 0.08,
    bootstrap_iters: int = 200,
    seed: int = 42,
) -> Tuple[Dict, pd.DataFrame]:
    covars = covariates or list(DEFAULT_COVARIATES)

    point_est, scored_df, att_matches, atc_matches = _estimate_once(
        df=df,
        covariates=covars,
        treatment_col=treatment_col,
        outcome_col=outcome_col,
        caliper=caliper,
    )

    rng = np.random.default_rng(seed)
    boot_att: List[float] = []
    boot_atc: List[float] = []
    boot_ate: List[float] = []

    for _ in range(max(0, bootstrap_iters)):
        sample_idx = rng.integers(0, len(df), len(df))
        sample_df = df.iloc[sample_idx].reset_index(drop=True)
        try:
            boot_est, _, _, _ = _estimate_once(
                df=sample_df,
                covariates=covars,
                treatment_col=treatment_col,
                outcome_col=outcome_col,
                caliper=caliper,
            )
            boot_att.append(float(boot_est.att))
            boot_atc.append(float(boot_est.atc))
            boot_ate.append(float(boot_est.ate))
        except Exception:
            continue

    matched_sample = _build_matched_sample(
        scored_df,
        att_matches=att_matches,
        atc_matches=atc_matches,
        treatment_col=treatment_col,
        outcome_col=outcome_col,
    )

    summary = {
        "n_samples": int(len(df)),
        "treated_rate": float(df[treatment_col].mean()),
        "caliper": float(caliper),
        "covariates": covars,
        "att": float(point_est.att),
        "atc": float(point_est.atc),
        "ate": float(point_est.ate),
        "n_att_pairs": int(point_est.n_att_pairs),
        "n_atc_pairs": int(point_est.n_atc_pairs),
        "bootstrap_iters": int(bootstrap_iters),
        "bootstrap_valid": int(len(boot_ate)),
        "att_ci95": _bootstrap_ci(boot_att),
        "atc_ci95": _bootstrap_ci(boot_atc),
        "ate_ci95": _bootstrap_ci(boot_ate),
    }

    return summary, matched_sample


def write_outputs(summary: Dict, matched_sample: pd.DataFrame, output_dir: Path) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    matched_path = output_dir / "psm_matched_sample.csv"
    summary_path = output_dir / "psm_effect_summary.json"
    report_path = output_dir / "psm_report.md"

    matched_sample.to_csv(matched_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report = f"""# PSM Causal Effect Report

## Setup
- Treatment: `complaint_inspection` (0/1)
- Outcome: `future_incident` (0/1)
- Covariates: {", ".join(summary.get("covariates", []))}
- Matching: 1-NN on propensity score with caliper {summary.get("caliper")}

## Point Estimates
- ATT: {summary.get("att"):.6f}
- ATC: {summary.get("atc"):.6f}
- ATE: {summary.get("ate"):.6f}

## 95% Bootstrap CI
- ATT CI: {summary.get("att_ci95")}
- ATC CI: {summary.get("atc_ci95")}
- ATE CI: {summary.get("ate_ci95")}

## Match Quality
- ATT pairs: {summary.get("n_att_pairs")}
- ATC pairs: {summary.get("n_atc_pairs")}
- Valid bootstrap draws: {summary.get("bootstrap_valid")} / {summary.get("bootstrap_iters")}

## Interpretation
- Negative effect indicates complaint-driven inspections are associated with lower future incident probability.
- This version uses synthetic data for reproducibility and pipeline validation.

## TODO for Real Data
- Replace synthetic generation with `load_real_inspection_data()` once a real inspection table is provided.
"""
    report_path.write_text(report, encoding="utf-8")

    return {
        "matched_sample": matched_path,
        "effect_summary": summary_path,
        "report": report_path,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run lightweight PSM causal analysis")
    parser.add_argument("--output-dir", default="results", help="Output directory for artifacts")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--n-samples", type=int, default=6000, help="Synthetic sample size")
    parser.add_argument("--caliper", type=float, default=0.08, help="Propensity score matching caliper")
    parser.add_argument("--bootstrap", type=int, default=200, help="Bootstrap iterations")
    parser.add_argument("--real-data-csv", default="", help="Optional real inspection csv path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.real_data_csv:
        df = load_real_inspection_data(Path(args.real_data_csv))
        data_source = f"real::{args.real_data_csv}"
    else:
        df = simulate_data(n_samples=args.n_samples, seed=args.seed)
        data_source = "synthetic"

    summary, matched_sample = estimate_effects(
        df=df,
        caliper=args.caliper,
        bootstrap_iters=args.bootstrap,
        seed=args.seed,
    )
    summary["data_source"] = data_source

    paths = write_outputs(summary, matched_sample, output_dir=Path(args.output_dir))

    print("PSM analysis completed")
    print(f"ATE: {summary['ate']:.6f}")
    print(f"ATT: {summary['att']:.6f}")
    print(f"ATC: {summary['atc']:.6f}")
    print(f"Matched sample: {paths['matched_sample']}")
    print(f"Summary JSON: {paths['effect_summary']}")
    print(f"Report: {paths['report']}")


if __name__ == "__main__":
    main()
