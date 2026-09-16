import os, re, sys

with open('/work/skill/SKILL.md') as f:
    content = f.read()

errors = 0

# Verify frontmatter
if content.startswith('---'):
    print('Frontmatter starts correctly')
parts = content.split('---', 2)
if len(parts) >= 3:
    print('Frontmatter delimited correctly')
    name_match = re.search(r'name:\s*(.+)', parts[1])
    if name_match:
        print('Name:', name_match.group(1).strip())
    else:
        print('ERROR: name field not found in frontmatter')
        errors += 1

# Check relative links
links = re.findall(r'\]\(([^)]+)\)', content)
for link in links:
    if link.startswith('scripts/') or link.startswith('references/'):
        full = '/work/skill/' + link
        if os.path.exists(full):
            print(f'LINK OK: {link}')
        else:
            print(f'LINK MISSING: {link}')
            errors += 1

print(f'Total markdown links: {len(links)}')
print(f'Errors: {errors}')
sys.exit(0 if errors == 0 else 1)
