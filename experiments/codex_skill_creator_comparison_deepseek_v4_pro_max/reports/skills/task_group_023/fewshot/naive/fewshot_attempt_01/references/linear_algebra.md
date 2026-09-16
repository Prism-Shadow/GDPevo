# Weighted Linear Algebra and Robust Standard Errors

## Weighted Least Squares (WLS)

For design matrix X (n x k), outcome vector y (n x 1), and positive weight vector w (n x 1):
- Xw = diag(sqrt(w)) * X
- yw = diag(sqrt(w)) * y
- b = (Xw' Xw)^(-1) Xw' yw

Solve in declared column order. The intercept, if included, is the first column of X.

## HC3 Heteroskedasticity-Robust Standard Errors

For leverage h_i = diag(Xw (Xw' Xw)^(-1) Xw') and weighted residual ew_i = sqrt(w_i) * (y_i - X_i b):
- V_HC3 = (Xw' Xw)^(-1) Xw' diag(ew_i^2 / (1 - h_i)^2) Xw (Xw' Xw)^(-1)
- Standard error for coefficient j: sqrt(V_HC3[j,j])
- Use two-sided Student-t with n-k degrees of freedom for inference

## CR1 Cluster-Robust Standard Errors

For ordered clusters g = 1..G, cluster score s_g = Xw_g' ew_g:
- V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] * (Xw' Xw)^(-1) * sum_g(s_g * s_g') * (Xw' Xw)^(-1)
- Standard error for coefficient j: sqrt(V_CR1[j,j])
- Use two-sided Student-t with G-1 degrees of freedom for inference
- Ties in inference (e.g. for extrema selection): use the unrounded statistic, then the declared identifier order

## Ordinary Least Squares (unweighted)

When weights are not specified or are uniform:
- b = (X' X)^(-1) X' y
- Standard OLS variance: sigma^2 * (X' X)^(-1) with sigma^2 = SSE/(n-k)
- HC3: as above with w_i = 1 for all i
- CR1: as above with w_i = 1 for all i

## Two-Step GMM Weight Matrix

For first-step residuals u from identity-weight GMM:
- S_g = Z_g' u_g
- S = sum_g(S_g * S_g') / n
- W = Moore-Penrose pseudoinverse of S
- Use the declared relative singular-value cutoff: singular values below cutoff * max_singular_value are treated as zero in the pseudoinverse
