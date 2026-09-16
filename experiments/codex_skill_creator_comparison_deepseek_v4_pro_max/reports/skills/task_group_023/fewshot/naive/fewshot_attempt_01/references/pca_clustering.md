# PCA and Trajectory Clustering

## PCA via Covariance Matrix

### Data Preparation
1. Build columns in declared feature order: variable-major within each time period, then periods in chronological order.
2. Standardize each column: z_j = (x_j - mean(x_j)) / sd(x_j) where sd is the sample standard deviation (ddof=1, dividing by n-1).
3. Z is n x p, centered and scaled.

### Eigendecomposition by Symmetric Jacobi
1. Initialize eigenvectors V = I_p.
2. Form covariance matrix C = Z'Z / (n-1).
3. Repeat until max absolute off-diagonal < tolerance (e.g. 1e-10) or step cap:
   a. Find (p, q) with p < q maximizing |C[p,q]|. Tie: smaller p, then smaller q.
   b. Compute rotation: tau = (C[q,q] - C[p,p]) / (2 * C[p,q])
      t = sign_nonnegative(tau) / (|tau| + sqrt(1 + tau^2))
      c = 1 / sqrt(1 + t^2), s = t * c
   c. Apply rotation to C: update rows and columns p and q.
   d. Apply rotation to V: update columns p and q.
4. Eigenvalues = diag(C) after convergence.

### Ordering and Orientation
1. Sort eigenvalues descending. For ties, use the original diagonal index (smaller index first).
2. Sort eigenvectors to match eigenvalue order.
3. For each retained eigenvector, flip sign so its earliest maximum-absolute entry is positive. "Earliest" means smallest index among entries achieving the maximum absolute value.

### Scores and Explained Variance
1. Scores = Z * loadings (the oriented eigenvectors for retained components).
2. explained_ratio[j] = eigenvalue[j] / sum(all eigenvalues).
3. cumulative_explained_ratio = sum of explained ratios for retained components.

## K-Means Clustering

### Initialization (Farthest-First)
1. First center: the entity with the ASCII-smallest entity code (state abbreviation, county FIPS, or ISO3).
2. For each subsequent center: choose the entity maximizing its squared Euclidean distance to the nearest already-chosen center. Tie: smaller entity code.
3. Repeat until k centers are chosen.

### Lloyd's Algorithm
1. Assign each entity to the nearest center by squared Euclidean distance. Tie: lower cluster id (1, 2, ...).
2. Update each center as the arithmetic mean of its members (per-dimension).
3. If a cluster becomes empty: reassign the entity farthest from its currently assigned center among all entities to the empty cluster (tie: smaller entity code). Recompute centers and continue.
4. Stop when all cluster assignments are unchanged from the previous iteration, or at the iteration cap.
5. Canonicalize final cluster ids: sort cluster ids by their centroid coordinates lexicographically (pc1, then pc2, then pc3, ...), then remap to 1, 2, 3, ... in that order. This makes cluster labels deterministic regardless of initialization order.

### Silhouette (when requested)
For each entity i in cluster C_I:
- a_i = mean squared distance to other points in C_I (or 0 if |C_I| = 1)
- For each other cluster C_J, d(i, C_J) = mean squared distance from i to points in C_J
- b_i = min_{J != I} d(i, C_J)
- s_i = (b_i - a_i) / max(a_i, b_i), with s_i = 0 when a_i = b_i = 0
- average_silhouette = mean(s_i across all entities)

Select the best k by largest unrounded mean silhouette, tie-broken by smaller k.

## Leave-One-Out Stability

### Leave-Year-Out (for time-structured data)
For each omitted year in ascending order:
1. Remove all feature columns belonging to that year.
2. Rebuild standardization, covariance matrix, eigendecomposition, orientation, scores.
3. Rerun k-means with the same k from scratch (new initialization, new Lloyd iterations).
4. Compare refit labels to full-data labels via adjusted Rand index.

### Delete-State/Entity-Out (for entity-structured clusters)
For each deleted entity in ascending order:
1. Remove that entity's rows entirely.
2. Rebuild the full pipeline (standardization, PCA, orientation, clustering) from scratch.
3. Compare retained entity labels (excluding the deleted entity) to the corresponding full-assignment labels via adjusted Rand index.

### Adjusted Rand Index
Given two labelings U and V with contingency table n_ij (count of entities in cluster i of U and cluster j of V):
- a_i = sum_j n_ij (row sums), b_j = sum_i n_ij (column sums)
- sum_comb = sum_i C(a_i, 2) + sum_j C(b_j, 2)
- index = sum_ij C(n_ij, 2)
- expected = sum_i C(a_i, 2) * sum_j C(b_j, 2) / C(n, 2)   where n = total entities
- ARI = (index - expected) / (0.5 * sum_comb - expected)

### Label Alignment for Refit Comparisons
When comparing refit labels to full-assignment labels:
1. Enumerate all permutations of cluster ids in the refit.
2. For each permutation, count the number of entities whose permuted refit label matches the full-assignment label.
3. Choose the permutation maximizing matches.
4. Tie: choose the lexicographically smallest vector of permuted labels.
5. aligned_assignment_changes = total entities - max_matches.

### Stability Summaries
- leave_year_out_adjusted_rand_index: vector of ARIs for each omitted year, in year order
- median_delete_state_ari: median of delete-state ARIs
- minimum_delete_state_ari: minimum of delete-state ARIs
