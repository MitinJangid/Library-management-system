from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
import os
from werkzeug.utils import secure_filename
import csv
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/images'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DATABASE = 'students.db'

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS students (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL,
                        Father_name TEXT NOT NULL,
                        Father_occupation TEXT NOT NULL,
                        Mother_name TEXT NOT NULL,
                        Mother_occupation TEXT NOT NULL,
                        contact TEXT NOT NULL,
                        gender TEXT,
                        address TEXT NOT NULL,
                        photo TEXT,
                        aadhaar TEXT,
                        created_at TEXT
                    )''')

        conn.execute('''CREATE TABLE IF NOT EXISTS fees (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id INTEGER,
                        month TEXT,
                        year INTEGER,
                        amount_paid INTEGER,
                        date_paid DATE,
                        remark TEXT,
                        FOREIGN KEY (student_id) REFERENCES students(id)
                    )''')

@app.route('/')
def home():
    return render_template('form.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    email = request.form['email']
    Father_name = request.form['F-name']
    Father_occupation = request.form['F-OCC-name']
    Mother_name = request.form['M-name']
    Mother_occupation = request.form['M-OCC-name']
    contact = request.form['contact']
    gender = request.form['gender']
    address = request.form['address']
    photo = request.files['photo']
    aadhaar = request.files['aadhaar']

    photo_filename = secure_filename(photo.filename)
    photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))

    aadhaar_filename = secure_filename(aadhaar.filename)
    aadhaar.save(os.path.join(app.config['UPLOAD_FOLDER'], aadhaar_filename))

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''INSERT INTO students 
                        (name, email, Father_name, Father_occupation, Mother_name, Mother_occupation, contact, gender, address, photo, aadhaar, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (name, email, Father_name, Father_occupation, Mother_name, Mother_occupation, contact, gender, address, photo_filename, aadhaar_filename, created_at))

    return redirect(url_for('home', success=1))
@app.route('/pending-fees')
def pending_fees():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    today = datetime.now()

    cursor.execute("SELECT id, name, contact, created_at FROM students")
    students = cursor.fetchall()

    pending_students = []

    for student in students:
        student_id, name, contact, created_at = student
        reg_date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")

        due_day = reg_date.day
        try:
            due_date_this_month = datetime(today.year, today.month, due_day)
        except ValueError:
            # Skip invalid dates (e.g. Feb 30)
            continue

        if today >= due_date_this_month:
            due_month = due_date_this_month.strftime("%B").lower()
            due_year = due_date_this_month.year

            cursor.execute('''
                SELECT 1 FROM fees
                WHERE student_id = ? AND LOWER(month) = ? AND year = ?
            ''', (student_id, due_month, due_year))
            if not cursor.fetchone():
                # Add due date string here (format: yyyy-mm-dd)
                due_date_str = due_date_this_month.strftime("%Y-%m-%d")
                pending_students.append((student_id, name, contact, due_date_str))

    conn.close()
    return render_template('pending_fees.html', students=pending_students)


@app.route('/pay_fees/<int:student_id>', methods=['POST'])
def pay_fees(student_id):
    amount = request.form['amount']
    remark = request.form.get('remark', '')
    now = datetime.now()
    month = now.strftime('%B').lower()
    year = now.year
    date_paid = now.strftime('%Y-%m-%d')

    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''
            INSERT INTO fees (student_id, month, year, amount_paid, date_paid, remark)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (student_id, month, year, amount, date_paid, remark))
        conn.commit()

    return redirect(url_for('pending_fees'))

@app.route('/students')
def students():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students")
        student_list = cursor.fetchall()
    return render_template('students.html', students=student_list)

@app.route('/download')
def download():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students")
        data = cursor.fetchall()

    csv_path = os.path.join(app.config['UPLOAD_FOLDER'], 'students.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Name', 'Email', 'Father\'s Name', 'Father\'s Occupation',
                         'Mother\'s Name', 'Mother\'s Occupation', 'Contact', 'Gender', 
                         'Address', 'Photo', 'Aadhaar', 'Registration Time'])
        writer.writerows(data)

    return send_file(csv_path, as_attachment=True)

@app.route('/fees', methods=['GET', 'POST'])
def fees():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    if request.method == 'POST':
        student_id = request.form['student_id']
        month = request.form['month'].lower()
        year = request.form['year']
        amount_paid = request.form['amount_paid']
        remark = request.form['remark']
        date_paid = datetime.now().date().isoformat()

        c.execute('''INSERT INTO fees 
                     (student_id, month, year, amount_paid, date_paid, remark) 
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (student_id, month, year, amount_paid, date_paid, remark))
        conn.commit()

    c.execute('SELECT id, name FROM students')
    students = c.fetchall()

    selected_student_id = request.args.get('student_id')
    if selected_student_id:
        c.execute('''
            SELECT s.name, f.month, f.year, f.amount_paid, f.date_paid, f.remark
            FROM fees f
            JOIN students s ON f.student_id = s.id
            WHERE f.student_id = ?
        ''', (selected_student_id,))
        fees_data = c.fetchall()
    else:
        c.execute('''
            SELECT s.name, f.month, f.year, f.amount_paid, f.date_paid, f.remark
            FROM fees f
            JOIN students s ON f.student_id = s.id
        ''')
        fees_data = c.fetchall()

    conn.close()
    return render_template('fees.html', students=students, fees_data=fees_data)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
