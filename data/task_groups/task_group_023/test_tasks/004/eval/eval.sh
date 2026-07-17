#!/usr/bin/env bash
set -u
python3 - "$@" <<'PY'
import json, math, sys

WEIGHTS=[1,3,3,3,3,3,3,2]
TOTAL=sum(WEIGHTS)
GOALS=[
 "Reconcile releases and construct the primary and strict balanced cohorts.",
 "Apply the delete-one-state panel jackknife and bias-corrected inference.",
 "Reproduce division-nested elastic-net coordinate descent and every fold/grid diagnostic.",
 "Reproduce the seeded wild-cluster bootstrap-t distribution and test.",
 "Construct grouped out-of-fold conformal intervals and division diagnostics.",
 "Reproduce trajectory PCA, deterministic clusters, and leave-one-year stability.",
 "Enumerate all source scenarios and reproduce the Shapley decomposition.",
 "Apply all six registered flags and the precedence decision."
]
EXPECTED=json.loads(r'''{
  "request_id": "OBS-STATE-ALGORITHMIC-AUDIT-2022-PM-R4",
  "release_and_cohort": {
    "reference_year": 2022,
    "jurisdiction_universe_count": 51,
    "yearly_complete_case_counts": [
      {
        "year": 2020,
        "count": 48
      },
      {
        "year": 2021,
        "count": 43
      },
      {
        "year": 2022,
        "count": 43
      },
      {
        "year": 2023,
        "count": 45
      },
      {
        "year": 2024,
        "count": 49
      }
    ],
    "primary_complete_case_count": 43,
    "primary_excluded_state_codes": [
      "DE",
      "FL",
      "KY",
      "MS",
      "MT",
      "OH",
      "TX",
      "VT"
    ],
    "balanced_state_count": 28,
    "balanced_state_codes": [
      "AK",
      "AR",
      "AZ",
      "CA",
      "CO",
      "DC",
      "IL",
      "IN",
      "LA",
      "MA",
      "MD",
      "ME",
      "MI",
      "MN",
      "MO",
      "NC",
      "ND",
      "NE",
      "NJ",
      "NM",
      "NV",
      "OK",
      "OR",
      "RI",
      "SD",
      "UT",
      "VA",
      "WA"
    ]
  },
  "cluster_jackknife": {
    "full_within_smoking_coefficient": 6.1172,
    "delete_one_results": [
      {
        "state_code": "AK",
        "coefficient": 6.147,
        "absolute_percent_change": 0.4875
      },
      {
        "state_code": "AR",
        "coefficient": 7.1926,
        "absolute_percent_change": 17.5799
      },
      {
        "state_code": "AZ",
        "coefficient": 6.2425,
        "absolute_percent_change": 2.0486
      },
      {
        "state_code": "CA",
        "coefficient": 5.9395,
        "absolute_percent_change": 2.9048
      },
      {
        "state_code": "CO",
        "coefficient": 6.0772,
        "absolute_percent_change": 0.6526
      },
      {
        "state_code": "DC",
        "coefficient": 6.5241,
        "absolute_percent_change": 6.653
      },
      {
        "state_code": "IL",
        "coefficient": 5.7886,
        "absolute_percent_change": 5.3707
      },
      {
        "state_code": "IN",
        "coefficient": 6.1248,
        "absolute_percent_change": 0.1249
      },
      {
        "state_code": "LA",
        "coefficient": 6.5038,
        "absolute_percent_change": 6.32
      },
      {
        "state_code": "MA",
        "coefficient": 5.2735,
        "absolute_percent_change": 13.7923
      },
      {
        "state_code": "MD",
        "coefficient": 6.164,
        "absolute_percent_change": 0.766
      },
      {
        "state_code": "ME",
        "coefficient": 5.7474,
        "absolute_percent_change": 6.0442
      },
      {
        "state_code": "MI",
        "coefficient": 4.8492,
        "absolute_percent_change": 20.7285
      },
      {
        "state_code": "MN",
        "coefficient": 6.3637,
        "absolute_percent_change": 4.0297
      },
      {
        "state_code": "MO",
        "coefficient": 6.4081,
        "absolute_percent_change": 4.7563
      },
      {
        "state_code": "NC",
        "coefficient": 6.1148,
        "absolute_percent_change": 0.0386
      },
      {
        "state_code": "ND",
        "coefficient": 6.0131,
        "absolute_percent_change": 1.7019
      },
      {
        "state_code": "NE",
        "coefficient": 6.1558,
        "absolute_percent_change": 0.6317
      },
      {
        "state_code": "NJ",
        "coefficient": 6.2184,
        "absolute_percent_change": 1.655
      },
      {
        "state_code": "NM",
        "coefficient": 5.6642,
        "absolute_percent_change": 7.4056
      },
      {
        "state_code": "NV",
        "coefficient": 6.5409,
        "absolute_percent_change": 6.9261
      },
      {
        "state_code": "OK",
        "coefficient": 6.3889,
        "absolute_percent_change": 4.4425
      },
      {
        "state_code": "OR",
        "coefficient": 6.1442,
        "absolute_percent_change": 0.4424
      },
      {
        "state_code": "RI",
        "coefficient": 6.4625,
        "absolute_percent_change": 5.6456
      },
      {
        "state_code": "SD",
        "coefficient": 5.9312,
        "absolute_percent_change": 3.0407
      },
      {
        "state_code": "UT",
        "coefficient": 6.4027,
        "absolute_percent_change": 4.6674
      },
      {
        "state_code": "VA",
        "coefficient": 6.0262,
        "absolute_percent_change": 1.4866
      },
      {
        "state_code": "WA",
        "coefficient": 5.9208,
        "absolute_percent_change": 3.2109
      }
    ],
    "mean_delete_one_coefficient": 6.1189,
    "bias_corrected_coefficient": 6.07,
    "jackknife_standard_error": 2.1952,
    "jackknife_t_statistic": 2.7652,
    "jackknife_t_p_value": 0.0101,
    "maximum_delete_one_absolute_percent_change": 20.7285,
    "most_influential_state_code": "MI"
  },
  "nested_elastic_net": {
    "alpha": 0.65,
    "lambda_grid": [
      0.25,
      0.5,
      1.0,
      2.0,
      4.0,
      8.0
    ],
    "outer_folds": [
      {
        "held_out_division": "New England",
        "held_out_count": 5,
        "chosen_lambda": 0.5,
        "nonzero_feature_count": 9,
        "outer_rmse": 24.935,
        "inner_grid": [
          {
            "lambda": 0.25,
            "inner_grouped_rmse": 18.3314
          },
          {
            "lambda": 0.5,
            "inner_grouped_rmse": 18.1345
          },
          {
            "lambda": 1.0,
            "inner_grouped_rmse": 18.5661
          },
          {
            "lambda": 2.0,
            "inner_grouped_rmse": 20.3692
          },
          {
            "lambda": 4.0,
            "inner_grouped_rmse": 24.0923
          },
          {
            "lambda": 8.0,
            "inner_grouped_rmse": 30.5218
          }
        ]
      },
      {
        "held_out_division": "Middle Atlantic",
        "held_out_count": 3,
        "chosen_lambda": 0.25,
        "nonzero_feature_count": 12,
        "outer_rmse": 16.7364,
        "inner_grid": [
          {
            "lambda": 0.25,
            "inner_grouped_rmse": 19.2815
          },
          {
            "lambda": 0.5,
            "inner_grouped_rmse": 19.3112
          },
          {
            "lambda": 1.0,
            "inner_grouped_rmse": 19.8609
          },
          {
            "lambda": 2.0,
            "inner_grouped_rmse": 21.5456
          },
          {
            "lambda": 4.0,
            "inner_grouped_rmse": 24.9429
          },
          {
            "lambda": 8.0,
            "inner_grouped_rmse": 31.0618
          }
        ]
      },
      {
        "held_out_division": "East North Central",
        "held_out_count": 4,
        "chosen_lambda": 0.25,
        "nonzero_feature_count": 10,
        "outer_rmse": 15.3763,
        "inner_grid": [
          {
            "lambda": 0.25,
            "inner_grouped_rmse": 19.4274
          },
          {
            "lambda": 0.5,
            "inner_grouped_rmse": 19.488
          },
          {
            "lambda": 1.0,
            "inner_grouped_rmse": 20.1498
          },
          {
            "lambda": 2.0,
            "inner_grouped_rmse": 21.8233
          },
          {
            "lambda": 4.0,
            "inner_grouped_rmse": 25.2059
          },
          {
            "lambda": 8.0,
            "inner_grouped_rmse": 31.2174
          }
        ]
      },
      {
        "held_out_division": "West North Central",
        "held_out_count": 7,
        "chosen_lambda": 0.25,
        "nonzero_feature_count": 13,
        "outer_rmse": 17.4878,
        "inner_grid": [
          {
            "lambda": 0.25,
            "inner_grouped_rmse": 19.3258
          },
          {
            "lambda": 0.5,
            "inner_grouped_rmse": 19.4995
          },
          {
            "lambda": 1.0,
            "inner_grouped_rmse": 20.2737
          },
          {
            "lambda": 2.0,
            "inner_grouped_rmse": 22.094
          },
          {
            "lambda": 4.0,
            "inner_grouped_rmse": 25.9555
          },
          {
            "lambda": 8.0,
            "inner_grouped_rmse": 32.3526
          }
        ]
      },
      {
        "held_out_division": "South Atlantic",
        "held_out_count": 7,
        "chosen_lambda": 1.0,
        "nonzero_feature_count": 11,
        "outer_rmse": 20.8584,
        "inner_grid": [
          {
            "lambda": 0.25,
            "inner_grouped_rmse": 20.7454
          },
          {
            "lambda": 0.5,
            "inner_grouped_rmse": 20.2896
          },
          {
            "lambda": 1.0,
            "inner_grouped_rmse": 20.2454
          },
          {
            "lambda": 2.0,
            "inner_grouped_rmse": 21.5355
          },
          {
            "lambda": 4.0,
            "inner_grouped_rmse": 24.5295
          },
          {
            "lambda": 8.0,
            "inner_grouped_rmse": 29.9442
          }
        ]
      },
      {
        "held_out_division": "East South Central",
        "held_out_count": 2,
        "chosen_lambda": 0.5,
        "nonzero_feature_count": 10,
        "outer_rmse": 22.3734,
        "inner_grid": [
          {
            "lambda": 0.25,
            "inner_grouped_rmse": 18.7458
          },
          {
            "lambda": 0.5,
            "inner_grouped_rmse": 18.6749
          },
          {
            "lambda": 1.0,
            "inner_grouped_rmse": 19.1647
          },
          {
            "lambda": 2.0,
            "inner_grouped_rmse": 20.8882
          },
          {
            "lambda": 4.0,
            "inner_grouped_rmse": 24.4443
          },
          {
            "lambda": 8.0,
            "inner_grouped_rmse": 30.7524
          }
        ]
      },
      {
        "held_out_division": "West South Central",
        "held_out_count": 3,
        "chosen_lambda": 0.25,
        "nonzero_feature_count": 9,
        "outer_rmse": 10.666,
        "inner_grid": [
          {
            "lambda": 0.25,
            "inner_grouped_rmse": 19.4984
          },
          {
            "lambda": 0.5,
            "inner_grouped_rmse": 19.6218
          },
          {
            "lambda": 1.0,
            "inner_grouped_rmse": 20.2012
          },
          {
            "lambda": 2.0,
            "inner_grouped_rmse": 21.8571
          },
          {
            "lambda": 4.0,
            "inner_grouped_rmse": 25.0195
          },
          {
            "lambda": 8.0,
            "inner_grouped_rmse": 30.6451
          }
        ]
      },
      {
        "held_out_division": "Mountain",
        "held_out_count": 7,
        "chosen_lambda": 0.25,
        "nonzero_feature_count": 12,
        "outer_rmse": 21.1631,
        "inner_grid": [
          {
            "lambda": 0.25,
            "inner_grouped_rmse": 18.6073
          },
          {
            "lambda": 0.5,
            "inner_grouped_rmse": 18.6608
          },
          {
            "lambda": 1.0,
            "inner_grouped_rmse": 19.2715
          },
          {
            "lambda": 2.0,
            "inner_grouped_rmse": 20.8066
          },
          {
            "lambda": 4.0,
            "inner_grouped_rmse": 24.1327
          },
          {
            "lambda": 8.0,
            "inner_grouped_rmse": 30.1811
          }
        ]
      },
      {
        "held_out_division": "Pacific",
        "held_out_count": 5,
        "chosen_lambda": 0.5,
        "nonzero_feature_count": 12,
        "outer_rmse": 18.3723,
        "inner_grid": [
          {
            "lambda": 0.25,
            "inner_grouped_rmse": 18.9195
          },
          {
            "lambda": 0.5,
            "inner_grouped_rmse": 18.9058
          },
          {
            "lambda": 1.0,
            "inner_grouped_rmse": 19.3806
          },
          {
            "lambda": 2.0,
            "inner_grouped_rmse": 21.1486
          },
          {
            "lambda": 4.0,
            "inner_grouped_rmse": 24.8598
          },
          {
            "lambda": 8.0,
            "inner_grouped_rmse": 31.2727
          }
        ]
      }
    ],
    "pooled_oof_rmse": 19.4377,
    "pooled_oof_mae": 16.4148,
    "pooled_oof_r_squared": 0.9282
  },
  "wild_cluster_bootstrap": {
    "seed": 20220715,
    "bootstrap_count": 1999,
    "observed_absolute_cr1_t": 3.0367,
    "exceedance_count": 10,
    "plus_one_p_value": 0.0055,
    "absolute_t_q90": 1.8023,
    "absolute_t_q95": 2.1022,
    "absolute_t_q99": 2.7223,
    "final_prng_state": 3524156134
  },
  "grouped_conformal": {
    "nominal_coverage": 0.9,
    "division_results": [
      {
        "held_out_division": "New England",
        "calibration_count": 38,
        "finite_sample_rank": 36,
        "interval_radius": 28.0142,
        "held_out_count": 5,
        "covered_count": 3,
        "coverage_fraction": 0.6,
        "mean_interval_width": 56.0284,
        "maximum_excess": 10.6543
      },
      {
        "held_out_division": "Middle Atlantic",
        "calibration_count": 40,
        "finite_sample_rank": 37,
        "interval_radius": 34.2505,
        "held_out_count": 3,
        "covered_count": 3,
        "coverage_fraction": 1.0,
        "mean_interval_width": 68.5009,
        "maximum_excess": 0
      },
      {
        "held_out_division": "East North Central",
        "calibration_count": 39,
        "finite_sample_rank": 36,
        "interval_radius": 34.7628,
        "held_out_count": 4,
        "covered_count": 4,
        "coverage_fraction": 1.0,
        "mean_interval_width": 69.5255,
        "maximum_excess": 0
      },
      {
        "held_out_division": "West North Central",
        "calibration_count": 36,
        "finite_sample_rank": 34,
        "interval_radius": 37.0318,
        "held_out_count": 7,
        "covered_count": 7,
        "coverage_fraction": 1.0,
        "mean_interval_width": 74.0636,
        "maximum_excess": 0
      },
      {
        "held_out_division": "South Atlantic",
        "calibration_count": 36,
        "finite_sample_rank": 34,
        "interval_radius": 37.8275,
        "held_out_count": 7,
        "covered_count": 7,
        "coverage_fraction": 1.0,
        "mean_interval_width": 75.655,
        "maximum_excess": 0
      },
      {
        "held_out_division": "East South Central",
        "calibration_count": 41,
        "finite_sample_rank": 38,
        "interval_radius": 34.0158,
        "held_out_count": 2,
        "covered_count": 2,
        "coverage_fraction": 1.0,
        "mean_interval_width": 68.0316,
        "maximum_excess": 0
      },
      {
        "held_out_division": "West South Central",
        "calibration_count": 40,
        "finite_sample_rank": 37,
        "interval_radius": 36.3706,
        "held_out_count": 3,
        "covered_count": 3,
        "coverage_fraction": 1.0,
        "mean_interval_width": 72.7413,
        "maximum_excess": 0
      },
      {
        "held_out_division": "Mountain",
        "calibration_count": 36,
        "finite_sample_rank": 34,
        "interval_radius": 31.7406,
        "held_out_count": 7,
        "covered_count": 6,
        "coverage_fraction": 0.8571,
        "mean_interval_width": 63.4813,
        "maximum_excess": 7.084
      },
      {
        "held_out_division": "Pacific",
        "calibration_count": 38,
        "finite_sample_rank": 36,
        "interval_radius": 34.8709,
        "held_out_count": 5,
        "covered_count": 5,
        "coverage_fraction": 1.0,
        "mean_interval_width": 69.7418,
        "maximum_excess": 0
      }
    ],
    "pooled_covered_count": 40,
    "pooled_state_count": 43,
    "pooled_coverage_fraction": 0.9302,
    "held_out_weighted_mean_interval_width": 68.8173,
    "worst_coverage_division": "New England"
  },
  "trajectory_pca_clustering": {
    "trajectory_feature_count": 20,
    "first_three_explained_variance_ratios": [
      0.8406,
      0.1059,
      0.0092
    ],
    "initial_centroid_state_codes": [
      "AK",
      "RI",
      "VA"
    ],
    "lloyd_update_count": 2,
    "cluster_centroids_pc1_pc2_pc3": [
      {
        "cluster_id": 1,
        "pc1": 5.7184,
        "pc2": -0.4341,
        "pc3": -0.2559
      },
      {
        "cluster_id": 2,
        "pc1": -4.7351,
        "pc2": -0.508,
        "pc3": -0.1433
      },
      {
        "cluster_id": 3,
        "pc1": -0.1652,
        "pc2": 0.5464,
        "pc3": 0.226
      }
    ],
    "state_assignments": [
      {
        "state_code": "AK",
        "cluster_id": 1,
        "pc1": 6.2366,
        "pc2": 0.3177,
        "pc3": -0.0998
      },
      {
        "state_code": "AR",
        "cluster_id": 1,
        "pc1": 4.5739,
        "pc2": 2.8744,
        "pc3": -0.3007
      },
      {
        "state_code": "AZ",
        "cluster_id": 2,
        "pc1": -3.9836,
        "pc2": -2.4989,
        "pc3": -0.1745
      },
      {
        "state_code": "CA",
        "cluster_id": 3,
        "pc1": -0.3322,
        "pc2": -0.7805,
        "pc3": 0.3225
      },
      {
        "state_code": "CO",
        "cluster_id": 2,
        "pc1": -4.0048,
        "pc2": -0.9891,
        "pc3": 0.0987
      },
      {
        "state_code": "DC",
        "cluster_id": 1,
        "pc1": 7.7079,
        "pc2": 0.7504,
        "pc3": -0.5525
      },
      {
        "state_code": "IL",
        "cluster_id": 3,
        "pc1": 0.7673,
        "pc2": 0.6013,
        "pc3": 0.8693
      },
      {
        "state_code": "IN",
        "cluster_id": 2,
        "pc1": -5.9346,
        "pc2": -0.0582,
        "pc3": 0.0788
      },
      {
        "state_code": "LA",
        "cluster_id": 3,
        "pc1": -2.4072,
        "pc2": 0.6532,
        "pc3": -0.638
      },
      {
        "state_code": "MA",
        "cluster_id": 3,
        "pc1": -0.7704,
        "pc2": 0.9664,
        "pc3": 0.6978
      },
      {
        "state_code": "MD",
        "cluster_id": 1,
        "pc1": 7.1667,
        "pc2": -1.8637,
        "pc3": 0.1241
      },
      {
        "state_code": "ME",
        "cluster_id": 2,
        "pc1": -3.2591,
        "pc2": 0.1249,
        "pc3": 0.1183
      },
      {
        "state_code": "MI",
        "cluster_id": 2,
        "pc1": -4.1912,
        "pc2": 1.5339,
        "pc3": -0.4144
      },
      {
        "state_code": "MN",
        "cluster_id": 3,
        "pc1": 0.5942,
        "pc2": 0.1131,
        "pc3": 0.4672
      },
      {
        "state_code": "MO",
        "cluster_id": 1,
        "pc1": 5.9337,
        "pc2": -0.7587,
        "pc3": -0.3165
      },
      {
        "state_code": "NC",
        "cluster_id": 1,
        "pc1": 3.9084,
        "pc2": -1.576,
        "pc3": 0.0281
      },
      {
        "state_code": "ND",
        "cluster_id": 1,
        "pc1": 4.5018,
        "pc2": -2.7826,
        "pc3": -0.674
      },
      {
        "state_code": "NE",
        "cluster_id": 3,
        "pc1": -1.5162,
        "pc2": -0.8247,
        "pc3": 0.179
      },
      {
        "state_code": "NJ",
        "cluster_id": 3,
        "pc1": 0.9681,
        "pc2": 0.187,
        "pc3": 0.4341
      },
      {
        "state_code": "NM",
        "cluster_id": 3,
        "pc1": 2.2252,
        "pc2": 1.669,
        "pc3": 0.1333
      },
      {
        "state_code": "NV",
        "cluster_id": 2,
        "pc1": -3.4027,
        "pc2": -0.6179,
        "pc3": 0.0078
      },
      {
        "state_code": "OK",
        "cluster_id": 2,
        "pc1": -5.6231,
        "pc2": -2.1618,
        "pc3": 0.3032
      },
      {
        "state_code": "OR",
        "cluster_id": 3,
        "pc1": -1.0229,
        "pc2": 2.1616,
        "pc3": 0.0794
      },
      {
        "state_code": "RI",
        "cluster_id": 2,
        "pc1": -7.482,
        "pc2": 0.603,
        "pc3": -1.164
      },
      {
        "state_code": "SD",
        "cluster_id": 3,
        "pc1": -0.5012,
        "pc2": 0.0854,
        "pc3": 0.2519
      },
      {
        "state_code": "UT",
        "cluster_id": 3,
        "pc1": -0.1588,
        "pc2": 1.2706,
        "pc3": -0.0893
      },
      {
        "state_code": "VA",
        "cluster_id": 3,
        "pc1": -0.7569,
        "pc2": 2.278,
        "pc3": 0.1678
      },
      {
        "state_code": "WA",
        "cluster_id": 3,
        "pc1": 0.7633,
        "pc2": -1.2777,
        "pc3": 0.0623
      }
    ],
    "leave_one_year_out_stability": [
      {
        "omitted_year": 2020,
        "adjusted_rand_index": 1.0,
        "aligned_assignment_changes": 0
      },
      {
        "omitted_year": 2021,
        "adjusted_rand_index": 1.0,
        "aligned_assignment_changes": 0
      },
      {
        "omitted_year": 2022,
        "adjusted_rand_index": 1.0,
        "aligned_assignment_changes": 0
      },
      {
        "omitted_year": 2023,
        "adjusted_rand_index": 0.8805,
        "aligned_assignment_changes": 1
      },
      {
        "omitted_year": 2024,
        "adjusted_rand_index": 1.0,
        "aligned_assignment_changes": 0
      }
    ],
    "minimum_adjusted_rand_index": 0.8805
  },
  "exhaustive_source_perturbation": {
    "ordered_rollup_state_codes": [
      "MD",
      "AZ",
      "WV",
      "RI",
      "ND",
      "NM",
      "ID",
      "NC",
      "VA"
    ],
    "scenario_count": 512,
    "by_replacement_count": [
      {
        "replacement_count": 0,
        "scenario_count": 1,
        "minimum_coefficient": 13.5917,
        "maximum_coefficient": 13.5917,
        "minimum_hc3_p_value": 0.0,
        "maximum_hc3_p_value": 0.0,
        "mean_absolute_percent_shift": 0.0
      },
      {
        "replacement_count": 1,
        "scenario_count": 9,
        "minimum_coefficient": 13.1211,
        "maximum_coefficient": 14.2173,
        "minimum_hc3_p_value": 0.0,
        "maximum_hc3_p_value": 0.0,
        "mean_absolute_percent_shift": 1.6932
      },
      {
        "replacement_count": 2,
        "scenario_count": 36,
        "minimum_coefficient": 12.7784,
        "maximum_coefficient": 14.23,
        "minimum_hc3_p_value": 0.0,
        "maximum_hc3_p_value": 0.0,
        "mean_absolute_percent_shift": 2.7597
      },
      {
        "replacement_count": 3,
        "scenario_count": 84,
        "minimum_coefficient": 12.4701,
        "maximum_coefficient": 14.2348,
        "minimum_hc3_p_value": 0.0,
        "maximum_hc3_p_value": 0.0,
        "mean_absolute_percent_shift": 3.3336
      },
      {
        "replacement_count": 4,
        "scenario_count": 126,
        "minimum_coefficient": 12.2837,
        "maximum_coefficient": 14.2061,
        "minimum_hc3_p_value": 0.0,
        "maximum_hc3_p_value": 0.0,
        "mean_absolute_percent_shift": 3.5986
      },
      {
        "replacement_count": 5,
        "scenario_count": 126,
        "minimum_coefficient": 12.1923,
        "maximum_coefficient": 14.1147,
        "minimum_hc3_p_value": 0.0,
        "maximum_hc3_p_value": 0.0,
        "mean_absolute_percent_shift": 3.774
      },
      {
        "replacement_count": 6,
        "scenario_count": 84,
        "minimum_coefficient": 12.1636,
        "maximum_coefficient": 13.9283,
        "minimum_hc3_p_value": 0.0,
        "maximum_hc3_p_value": 0.0,
        "mean_absolute_percent_shift": 4.0443
      },
      {
        "replacement_count": 7,
        "scenario_count": 36,
        "minimum_coefficient": 12.1684,
        "maximum_coefficient": 13.62,
        "minimum_hc3_p_value": 0.0,
        "maximum_hc3_p_value": 0.0,
        "mean_absolute_percent_shift": 4.5035
      },
      {
        "replacement_count": 8,
        "scenario_count": 9,
        "minimum_coefficient": 12.1811,
        "maximum_coefficient": 13.2773,
        "minimum_hc3_p_value": 0.0,
        "maximum_hc3_p_value": 0.0,
        "mean_absolute_percent_shift": 5.1336
      },
      {
        "replacement_count": 9,
        "scenario_count": 1,
        "minimum_coefficient": 12.8067,
        "maximum_coefficient": 12.8067,
        "minimum_hc3_p_value": 0.0,
        "maximum_hc3_p_value": 0.0,
        "mean_absolute_percent_shift": 5.7753
      }
    ],
    "stable_scenario_count": 512,
    "maximum_shift_bitmask": 183,
    "maximum_shift_replaced_state_codes": [
      "MD",
      "AZ",
      "WV",
      "ND",
      "NM",
      "NC"
    ],
    "maximum_shift_coefficient": 12.1636,
    "maximum_shift_hc3_p_value": 0.0,
    "maximum_absolute_percent_shift": 10.5069,
    "ordered_shapley_effects": [
      {
        "state_code": "MD",
        "signed_shapley_coefficient_change": -0.1864
      },
      {
        "state_code": "AZ",
        "signed_shapley_coefficient_change": -0.4706
      },
      {
        "state_code": "WV",
        "signed_shapley_coefficient_change": -0.3083
      },
      {
        "state_code": "RI",
        "signed_shapley_coefficient_change": 0.6256
      },
      {
        "state_code": "ND",
        "signed_shapley_coefficient_change": -0.0287
      },
      {
        "state_code": "NM",
        "signed_shapley_coefficient_change": -0.3427
      },
      {
        "state_code": "ID",
        "signed_shapley_coefficient_change": 0.0127
      },
      {
        "state_code": "NC",
        "signed_shapley_coefficient_change": -0.0913
      },
      {
        "state_code": "VA",
        "signed_shapley_coefficient_change": 0.0048
      }
    ],
    "shapley_sum": -0.785,
    "all_rollup_minus_all_direct_coefficient": -0.785
  },
  "decision_audit": {
    "cluster_jackknife_supported": false,
    "nested_prediction_stable": true,
    "wild_bootstrap_supported": true,
    "grouped_conformal_supported": true,
    "trajectory_stable": true,
    "source_exhaustive_stable": true,
    "first_failed_module": "CLUSTER_JACKKNIFE",
    "conclusion": "NOT_ROBUST_AT_CLUSTER_JACKKNIFE"
  }
}''')
MISSING=object()

def empty(msg):
    return {"score":0.0,"total_raw_weight":TOTAL,"points":[
      {"point_id":f"SP{i:03d}","goal":g,"raw_weight":w,
       "normalized_maximum":round(w/TOTAL,10),"earned_fraction":0.0,
       "earned_normalized_score":0.0,"subchecks":[]}
      for i,(g,w) in enumerate(zip(GOALS,WEIGHTS),1)],"diagnostics":[msg]}

if len(sys.argv)!=2:
    print(json.dumps(empty("Usage: eval.sh <prediction.json>"),indent=2)); raise SystemExit(0)
try:
    with open(sys.argv[1],encoding="utf-8") as f: pred=json.load(f)
    if not isinstance(pred,dict): raise ValueError("prediction root must be an object")
except Exception as exc:
    print(json.dumps(empty(f"Prediction parse failure: {exc}"),indent=2)); raise SystemExit(0)

def at(root,path):
    cur=root
    for key in path.split("."):
        if not isinstance(cur,dict) or key not in cur:return MISSING
        cur=cur[key]
    return cur

def sx(v,e):
    return 1.0 if v==e and type(v) is type(e) else 0.0

def sn(v,e):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):return 0.0
    return 1.0 if abs(float(v)-float(e))<=0.00011 else 0.0

def scalar(path):
    v=at(pred,path); e=at(EXPECTED,path)
    return sn(v,e) if isinstance(e,float) else sx(v,e)

def equal_group(paths):
    return sum(scalar(path) for path in paths)/len(paths) if paths else 0.0

def value_list_integrity(path):
    """Ordered-list integrity: content accuracy plus an explicit all-elements checkpoint."""
    v=at(pred,path); e=at(EXPECTED,path)
    if not isinstance(v,list) or not e:return 0.0
    scores=[]
    for i,ev in enumerate(e):
        if i>=len(v):scores.append(0.0)
        else:scores.append(sn(v[i],ev) if isinstance(ev,float) else sx(v[i],ev))
    positional=sum(scores)/len(scores)
    length_integrity=min(1.0,len(e)/max(len(v),1)) if len(v) else 0.0
    exact_checkpoint=1.0 if len(v)==len(e) and all(x==1.0 for x in scores) else 0.0
    return length_integrity*(0.75*positional+0.25*exact_checkpoint)

def table_integrity(path,key_fields,value_fields):
    """Score order, cells, complete rows, and the weakest required field separately.

    The row and weakest-field terms prevent a long table from hiding a systematically
    wrong diagnostic column while retaining continuous partial credit.
    """
    v=at(pred,path); e=at(EXPECTED,path)
    fields=key_fields+value_fields
    if not isinstance(v,list) or not e or not fields:return 0.0
    field_scores={field:[] for field in fields}
    row_scores=[]
    key_rows=[]
    for i,ee in enumerate(e):
        vv=v[i] if i<len(v) and isinstance(v[i],dict) else None
        cells=[]
        keys=[]
        for field in fields:
            ev=ee[field]; pv=vv.get(field,MISSING) if vv is not None else MISSING
            sc=sn(pv,ev) if isinstance(ev,float) else sx(pv,ev)
            field_scores[field].append(sc); cells.append(sc)
            if field in key_fields:keys.append(sc)
        row_scores.append(1.0 if cells and all(sc==1.0 for sc in cells) else 0.0)
        key_rows.append(1.0 if keys and all(sc==1.0 for sc in keys) else 0.0)
    length_integrity=min(1.0,len(e)/max(len(v),1)) if len(v) else 0.0
    key_order=sum(key_rows)/len(key_rows) if key_rows else length_integrity
    cell_accuracy=sum(sum(xs) for xs in field_scores.values())/(len(e)*len(fields))
    complete_rows=sum(row_scores)/len(row_scores)
    weakest_field=min(sum(xs)/len(xs) for xs in field_scores.values())
    base=.20*key_order+.30*cell_accuracy+.25*complete_rows+.25*weakest_field
    if len(v)!=len(e):base=min(base,.70)
    if key_order<1.0:base=min(base,.85)
    return length_integrity*base

def nested_inner_grid_integrity():
    path="nested_elastic_net.outer_folds"; v=at(pred,path); e=at(EXPECTED,path)
    if not isinstance(v,list) or not e:return 0.0
    fold_scores=[]; fold_exact=[]; outer_keys=[]
    for i,ee in enumerate(e):
        vv=v[i] if i<len(v) and isinstance(v[i],dict) else None
        outer_keys.append(sx(vv.get("held_out_division",MISSING),ee["held_out_division"]) if vv else 0.0)
        vg=vv.get("inner_grid",MISSING) if vv else MISSING; eg=ee["inner_grid"]
        if not isinstance(vg,list):
            fold_scores.append(0.0); fold_exact.append(0.0); continue
        fields=["lambda","inner_grouped_rmse"]
        by_field={f:[] for f in fields}; rows=[]
        for j,ge in enumerate(eg):
            gv=vg[j] if j<len(vg) and isinstance(vg[j],dict) else None
            cells=[]
            for f in fields:
                ev=ge[f]; pv=gv.get(f,MISSING) if gv else MISSING
                sc=sn(pv,ev) if isinstance(ev,float) else sx(pv,ev)
                by_field[f].append(sc); cells.append(sc)
            rows.append(1.0 if all(sc==1.0 for sc in cells) else 0.0)
        cell=sum(sum(xs) for xs in by_field.values())/(len(eg)*len(fields))
        complete=sum(rows)/len(rows); weakest=min(sum(xs)/len(xs) for xs in by_field.values())
        length=min(1.0,len(eg)/max(len(vg),1)) if len(vg) else 0.0
        fs=length*(.45*cell+.30*complete+.25*weakest)
        if len(vg)!=len(eg):fs=min(fs,.70)
        fold_scores.append(fs); fold_exact.append(1.0 if fs==1.0 else 0.0)
    length=min(1.0,len(e)/max(len(v),1)) if len(v) else 0.0
    order=sum(outer_keys)/len(outer_keys)
    mean=sum(fold_scores)/len(fold_scores); exact=sum(fold_exact)/len(fold_exact); weakest=min(fold_scores)
    base=.15*order+.40*mean+.20*exact+.25*weakest
    if len(v)!=len(e):base=min(base,.70)
    if order<1.0:base=min(base,.85)
    return length*base

def integrity_level(score):
    if score==1.0:return "complete"
    if score>=.95:return "near_complete"
    if score>=.75:return "coherent"
    if score>=.40:return "partial"
    return "deficient"

def critical_cap(score):
    # A critical module that is incomplete limits the point without making it binary.
    if score==1.0:return 1.0
    if score>=.95:return .98
    if score>=.75:return .90
    if score>=.40:return .75
    return .55

points=[]
def add(pid,goal,w,modules):
    """modules are (semantic name, score, share, is_critical)."""
    total=sum(share for _,_,share,_ in modules)
    uncapped=sum(score*share for _,score,share,_ in modules)/total if total else 0.0
    cap=min([critical_cap(score) for _,score,_,critical in modules if critical] or [1.0])
    frac=min(uncapped,cap)
    points.append({"point_id":pid,"goal":goal,"raw_weight":w,
      "normalized_maximum":round(w/TOTAL,10),"earned_fraction":round(frac,10),
      "earned_normalized_score":round(frac*w/TOTAL,10),
      "uncapped_fraction":round(uncapped,10),"critical_integrity_cap":round(cap,10),
      "subchecks":[{"name":n,"within_point_share":round(s/total,10),
                    "earned_fraction":round(sc,10),"integrity_level":integrity_level(sc),
                    "critical":critical,"passed":sc==1.0}
                   for n,sc,s,critical in modules]})

add("SP001",GOALS[0],1,[
 ("request_and_universe_registration",equal_group(["request_id","release_and_cohort.reference_year","release_and_cohort.jurisdiction_universe_count"]),.15,False),
 ("annual_complete_case_integrity",table_integrity("release_and_cohort.yearly_complete_case_counts",["year"],["count"]),.20,False),
 ("primary_cohort_integrity",.45*scalar("release_and_cohort.primary_complete_case_count")+.55*value_list_integrity("release_and_cohort.primary_excluded_state_codes"),.25,False),
 ("balanced_cohort_integrity",.25*scalar("release_and_cohort.balanced_state_count")+.75*value_list_integrity("release_and_cohort.balanced_state_codes"),.40,True),
])
add("SP002",GOALS[1],3,[
 ("full_panel_fit",scalar("cluster_jackknife.full_within_smoking_coefficient"),.15,False),
 ("delete_one_table_integrity",table_integrity("cluster_jackknife.delete_one_results",["state_code"],["coefficient","absolute_percent_change"]),.35,True),
 ("bias_corrected_inference_summary",equal_group(["cluster_jackknife.mean_delete_one_coefficient","cluster_jackknife.bias_corrected_coefficient","cluster_jackknife.jackknife_standard_error","cluster_jackknife.jackknife_t_statistic","cluster_jackknife.jackknife_t_p_value"]),.35,True),
 ("influence_checkpoint",equal_group(["cluster_jackknife.maximum_delete_one_absolute_percent_change","cluster_jackknife.most_influential_state_code"]),.15,True),
])
add("SP003",GOALS[2],3,[
 ("registered_penalty",.40*scalar("nested_elastic_net.alpha")+.60*value_list_integrity("nested_elastic_net.lambda_grid"),.10,False),
 ("outer_selection_integrity",table_integrity("nested_elastic_net.outer_folds",["held_out_division"],["held_out_count","chosen_lambda","nonzero_feature_count","outer_rmse"]),.25,True),
 ("inner_grid_integrity",nested_inner_grid_integrity(),.45,True),
 ("pooled_prediction_summary",equal_group(["nested_elastic_net.pooled_oof_rmse","nested_elastic_net.pooled_oof_mae","nested_elastic_net.pooled_oof_r_squared"]),.20,True),
])
add("SP004",GOALS[3],3,[
 ("stream_registration",equal_group(["wild_cluster_bootstrap.seed","wild_cluster_bootstrap.bootstrap_count"]),.10,False),
 ("observed_t_checkpoint",scalar("wild_cluster_bootstrap.observed_absolute_cr1_t"),.15,True),
 ("bootstrap_test_summary",equal_group(["wild_cluster_bootstrap.exceedance_count","wild_cluster_bootstrap.plus_one_p_value"]),.30,True),
 ("distribution_quantiles",equal_group(["wild_cluster_bootstrap.absolute_t_q90","wild_cluster_bootstrap.absolute_t_q95","wild_cluster_bootstrap.absolute_t_q99"]),.25,True),
 ("terminal_prng_checkpoint",scalar("wild_cluster_bootstrap.final_prng_state"),.20,True),
])
add("SP005",GOALS[4],3,[
 ("coverage_registration",scalar("grouped_conformal.nominal_coverage"),.05,False),
 ("division_order_and_calibration_integrity",table_integrity("grouped_conformal.division_results",["held_out_division"],["calibration_count","finite_sample_rank"]),.25,True),
 ("division_interval_integrity",table_integrity("grouped_conformal.division_results",["held_out_division"],["interval_radius","held_out_count","mean_interval_width"]),.25,True),
 ("division_coverage_integrity",table_integrity("grouped_conformal.division_results",["held_out_division"],["covered_count","coverage_fraction","maximum_excess"]),.25,True),
 ("pooled_coverage_summary",equal_group(["grouped_conformal.pooled_covered_count","grouped_conformal.pooled_state_count","grouped_conformal.pooled_coverage_fraction","grouped_conformal.held_out_weighted_mean_interval_width","grouped_conformal.worst_coverage_division"]),.20,True),
])
add("SP006",GOALS[5],3,[
 ("trajectory_registration",.35*scalar("trajectory_pca_clustering.trajectory_feature_count")+.65*value_list_integrity("trajectory_pca_clustering.first_three_explained_variance_ratios"),.10,False),
 ("initialization_checkpoint",.60*value_list_integrity("trajectory_pca_clustering.initial_centroid_state_codes")+.40*scalar("trajectory_pca_clustering.lloyd_update_count"),.10,True),
 ("centroid_integrity",table_integrity("trajectory_pca_clustering.cluster_centroids_pc1_pc2_pc3",["cluster_id"],["pc1","pc2","pc3"]),.15,True),
 ("state_assignment_integrity",table_integrity("trajectory_pca_clustering.state_assignments",["state_code"],["cluster_id","pc1","pc2","pc3"]),.40,True),
 ("leave_one_year_stability_integrity",.80*table_integrity("trajectory_pca_clustering.leave_one_year_out_stability",["omitted_year"],["adjusted_rand_index","aligned_assignment_changes"])+.20*scalar("trajectory_pca_clustering.minimum_adjusted_rand_index"),.25,True),
])
add("SP007",GOALS[6],3,[
 ("scenario_registration_and_order",.65*value_list_integrity("exhaustive_source_perturbation.ordered_rollup_state_codes")+.35*scalar("exhaustive_source_perturbation.scenario_count"),.12,True),
 ("replacement_count_integrity",table_integrity("exhaustive_source_perturbation.by_replacement_count",["replacement_count"],["scenario_count","minimum_coefficient","maximum_coefficient","minimum_hc3_p_value","maximum_hc3_p_value","mean_absolute_percent_shift"]),.30,True),
 ("stability_summary",scalar("exhaustive_source_perturbation.stable_scenario_count"),.10,True),
 ("maximum_scenario_checkpoint",.18*scalar("exhaustive_source_perturbation.maximum_shift_bitmask")+.20*value_list_integrity("exhaustive_source_perturbation.maximum_shift_replaced_state_codes")+.62*equal_group(["exhaustive_source_perturbation.maximum_shift_coefficient","exhaustive_source_perturbation.maximum_shift_hc3_p_value","exhaustive_source_perturbation.maximum_absolute_percent_shift"]),.25,True),
 ("shapley_integrity_and_efficiency",.60*table_integrity("exhaustive_source_perturbation.ordered_shapley_effects",["state_code"],["signed_shapley_coefficient_change"])+.40*equal_group(["exhaustive_source_perturbation.shapley_sum","exhaustive_source_perturbation.all_rollup_minus_all_direct_coefficient"]),.23,True),
])
flag_fields=["cluster_jackknife_supported","nested_prediction_stable","wild_bootstrap_supported","grouped_conformal_supported","trajectory_stable","source_exhaustive_stable"]
add("SP008",GOALS[7],2,[
 ("registered_flags",sum(scalar("decision_audit."+x) for x in flag_fields)/6,.55,True),
 ("precedence_checkpoint",scalar("decision_audit.first_failed_module"),.20,True),
 ("conclusion_checkpoint",scalar("decision_audit.conclusion"),.25,True),
])
required_subchecks={
 "SP001":{"request_and_universe_registration","annual_complete_case_integrity","primary_cohort_integrity","balanced_cohort_integrity"},
 "SP002":{"bias_corrected_inference_summary"},
 "SP003":{"pooled_prediction_summary"},
 "SP004":{"bootstrap_test_summary"},
 "SP005":{"pooled_coverage_summary"},
 "SP006":{"initialization_checkpoint","centroid_integrity","state_assignment_integrity","leave_one_year_stability_integrity"},
 "SP007":{"stability_summary"},
 "SP008":{"conclusion_checkpoint"},
}
for point in points:
    by_name={item["name"]:item for item in point["subchecks"]}
    required=required_subchecks[point["point_id"]]
    passed=all(by_name.get(name,{}).get("passed") is True for name in required)
    point["diagnostic_fraction"]=point["earned_fraction"]
    point["point_pass"]=passed
    point["earned_fraction"]=1.0 if passed else 0.0
    point["earned_normalized_score"]=round(point["normalized_maximum"] if passed else 0.0,10)
    point["required_subchecks"]=sorted(required)
score=sum(p["raw_weight"]*p["earned_fraction"] for p in points)/TOTAL
print(json.dumps({"score":round(max(0,min(1,score)),10),"total_raw_weight":TOTAL,"points":points,"diagnostics":[]},indent=2))
PY
