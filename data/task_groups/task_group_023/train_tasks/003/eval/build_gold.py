#!/usr/bin/env python3
"""Rebuild train_003 results from the Public Health Observatory Web exports."""

import argparse
import io
import json
import math
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score


TASK_DIR = Path(__file__).resolve().parents[1]
REQUEST_PATH = TASK_DIR / "input" / "payloads" / "analysis_request.json"
ANOMALY_RATIO = 5.0
KMEANS_SEED = 2307
KMEANS_N_INIT = 50


def download_csv(base_url, dataset, **filters):
    query = {"dataset": dataset, "format": "csv"}
    query.update({key: value for key, value in filters.items() if value is not None})
    url = base_url.rstrip("/") + "/download?" + urllib.parse.urlencode(query)
    with urllib.request.urlopen(url) as response:
        return pd.read_csv(io.BytesIO(response.read()), keep_default_na=True)


def latest_final(rows):
    final = rows.loc[rows["release_status"].eq("FINAL")].copy()
    final["revision"] = pd.to_numeric(final["revision"])
    final = final.sort_values(
        ["iso3", "year", "indicator_id", "revision", "released_at", "observation_id"]
    )
    return final.groupby(["iso3", "year", "indicator_id"], as_index=False).tail(1)


def anomaly_keys(selected, indicator_ids, years):
    keys = []
    scope = selected.loc[
        selected["indicator_id"].isin(indicator_ids) & selected["year"].isin(years)
    ]
    for (iso3, indicator_id), group in scope.groupby(["iso3", "indicator_id"]):
        series = group.sort_values("year")[["year", "value"]].dropna()
        values = dict(zip(series["year"].astype(int), series["value"].astype(float)))
        flagged_years = set(
            group.loc[group["quality_flag"].eq("SCALE_REVIEW"), "year"].astype(int)
        )
        for year in sorted(values):
            if year not in flagged_years:
                continue
            value = abs(values[year])
            adjacent = [
                abs(values[y])
                for y in (year - 1, year + 1)
                if y in values and abs(values[y]) > 0
            ]
            if not adjacent or value == 0:
                continue
            if all(value / max(other, 1e-12) >= ANOMALY_RATIO for other in adjacent):
                keys.append(f"{iso3}|{year}|{indicator_id}")
    return sorted(set(keys))


def round4(value):
    return round(float(value), 4)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://task-env:9023")
    args = parser.parse_args()
    request = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))

    countries = download_csv(args.base_url, "countries")
    label_map = {}
    for row in countries.itertuples(index=False):
        labels = {str(row.canonical_name), str(row.portal_label)}
        labels.update(str(row.alternate_labels).split("|"))
        for label in labels:
            label_map.setdefault(label.strip().casefold(), set()).add(str(row.iso3))

    mappings = []
    for label in request["country_labels"]:
        matches = sorted(label_map.get(label.strip().casefold(), set()))
        if len(matches) == 1:
            mappings.append({"country_label": label, "iso3": matches[0]})
    iso3s = sorted(item["iso3"] for item in mappings)
    alias_count = sum(
        1
        for item in mappings
        if item["country_label"]
        != countries.loc[countries["iso3"].eq(item["iso3"]), "canonical_name"].iloc[0]
    )

    years = list(range(request["panel_start_year"], request["panel_end_year"] + 1))
    all_indicators = request["burden_indicator_ids"] + [request["panel_outcome_indicator_id"]]
    observations = download_csv(
        args.base_url,
        "country_indicators",
        iso3=",".join(iso3s),
        indicator_id=",".join(all_indicators),
        year=",".join(str(year) for year in years),
    )
    selected = latest_final(observations)

    revisions = download_csv(
        args.base_url,
        "revisions",
        domain="COUNTRY",
    )
    revision_scope = revisions.loc[
        revisions["entity_id"].isin(iso3s)
        & revisions["effective_year"].isin(years)
        & revisions["field_id"].isin(request["burden_indicator_ids"])
    ].copy()
    applied_revision_ids = sorted(
        revision_scope.loc[revision_scope["status"].eq("APPLIED"), "revision_event_id"].astype(str)
    )
    nonapplied_revision_ids = sorted(
        revision_scope.loc[~revision_scope["status"].eq("APPLIED"), "revision_event_id"].astype(str)
    )

    anomalies = anomaly_keys(selected, request["burden_indicator_ids"], years)
    anomaly_tuples = {tuple(key.split("|")) for key in anomalies}
    cleaned = selected.copy()
    cleaned["year_text"] = cleaned["year"].astype(int).astype(str)
    mask = cleaned.apply(
        lambda row: (str(row["iso3"]), row["year_text"], str(row["indicator_id"]))
        in anomaly_tuples,
        axis=1,
    )
    cleaned.loc[mask, "value"] = np.nan

    cross = cleaned.loc[
        cleaned["year"].eq(request["reference_year"])
        & cleaned["indicator_id"].isin(request["burden_indicator_ids"])
    ].pivot(index="iso3", columns="indicator_id", values="value")
    cross = cross.reindex(index=iso3s, columns=request["burden_indicator_ids"])
    raw_cross = selected.loc[
        selected["year"].eq(request["reference_year"])
        & selected["indicator_id"].isin(request["burden_indicator_ids"])
    ].pivot(index="iso3", columns="indicator_id", values="value")
    raw_cross = raw_cross.reindex(index=iso3s, columns=request["burden_indicator_ids"])
    raw_missing = int(raw_cross.isna().sum().sum())
    anomaly_cross = sum(key.split("|")[1] == str(request["reference_year"]) for key in anomalies)
    medians = cross.median(axis=0)
    imputed = cross.fillna(medians)
    imputed_count = int(cross.isna().sum().sum())
    means = imputed.mean(axis=0)
    sample_sds = imputed.std(axis=0, ddof=1)
    standardized = (imputed - means) / sample_sds

    pca = PCA(svd_solver="full")
    scores = pca.fit_transform(standardized)
    components = pca.components_.copy()
    if components[0].sum() < 0:
        components[0] *= -1
        scores[:, 0] *= -1
    retained = int(np.sum(pca.explained_variance_ > 1.0))
    retained = max(retained, 1)
    loading_order = sorted(
        zip(request["burden_indicator_ids"], components[0]),
        key=lambda pair: (-abs(pair[1]), pair[0]),
    )
    top_loadings = [
        {"indicator_id": indicator, "loading": round4(loading)}
        for indicator, loading in loading_order[:3]
    ]

    retained_scores = scores[:, :retained]
    silhouettes = {}
    for k in range(2, 6):
        fitted = KMeans(n_clusters=k, random_state=KMEANS_SEED, n_init=KMEANS_N_INIT).fit(
            retained_scores
        )
        silhouettes[k] = silhouette_score(retained_scores, fitted.labels_)
    selected_k = sorted(silhouettes, key=lambda k: (-silhouettes[k], k))[0]

    k3 = KMeans(
        n_clusters=request["requested_cluster_count"],
        random_state=KMEANS_SEED,
        n_init=KMEANS_N_INIT,
    ).fit(retained_scores)
    cluster_pc1 = {
        label: float(scores[k3.labels_ == label, 0].mean()) for label in set(k3.labels_)
    }
    ordered_labels = sorted(cluster_pc1, key=cluster_pc1.get)
    semantic = {
        ordered_labels[0]: "LOW_BURDEN",
        ordered_labels[1]: "MIDDLE_BURDEN",
        ordered_labels[2]: "HIGH_BURDEN",
    }
    cluster_sizes = {name: 0 for name in ("LOW_BURDEN", "MIDDLE_BURDEN", "HIGH_BURDEN")}
    high_burden_iso3 = []
    for iso3, label in zip(iso3s, k3.labels_):
        cluster_sizes[semantic[label]] += 1
        if semantic[label] == "HIGH_BURDEN":
            high_burden_iso3.append(iso3)

    panel_predictors = cleaned.loc[
        cleaned["year"].isin(years)
        & cleaned["indicator_id"].isin(request["burden_indicator_ids"])
    ].pivot(index=["iso3", "year"], columns="indicator_id", values="value")
    full_index = pd.MultiIndex.from_product([iso3s, years], names=["iso3", "year"])
    panel_predictors = panel_predictors.reindex(
        index=full_index, columns=request["burden_indicator_ids"]
    )
    panel_predictors = panel_predictors.fillna(medians)
    panel_z = (panel_predictors - means) / sample_sds
    panel_pc1 = panel_z.to_numpy().dot(components[0])

    outcomes = cleaned.loc[
        cleaned["year"].isin(years)
        & cleaned["indicator_id"].eq(request["panel_outcome_indicator_id"])
    ][["iso3", "year", "value"]].rename(columns={"value": "life_expectancy"})
    panel = pd.DataFrame(index=full_index).reset_index()
    panel["pc1_burden"] = panel_pc1
    panel = panel.merge(outcomes, how="left", on=["iso3", "year"])
    panel = panel.merge(countries[["iso3", "region"]], how="left", on="iso3")
    panel = panel.dropna(subset=["life_expectancy", "pc1_burden", "region"])
    region_dummies = pd.get_dummies(panel["region"], prefix="region", drop_first=True, dtype=float)
    design = pd.concat([panel[["pc1_burden"]].astype(float), region_dummies], axis=1)
    design = sm.add_constant(design, has_constant="add")
    model = sm.OLS(panel["life_expectancy"].astype(float), design).fit()
    slope = float(model.params["pc1_burden"])
    p_value = float(model.pvalues["pc1_burden"])
    if slope < 0 and p_value < 0.05:
        advisory = "PRIORITIZE_HIGH_BURDEN_CLUSTER"
    elif slope < 0:
        advisory = "MONITOR_GRADIENT"
    else:
        advisory = "NO_ADVERSE_GRADIENT"

    result = {
        "reconciliation": {
            "requested_label_count": len(request["country_labels"]),
            "resolved_label_count": len(mappings),
            "alias_resolution_count": alias_count,
            "resolved_iso3": iso3s,
        },
        "quality_audit": {
            "applied_revision_event_ids": applied_revision_ids,
            "nonapplied_revision_event_ids": nonapplied_revision_ids,
            "anomaly_observation_keys": anomalies,
            "raw_missing_2022_cells": raw_missing,
            "anomaly_2022_cells": anomaly_cross,
            "imputed_2022_cells": imputed_count,
            "usable_country_count": int(imputed.shape[0]),
            "usable_indicator_count": int(imputed.shape[1]),
        },
        "pca": {
            "retained_component_count": retained,
            "pc1_variance_fraction": round4(pca.explained_variance_ratio_[0]),
            "top_absolute_loadings": top_loadings,
        },
        "clusters": {
            "requested_k": request["requested_cluster_count"],
            "silhouette_selected_k": int(selected_k),
            "silhouette_by_k": {str(k): round4(silhouettes[k]) for k in sorted(silhouettes)},
            "sizes": cluster_sizes,
            "high_burden_iso3": sorted(high_burden_iso3),
        },
        "panel_model": {
            "n_observations": int(model.nobs),
            "pc1_coefficient": round4(slope),
            "pc1_standard_error": round4(model.bse["pc1_burden"]),
            "pc1_p_value": round4(p_value),
            "r_squared": round4(model.rsquared),
            "region_fixed_effects": True,
        },
        "advisory": advisory,
    }
    print(json.dumps(result, indent=2, sort_keys=False, allow_nan=False))


if __name__ == "__main__":
    main()
