with open('app/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# تعديل printOrder فقط
old = '''        async function printOrder() {
            if(cart.length===0) return showToast('⚠️ السلة فارغة');
            if(!window.lastOrder || !window.lastOrder.id) {
                await saveOrder();
            }
            if(cart.length===0) return;
            document.getElementById('printReceipt').innerHTML = buildReceiptHTML();
            window.print();
            window.lastOrder = null;
        }'''

new = '''        function printOrder() {
            if(cart.length===0) return showToast('⚠️ السلة فارغة');
            document.getElementById('printReceipt').innerHTML = buildReceiptHTML();
            window.print();
        }'''

content = content.replace(old, new)

with open('app/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done!")
