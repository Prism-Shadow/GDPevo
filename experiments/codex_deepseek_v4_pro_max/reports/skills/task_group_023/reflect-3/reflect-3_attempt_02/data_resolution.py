 """
 Data resolution helpers for Public Health Observatory audits.
 Implements REGISTERED_FINAL_RELEASE_RESOLUTION protocol.
 """
 
 import csv
 from collections import defaultdict
 
 def safe_float(value):
     """Convert to float, returning None for missing/invalid."""
     if value is None or value == '' or value == 'NA':
         return None
     try:
         return float(value)
     except (ValueError, TypeError):
         return None
 
 def safe_int(value):
     """Convert to int, returning None for missing/invalid."""
     if value is None or value == '' or value == 'NA':
         return None
     try:
         return int(float(value))
     except (ValueError, TypeError):
         return None
 
 def resolve_observations(rows, years, measures, release_status='FINAL',
                          value_type=None, source_type=None,
                          invalid_quality_flags=None,
                          entity_key='state_abbr',
                          measure_key='measure_id'):
     """
     Resolve observations using REGISTERED_FINAL_RELEASE_RESOLUTION.
     
     For each (entity, year, measure, value_type, source_type):
     - Filter to specified release_status
     - Exclude invalid quality flags
     - Exclude suppressed or blank values
     - Take the highest revision number
     
     Returns: nested dict: entity -> year -> (measure, vt, st) -> (value, revision)
     """
     if invalid_quality_flags is None:
         invalid_quality_flags = ['INVALID_SCALE', 'INVALID', 'WITHDRAWN']
     
     data = defaultdict(lambda: defaultdict(dict))
     
     for row in rows:
         year = safe_int(row.get('year'))
         if year not in years:
             continue
         
         measure = row.get(measure_key)
         if measure not in measures:
             continue
         
         if row.get('release_status') != release_status:
             continue
         
         if value_type and row.get('value_type') != value_type:
             continue
         
         if source_type and row.get('source_type') != source_type:
             continue
         
         if row.get('quality_flag') in invalid_quality_flags:
             continue
         
         if row.get('suppression_flag') == '1':
             continue
         
         value = safe_float(row.get('value'))
         if value is None:
             continue
         
         entity = row.get(entity_key)
         vt = row.get('value_type', '')
         st = row.get('source_type', '')
         key = (measure, vt, st)
         revision = safe_int(row.get('revision')) or 0
         
         if key not in data[entity][year] or revision > data[entity][year][key][1]:
             data[entity][year][key] = (value, revision)
     
     return data
 
 def resolve_socioeconomic(rows, years, variables, release_status='FINAL',
                           invalid_quality_flags=None,
                           entity_key='state_abbr'):
     """
     Resolve socioeconomic records with revision priority.
     Returns: nested dict: entity -> year -> variable_name -> (value, revision)
     """
     if invalid_quality_flags is None:
         invalid_quality_flags = ['INVALID_SCALE', 'INVALID', 'WITHDRAWN']
     
     data = defaultdict(lambda: defaultdict(dict))
     
     for row in rows:
         year = safe_int(row.get('year'))
         if year not in years:
             continue
         
         if row.get('release_status') != release_status:
             continue
         
         if row.get('quality_flag') in invalid_quality_flags:
             continue
         
         entity = row.get(entity_key)
         revision = safe_int(row.get('revision')) or 0
         
         for var in variables:
             value = safe_float(row.get(var))
             if value is None:
                 continue
             if var not in data[entity][year] or revision > data[entity][year][var][1]:
                 data[entity][year][var] = (value, revision)
     
     return data
 
 def load_csv(path):
     """Load a CSV file into a list of dicts."""
     with open(path) as f:
         return list(csv.DictReader(f))
 
 def build_balanced_cohort(data_dict, entities, years, required_keys, check_fn=None):
     """
     Build a balanced cohort: entities with non-null values for all
     required_keys in every analysis year.
     
     check_fn(entity, year) -> bool can override the default checks.
     """
     balanced = set(entities)
     for entity in entities:
         for year in years:
             if check_fn:
                 if not check_fn(entity, year):
                     balanced.discard(entity)
                     break
             else:
                 if not all(key in data_dict[entity][year] for key in required_keys):
                     balanced.discard(entity)
                     break
     return sorted(balanced)
