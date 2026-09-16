import json

def convert_schema():
    with open('/work/skill/references/schema.json') as f:
        schema = json.load(f)

    lines = []
    lines.append('# Atlas Commerce Operations Schema')
    lines.append('')
    lines.append(f'Schema version: {schema["schema_version"]}')
    lines.append('')

    for table in schema['tables']:
        lines.append(f'## {table["name"]}')
        lines.append('')
        lines.append('```sql')
        lines.append(table['ddl'])
        lines.append('```')
        lines.append('')

    lines.append('## Indexes')
    lines.append('')
    for idx in schema['indexes']:
        lines.append(f'### {idx["name"]}')
        lines.append('')
        lines.append('```sql')
        lines.append(idx['ddl'])
        lines.append('```')
        lines.append('')

    with open('/work/skill/references/schema.md', 'w') as f:
        f.write('\n'.join(lines))
    print('schema.md written')

def convert_dictionary():
    with open('/work/skill/references/data_dictionary.json') as f:
        dd = json.load(f)

    lines = []
    lines.append('# Atlas Commerce Operations Data Dictionary')
    lines.append('')
    lines.append(f'Schema version: {dd["schema_version"]}')
    lines.append('')

    conv = dd['conventions']
    lines.append('## Conventions')
    lines.append('')
    for k, v in conv.items():
        lines.append(f'- **{k}**: {v}')
    lines.append('')

    for table in dd['tables']:
        lines.append(f'## {table["name"]}')
        lines.append('')
        if 'description' in table:
            lines.append(table['description'])
            lines.append('')
        lines.append('| Column | Type | Nullable | Description |')
        lines.append('|--------|------|----------|-------------|')
        for col in table['columns']:
            nullable = 'YES' if col['nullable'] else 'NO'
            lines.append(f'| {col["name"]} | {col["type"]} | {nullable} | {col["description"]} |')
        lines.append('')

    with open('/work/skill/references/dictionary.md', 'w') as f:
        f.write('\n'.join(lines))
    print('dictionary.md written')

convert_schema()
convert_dictionary()
