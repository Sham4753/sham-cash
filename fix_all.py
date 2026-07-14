import re

with open('app/server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add category_sales calculation before # 7
old1 = "    # 7. أكثر الأصناف مبيعاً"
new1 = """    # 8. مبيعات الأقسام
    category_sales = {}
    for o in orders:
        for i in o.get('items', []):
            cat = i.get('category', 'غير مصنف')
            if cat not in category_sales:
                category_sales[cat] = 0
            category_sales[cat] += i.get('quantity', i.get('qty', 1)) * i.get('price', 0)

    # 7. أكثر الأصناف مبيعاً"""
content = content.replace(old1, new1)

# 2. Add category_sales to return jsonify
old2 = '"top_items": top_items,'
new2 = '"top_items": top_items,\n        "category_sales": category_sales,'
content = content.replace(old2, new2)

with open('app/server.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done!")
