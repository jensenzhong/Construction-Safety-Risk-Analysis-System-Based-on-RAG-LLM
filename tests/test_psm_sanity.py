from analysis.causal_psm import estimate_effects, simulate_data


def test_psm_sanity_effect_direction_is_negative() -> None:
    df = simulate_data(n_samples=5000, seed=2026)
    summary, _ = estimate_effects(
        df,
        caliper=0.10,
        bootstrap_iters=30,
        seed=2026,
    )

    assert summary["ate"] < 0
    assert summary["att"] < 0
