with open('app/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find where to insert category_sales calculation
insert_idx = None
for i, line in enumerate(lines):
    if '# 7. أكثر الأصناف مبيعاً' in line:
        insert_idx = i
        break

if insert_idx:
    new_code = [
        '    # 8. مبيعات الأقسام\n',
        '    category_sales = {}\n',
        '    for o in orders:\n',
        '        for i in o.get(\'items\', []):\n',
        '            cat = i.get(\'category\', \'غير مصنف\')\n',
        '            if cat not in category_sales:\n',
        '                category_sales[cat] = 0\n',
        '            category_sales[cat] += i.get(\'quantity\', i.get(\'qty\', 1)) * i.get(\'price\', 0)\n',
        '\n',
    ]
    for line in reversed(new_code):
        lines.insert(insert_idx, line)

with open('app/server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Done! Check server.py")
