"""Portfolio category classifier — pure risk precedence (validated convention).

Classify a work item into exactly one of NewFeature / TechDebt / Reliability / Security using
Security > Reliability > TechDebt > NewFeature precedence over the UNION of work_type + labels +
title signals. Ignores legacy_category, mirror_status, and the 'stale-export' label, and does NOT
demote on title disclaimers (those are traps).

`work_item` is a dict with at least: work_type, labels (list[str] or None), title (str).
Returns one of 'NewFeature','TechDebt','Reliability','Security'.
"""
SEC = {'security','cve','auth','encryption','compliance','audit','harden','patch','rotate','remediation'}
REL = {'reliability','latency','outage','flaky','incident','stabilize','repair','recover','rehearsal'}
TD  = {'cleanup','refactor','migrate','migration','deprecate','tech-debt'}
NF  = {'feature','rollout','launch','extend','enable','build'}

WT_CAT = {'Feature':'NewFeature','Enhancement':'NewFeature','Security':'Security','Compliance':'Security',
          'Reliability':'Reliability','Incident':'Reliability','Bug':'Reliability',
          'Refactor':'TechDebt','Chore':'TechDebt','Dependency':'TechDebt'}
SETS = {'Security':SEC,'Reliability':REL,'TechDebt':TD,'NewFeature':NF}
PRECEDENCE = ['Security','Reliability','TechDebt','NewFeature']


def classify(w):
    sigs = set()
    wc = WT_CAT.get(w.get('work_type'))
    if wc:
        sigs.add(wc)
    for l in (w.get('labels') or []):
        l = l.lower()
        if l == 'stale-export':
            continue
        for c, kw in SETS.items():
            if l in kw:
                sigs.add(c)
                break
    for word in (w.get('title') or '').lower().split():
        word = word.rstrip('s,.')
        for c, kw in SETS.items():
            if word in kw:
                sigs.add(c)
                break
    for c in PRECEDENCE:
        if c in sigs:
            return c
    return 'NewFeature'


# Notes on the closed/complete status set and overdue rule (kept here as the canonical reference):
#   CLOSED = {'Closed','Done','Verified','Deployed'}
#   duplicate if duplicate_of non-null OR status == 'Duplicate'  (duplicate_of is authoritative)
#   overdue if due_at <= as_of  (boundary due==as_of counts as overdue; open AND recently-closed)
#   as-of-aware: closed_at > as_of  ==> the item was OPEN at audit (status may now read closed).
