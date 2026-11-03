# =============================================================
#  RxCore Pharmacy Management System — Complete Backend
#  All 6 Modules:
#   1. User / Admin Management  (login, roles, sessions)
#   2. Medicine Management      (CRUD + search)
#   3. Stock Management         (alerts, restock, history)
#   4. Supplier Management      (CRUD)
#   5. Sales & Billing          (line items, stock reduction)
#   6. Customer Management      (CRUD)
#
#  Run:  python app.py
#  Open: http://localhost:5000
#  Default login — username: admin   password: admin123
# =============================================================

from flask import Flask, request, jsonify, send_file, session
from functools import wraps
import mysql.connector
from mysql.connector import Error
import hashlib, os

app = Flask(__name__)
app.secret_key = 'rxcore-pharmacy-secret-key-2024'

# =============================================================
#  CHANGE ONLY THESE TWO LINES TO MATCH YOUR MYSQL SETUP
# =============================================================
DB_USER     = 'root'
DB_PASSWORD = '123456789'
# =============================================================
DB_HOST = 'localhost'
DB_NAME = 'pharmacy_db'
DB_PORT = 3306


def get_db():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, port=DB_PORT
    )

def hash_pw(p):   return hashlib.sha256(p.encode()).hexdigest()
def check_pw(p,h): return hashlib.sha256(p.encode()).hexdigest() == h

def login_required(f):
    @wraps(f)
    def d(*a,**k):
        if 'user_id' not in session: return jsonify({'error':'Login required'}),401
        return f(*a,**k)
    return d

def admin_required(f):
    @wraps(f)
    def d(*a,**k):
        if 'user_id' not in session: return jsonify({'error':'Login required'}),401
        if session.get('role')!='admin': return jsonify({'error':'Admin only'}),403
        return f(*a,**k)
    return d


# =============================================================
#  DATABASE INIT — creates ALL tables + default admin + samples
# =============================================================
def init_database():
    print('\n'+'='*60)
    print('  RxCore — Initializing All 6 Modules...')
    print('='*60)
    try:
        conn = mysql.connector.connect(host=DB_HOST,user=DB_USER,password=DB_PASSWORD,port=DB_PORT)
        cur  = conn.cursor()

        cur.execute('CREATE DATABASE IF NOT EXISTS pharmacy_db')
        cur.execute('USE pharmacy_db')

        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username  VARCHAR(100) NOT NULL UNIQUE,
            password  VARCHAR(255) NOT NULL,
            role      ENUM('admin','staff') DEFAULT 'staff',
            full_name VARCHAR(150),
            email     VARCHAR(150),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

        cur.execute("""CREATE TABLE IF NOT EXISTS customers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name      VARCHAR(150) NOT NULL,
            phone     VARCHAR(20),
            email     VARCHAR(150),
            address   TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

        cur.execute("""CREATE TABLE IF NOT EXISTS suppliers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name           VARCHAR(150) NOT NULL,
            contact_person VARCHAR(150),
            phone          VARCHAR(20),
            email          VARCHAR(150),
            address        TEXT,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

        cur.execute("""CREATE TABLE IF NOT EXISTS medicines (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name         VARCHAR(150) NOT NULL,
            category     VARCHAR(100),
            price        DECIMAL(10,2) NOT NULL DEFAULT 0.00,
            stock        INT NOT NULL DEFAULT 0,
            expiry_date  DATE,
            manufacturer VARCHAR(150),
            supplier_id  INT,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL)""")

        cur.execute("""CREATE TABLE IF NOT EXISTS stock_transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            medicine_id INT NOT NULL,
            supplier_id INT,
            type        ENUM('restock','sale','adjustment') DEFAULT 'restock',
            quantity    INT NOT NULL,
            notes       TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL)""")

        cur.execute("""CREATE TABLE IF NOT EXISTS bills (
            id INT AUTO_INCREMENT PRIMARY KEY,
            customer_id  INT NOT NULL,
            total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
            discount     DECIMAL(10,2) DEFAULT 0.00,
            bill_date    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes        TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE)""")

        cur.execute("""CREATE TABLE IF NOT EXISTS bill_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            bill_id     INT NOT NULL,
            medicine_id INT NOT NULL,
            quantity    INT NOT NULL,
            unit_price  DECIMAL(10,2) NOT NULL,
            subtotal    DECIMAL(10,2) NOT NULL,
            FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE,
            FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE)""")

        print('  [OK] All 7 tables ready')

        # Default admin
        cur.execute('SELECT COUNT(*) FROM users'); 
        if cur.fetchone()[0]==0:
            cur.execute('INSERT INTO users (username,password,role,full_name,email) VALUES (%s,%s,%s,%s,%s)',
                ('admin',hash_pw('admin123'),'admin','Administrator','admin@pharmacy.com'))
            print('  [OK] Admin account: admin / admin123')

        # Sample suppliers
        cur.execute('SELECT COUNT(*) FROM suppliers')
        if cur.fetchone()[0]==0:
            cur.executemany('INSERT INTO suppliers (name,contact_person,phone,email) VALUES (%s,%s,%s,%s)',[
                ('Sun Pharma Dist.','Raj Kumar',  '9876500001','raj@sunpharma.com'),
                ('Cipla Wholesale', 'Priya Mehta','9876500002','priya@cipla.com'),
                ('Mankind Pharma',  'Amit Shah',  '9876500003','amit@mankind.com'),
            ])
            print('  [OK] Sample suppliers added')

        # Sample medicines
        cur.execute('SELECT COUNT(*) FROM medicines')
        if cur.fetchone()[0]==0:
            cur.executemany('INSERT INTO medicines (name,category,price,stock,expiry_date,manufacturer,supplier_id) VALUES (%s,%s,%s,%s,%s,%s,%s)',[
                ('Paracetamol 500mg', 'Analgesic',    12.50, 250,'2026-06-30','Sun Pharma',1),
                ('Amoxicillin 250mg', 'Antibiotic',   45.00,   8,'2025-12-31','Cipla',     2),
                ('Metformin 500mg',   'Antidiabetic', 28.00,   0,'2027-01-15','Dr Reddys', 1),
                ('Cetirizine 10mg',   'Antihistamine',18.00, 120,'2026-09-20','Mankind',   3),
                ('Omeprazole 20mg',   'Antacid',      55.00,  60,'2026-03-10','Zydus',     2),
                ('Azithromycin 500mg','Antibiotic',   85.00,   5,'2026-11-15','Cipla',     2),
            ])
            print('  [OK] Sample medicines added')

        # Sample customers
        cur.execute('SELECT COUNT(*) FROM customers')
        if cur.fetchone()[0]==0:
            cur.executemany('INSERT INTO customers (name,phone,email,address) VALUES (%s,%s,%s,%s)',[
                ('Riya Sharma','9876543210','riya@email.com',  '12 MG Road, Chennai'),
                ('Arjun Mehta','9123456789','arjun@email.com', '45 Anna Nagar, Chennai'),
                ('Priya Nair', '9988776655','priya@email.com', '8 Velachery Main Rd'),
            ])
            print('  [OK] Sample customers added')

        conn.commit(); conn.close()
        print('='*60)
        print('  Done! Open: http://localhost:5000')
        print('  Login:      admin / admin123')
        print('='*60+'\n')
    except Error as e:
        print(f'\n  [ERROR] {e}')
        print('  Fix DB_USER and DB_PASSWORD above, then try again.\n')
        exit(1)


# ── Serve HTML ────────────────────────────────────────────────
@app.route('/')
def index():
    path = os.path.join(os.path.dirname(__file__),'pharmacy_system.html')
    return send_file(path) if os.path.exists(path) else ('<h2>pharmacy_system.html not found</h2>',404)


# =============================================================
#  MODULE 1 — USER / ADMIN MANAGEMENT
# =============================================================
@app.route('/api/login',methods=['POST'])
def login():
    d=request.json
    conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute('SELECT * FROM users WHERE username=%s',(d.get('username',''),))
    user=cur.fetchone(); conn.close()
    if not user or not check_pw(d.get('password',''),user['password']):
        return jsonify({'error':'Invalid username or password'}),401
    session.update({'user_id':user['id'],'username':user['username'],'role':user['role'],'full_name':user['full_name']})
    return jsonify({'id':user['id'],'username':user['username'],'role':user['role'],'full_name':user['full_name']})

@app.route('/api/logout',methods=['POST'])
def logout():
    session.clear(); return jsonify({'message':'Logged out'})

@app.route('/api/me')
def me():
    if 'user_id' not in session: return jsonify({'error':'Not logged in'}),401
    return jsonify({'id':session['user_id'],'username':session['username'],'role':session['role'],'full_name':session['full_name']})

@app.route('/api/users',methods=['GET'])
@admin_required
def get_users():
    conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute('SELECT id,username,role,full_name,email,created_at FROM users ORDER BY role,full_name')
    rows=cur.fetchall(); [r.update(created_at=str(r['created_at'])) for r in rows]; conn.close()
    return jsonify(rows)

@app.route('/api/users',methods=['POST'])
@admin_required
def add_user():
    d=request.json
    if not d.get('username') or not d.get('password'): return jsonify({'error':'Username and password required'}),400
    conn=get_db(); cur=conn.cursor()
    try:
        cur.execute('INSERT INTO users (username,password,role,full_name,email) VALUES (%s,%s,%s,%s,%s)',
            (d['username'],hash_pw(d['password']),d.get('role','staff'),d.get('full_name',''),d.get('email','')))
        conn.commit(); new_id=cur.lastrowid; conn.close()
        return jsonify({'message':'User created','id':new_id}),201
    except Error as e:
        conn.close(); return jsonify({'error':str(e)}),400

@app.route('/api/users/<int:uid>',methods=['PUT'])
@admin_required
def update_user(uid):
    d=request.json; conn=get_db(); cur=conn.cursor()
    if d.get('password'):
        cur.execute('UPDATE users SET full_name=%s,email=%s,role=%s,password=%s WHERE id=%s',
            (d.get('full_name'),d.get('email'),d.get('role'),hash_pw(d['password']),uid))
    else:
        cur.execute('UPDATE users SET full_name=%s,email=%s,role=%s WHERE id=%s',
            (d.get('full_name'),d.get('email'),d.get('role'),uid))
    conn.commit(); conn.close(); return jsonify({'message':'User updated'})

@app.route('/api/users/<int:uid>',methods=['DELETE'])
@admin_required
def delete_user(uid):
    if uid==session.get('user_id'): return jsonify({'error':'Cannot delete your own account'}),400
    conn=get_db(); cur=conn.cursor()
    cur.execute('DELETE FROM users WHERE id=%s',(uid,)); conn.commit(); conn.close()
    return jsonify({'message':'User deleted'})


# =============================================================
#  MODULE 2 — MEDICINE MANAGEMENT
# =============================================================
@app.route('/api/medicines',methods=['GET'])
@login_required
def get_medicines():
    search=request.args.get('search',''); conn=get_db(); cur=conn.cursor(dictionary=True)
    q="""SELECT m.*,s.name AS supplier_name FROM medicines m
         LEFT JOIN suppliers s ON m.supplier_id=s.id"""
    if search:
        cur.execute(q+' WHERE m.name LIKE %s OR m.category LIKE %s ORDER BY m.name',(f'%{search}%',f'%{search}%'))
    else:
        cur.execute(q+' ORDER BY m.name')
    rows=cur.fetchall()
    for r in rows:
        if r.get('expiry_date'): r['expiry_date']=str(r['expiry_date'])
        if r.get('created_at'):  r['created_at'] =str(r['created_at'])
    conn.close(); return jsonify(rows)

@app.route('/api/medicines',methods=['POST'])
@login_required
def add_medicine():
    d=request.json; conn=get_db(); cur=conn.cursor()
    cur.execute('INSERT INTO medicines (name,category,price,stock,expiry_date,manufacturer,supplier_id) VALUES (%s,%s,%s,%s,%s,%s,%s)',
        (d['name'],d.get('category'),d['price'],d.get('stock',0),d.get('expiry_date') or None,d.get('manufacturer'),d.get('supplier_id') or None))
    conn.commit(); new_id=cur.lastrowid; conn.close()
    return jsonify({'message':'Medicine added','id':new_id}),201

@app.route('/api/medicines/<int:mid>',methods=['PUT'])
@login_required
def update_medicine(mid):
    d=request.json; conn=get_db(); cur=conn.cursor()
    cur.execute('UPDATE medicines SET name=%s,category=%s,price=%s,stock=%s,expiry_date=%s,manufacturer=%s,supplier_id=%s WHERE id=%s',
        (d['name'],d.get('category'),d['price'],d.get('stock',0),d.get('expiry_date') or None,d.get('manufacturer'),d.get('supplier_id') or None,mid))
    conn.commit(); conn.close(); return jsonify({'message':'Medicine updated'})

@app.route('/api/medicines/<int:mid>',methods=['DELETE'])
@login_required
def delete_medicine(mid):
    conn=get_db(); cur=conn.cursor()
    cur.execute('DELETE FROM medicines WHERE id=%s',(mid,)); conn.commit(); conn.close()
    return jsonify({'message':'Medicine deleted'})


# =============================================================
#  MODULE 3 — STOCK MANAGEMENT
# =============================================================
@app.route('/api/stock/low')
@login_required
def low_stock():
    conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute("""SELECT m.*,s.name AS supplier_name FROM medicines m
        LEFT JOIN suppliers s ON m.supplier_id=s.id WHERE m.stock<=10 ORDER BY m.stock ASC""")
    rows=cur.fetchall()
    for r in rows:
        if r.get('expiry_date'): r['expiry_date']=str(r['expiry_date'])
    conn.close(); return jsonify(rows)

@app.route('/api/stock/restock',methods=['POST'])
@login_required
def restock():
    d=request.json; med_id=d['medicine_id']; qty=int(d['quantity'])
    conn=get_db(); cur=conn.cursor()
    cur.execute('UPDATE medicines SET stock=stock+%s WHERE id=%s',(qty,med_id))
    cur.execute("INSERT INTO stock_transactions (medicine_id,supplier_id,type,quantity,notes) VALUES (%s,%s,'restock',%s,%s)",
        (med_id,d.get('supplier_id') or None,qty,d.get('notes','')))
    conn.commit(); conn.close()
    return jsonify({'message':f'Stock updated +{qty} units'})

@app.route('/api/stock/transactions')
@login_required
def stock_transactions():
    conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute("""SELECT st.*,m.name AS medicine_name,s.name AS supplier_name
        FROM stock_transactions st JOIN medicines m ON st.medicine_id=m.id
        LEFT JOIN suppliers s ON st.supplier_id=s.id ORDER BY st.created_at DESC LIMIT 200""")
    rows=cur.fetchall()
    for r in rows:
        if r.get('created_at'): r['created_at']=str(r['created_at'])
    conn.close(); return jsonify(rows)


# =============================================================
#  MODULE 4 — SUPPLIER MANAGEMENT
# =============================================================
@app.route('/api/suppliers',methods=['GET'])
@login_required
def get_suppliers():
    conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute('SELECT * FROM suppliers ORDER BY name')
    rows=cur.fetchall()
    for r in rows:
        if r.get('created_at'): r['created_at']=str(r['created_at'])
    conn.close(); return jsonify(rows)

@app.route('/api/suppliers',methods=['POST'])
@login_required
def add_supplier():
    d=request.json; conn=get_db(); cur=conn.cursor()
    cur.execute('INSERT INTO suppliers (name,contact_person,phone,email,address) VALUES (%s,%s,%s,%s,%s)',
        (d['name'],d.get('contact_person'),d.get('phone'),d.get('email'),d.get('address')))
    conn.commit(); new_id=cur.lastrowid; conn.close()
    return jsonify({'message':'Supplier added','id':new_id}),201

@app.route('/api/suppliers/<int:sid>',methods=['PUT'])
@login_required
def update_supplier(sid):
    d=request.json; conn=get_db(); cur=conn.cursor()
    cur.execute('UPDATE suppliers SET name=%s,contact_person=%s,phone=%s,email=%s,address=%s WHERE id=%s',
        (d['name'],d.get('contact_person'),d.get('phone'),d.get('email'),d.get('address'),sid))
    conn.commit(); conn.close(); return jsonify({'message':'Supplier updated'})

@app.route('/api/suppliers/<int:sid>',methods=['DELETE'])
@login_required
def delete_supplier(sid):
    conn=get_db(); cur=conn.cursor()
    cur.execute('DELETE FROM suppliers WHERE id=%s',(sid,)); conn.commit(); conn.close()
    return jsonify({'message':'Supplier deleted'})


# =============================================================
#  MODULE 5 — SALES & BILLING
# =============================================================
@app.route('/api/bills',methods=['GET'])
@login_required
def get_bills():
    conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute("""SELECT b.id,c.name AS customer_name,c.phone AS customer_phone,
        b.total_amount,b.discount,b.bill_date,b.notes
        FROM bills b JOIN customers c ON b.customer_id=c.id ORDER BY b.bill_date DESC""")
    rows=cur.fetchall()
    for r in rows:
        if r.get('bill_date'): r['bill_date']=str(r['bill_date'])
    conn.close(); return jsonify(rows)

@app.route('/api/bills/<int:bid>')
@login_required
def get_bill(bid):
    conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute("""SELECT b.*,c.name AS customer_name,c.phone AS customer_phone,c.address AS customer_address
        FROM bills b JOIN customers c ON b.customer_id=c.id WHERE b.id=%s""",(bid,))
    bill=cur.fetchone()
    if not bill: conn.close(); return jsonify({'error':'Not found'}),404
    bill['bill_date']=str(bill['bill_date'])
    cur.execute("""SELECT bi.*,m.name AS medicine_name,m.category FROM bill_items bi
        JOIN medicines m ON bi.medicine_id=m.id WHERE bi.bill_id=%s""",(bid,))
    bill['items']=cur.fetchall(); conn.close(); return jsonify(bill)

@app.route('/api/bills',methods=['POST'])
@login_required
def create_bill():
    d=request.json; items=d.get('items',[])
    if not d.get('customer_id'): return jsonify({'error':'Customer required'}),400
    if not items: return jsonify({'error':'Add at least one medicine'}),400
    conn=get_db(); cur=conn.cursor(dictionary=True)
    # Validate stock
    for item in items:
        cur.execute('SELECT stock,name FROM medicines WHERE id=%s',(item['medicine_id'],))
        med=cur.fetchone()
        if not med: conn.close(); return jsonify({'error':f'Medicine not found'}),400
        if med['stock']<item['quantity']:
            conn.close()
            return jsonify({'error':f'Insufficient stock for {med["name"]} (only {med["stock"]} left)'}),400
    discount=float(d.get('discount',0))
    total=max(0,sum(float(i['unit_price'])*int(i['quantity']) for i in items)-discount)
    cur2=conn.cursor()
    cur2.execute('INSERT INTO bills (customer_id,total_amount,discount,notes) VALUES (%s,%s,%s,%s)',
        (d['customer_id'],total,discount,d.get('notes','')))
    bid=cur2.lastrowid
    for item in items:
        qty=int(item['quantity']); up=float(item['unit_price'])
        cur2.execute('INSERT INTO bill_items (bill_id,medicine_id,quantity,unit_price,subtotal) VALUES (%s,%s,%s,%s,%s)',
            (bid,item['medicine_id'],qty,up,qty*up))
        cur2.execute('UPDATE medicines SET stock=stock-%s WHERE id=%s',(qty,item['medicine_id']))
        cur2.execute("INSERT INTO stock_transactions (medicine_id,type,quantity,notes) VALUES (%s,'sale',%s,%s)",
            (item['medicine_id'],qty,f'Bill #{bid}'))
    conn.commit(); conn.close()
    return jsonify({'message':'Bill created','id':bid,'total':total}),201

@app.route('/api/reports/sales')
@login_required
def sales_report():
    conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute("""SELECT DATE(bill_date) AS sale_date,COUNT(*) AS bill_count,SUM(total_amount) AS revenue
        FROM bills WHERE bill_date>=DATE_SUB(NOW(),INTERVAL 30 DAY)
        GROUP BY DATE(bill_date) ORDER BY sale_date DESC""")
    rows=cur.fetchall()
    for r in rows: r['sale_date']=str(r['sale_date']); r['revenue']=float(r['revenue'])
    conn.close(); return jsonify(rows)


# =============================================================
#  MODULE 6 — CUSTOMER MANAGEMENT
# =============================================================
@app.route('/api/customers',methods=['GET'])
@login_required
def get_customers():
    conn=get_db(); cur=conn.cursor(dictionary=True)
    cur.execute('SELECT * FROM customers ORDER BY name')
    rows=cur.fetchall()
    for r in rows:
        if r.get('created_at'): r['created_at']=str(r['created_at'])
    conn.close(); return jsonify(rows)

@app.route('/api/customers',methods=['POST'])
@login_required
def add_customer():
    d=request.json; conn=get_db(); cur=conn.cursor()
    cur.execute('INSERT INTO customers (name,phone,email,address) VALUES (%s,%s,%s,%s)',
        (d['name'],d.get('phone'),d.get('email'),d.get('address')))
    conn.commit(); new_id=cur.lastrowid; conn.close()
    return jsonify({'message':'Customer added','id':new_id}),201

@app.route('/api/customers/<int:cid>',methods=['PUT'])
@login_required
def update_customer(cid):
    d=request.json; conn=get_db(); cur=conn.cursor()
    cur.execute('UPDATE customers SET name=%s,phone=%s,email=%s,address=%s WHERE id=%s',
        (d['name'],d.get('phone'),d.get('email'),d.get('address'),cid))
    conn.commit(); conn.close(); return jsonify({'message':'Customer updated'})

@app.route('/api/customers/<int:cid>',methods=['DELETE'])
@login_required
def delete_customer(cid):
    conn=get_db(); cur=conn.cursor()
    cur.execute('DELETE FROM customers WHERE id=%s',(cid,)); conn.commit(); conn.close()
    return jsonify({'message':'Customer deleted'})


# =============================================================
#  DASHBOARD
# =============================================================
@app.route('/api/dashboard')
@login_required
def dashboard():
    conn=get_db(); cur=conn.cursor(dictionary=True)
    def q(sql): cur.execute(sql); return list(cur.fetchone().values())[0]
    data={
        'total_medicines': q('SELECT COUNT(*) FROM medicines'),
        'total_customers': q('SELECT COUNT(*) FROM customers'),
        'total_revenue':   float(q('SELECT COALESCE(SUM(total_amount),0) FROM bills')),
        'total_bills':     q('SELECT COUNT(*) FROM bills'),
        'total_suppliers': q('SELECT COUNT(*) FROM suppliers'),
        'out_of_stock':    q('SELECT COUNT(*) FROM medicines WHERE stock=0'),
        'low_stock':       q('SELECT COUNT(*) FROM medicines WHERE stock>0 AND stock<=10'),
        'total_users':     q('SELECT COUNT(*) FROM users'),
    }
    conn.close(); return jsonify(data)


if __name__=='__main__':
    init_database()
    app.run(host='0.0.0.0',port=5000,debug=True)
