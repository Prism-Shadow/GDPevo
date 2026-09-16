import re

with open('/work/skill/SKILL.md') as f:
    content = f.read()

specific_ids = [
    'ORD-000018', 'ORD-000026', 'ORD-000344', 'ORD-000436',
    'SCN-0001272', 'SHP-000212', 'WT-000170', 'WT-002540',
    'EMP-0007', 'CASE-000460', 'CASE-000775', 'ACC-0210',
    'WH-NORTH-01-TEAM-3', 'CQR-20260320-EAST-CARRIER-003',
    'AUD-CQR-20260320-003', 'BATCH-03-01-2'
]

found = []
for sid in specific_ids:
    if sid in content:
        found.append(sid)

if found:
    print(f'WARNING: skill contains task-specific IDs: {found}')
else:
    print('OK: No train-answer-specific IDs found in SKILL.md')

specific_values = [
    ('1477', 'eligible_production_order_count'),
    ('0.1903', 'on_time_complete_order_rate'),
    ('115674.62', 'net_refund_amount_usd'),
    ('484', 'eligible_refunded_order_count'),
    ('9408', 'completed_production_units'),
    ('159', 'eligible_case_count'),
]

for val, label in specific_values:
    if val in content:
        print(f'WARNING: skill contains specific value {val} ({label})')
    else:
        print(f'OK: {val} ({label}) not found')
