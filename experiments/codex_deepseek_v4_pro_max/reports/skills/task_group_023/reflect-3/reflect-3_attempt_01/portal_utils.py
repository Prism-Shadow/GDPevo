 """
 Utility functions for interacting with the Public Health Observatory data portal.
 Used by analysis scripts to download, resolve, and structure portal data.
 """
 import csv
 import json
 from collections import defaultdict
 from pathlib import Path

 # ---------------------------------------------------------------------------
 # Data Loading
 # ---------------------------------------------------------------------------

 def load_csv(path: str) -> list[dict]:
     """Load a CSV file as a list of dicts using csv.DictReader."""
     with open(path) as f:
         return list(csv.DictReader(f))


 def load_all_datasets(data_dir: str = ".") -> dict[str, list[dict]]:
     """Load all standard PHO datasets from a directory."""
     datasets = {}
     for name in [
         "states", "counties", "countries",
         "state_health", "state_socioeconomic",
         "county_health", "county_socioeconomic",
         "country_indicators", "revisions",
     ]:
         path = Path(data_dir) / f"{name}.csv"
         if path.exists():
             datasets[name] = load_csv(str(path))
     return datasets


# ---------------------------------------------------------------------------
# Release Resolution
# ---------------------------------------------------------------------------

 def resolve_final_releases(
     rows: list[dict],
     key_fn,
     quality_flags_to_drop: set = None,
     suppression_check: bool = True,
) -> dict:
    """
    Resolve the highest FINAL revision for each entity key.

    Rules:
    1. Keep only release_status == "FINAL".
    2. Drop rows with quality_flag in quality_flags_to_drop (default: INVALID_SCALE, INVALID, WITHDRAWN).
    3. Drop suppressed rows when suppression_check=True (suppression_flag == "1").
    4. For each key, select highest revision number.
    5. If multiple rows share highest revision, select latest released_at.

    Returns: dict mapping key_fn(row) -> resolved row dict.
    """
    if quality_flags_to_drop is None:
        quality_flags_to_drop = {"INVALID_SCALE", "INVALID", "WITHDRAWN"}

    groups = defaultdict(list)
    for r in rows:
        if r.get("release_status") != "FINAL":
            continue
        qf = r.get("quality_flag", "")
        if qf in quality_flags_to_drop:
            continue
        if suppression_check and r.get("suppression_flag") == "1":
            continue
        k = key_fn(r)
        groups[k].append(r)

    resolved = {}
    for k, grp in groups.items():
        max_rev = max(int(r.get("revision", 0) or 0) for r in grp)
        candidates = [r for r in grp if int(r.get("revision", 0) or 0) == max_rev]
        candidates.sort(key=lambda r: r.get("released_at", ""))
        resolved[k] = candidates[-1]
    return resolved


# ---------------------------------------------------------------------------
# Common Entity Key Functions
# ---------------------------------------------------------------------------

 def state_health_key(row: dict) -> tuple:
    """(state_abbr, year, measure_id, value_type, source_type)"""
    return (
        row["state_abbr"],
        int(row["year"]),
        row["measure_id"],
        row.get("value_type", ""),
        row.get("source_type", ""),
    )


 def state_socioeconomic_key(row: dict) -> tuple:
    """(state_abbr, year)"""
    return (row["state_abbr"], int(row["year"]))


 def county_health_key(row: dict) -> tuple:
    """(county_fips, year, measure_id, value_type)"""
    return (row["county_fips"], int(row["year"]), row["measure_id"], row.get("value_type", ""))


 def county_socioeconomic_key(row: dict) -> tuple:
    """(county_fips, year)"""
    return (row["county_fips"], int(row["year"]))


 def country_indicator_key(row: dict) -> tuple:
    """(iso3, year, indicator_id)"""
    return (row["iso3"], int(row["year"]), row["indicator_id"])


# ---------------------------------------------------------------------------
# Geography Lookups
# ---------------------------------------------------------------------------

 def build_division_lookup(states_rows: list[dict]) -> dict[str, str]:
    """Map state_abbr -> division. Adds DC = 'South Atlantic'."""
    lookup = {r["state_abbr"]: r["division"] for r in states_rows if r.get("is_state") == "1"}
    lookup["DC"] = "South Atlantic"
    return lookup


 def build_region_lookup(states_rows: list[dict]) -> dict[str, str]:
    """Map state_abbr -> region. Adds DC = 'South'."""
    lookup = {r["state_abbr"]: r["region"] for r in states_rows if r.get("is_state") == "1"}
    lookup["DC"] = "South"
    return lookup


 def build_county_reference(counties_rows: list[dict]) -> dict[str, dict]:
    """Map county_fips -> county info dict."""
    return {r["county_fips"]: r for r in counties_rows}


 def build_country_label_map(countries_rows: list[dict]) -> dict[str, str]:
    """
    Build a mapping from any label (canonical, portal, alternate) to iso3.
    Alternate labels are semicolon-separated.
    """
    label_to_iso3 = {}
    for r in countries_rows:
        iso3 = r["iso3"]
        label_to_iso3[r["canonical_name"]] = iso3
        label_to_iso3[r["portal_label"]] = iso3
        alts = r.get("alternate_labels", "")
        if alts:
            for a in alts.split(";"):
                a = a.strip()
                if a:
                    label_to_iso3[a] = iso3
    return label_to_iso3


# ---------------------------------------------------------------------------
# Cohort Helpers
# ---------------------------------------------------------------------------

 def filter_by_regions(county_ref: dict[str, dict], regions: list[str]) -> set[str]:
    """Return set of county_fips in the given regions."""
    return {fips for fips, info in county_ref.items() if info.get("region", "") in regions}


 def check_complete(
    county_fips: str,
    year: int,
    county_ref: dict[str, dict],
    health_data: dict,
    socio_data: dict,
    required_health_measures: list[tuple],
    required_socio_fields: list[str],
) -> bool:
    """
    Check if a county has all required fields non-null for a given year.
    required_health_measures: list of (measure_id, value_type)
    """
    if county_fips not in county_ref:
        return False
    rucc = county_ref[county_fips].get("rucc", "")
    if not rucc or rucc == "":
        return False
    for measure_id, value_type in required_health_measures:
        col = f"{measure_id}__{value_type}"
        if health_data.get((county_fips, year), {}).get(col) is None:
            return False
    for field in required_socio_fields:
        if socio_data.get((county_fips, year), {}).get(field) is None:
            return False
    return True


# ---------------------------------------------------------------------------
# Answer Validation
# ---------------------------------------------------------------------------

 def validate_against_template(answer: dict, template_path: str) -> list[str]:
    """
    Check that answer has all required top-level keys and basic structural constraints.
    Returns list of error messages (empty if valid).
    """
    errors = []
    with open(template_path) as f:
        template = json.load(f)

    # Handle both template formats
    if "required_top_level_keys" in template:
        required_keys = template["required_top_level_keys"]
        sections = template.get("template", {})
    elif "required_output" in template:
        sections = template["required_output"]
        required_keys = list(sections.keys())
    else:
        return ["Cannot determine required keys from template"]

    for key in required_keys:
        if key not in answer:
            errors.append(f"Missing required key: {key}")
        elif key in sections:
            spec = sections[key]
            if isinstance(spec, dict) and "required_keys" in spec:
                for rk in spec["required_keys"]:
                    if rk not in answer[key]:
                        errors.append(f"Missing required key: {key}.{rk}")
            # Check array lengths
            if isinstance(spec, dict) and "array_lengths" in spec:
                for field, expected_len in spec["array_lengths"].items():
                    if field in answer[key]:
                        val = answer[key][field]
                        if isinstance(val, list):
                            if isinstance(expected_len, list):
                                if len(val) != expected_len[0]:
                                    errors.append(f"{key}.{field}: expected {expected_len[0]} rows, got {len(val)}")
                            elif len(val) != expected_len:
                                errors.append(f"{key}.{field}: expected length {expected_len}, got {len(val)}")

    return errors


# ---------------------------------------------------------------------------
# Rounding Helper
# ---------------------------------------------------------------------------

 def r4(x: float) -> float:
    """Round to 4 decimal places, return as float."""
    return round(float(x), 4)


 def r6(x: float) -> float:
    """Round to 6 decimal places, return as float."""
    return round(float(x), 6)
