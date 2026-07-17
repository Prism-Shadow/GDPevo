#!/usr/bin/env python3
"""Granular deterministic evaluator for test_002."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

POINTS = [
    ("SP001", "Four-year publication reconciliation and three linked cohorts", 1),
    ("SP002", "Cluster-robust multi-period difference-GMM mediation with ordered state deletions", 3),
    ("SP003", "Nested state-blocked ridge grids and outer-fold predictive diagnostics", 3),
    ("SP004", "Restricted-null paired-state wild-cluster bootstrap-t with PRNG checkpoints", 3),
    ("SP005", "State-grouped split-conformal calibration cycles and state coverage", 3),
    ("SP006", "Partial-R2 causal-mediation sensitivity surface and tipping boundary", 3),
    ("SP007", "Four-year trajectory PCA, deterministic clustering, and stability audit", 3),
    ("SP008", "Controlled six-module evidence decision", 2),
]
TOTAL = sum(x[2] for x in POINTS)
MISSING = object()


def at(obj: Any, path: str) -> Any:
    cur = obj
    for key in path.split(".") if path else []:
        if not isinstance(cur, dict) or key not in cur:
            return MISSING
        cur = cur[key]
    return cur


def number(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    x = float(v)
    return x if math.isfinite(x) else None


def numeq(a: Any, b: Any) -> float:
    x, y = number(a), number(b)
    return float(x is not None and y is not None and abs(x-y) <= 0.00005 + 1e-12)


def inteq(a: Any, b: Any) -> float:
    x, y = number(a), number(b)
    return float(x is not None and y is not None and x == int(x) and y == int(y) and int(x) == int(y))


def texteq(a: Any, b: Any) -> float:
    return float(isinstance(a, str) and isinstance(b, str) and a.strip().upper() == b.strip().upper())


def booleq(a: Any, b: Any) -> float:
    return float(isinstance(a, bool) and isinstance(b, bool) and a is b)


CHECKERS: dict[str, Callable[[Any, Any], float]] = {"n": numeq, "i": inteq, "t": texteq, "b": booleq}


def paths_fraction(pred: dict, gold: dict, specs: list[tuple[str, str]]) -> float:
    if not specs:
        return 0.0
    return sum(CHECKERS[k](at(pred,p),at(gold,p)) for p,k in specs)/len(specs)


def ordered_rows_fraction(pv: Any, gv: Any, specs: list[tuple[str, str]]) -> float:
    if not isinstance(gv, list) or not isinstance(pv, list):
        return 0.0
    denom = 1 + len(gv)*len(specs)
    earned = float(len(pv) == len(gv))
    for i, grow in enumerate(gv):
        prow = pv[i] if i < len(pv) and isinstance(pv[i], dict) else {}
        if not isinstance(grow, dict):
            continue
        for field, kind in specs:
            earned += CHECKERS[kind](at(prow,field),at(grow,field))
    return earned/denom


def num_list_fraction(pv: Any, gv: Any) -> float:
    if not isinstance(pv,list) or not isinstance(gv,list): return 0.0
    return (float(len(pv)==len(gv))+sum(numeq(pv[i],v) for i,v in enumerate(gv) if i<len(pv)))/(1+len(gv))


def semantic_band(raw_fraction: float) -> float:
    """Turn element accuracy into stable semantic partial-credit levels.

    Exact work receives full credit.  A defect in a long diagnostic table can no
    longer disappear into hundreds of correct cells: the affected semantic
    component drops to a documented partial-credit tier.
    """
    f=max(0.0,min(1.0,float(raw_fraction)))
    if math.isclose(f,1.0,abs_tol=1e-12): return 1.0
    if f >= .90: return .75
    if f >= .60: return .50
    if f > 0.0: return .25
    return 0.0


def semantic_paths(pred: dict, gold: dict, specs: list[tuple[str,str]]) -> float:
    return semantic_band(paths_fraction(pred,gold,specs))


def semantic_num_list(pv: Any, gv: Any) -> float:
    return semantic_band(num_list_fraction(pv,gv))


def semantic_table(
    pv: Any,
    gv: Any,
    groups: list[tuple[float,list[tuple[str,str]]]],
) -> float:
    """Score a table by a few named-by-caller column groups, not by cell count."""
    if not math.isclose(sum(x[0] for x in groups),1.0,abs_tol=1e-12):
        raise ValueError("semantic table shares")
    return sum(share*semantic_band(ordered_rows_fraction(pv,gv,specs))
               for share,specs in groups)


def semantic_nested_grid(pf: Any, gf: Any, key: str) -> float:
    """Give every fold semantic status before aggregating a nested grid."""
    if not isinstance(pf,list) or not isinstance(gf,list) or not gf:
        return 0.0
    fold_scores=[]
    for i,grow in enumerate(gf):
        prow=pf[i] if i<len(pf) and isinstance(pf[i],dict) else {}
        pgrid=prow.get(key) if isinstance(prow,dict) else None
        ggrid=grow.get(key) if isinstance(grow,dict) else None
        fold_scores.append(semantic_table(pgrid,ggrid,[
            (.20,[("lambda","n")]),
            (.80,[("rmse","n")]),
        ]))
    # A single defective fold must move the grid module off full credit.
    raw=(float(len(pf)==len(gf))+sum(fold_scores))/(1+len(gf))
    return semantic_band(raw)


def weighted(items: list[tuple[str,float,float]]) -> tuple[float,list[dict[str,Any]]]:
    if not math.isclose(sum(x[1] for x in items),1.0,abs_tol=1e-12): raise ValueError("shares")
    earned=0.0; details=[]
    for name,share,fraction in items:
        f=max(0.0,min(1.0,float(fraction)));earned += share*f
        details.append({"name":name,"share_within_point":share,"earned_fraction":round(f,12),"passed":math.isclose(f,1.0,abs_tol=1e-12)})
    return earned,details


def score_points(p: dict, g: dict) -> list[tuple[float,list[dict[str,Any]]]]:
    cohort_lists=[]
    for key in ["selected_health_rows_by_year","selected_socioeconomic_rows_by_year","complete_count_by_year"]:
        cohort_lists.append(ordered_rows_fraction(at(p,f"cohort_audit.{key}"),at(g,f"cohort_audit.{key}"),[("year","i"),("count","i")]))
    sp1=weighted([
      ("county universe and cohort totals",.45,paths_fraction(p,g,[(f"cohort_audit.{x}","i") for x in ["requested_county_count","primary_2024_count","balanced_four_year_count","machine_learning_complete_count","state_count"]])),
      ("ordered selected health publications",.20,cohort_lists[0]),
      ("ordered selected socioeconomic publications",.15,cohort_lists[1]),
      ("ordered annual completeness audit",.20,cohort_lists[2]),
    ])

    eqspec=[("coefficient","n"),("cluster_se","n"),("t_statistic","n"),("confidence_interval_95.lower","n"),("confidence_interval_95.upper","n")]
    eqscores=[semantic_paths(
        at(p,f"difference_gmm_mediation.{x}") if isinstance(at(p,f"difference_gmm_mediation.{x}"),dict) else {},
        at(g,f"difference_gmm_mediation.{x}"),eqspec)
        for x in ["total_housing","path_a_housing","path_b_sleep","direct_housing"]]
    loso=semantic_table(
        at(p,"difference_gmm_mediation.leave_one_state_out"),
        at(g,"difference_gmm_mediation.leave_one_state_out"),
        [(.15,[("omitted_state","t")]),(.10,[("n","i")]),
         (.375,[("indirect_effect","n")]),(.375,[("direct_housing","n")])],
    )
    stacked=weighted([
      ("cross-equation correction and covariance",.35,semantic_paths(p,g,[("difference_gmm_mediation.stacked_indirect.cross_equation_correction","n"),("difference_gmm_mediation.stacked_indirect.a_b_covariance","n")])),
      ("indirect estimate and cluster uncertainty",.65,semantic_paths(p,g,[(f"difference_gmm_mediation.stacked_indirect.{x}","n") for x in ["estimate","cluster_se","confidence_interval_95.lower","confidence_interval_95.upper"]])),
    ])[0]
    sp2=weighted([
      ("GMM panel dimensions",.05,semantic_paths(p,g,[(f"difference_gmm_mediation.{x}","i") for x in ["observation_count","county_count","state_count"]])),
      ("four clustered equation estimates and uncertainty",.20,sum(eqscores)/len(eqscores)),
      ("two endogenous first-stage partial F statistics",.08,semantic_paths(p,g,[("difference_gmm_mediation.first_stage_partial_f.delta_housing","n"),("difference_gmm_mediation.first_stage_partial_f.delta_sleep","n")])),
      ("stacked cross-equation indirect effect and uncertainty",.37,stacked),
      ("ordered leave-one-state-out influence diagnostics",.30,loso),
    ])

    pf=at(p,"nested_state_ridge.outer_folds");gf=at(g,"nested_state_ridge.outer_folds")
    foldmeta=semantic_table(pf,gf,[
      (.20,[("held_out_state","t")]),(.15,[("n","i")]),
      (.325,[("base_selected_lambda","n")]),(.325,[("augmented_selected_lambda","n")]),
    ])
    outermetrics=semantic_table(pf,gf,[
      (.20,[("held_out_state","t")]),(.40,[("base_outer_rmse","n")]),
      (.40,[("augmented_outer_rmse","n")]),
    ])
    sp3=weighted([
      ("ridge cohort, fold count, and fixed lambda grid",.08,(semantic_paths(p,g,[("nested_state_ridge.n","i"),("nested_state_ridge.fold_count","i")])+semantic_num_list(at(p,"nested_state_ridge.lambda_grid"),at(g,"nested_state_ridge.lambda_grid")))/2),
      ("pooled outer errors and state win count",.12,semantic_paths(p,g,[("nested_state_ridge.pooled_base_rmse","n"),("nested_state_ridge.pooled_augmented_rmse","n"),("nested_state_ridge.augmented_better_state_count","i")])),
      ("ordered fold sizes and selected hyperparameters",.18,foldmeta),
      ("base-model nested lambda-grid diagnostics",.20,semantic_nested_grid(pf,gf,"base_inner_grid_rmse")),
      ("augmented-model nested lambda-grid diagnostics",.20,semantic_nested_grid(pf,gf,"augmented_inner_grid_rmse")),
      ("ordered held-out-state RMSE pairs",.22,outermetrics),
    ])

    beq=semantic_table(at(p,"wild_cluster_bootstrap_t.equations"),at(g,"wild_cluster_bootstrap_t.equations"),[
      (.08,[("equation","t")]),
      (.32,[("observed_coefficient","n"),("observed_cr1_se","n"),("observed_t","n")]),
      (.30,[("bootstrap_p_value","n"),("bootstrap_t_q025","n"),("bootstrap_t_q975","n")]),
      (.30,[("confidence_interval_95.lower","n"),("confidence_interval_95.upper","n")]),
    ])
    third=.65/3
    bcp=semantic_table(at(p,"wild_cluster_bootstrap_t.checkpoints"),at(g,"wild_cluster_bootstrap_t.checkpoints"),[
      (.10,[("replicate","i")]),(.25,[("prng_state","i")]),
      (third,[("total_housing_t","n")]),(third,[("path_a_housing_t","n")]),
      (third,[("path_b_sleep_t","n")]),
    ])
    sp4=weighted([
      ("bootstrap method, seed, replicate count, and terminal state",.10,semantic_paths(p,g,[("wild_cluster_bootstrap_t.method","t"),("wild_cluster_bootstrap_t.seed","i"),("wild_cluster_bootstrap_t.replicate_count","i"),("wild_cluster_bootstrap_t.final_prng_state","i")])),
      ("three restricted-null equation distributions",.48,beq),
      ("ordered PRNG and equation-t checkpoints",.42,bcp),
    ])

    cyc=semantic_table(at(p,"state_grouped_conformal.cycles"),at(g,"state_grouped_conformal.cycles"),[
      (.15,[("test_fold","i"),("calibration_fold","i")]),
      (.15,[("training_state_count","i"),("calibration_state_count","i"),("test_state_count","i")]),
      (.15,[("calibration_count","i"),("test_count","i")]),
      (.20,[("qhat_state_max","n")]),(.15,[("test_coverage","n")]),
      (.10,[("mean_interval_width","n")]),(.10,[("worst_test_state","t")]),
    ])
    scov=semantic_table(at(p,"state_grouped_conformal.state_coverage"),at(g,"state_grouped_conformal.state_coverage"),[
      (.15,[("state_abbr","t")]),(.15,[("n","i")]),
      (.45,[("coverage","n")]),(.25,[("mean_width","n")]),
    ])
    sp5=weighted([
      ("conformal nominal level and fixed learner",.05,semantic_paths(p,g,[("state_grouped_conformal.nominal_coverage","n"),("state_grouped_conformal.fixed_lambda","n")])),
      ("pooled calibration performance",.15,semantic_paths(p,g,[("state_grouped_conformal.overall_coverage","n"),("state_grouped_conformal.mean_interval_width","n"),("state_grouped_conformal.state_count_at_or_above_80pct","i")])),
      ("five ordered train-calibration-test cycles",.42,cyc),
      ("ordered per-state coverage and width",.38,scov),
    ])

    coords=semantic_table(at(p,"mediation_sensitivity_surface.surface"),at(g,"mediation_sensitivity_surface.surface"),[
      (.75,[("r2_mediator_confounder","n"),("r2_outcome_confounder","n")]),
      (.25,[("bias_direction","t")]),
    ])
    surf=semantic_table(at(p,"mediation_sensitivity_surface.surface"),at(g,"mediation_sensitivity_surface.surface"),[
      (.30,[("adjusted_path_b","n")]),(.30,[("adjusted_indirect","n")]),
      (.20,[("adjusted_direct","n")]),(.20,[("proportion_mediated","n")]),
    ])
    sp6=weighted([
      ("baseline mediation and residual degrees of freedom",.15,semantic_paths(p,g,[("mediation_sensitivity_surface.baseline_path_a","n"),("mediation_sensitivity_surface.baseline_path_b","n"),("mediation_sensitivity_surface.baseline_path_b_se","n"),("mediation_sensitivity_surface.residual_degrees_of_freedom","i")])),
      ("equal-strength tipping boundary",.10,semantic_paths(p,g,[("mediation_sensitivity_surface.equal_strength_tipping_r2","n")])),
      ("ordered two-dimensional R2 grid coordinates",.25,coords),
      ("adjusted path and mediation surface",.50,surf),
    ])

    loads=semantic_table(at(p,"trajectory_pca_clustering.loadings"),at(g,"trajectory_pca_clustering.loadings"),[
      (.15,[("feature","t")]),(.425,[("pc1","n")]),(.425,[("pc2","n")]),
    ])
    sts=semantic_table(at(p,"trajectory_pca_clustering.states"),at(g,"trajectory_pca_clustering.states"),[
      (.10,[("state_abbr","t")]),(.10,[("balanced_county_count","i")]),
      (.20,[("pc1_score","n")]),(.20,[("pc2_score","n")]),(.40,[("cluster","i")]),
    ])
    stab=semantic_table(at(p,"trajectory_pca_clustering.leave_one_year_out_stability"),at(g,"trajectory_pca_clustering.leave_one_year_out_stability"),[
      (.20,[("omitted_year","i")]),(.80,[("adjusted_rand_index","n")]),
    ])
    sp7=weighted([
      ("trajectory dimensions and deterministic k-means iterations",.10,semantic_paths(p,g,[("trajectory_pca_clustering.state_count","i"),("trajectory_pca_clustering.feature_count","i"),("trajectory_pca_clustering.kmeans_iterations","i")])),
      ("leading PCA spectrum",.15,(semantic_num_list(at(p,"trajectory_pca_clustering.eigenvalues"),at(g,"trajectory_pca_clustering.eigenvalues"))+semantic_num_list(at(p,"trajectory_pca_clustering.explained_variance_ratio"),at(g,"trajectory_pca_clustering.explained_variance_ratio")))/2),
      ("ordered signed PC1 and PC2 loadings",.20,loads),
      ("ordered state scores and cluster assignments",.40,sts),
      ("leave-year-out ARI sequence and stability summaries",.15,(stab+semantic_paths(p,g,[("trajectory_pca_clustering.mean_stability_ari","n"),("trajectory_pca_clustering.minimum_stability_ari","n")]))/2),
    ])

    sp8=weighted([
      ("six controlled evidence flags",.75,paths_fraction(p,g,[(f"controlled_conclusion.{x}","b") for x in ["difference_gmm_supported","nested_ridge_supported","bootstrap_supported","grouped_conformal_calibrated","sensitivity_robust","trajectory_stable"]])),
      ("supported-module count and ordered classification",.25,paths_fraction(p,g,[("controlled_conclusion.supported_module_count","i"),("controlled_conclusion.classification","t")])),
    ])
    return [sp1,sp2,sp3,sp4,sp5,sp6,sp7,sp8]


def evaluate(prediction: Any, gold: dict) -> dict[str,Any]:
    valid=isinstance(prediction,dict) and bool(prediction)
    results=score_points(prediction,gold) if valid else [(0.0,[]) for _ in POINTS]
    required_subchecks={
      "SP001":{"county universe and cohort totals"},
      "SP002":{"GMM panel dimensions"},
      "SP003":{"pooled outer errors and state win count"},
      "SP004":{"three restricted-null equation distributions"},
      "SP005":{"pooled calibration performance"},
      "SP006":{"equal-strength tipping boundary"},
      "SP007":{"leave-year-out ARI sequence and stability summaries"},
      "SP008":{"supported-module count and ordered classification"},
    }
    rubric=[];score=0.0
    for (pid,goal,w),(fraction,subs) in zip(POINTS,results):
        by_name={item["name"]:item for item in subs}
        required=required_subchecks[pid]
        passed=valid and all(by_name.get(name,{}).get("passed") is True for name in required)
        earned=w/TOTAL if passed else 0.0;score+=earned
        rubric.append({"id":pid,"goal":goal,"raw_weight":w,"normalized_max":round(w/TOTAL,12),"point_pass":passed,"earned_fraction":1.0 if passed else 0.0,"earned_normalized_score":round(earned,12),"required_subchecks":sorted(required),"subchecks":subs})
    return {"score":round(score,12),"max_score":1.0,"total_raw_weight":TOTAL,"rubric":rubric}


def main() -> None:
    gold_path=Path(__file__).resolve().parent.parent/"output"/"answer.json"
    gold=json.loads(gold_path.read_text())
    try:
        if len(sys.argv)!=2: prediction={}
        else: prediction=json.loads(Path(sys.argv[1]).read_text())
    except Exception:
        prediction={}
    print(json.dumps(evaluate(prediction,gold),indent=2))


if __name__=="__main__": main()
