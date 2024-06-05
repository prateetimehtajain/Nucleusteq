import pytest
from unittest.mock import patch, MagicMock
from app import app, is_valid_email, run_app
from flask import session
import webbrowser
@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['secretkey'] = 'mysecretkey'
    with app.test_client() as client:
        with app.app_context():
            yield client
            
class MockCursor:
    def __init__(self):
        self.fetchall_data = None
        self.data=None
        self.commit_called = False
        self.close_called = False
        self.queries = []
    def execute(self, query, params=None):
        self.queries.append((query, params))

    def fetchone(self):
        return self.data

    def fetchall(self):
        return self.fetchall_data if self.fetchall_data is not None else []

    def close(self):
        pass

    def close(self):
        self.close_called = True

    def commit(self):
        self.commit_called = True

    def execute(self, query, params=None):
        self.executed_query = query
        self.executed_params = params

@pytest.fixture
def mock_db():
    mock_cursor = MockCursor()
    with patch('flask_mysqldb.MySQL.connection', new_callable=MagicMock) as mock_conn:
        mock_conn.cursor.return_value = mock_cursor
        yield mock_cursor

def test_is_valid_email():
    assert is_valid_email('test@nucleusteq.com') == True
    assert is_valid_email('invalid@example.com') == False

def test_login_valid(client, mock_db):
    mock_db.data = (1, 'password', 0, 'John Doe')
    response = client.post('/login', data={'email': 'test@nucleusteq.com', 'password': 'password'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Employee Details' in response.data

def test_login_invalid_email(client, mock_db):
    mock_db.data = None
    response = client.post('/login', data={'email': 'invalid@example.com', 'password': 'password'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid email. Please use company email address.' in response.data

def test_admin_dashboard(client, mock_db):
    mock_db.data = (5,)
    mock_db.fetchall_data = [(5,), (10,), (15,), (5,)]
    with client.session_transaction() as sess:
        sess['name'] = 'Admin'
    response = client.get('/admin_dashboard')
    assert response.status_code == 200
    assert b'Admin Dashboard' in response.data

def test_view_employee_item(client, mock_db):
    mock_db.data = {'Itemid': 1, 'Itemname': 'Item1', 'Serialno': 'SN12345', 'empid': 1}
    response = client.get('/view_employee_item/1')
    assert response.status_code == 200
    assert b'Item1' in response.data
    assert b'SN12345' in response.data

def test_add_employee(client, mock_db):
    form_data = {
        'employee_id': 123,
        'name': 'John Doe',
        'email': 'test@nucleusteq.com',
        'password': 'password',
        'position': 'Employee'
    }
    with client.session_transaction() as sess:
        sess['name'] = 'Admin'
    with patch('app.mysql.connection.cursor', return_value=mock_db), \
         patch('app.mysql.connection.commit') as mock_commit:
        response = client.post('/add_employee', data=form_data, follow_redirects=True)

    assert response.status_code == 200
 

    mock_db.execute(
        "INSERT INTO employee(empid, name, email, password, position) VALUES (%s, %s, %s, %s, %s)",
        (123, 'John Doe', 'john@example.com', 'password', 1)  
    )

    mock_commit.assert_called_once()

def test_delete_employee(client, mock_db):
    mock_db.data = [{'itemid': 1}, {'itemid': 2}]
    response = client.get('/delete_employee/123')
    assert response.status_code == 302 
    assert response.location == '/employee_details'

def test_employee_details(client, mock_db):
    mock_db.fetchall_data = ({'Empid': 1, 'Name': 'John Doe', 'Email': 'john@example.com', 'Password': 'password', 'Position': 1},{'Empid': 2, 'Name': 'Jane Smith', 'Email': 'jane@example.com', 'Password': '1234', 'Position': 1},)
    with client.session_transaction() as sess:
        sess['name'] = 'Admin'
    response = client.get('/employee_details')
    assert response.status_code == 200
    assert b'Employee Details' in response.data

def test_update_password(client, mock_db):
    mock_db.data = ('old_password',)
    with client.session_transaction() as sess:
        sess['employee_id'] = 1
    response = client.post('/update_password', data={'old_password': 'old_password', 'new_password': 'new_password'})

    assert response.status_code == 302
    assert response.location == '/admin_dashboard'

def test_employee_dashboard(client, mock_db):
    with client.session_transaction() as sess:
        sess['employee_id'] = 123
        sess['name'] = 'John Doe'

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {'Itemid': 1, 'Itemname': 'Item 1', 'Serialno': '123'},
        {'Itemid': 2, 'Itemname': 'Item 2', 'Serialno': '456'}
    ]
    mock_connection = MagicMock()
    mock_connection.cursor.return_value = mock_cursor

    with patch('app.mysql.connection', mock_connection):
        response = client.get('/employee_dashboard')

    assert response.status_code == 200
    assert b'Employee Dashboard' in response.data
    assert b'Item 1' in response.data
    assert b'Item 2' in response.data
    mock_cursor.execute.assert_called_once_with("SELECT * from inventory where empid=%s", (123,))
    mock_cursor.fetchall.assert_called_once()
    assert session['employee_id'] == 123
    assert session['name'] == 'John Doe'

def test_update_password_employee(client, mock_db):
    with client.session_transaction() as sess:
        sess['employee_id'] = 123

    form_data = {
        'old_password': 'old_password',
        'new_password': 'new_password'
    }

    with patch('app.mysql.connection.cursor') as mock_cursor_factory:
        mock_execute = mock_cursor_factory.return_value.__enter__.return_value.execute
        response = client.post('/update_password_employee', data=form_data)
    mock_execute(
        "UPDATE employee SET password=%s WHERE empid=%s", ('new_password', 123))
    assert response.location == '/employee_dashboard'

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/login")

@patch('webbrowser.open_new')
def test_open_browser(mock_open_new):
    open_browser()
    mock_open_new.assert_called_once_with("http://127.0.0.1:5000/login")

def test_logout(client):

    with client.session_transaction() as sess:
        sess['employee_id'] = 123    
    response = client.get('/logout')

    with client.session_transaction() as sess:
        assert 'employee_id' not in sess
    assert response.status_code == 200
    assert b'Login' in response.data

def test_update_password_employee(client, mock_db):
    mock_db.data = ('old_password',)
    with client.session_transaction() as sess:
        sess['employee_id'] = 1
    response = client.post('/update_password_employee', data={'old_password': 'old_password', 'new_password': 'new_password'})

    assert response.status_code == 302
    assert response.location == '/employee_dashboard'

def test_add_item(client, mock_db):
    form_data = {
        'itemid': '1',
        'itemname': 'Laptop',
        'serialno': 'ABC123',
        'billno': '123456',
        'purchasedate': '2023-01-01',
        'warranty': '2 years',
        'price': '1000',
        'categoryname': 'Electronics'
    }
    with client.session_transaction() as sess:
        sess['name'] = 'Admin'
    with patch('app.mysql.connection.cursor', return_value=mock_db), \
         patch('app.mysql.connection.commit') as mock_commit:
        response = client.post('/add_item', data=form_data, follow_redirects=True)

    assert response.status_code == 200
 

    mock_db.execute(
        "INSERT into inventory(Itemid,Itemname,Serialno,Billno,Purchasedate,Warranty,Price,Categoryname) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        ('1', 'Laptop', 'ABC123', '123456', '2023-01-01', '2 years', '1000', 'Electronics')
    )

    mock_commit.assert_called_once()

def test_delete_item(client, mock_db):
    response = client.get('/delete_item/123')
    assert response.status_code == 302 
    assert response.location == '/all_items'

def test_all_items(client, mock_db):

    mock_db.fetchall_data = (
        {'Itemid': 1, 'Itemname': 'Laptop', 'Empid': 'NULL'},
        {'Itemid': 2, 'Itemname': 'Monitor', 'Empid': 101}
    )

    with client.session_transaction() as sess:
        sess['name'] = 'Admin'
    response = client.get('/all_items')
    assert response.status_code == 200
    assert b'All Items' in response.data

    assert response.status_code == 200
    assert b'Admin' in response.data
    assert b'Laptop' in response.data
    assert b'Monitor' in response.data
    assert b'Assigned' in response.data

def test_assigned_items(client, mock_db):
    mock_db.fetchall_data = (
        {'Itemid': 1, 'Itemname': 'Laptop', 'Serialno': '1234', 'Billno': '5678', 'Purchasedate': '2023-01-01', 'Warranty': '2 years', 'Price': 1000, 'Categoryname': 'Electronics', 'empid': 101, 'name': 'Naman Khanna'},
        {'Itemid': 2, 'Itemname': 'Monitor', 'Serialno': '4321', 'Billno': '8765', 'Purchasedate': '2023-02-01', 'Warranty': '1 year', 'Price': 200, 'Categoryname': 'Electronics', 'empid': 102, 'name': 'Luv Jain'}
    )

    with client.session_transaction() as sess:
        sess['name'] = 'Admin'
    response = client.get('/assigned_items')
    
    assert response.status_code == 200
    assert b'Assigned Items' in response.data

    assert response.status_code == 200
    assert b'Admin' in response.data
    assert b'Laptop' in response.data
    assert b'Monitor' in response.data
    assert b'Naman Khanna' in response.data
    assert b'Luv Jain' in response.data

def test_run_app():
    with patch('app.app.run') as mock_run:
        run_app()
        mock_run.assert_called_once_with(debug=True, use_reloader=False)

def test_view_item(client, mock_db):
    mock_db.data = {'Itemid': 123, 'Itemname': 'Item1', 'Serialno': 'SN12345', 'empid': 1}
    response = client.get('/view_item/123')
    assert response.status_code == 200
    assert b'Item1' in response.data
    assert b'SN12345' in response.data

def test_unassigned_items(client, mock_db):
    mock_db.fetchall_data = (
        {'Itemid': 1, 'Itemname': 'Laptop', 'Serialno': '1234', 'Billno': '5678', 'Purchasedate': '2023-01-01', 'Warranty': '2 years', 'Price': 1000, 'Categoryname': 'Electronics'},
        {'Itemid': 2, 'Itemname': 'Monitor', 'Serialno': '4321', 'Billno': '8765', 'Purchasedate': '2023-02-01', 'Warranty': '1 year', 'Price': 200, 'Categoryname': 'Electronics'}
    )

    with client.session_transaction() as sess:
        sess['name'] = 'Admin'
    response = client.get('/unassigned_items')
    
    assert response.status_code == 200
    assert b'Unassigned Items' in response.data

    assert response.status_code == 200
    assert b'Admin' in response.data
    assert b'Laptop' in response.data
    assert b'Monitor' in response.data

def test_view_unassigned_item(client, mock_db):
    mock_db.data = {'Itemid': 123, 'Itemname': 'Item1', 'Serialno': 'SN12345'}
    response = client.get('/view_unassigned_item/123')
    assert response.status_code == 200
    assert b'Item1' in response.data
    assert b'SN12345' in response.data

def test_unassign_employee(client, mock_db):
    item_id = 1
    response = client.get(f'/unassign_employee/{item_id}')
    assert mock_db.executed_query == "UPDATE inventory set empid=NULL where itemid=%s"
    assert mock_db.executed_params == (item_id,)
    assert response.status_code == 302
    assert response.location == '/assigned_items'

def test_employee_assign(client, mock_db):
    item_id = 1
    mock_db.data = ['category1']
    mock_db.fetchall_data = [('Employee1',), ('Employee2',)]
    response = client.get(f'/employee_assign/{item_id}')
    assert mock_db.close_called
    assert response.status_code == 200
    assert b'Employee1' in response.data
    assert b'Employee2' in response.data
    mock_db.queries = []
    mock_db.data = [1] 
    mock_db.close_called = False
    mock_db.commit_called = False
    response = client.post(f'/employee_assign/{item_id}', data={'name': 'Employee1'})
    assert response.status_code == 302
    assert response.location == '/unassigned_items'