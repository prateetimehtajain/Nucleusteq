from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
import re
from MySQLdb.cursors import DictCursor
import webbrowser
import logging


app = Flask(__name__)
app.secret_key = 'mysecretkey'

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456789'
app.config['MYSQL_DB'] = 'inventorypro'
mysql = MySQL(app)


def is_valid_email(email):
    regex=rf'^[a-zA-Z][a-zA-Z0-9._%+-]+@{"nucleusteq.com"}$'
    if re.fullmatch(regex, email):
        return True
    else:
        return False

def open_browser():
    logging.info("Opening browser")
    webbrowser.open_new("http://127.0.0.1:5000/login")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if not is_valid_email(email):
            flash(f"Invalid email. Please use company email address.")
            return redirect(url_for('login'))
        
        # Here you would typically check the password and handle login
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT empid, password, position, name FROM employee WHERE email = %s", (email,))
        employee = cursor.fetchone()
        cursor.close()

        if employee and password==employee[1]:
            session['employee_id'] = employee[0]
            session['email'] = email
            session['position'] = employee[2]
            session['name']=employee[3]
            if employee[2] == 0:
                logging.info("Direct to admin dashboard")
                return redirect(url_for('admin_dashboard'))           
            else:
                logging.info("Direct to employee dashboard")
                return redirect(url_for('employee_dashboard'))
        else:
            logging.info("Wrong email or password entered")
            flash("Invalid email or password")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    name = session.get('name')
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT Count(*) from employee")
    count_row = cursor.fetchone()
    count = count_row[0] if count_row else 0
    cursor.execute("SELECT count(*) from inventory where empid is not NULL")
    assigned_row = cursor.fetchone()
    assigned = assigned_row[0] if assigned_row else 0
    cursor.execute("SELECT count(*) from inventory")
    total_row = cursor.fetchone()
    total = total_row[0] if total_row else 0
    unassigned = total - assigned
    cursor.execute("SELECT COUNT(DISTINCT empid) FROM inventory")
    employee_assigned_row = cursor.fetchone()
    employee_assigned = employee_assigned_row[0] if employee_assigned_row else 0
    logging.info("Admin dashboard accessed")
    return render_template("admin_dashboard.html", name=name, count=count, assigned=assigned, total=total, unassigned=unassigned, employee_assigned=employee_assigned)

@app.route('/employee_dashboard')
def employee_dashboard():
    employee_id=session['employee_id']
    name=session.get('name')
    cursor=mysql.connection.cursor(DictCursor)
    cursor.execute("SELECT * from inventory where empid=%s",(employee_id,))
    items=cursor.fetchall()
    logging.info("Dashboard accessed")
    return render_template('employee_dashboard.html',name=name,items=items)

@app.route('/view_employee_item/<int:item_id>')
def view_employee_item(item_id):
    cursor = mysql.connection.cursor(DictCursor)
    cursor.execute("SELECT * FROM inventory WHERE itemid = %s", (item_id,))
    item = cursor.fetchone()
    cursor.close()
    logging.info("Employee viewed item ")
    return render_template('view_employee_item.html', item=item)

@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        position=request.form['position']
        if position=="Employee":
            position=1
        else:
            position=0
        if not is_valid_email(email):
            flash(f"Invalid email. Please use valid email address.")
            return redirect(url_for('add_employee'))

        try:
            logging.info("Employee added")
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO employee(empid, name, email, password, position) VALUES (NULL, %s, %s, %s, %s)",
                 (name, email, password, position)
            )
            mysql.connection.commit()
            return redirect(url_for('admin_dashboard'))
        except:
            logging.info("Employee addition failed")
            mysql.connection.rollback()
            flash('Email already exists.')
            return redirect(url_for('add_employee'))
        finally:
            cursor.close()

    return render_template('add_employee.html')

@app.route('/delete_employee/<int:employee_id>',methods=['GET'])
def delete_employee(employee_id):
    cursor=mysql.connection.cursor(DictCursor)
    cursor.execute("SELECT itemid from inventory where empid=%s",(employee_id,))
    items=cursor.fetchall()
    for i in range(0,len(items)):
        item_id=items[i]['itemid']
        cursor.execute("UPDATE inventory SET empid=NULL where itemid=%s",(item_id,))
        mysql.connection.commit()
    cursor.close()
    cursor=mysql.connection.cursor()
    cursor.execute("DELETE from employee where empid=%s", (employee_id,))
    mysql.connection.commit()
    cursor.close()
    logging.info("Emloyee deleted successfully")
    return redirect(url_for("employee_details"))

@app.route('/employee_details')
def employee_details():
    name=session.get('name')
    cursor = mysql.connection.cursor(DictCursor)
    cursor.execute("SELECT * from employee where Position=1")
    items = cursor.fetchall()
    cursor.close()
    for i in range (0,len(items)):
            items[i]['Position']="Employee"
    logging.info("Employee details accesseds")
    return render_template('employee_details.html', items=items,name=name) 

@app.route('/update_password',methods=['GET','POST'])
def update_password():
    if request.method=='POST':
        old_password=request.form['old_password']
        new_password=request.form['new_password']
        employee_id = session.get('employee_id')
        cursor=mysql.connection.cursor()
        cursor.execute("SELECT password FROM employee WHERE empid = %s", (employee_id,))
        employee=cursor.fetchone()
        password=employee[0]
        if password==old_password:
            cursor.execute("UPDATE employee SET password=%s where empid=%s",(new_password,employee_id,))
            mysql.connection.commit()
            cursor.close()
            logging.info("Password updated")
            return redirect(url_for('admin_dashboard'))
        else:
            logging.info("Password update failed")
            flash("Please enter correct old password.")
            return redirect(url_for('update_password'))
    
    return render_template('update_password.html')

@app.route('/update_password_employee',methods=['GET','POST'])
def update_password_employee():
    if request.method=='POST':
        old_password=request.form['old_password']
        new_password=request.form['new_password']
        employee_id = session.get('employee_id')
        cursor=mysql.connection.cursor()
        cursor.execute("SELECT password FROM employee WHERE empid = %s", (employee_id,))
        employee=cursor.fetchone()
        password=employee[0]
        if password==old_password:
            logging.info("Password updated")
            cursor.execute("UPDATE employee SET password=%s where empid=%s",(new_password,employee_id,))
            mysql.connection.commit()
            cursor.close()
            return redirect(url_for('employee_dashboard'))
        else:
            logging.info("Password update failed")
            flash("Please enter correct old password.")
            return redirect(url_for('update_password_employee'))
    
    return render_template('update_password_employee.html')

@app.route('/logout')
def logout():
    logging.info("Logged out")
    session.pop('employee_id', None) 
    return render_template('login.html')

@app.route('/add_item',methods=['GET','POST'])
def add_item():
    if request.method=='POST':
        itemname=request.form['itemname']
        serial_no=request.form['serialno']
        bill_no=request.form['billno']
        purchase_date=request.form['purchasedate']
        warranty=request.form['warranty']
        price=request.form['price']
        category_name=request.form['categoryname']
        try:
            cursor=mysql.connection.cursor()
            cursor.execute(
                "INSERT into inventory(Itemid,Itemname,Serialno,Billno,Purchasedate,Warranty,Price,Categoryname) VALUES (NULL,%s,%s,%s,%s,%s,%s,%s)",
                (itemname,serial_no,bill_no,purchase_date,warranty,price,category_name)
            )
            mysql.connection.commit()
            logging.info("Item added successfully")
            return redirect(url_for('admin_dashboard'))
        except:
            mysql.connection.rollback()
            logging.info("Item addition failed")
            flash("Check for the correct Serial Number, Bill Number")
        finally:
            cursor.close()
    return render_template("add_item.html")

@app.route('/delete_item/<int:item_id>')
def delete_item(item_id):
    cursor = mysql.connection.cursor(DictCursor)
    logging.info("Item deleted successfully")
    cursor.execute("DELETE from inventory where itemid=%s", (item_id,))
    mysql.connection.commit()
    return redirect(url_for('all_items'))

@app.route('/all_items')
def all_items():
    name=session['name']
    cursor=mysql.connection.cursor(DictCursor)
    cursor.execute("SELECT * from inventory")
    items=cursor.fetchall()
    for i in range(0,len(items)):
        if items[i]['Empid']==None:
            items[i]['Empid']="Unassigned"
        else:
            items[i]['Empid']="Assigned"
    logging.info("All items displayed")
    return render_template('all_items.html',name=name,items=items)

@app.route('/assigned_items')
def assigned_items():
    name=session.get('name')
    cursor = mysql.connection.cursor(DictCursor)
    cursor.execute("SELECT i.*,e.name FROM inventory i JOIN employee e ON i.empid=e.empid where i.empid is NOT NULL")
    items = cursor.fetchall()
    cursor.close()
    logging.info("Assigned items displayed")
    return render_template('assigned_items.html', items=items,name=name)

@app.route('/view_item/<int:item_id>')
def view_item(item_id):
    cursor = mysql.connection.cursor(DictCursor)
    cursor.execute("SELECT i.*,e.name FROM inventory i JOIN employee e ON i.empid=e.empid WHERE itemid = %s", (item_id,))
    item = cursor.fetchone()
    cursor.close()
    logging.info("Assigned item viewed")
    return render_template('view_assigned_item.html', item=item)

@app.route('/unassigned_items')
def unassigned_items():
    name=session['name']
    cursor = mysql.connection.cursor(DictCursor)
    cursor.execute("SELECT * FROM inventory where empid is NULL")
    items = cursor.fetchall()
    cursor.close()
    logging.info("Unassigned items viewed")
    return render_template('unassigned_items.html', items=items,name=name)

@app.route('/view_unassigned_item/<int:item_id>')
def view_unassigned_item(item_id):
    cursor = mysql.connection.cursor(DictCursor)
    cursor.execute("SELECT * FROM inventory WHERE itemid = %s", (item_id,))
    item = cursor.fetchone()
    cursor.close()
    logging.info("An unassigned item viewed")
    return render_template('view_unassigned_item.html', item=item)

@app.route('/unassign_employee/<int:item_id>',methods=['GET'])
def unassign_employee(item_id):
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE inventory set empid=NULL where itemid=%s", (item_id,))
    mysql.connection.commit()
    cursor.close()
    logging.info("Employee unassigned successfully")
    return redirect(url_for('assigned_items'))

@app.route('/employee_assign/<int:item_id>',methods=['GET','POST'])
def employee_assign(item_id):
    cursor=mysql.connection.cursor()
    cursor.execute("SELECT categoryname from inventory where itemid=%s",(item_id,))
    item=cursor.fetchone()
    category=item[0]
    cursor.execute("SELECT e.name FROM employee e LEFT JOIN inventory i ON e.empid = i.empid AND i.categoryname =%s WHERE i.empid IS NULL and e.position=1",(category,))
    items = [row[0] for row in cursor.fetchall()]
    if request.method=="POST":
        name=request.form['name']
        cursor.execute("SELECT empid from employee where name=%s",(name,))
        employee_id=cursor.fetchone()
        cursor.execute("UPDATE inventory SET empid=%s where itemid=%s",(employee_id[0],item_id,))
        mysql.connection.commit()
        logging.info("Employee Assigned to the")
        return redirect(url_for("unassigned_items"))
    cursor.close()


    return render_template("assign_employee.html", item_id=item_id,items=items)

logging.basicConfig(
    filename='app.log', 
    filemode='w',
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def run_app():
    logging.info("Running app")
    app.run(debug=True, use_reloader=False)
            
if __name__ == "__main__":
    logging.info("Acquired lock, starting operations")
    open_browser() 
    run_app()
    logging.info("Operations completed, releasing lock")

