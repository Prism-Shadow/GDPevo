"""
portal.py — reusable helpers for Public Health Observatory (PHO) algorithmic-audit tasks.

This module is portal-agnostic. It hardcodes NO host and contacts nothing except the
read-only evidence portal you point it at — the portal whose base URL your task provides
(the `<TASK_ENV_BASE_URL>` placeholder in the prompt / your environment access file).

Typical use:

    from portal import Portal
    p = Portal(base_url="<the base URL your task gives you>")
    states = p.dataset("states")                 # geography reference (state_abbr, region, division, ...)
    sh     = p.dataset("state_health")           # observation-level releases
    final  = p.resolve_final(sh, key=["state_abbr","measure_id","year",
                                      "value_type","source_type"], id_col="observation_id")

Everything else (models, bootstraps, PCA) is task-specific and lives in your own
solution script; this module only standardizes data loading, release resolution and
cohort assembly, which are identical across every PHO audit.
"""
from __future__ import annotations
import io
import os
import urllib.parse
import urllib.request

import pandas as pd


# Datasets the portal catalog exposes (verify names/columns against the live /catalog).
KNOWN_DATASETS = [
    "states", "counties", "countries",
    "state_health", "state_socioeconomic",
    "county_health", "county_socioeconomic",
    "country_indicators", "revisions",
]

# FIPS-like identifier columns must stay TEXT (leading zeros are meaningful).
_TEXT_COLS = {"state_fips", "county_fips", "iso3"}


class Portal:
    def __init__(self, base_url: str | None = None, timeout: int = 60):
        base_url = base_url or os.environ.get("GDPEVO_ENV_BASE_URL")
        if not base_url:
            raise ValueError(
                "Provide the portal base URL from your task (prompt placeholder / access file)."
            )
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self._cache: dict[str, pd.DataFrame] = {}

    # ---- raw access -------------------------------------------------------
    def _get(self, path: str) -> str:
        url = self.base + path
        with urllib.request.urlopen(url, timeout=self.timeout) as r:
            return r.read().decode("utf-8", "replace")

    def dataset(self, name: str) -> pd.DataFrame:
        """Download a full dataset as a DataFrame via the CSV export the catalog links to."""
        if name in self._cache:
            return self._cache[name].copy()
        q = urllib.parse.urlencode({"dataset": name, "format": "csv"})
        csv = self._get(f"/download?{q}")
        dtype = {c: str for c in _TEXT_COLS}
        df = pd.read_csv(io.StringIO(csv), dtype=dtype)
        self._cache[name] = df
        return df.copy()

    # ---- release resolution ----------------------------------------------
    @staticmethod
    def resolve_final(
        df: pd.DataFrame,
        key: list[str],
        id_col: str,
        status_col: str = "release_status",
        rev_col: str = "revision",
        released_col: str = "released_at",
        final_value: str = "FINAL",
    ) -> pd.DataFrame:
        """
        REGISTERED_FINAL_RELEASE_RESOLUTION.

        For each `key` group keep exactly one row: the FINAL record with the highest
        revision, breaking ties by latest `released_at`, then by descending id.
        Provisional records are used ONLY when a group has no FINAL record (rare;
        confirm your task's rule — most require a FINAL to exist).
        """
        f = df[df[status_col] == final_value]
        if f.empty:
            f = df  # fall back to whatever exists; caller decides if that is legal
        f = f.sort_values([rev_col, released_col, id_col],
                          ascending=[False, False, False])
        return f.groupby(key, as_index=False, sort=False).first()

    # ---- availability mask -----------------------------------------------
    @staticmethod
    def available(
        df: pd.DataFrame,
        value_col: str = "value",
        suppression_col: str = "suppression_flag",
        invalid_quality: tuple[str, ...] = (),
        quality_col: str = "quality_flag",
    ) -> pd.Series:
        """
        A cell is AVAILABLE iff it is not suppressed, its value is non-null, and its
        quality flag is not in the task's declared invalid set. Never zero-fill a
        suppressed / missing value.
        """
        ok = df[value_col].notna()
        if suppression_col in df.columns:
            ok &= (df[suppression_col].fillna(0).astype(int) != 1)
        if invalid_quality and quality_col in df.columns:
            ok &= ~df[quality_col].isin(list(invalid_quality))
        return ok


# ---- country label reconciliation (train tasks that resolve country labels) ----
def build_label_index(countries: pd.DataFrame) -> dict[str, str]:
    """
    Map every portal_label, canonical_name and pipe-delimited alternate_label to iso3.
    `alternate_labels` is a '|'-separated string.
    """
    idx: dict[str, str] = {}
    for _, r in countries.iterrows():
        iso3 = r["iso3"]
        for col in ("portal_label", "canonical_name"):
            v = r.get(col)
            if isinstance(v, str) and v:
                idx[v.strip()] = iso3
        alts = r.get("alternate_labels")
        if isinstance(alts, str):
            for a in alts.split("|"):
                a = a.strip()
                if a:
                    idx[a] = iso3
    return idx


def resolve_labels(requested: list[str], countries: pd.DataFrame):
    """Return (iso3_by_label, alias_count) where alias_count = labels whose text
    differs from the resolved canonical_name."""
    idx = build_label_index(countries)
    canon = dict(zip(countries["iso3"], countries["canonical_name"]))
    out, alias = {}, 0
    for lab in requested:
        iso = idx.get(lab.strip())
        out[lab] = iso
        if iso is not None and lab.strip() != str(canon.get(iso)):
            alias += 1
    return out, alias


if __name__ == "__main__":
    # Smoke test only runs if you pass a base URL via env; prints dataset shapes.
    p = Portal()
    for name in KNOWN_DATASETS:
        try:
            print(name, p.dataset(name).shape)
        except Exception as e:  # pragma: no cover
            print(name, "ERR", e)
