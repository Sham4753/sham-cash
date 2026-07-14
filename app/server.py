import os, sys, json, shutil, threading, urllib.request, hashlib
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory

# ========== إعدادات التحديث ==========
GITHUB_USER = "Sham4753"
GITHUB_REPO = "shamjb-updates"
GITHUB_BRANCH = "main"
BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}"
CURRENT_VERSION = "2.1.3"


def version_tuple(v):
    """تحويل رقم الإصدار إلى tuple للمقارنة الصحيحة"""
    return tuple(int(x) for x in v.strip().split('.'))

def check_for_updates():
    try:
        with urllib.request.urlopen(f"{BASE_URL}/version.txt", timeout=5) as f:
            latest = f.read().decode().strip()
        if version_tuple(latest) > version_tuple(CURRENT_VERSION):
            print(f"تحديث جديد: v{latest}")
            # تحديث index.html فقط
            url = f"{BASE_URL}/index.html"
            dest = os.path.join(APP_PATH, "index.html")
            urllib.request.urlretrieve(url, dest)
            print("  تم تحديث index.html")
            # كتابة log
            with open(os.path.join(APP_PATH, "update.log"), "a") as log:
                log.write(f"{datetime.now()}: Updated to v{latest}\n")
            return True
        else:
            print(f"النظام محدث (v{CURRENT_VERSION})")
            return False
    except Exception as e:
        print(f"تعذر التحديث: {e}")
        with open(os.path.join(APP_PATH, "update.log"), "a") as log:
            log.write(f"{datetime.now()}: Error - {e}\n")
        return False

# ========== مسارات ==========
# تحديد مسار التشغيل
if getattr(sys, 'frozen', False):
    APP_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))
    EXTERNAL_PATH = APP_PATH
else:
    APP_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))
    EXTERNAL_PATH = APP_PATH

BASE_DIR = EXTERNAL_PATH
if sys.platform == 'win32':
    VAULT_DIR = r'C:\ShamJB_Vault'
else:
    VAULT_DIR = os.path.join(os.path.expanduser('~'), 'Documents', 'ShamJB_Vault')

DATA_FILE = os.path.join(VAULT_DIR, 'data.json')
BACKUP_DIR = os.path.join(VAULT_DIR, 'backups')
FLASH_BACKUP = os.path.join(BASE_DIR, 'data_backup.json')

os.makedirs(VAULT_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

if not os.path.exists(DATA_FILE):
    if os.path.exists(FLASH_BACKUP):
        shutil.copy(FLASH_BACKUP, DATA_FILE)
    else:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({"menu": {}, "orders": [], "shifts": [], "log": [], "settings": {"currency": "SYP"}}, f, ensure_ascii=False, indent=2)

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')

def load():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if ensure_ids(data):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return data

def save(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    try:
        with open(FLASH_BACKUP, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except: pass

def backup():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    shutil.copy(DATA_FILE, os.path.join(BACKUP_DIR, f'backup_{ts}.json'))
    backups = sorted(os.listdir(BACKUP_DIR))
    for old in backups[:-30]:
        os.remove(os.path.join(BACKUP_DIR, old))

def ensure_ids(data):
    """يضمن أن كل سجل بالقوائم (موظفين/ديون/مواد) عنده id فريد.
    مهم لأن سجلات قديمة كانت تُضاف بدون id قبل التحديث الحالي."""
    changed = False
    for key in ('employees', 'debts', 'materials'):
        items = data.get(key, [])
        existing_ids = [i['id'] for i in items if isinstance(i, dict) and 'id' in i]
        next_id = (max(existing_ids) if existing_ids else 0) + 1
        for item in items:
            if 'id' not in item:
                item['id'] = next_id
                next_id += 1
                changed = True
    return changed

def hash_password(pw):
    return hashlib.sha256((pw or '').encode('utf-8')).hexdigest()

def next_order_id(data):
    """يولّد رقم فاتورة جديد، ويصفّر العداد تلقائياً + يؤرشف طلبات الأمس أول ما يبدأ يوم جديد.
    يُستخدم من كل مكان بالكود بيُنشئ طلب (POST /api/orders و تسديد الديون) لضمان عدم تعارض الأرقام."""
    today = datetime.now().strftime('%Y-%m-%d')
    last_date = data.get('settings', {}).get('last_order_date')
    if last_date != today:
        if data.get('orders'):
            shift_id = last_date or today
            for o in data['orders']:
                o['shift_id'] = shift_id
            data.setdefault('orders_archive', []).extend(data['orders'])
            data['orders'] = []
        data['order_counter'] = 0
        data.setdefault('settings', {})['last_order_date'] = today
    data['order_counter'] = data.get('order_counter', 0) + 1
    return f"ORD-{data['order_counter']:04d}"

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/api/menu', methods=['GET'])
def get_menu():
    return jsonify(load().get('menu', {}))

@app.route('/api/category', methods=['POST'])
def add_category():
    data = load()
    cat = request.json.get('name', '').strip()
    if cat and cat not in data['menu']:
        data['menu'][cat] = []
    save(data); backup()
    return jsonify({"ok": True})
    return jsonify({"ok": False})

@app.route('/api/category/<name>', methods=['DELETE'])
def delete_category(name):
    data = load()
    if name in data['menu']:
        del data['menu'][name]
    save(data); backup()
    return jsonify({"ok": True})

@app.route('/api/category/<name>/rename', methods=['POST'])
def rename_category(name):
    """إعادة تسمية قسم مع الحفاظ على كل منتجاته (بدل حذفه وإنشاء واحد فاضي بالخطأ)"""
    data = load()
    new_name = request.json.get('name', '').strip()
    if not new_name:
        return jsonify({"ok": False, "error": "الاسم الجديد فارغ"})
    if name not in data['menu']:
        return jsonify({"ok": False, "error": "القسم غير موجود"})
    if new_name != name and new_name in data['menu']:
        return jsonify({"ok": False, "error": "يوجد قسم بهذا الاسم مسبقاً"})
    data['menu'][new_name] = data['menu'].pop(name)
    save(data); backup()
    return jsonify({"ok": True})

@app.route('/api/product', methods=['POST'])
def add_product():
    data = load()
    cat = request.json.get('category')
    p = {"id": request.json.get('id'), "name": request.json.get('name'), "price": request.json.get('price')}
    if cat in data['menu']:
        data['menu'][cat].append(p)
    save(data); backup()
    return jsonify({"ok": True})
    return jsonify({"ok": False})

@app.route('/api/product/<int:pid>', methods=['PUT'])
def update_product(pid):
    data = load()
    for cat in data['menu']:
        for p in data['menu'][cat]:
            if p['id'] == pid:
                p['name'] = request.json.get('name', p['name'])
                p['price'] = request.json.get('price', p['price'])
            save(data); backup()
            return jsonify({"ok": True})
    return jsonify({"ok": False})

@app.route('/api/product/<int:pid>', methods=['DELETE'])
def delete_product(pid):
    data = load()
    for cat in data['menu']:
        for p in data['menu'][cat]:
            if p['id'] == pid:
                data['menu'][cat].remove(p)
            save(data); backup()
            return jsonify({"ok": True})
    return jsonify({"ok": False})

@app.route('/api/orders', methods=['GET', 'POST'])
def orders():
    data = load()
    if request.method == 'POST':
        o = request.json
        o['id'] = next_order_id(data)
        o["timestamp"] = datetime.now().isoformat()
        data["orders"].append(o)
        save(data); backup()
        return jsonify({"ok": True, "id": o['id']})
    return jsonify(data.get('orders', []))
@app.route('/api/shift/close', methods=['POST'])
def close_shift():
    data = load()
    today = datetime.now().strftime('%Y-%m-%d')
    today_orders = [o for o in data['orders'] if o['timestamp'].startswith(today)]
    total = sum(o.get('total', 0) for o in today_orders)
    shift = {"date": today, "time": datetime.now().isoformat(), "orders": len(today_orders), "total": total}
    data['shifts'].append(shift)
    save(data); backup()
    return jsonify(shift)

@app.route('/api/backup', methods=['POST'])
def force_backup():
    backup()
    return jsonify({"ok": True})

@app.route('/api/version', methods=['GET'])
def version():
    return jsonify({"current": CURRENT_VERSION, "check_url": f"{BASE_URL}/version.txt"})

def start_flask():
    app.run(host='127.0.0.1', port=8080, debug=False)





@app.route('/api/reload-menu', methods=['POST'])
def reload_menu():
    """تهيئة المنيو - تحميل من data.json المحلي"""
    try:
        vault_file = os.path.join(VAULT_DIR, 'data.json')
        if os.path.exists(vault_file):
            with open(vault_file, 'r', encoding='utf-8') as f:
                flash_data = json.load(f)
            local_data = load()
            local_data['menu'] = flash_data.get('menu', {})
            save(local_data)
            backup()
            return jsonify({"ok": True, "message": "تم تهيئة المنيو"})
        return jsonify({"ok": False, "error": "data.json غير موجود"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route('/api/debts', methods=['GET'])
def get_debts():
    data = load()
    return jsonify(data.get('debts', []))

@app.route('/api/debts', methods=['POST'])
def add_debt():
    data = load()
    if 'debts' not in data:
        data['debts'] = []
    new_id = (max([d['id'] for d in data['debts']], default=0)) + 1
    data['debts'].append({
        'id': new_id,
        'name': request.json.get('name'),
        'amount': request.json.get('amount'),
        'paid': 0,
        'note': request.json.get('note', ''),
        'date': datetime.now().strftime('%Y-%m-%d')
    })
    save(data)
    backup()
    return jsonify({"ok": True, "id": new_id})

@app.route('/api/debts/<int:did>', methods=['PUT'])
def update_debt(did):
    data = load()
    for d in data.get('debts', []):
        if d['id'] == did:
            d['name'] = request.json.get('name', d['name'])
            d['amount'] = request.json.get('amount', d['amount'])
            d['note'] = request.json.get('note', d.get('note', ''))
            save(data); backup()
            return jsonify({"ok": True})
    return jsonify({"ok": False}), 404

@app.route('/api/debts/<int:did>/pay', methods=['POST'])
def pay_debt(did):
    """تسجيل دفعة على دين - تُسجَّل تلقائياً كدخل بالكاشير (تظهر بالمبيعات والتحليلات)"""
    data = load()
    for d in data.get('debts', []):
        if d['id'] == did:
            amount = request.json.get('amount', 0)
            d['paid'] = d.get('paid', 0) + amount
            payment_order = {
                'id': next_order_id(data),
                'items': [{'name': f"تسديد دين: {d['name']}", 'price': amount, 'quantity': 1}],
                'total': amount,
                'type': 'تسديد دين',
                'note': d.get('note', ''),
                'payment': 'نقدي',
                'date': datetime.now().isoformat(),
                'timestamp': datetime.now().isoformat()
            }
            data.setdefault('orders', []).append(payment_order)
            save(data); backup()
            return jsonify({"ok": True, "paid": d['paid'], "remaining": d['amount'] - d['paid']})
    return jsonify({"ok": False}), 404

@app.route('/api/debts/<int:did>', methods=['DELETE'])
def delete_debt(did):
    data = load()
    data['debts'] = [d for d in data.get('debts', []) if d['id'] != did]
    save(data)
    backup()
    return jsonify({"ok": True})

@app.route('/api/orders/archive', methods=['POST'])
def archive_orders():
    """أرشفة الطلبات بدل تصفيرها"""
    data = load()
    if 'orders_archive' not in data:
        data['orders_archive'] = []
    shift_id = datetime.now().strftime('%Y%m%d_%H%M')
    for o in data.get('orders', []):
        o['shift_id'] = shift_id
    data['orders_archive'].extend(data['orders'])
    data['orders'] = []
    # تصفير عداد الطلبات
    data['order_counter'] = 0
    data.setdefault('settings', {})['last_order_date'] = datetime.now().strftime('%Y-%m-%d')
    save(data)
    backup()
    return jsonify({"ok": True, "shift_id": shift_id, "next_id": "ORD-0001"})


@app.route('/api/employees', methods=['GET'])
def get_employees():
    data = load()
    return jsonify(data.get('employees', []))

@app.route('/api/employees', methods=['POST'])
def add_employee():
    data = load()
    if 'employees' not in data:
        data['employees'] = []
    new_id = (max([e['id'] for e in data['employees']], default=0)) + 1
    advance = request.json.get('advance', 0)
    data['employees'].append({
        'id': new_id,
        'name': request.json.get('name'),
        'salary': request.json.get('salary'),
        'advance': advance,
        'start_date': request.json.get('start_date', datetime.now().strftime('%Y-%m-%d'))
    })
    # السلفة تُخصم فوراً من الكاشير كمصروف
    if advance:
        data.setdefault('expenses', []).append({
            'employee_id': new_id, 'amount': advance,
            'date': datetime.now().isoformat(), 'note': f"سلفة موظف: {request.json.get('name')}"
        })
    save(data)
    backup()
    return jsonify({"ok": True, "id": new_id})

@app.route('/api/employees/<int:eid>', methods=['PUT'])
def update_employee(eid):
    data = load()
    for e in data.get('employees', []):
        if e['id'] == eid:
            e['name'] = request.json.get('name', e['name'])
            e['salary'] = request.json.get('salary', e['salary'])
            e['advance'] = request.json.get('advance', e['advance'])
            save(data); backup()
            return jsonify({"ok": True})
    return jsonify({"ok": False}), 404

@app.route('/api/employees/<int:eid>', methods=['DELETE'])
def delete_employee(eid):
    """حذف موظف - ترجع السلفة (تُحذف كمصروف مرتبط)"""
    data = load()
    data['employees'] = [e for e in data.get('employees', []) if e['id'] != eid]
    data['expenses'] = [x for x in data.get('expenses', []) if x.get('employee_id') != eid]
    save(data)
    backup()
    return jsonify({"ok": True})


@app.route('/api/materials', methods=['GET'])
def get_materials():
    data = load()
    return jsonify(data.get('materials', []))

@app.route('/api/materials', methods=['POST'])
def add_material():
    """شراء مادة خام - تُسجَّل تلقائياً كمصروف يخصم من صافي الربح بالتحليلات"""
    data = load()
    if 'materials' not in data:
        data['materials'] = []
    new_id = (max([m['id'] for m in data['materials']], default=0)) + 1
    material = {
        'id': new_id,
        'name': request.json.get('name', ''),
        'quantity': request.json.get('quantity', 0),
        'unit': request.json.get('unit', ''),
        'price': request.json.get('price', 0)
    }
    data['materials'].append(material)
    data.setdefault('expenses', []).append({
        'material_id': new_id, 'amount': material['price'],
        'date': datetime.now().isoformat(), 'note': f"شراء مادة: {material['name']}"
    })
    save(data); backup()
    return jsonify({"ok": True, "id": new_id})

@app.route('/api/materials/<int:mid>', methods=['PUT'])
def update_material(mid):
    data = load()
    for m in data.get('materials', []):
        if m['id'] == mid:
            m['name'] = request.json.get('name', m['name'])
            m['quantity'] = request.json.get('quantity', m['quantity'])
            m['unit'] = request.json.get('unit', m['unit'])
            m['price'] = request.json.get('price', m['price'])
            # مزامنة المصروف المرتبط بهذه المادة
            for e in data.get('expenses', []):
                if e.get('material_id') == mid:
                    e['amount'] = m['price']
            save(data); backup()
            return jsonify({"ok": True})
    return jsonify({"ok": False}), 404

@app.route('/api/materials/<int:mid>', methods=['DELETE'])
def delete_material(mid):
    """حذف مادة - يرجع مبلغها للجرد (يحذف المصروف المرتبط)"""
    data = load()
    data['materials'] = [m for m in data.get('materials', []) if m['id'] != mid]
    data['expenses'] = [e for e in data.get('expenses', []) if e.get('material_id') != mid]
    save(data); backup()
    return jsonify({"ok": True})


@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """الجرد المطور - 7 مؤشرات"""
    data = load()
    period = request.args.get('period', 'daily')
    
    # فلترة الطلبات حسب الفترة
    now = datetime.now()
    all_orders = data.get('orders', []) + data.get('orders_archive', [])
    
    if period == 'daily':
        orders = [o for o in all_orders if o.get('timestamp', '').startswith(now.strftime('%Y-%m-%d'))]
    elif period == 'monthly':
        orders = [o for o in all_orders if o.get('timestamp', '').startswith(now.strftime('%Y-%m'))]
    elif period == 'yearly':
        orders = [o for o in all_orders if o.get('timestamp', '').startswith(now.strftime('%Y'))]
    else:
        orders = all_orders
    
    total_sales = sum(o.get('total', 0) for o in orders)
    total_orders = len(orders)
    
    # 1. متوسط قيمة الطلب
    avg_order = total_sales / total_orders if total_orders > 0 else 0
    
    # 2. نسبة كل نوع طلب
    type_stats = {'سفري': 0, 'صالة': 0, 'ديليفري': 0}
    for o in orders:
        t = o.get('type', 'سفري')
        type_stats[t] = type_stats.get(t, 0) + 1
    type_pct = {k: round(v/total_orders*100, 1) if total_orders > 0 else 0 for k, v in type_stats.items()}
    
    # 3. أداء الموظفين
    cashier_stats = {}
    for o in orders:
        c = o.get('cashier_name', 'غير معروف')
        if c not in cashier_stats:
            cashier_stats[c] = {'orders': 0, 'sales': 0}
        cashier_stats[c]['orders'] += 1
        cashier_stats[c]['sales'] += o.get('total', 0)
    
    # 4. صافي الربح
    total_expenses = sum(e.get('amount', 0) for e in data.get('expenses', []))
    total_salaries = sum(e.get('salary', 0) for e in data.get('employees', []))
    net_profit = total_sales - total_expenses - total_salaries
    
    # 5. الديون المتراكمة
    total_debts = sum(d.get('amount', 0) for d in data.get('debts', []))
    
    # 6. أكثر الأصناف ركوداً
    item_sales = {}
    for o in orders:
        for i in o.get('items', []):
            name = i.get('name', '')
            if name not in item_sales:
                item_sales[name] = 0
            item_sales[name] += i.get('quantity', i.get('qty', 1))
    slow_items = sorted(item_sales.items(), key=lambda x: x[1])[:5]
    
    # 8. مبيعات الأقسام
    category_sales = {}
    for o in orders:
        for i in o.get('items', []):
            cat = i.get('category', 'غير مصنف')
            if cat not in category_sales:
                category_sales[cat] = 0
            category_sales[cat] += i.get('quantity', i.get('qty', 1)) * i.get('price', 0)

    # 7. أكثر الأصناف مبيعاً
    top_items = sorted(item_sales.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return jsonify({
        "period": period,
        "total_sales": total_sales,
        "total_orders": total_orders,
        "avg_order": round(avg_order, 2),
        "type_pct": type_pct,
        "cashier_stats": cashier_stats,
        "total_expenses": total_expenses,
        "total_salaries": total_salaries,
        "net_profit": net_profit,
        "total_debts": total_debts,
        "slow_items": slow_items,
        "top_items": top_items,
        "category_sales": category_sales,
    })


@app.route('/api/settings/currency', methods=['POST'])
def set_currency():
    """تغيير العملة للنظام كله + أسعار الصرف"""
    data = load()
    if 'settings' not in data:
        data['settings'] = {}
    data['settings']['currency'] = request.json.get('currency', 'SYP')
    data['settings']['usd_rate'] = request.json.get('usd_rate', data['settings'].get('usd_rate', 0))
    data['settings']['eur_rate'] = request.json.get('eur_rate', data['settings'].get('eur_rate', 0))
    save(data)
    return jsonify({
        "ok": True,
        "currency": data['settings']['currency'],
        "usd_rate": data['settings']['usd_rate'],
        "eur_rate": data['settings']['eur_rate']
    })

@app.route('/api/settings/currency', methods=['GET'])
def get_currency():
    data = load()
    settings = data.get('settings', {})
    return jsonify({
        "currency": settings.get('currency', 'SYP'),
        "usd_rate": settings.get('usd_rate', 0),
        "eur_rate": settings.get('eur_rate', 0)
    })


@app.route('/api/settings/restaurant', methods=['GET'])
def get_restaurant():
    data = load()
    r = data.get('settings', {}).get('restaurant', {})
    return jsonify({"name": r.get('name', ''), "phone": r.get('phone', ''), "address": r.get('address', '')})

@app.route('/api/settings/restaurant', methods=['POST'])
def set_restaurant():
    data = load()
    if 'settings' not in data:
        data['settings'] = {}
    data['settings']['restaurant'] = {
        'name': request.json.get('name', ''),
        'phone': request.json.get('phone', ''),
        'address': request.json.get('address', '')
    }
    save(data)
    return jsonify({"ok": True})

@app.route('/api/restaurant/name', methods=['GET'])
def get_restaurant_name():
    """يُستخدم من شاشة الكاشير لعرض اسم المطعم بالهيدر"""
    data = load()
    r = data.get('settings', {}).get('restaurant', {})
    return jsonify({"name": r.get('name', '')})


@app.route('/api/printer/settings', methods=['GET'])
def get_printer_settings():
    data = load()
    p = data.get('settings', {}).get('printer', {})
    return jsonify({
        "paper_width": p.get('paper_width', 80),
        "font_size": p.get('font_size', 'medium'),
        "copies": p.get('copies', 1),
        "footer_text": p.get('footer_text', '')
    })

@app.route('/api/printer/settings', methods=['POST'])
def set_printer_settings():
    data = load()
    if 'settings' not in data:
        data['settings'] = {}
    data['settings']['printer'] = {
        'paper_width': request.json.get('paper_width', 80),
        'font_size': request.json.get('font_size', 'medium'),
        'copies': request.json.get('copies', 1),
        'footer_text': request.json.get('footer_text', '')
    }
    save(data)
    return jsonify({"ok": True})

@app.route('/api/printer/test', methods=['POST'])
def test_printer():
    """طباعة تجريبية - ملاحظة: هذا stub فقط، لا يوجد تكامل فعلي مع درايفر طابعة حرارية بعد.
    يحتاج ربط حقيقي (مثلاً عبر python-escpos) قبل الاعتماد عليه بالإنتاج."""
    return jsonify({"ok": True, "message": "تم إرسال طباعة تجريبية (محاكاة - بدون طابعة فعلية بعد)"})


@app.route('/api/settings/users', methods=['GET'])
def get_users():
    data = load()
    users = data.get('settings', {}).get('users', [])
    safe = [{"id": u['id'], "username": u['username'], "role": u.get('role', 'cashier')} for u in users]
    return jsonify(safe)

@app.route('/api/settings/users', methods=['POST'])
def add_user():
    data = load()
    if 'settings' not in data:
        data['settings'] = {}
    if 'users' not in data['settings']:
        data['settings']['users'] = []
    new_id = (max([u['id'] for u in data['settings']['users']], default=0)) + 1
    data['settings']['users'].append({
        'id': new_id,
        'username': request.json.get('username', ''),
        'password_hash': hash_password(request.json.get('password', '')),
        'role': request.json.get('role', 'cashier')
    })
    save(data)
    return jsonify({"ok": True, "id": new_id})

@app.route('/api/settings/users/<int:uid>', methods=['DELETE'])
def delete_user(uid):
    data = load()
    users = data.get('settings', {}).get('users', [])
    data['settings']['users'] = [u for u in users if u['id'] != uid]
    save(data)
    return jsonify({"ok": True})


@app.route('/api/settings/lock', methods=['GET'])
def get_lock():
    data = load()
    l = data.get('settings', {}).get('lock', {})
    return jsonify({"enabled": l.get('enabled', False), "timeout": l.get('timeout', 5)})

@app.route('/api/settings/lock', methods=['POST'])
def set_lock():
    data = load()
    if 'settings' not in data:
        data['settings'] = {}
    data['settings']['lock'] = {
        'enabled': request.json.get('enabled', False),
        'timeout': request.json.get('timeout', 5)
    }
    save(data)
    return jsonify({"ok": True})


@app.route('/api/settings/backups', methods=['GET'])
def list_backups():
    try:
        files = sorted(os.listdir(BACKUP_DIR), reverse=True)
        return jsonify(files[:30])
    except Exception:
        return jsonify([])

@app.route('/api/settings/backup', methods=['POST'])
def create_backup_endpoint():
    backup()
    return jsonify({"ok": True})


@app.route('/api/check-update', methods=['GET'])
def check_update_route():
    """تستخدمها settings.html لعرض رقم الإصدار الحالي فقط (فحص الاتصال بـ GitHub معطّل حالياً)"""
    return jsonify({"current": CURRENT_VERSION})


@app.route('/api/order/<order_id>', methods=['GET'])
def get_order(order_id):
    """البحث عن فاتورة برقمها"""
    data = load()
    all_orders = data.get('orders', []) + data.get('orders_archive', [])
    for o in all_orders:
        if o.get('id') == order_id:
            return jsonify(o)
    return jsonify({"error": "الفاتورة غير موجودة"}), 404

if __name__ == '__main__':
    print('='*50)
    print('Sham JB Pro')
    print(f' Version: {CURRENT_VERSION}')
    print(f'  Vault: {VAULT_DIR}')
    print('='*50)
    
    # فحص التحديثات
    updated = False  # Disabled
    if updated:
        print(' تم التحديث! يرجى إعادة التشغيل.')
    
    import webbrowser
   # webbrowser.open('http://127.0.0.1:8080')

    # flask_thread removed
    start_flask()
