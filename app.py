from flask import Flask, render_template, request, redirect, jsonify, session, url_for, flash
from bplustree import BPlusTree
import json
import os
import secrets,random,string

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)   # Set a secret key for session management

data_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

db_file = os.path.join(data_directory, 'employee_data.json')
manager_file = os.path.join(data_directory, 'manager_data.json')
inventory_file = os.path.join(data_directory, 'inventory_data.json')
reservation_file = os.path.join(data_directory, 'reservation_data.json')
contact_file = os.path.join(data_directory, 'contact_data.json')
order_file = os.path.join(data_directory, 'order_data.json')

order_data = {}  
inventory_data = {}
reservation_data = {}
contact_data = {}


@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if 'id' in session:
        if request.method == 'POST':
            product_name = request.json['name']
            product_quantity = request.json['quantity']
            product_id = len(inventory_data) + 1

            product = {
                'name': product_name,
                'quantity': product_quantity
            }

            inventory_data[str(product_id)] = product

            save_inventory_data()

            return 'Product added successfully!'
        else:
            return render_template('inventory.html', inventory=inventory_data)

    else:
        return redirect(url_for('dashboard'))


@app.route('/inventory_data', methods=['GET'])
def get_inventory_data():
    if 'id' in session:
        return json.dumps(inventory_data)
    else:
        return redirect(url_for('dashboard'))


def load_inventory_data():
    global inventory_data
    if os.path.exists(inventory_file):
        with open(inventory_file, 'r') as f:
            inventory_data = json.load(f)
    else:
        inventory_data = {}  # Initialize as an empty dictionary if the file doesn't exist


def save_inventory_data():
    with open(inventory_file, 'w') as f:
        json.dump(inventory_data, f,indent=4)


@app.route('/decrease_quantity', methods=['POST'])
def decrease_quantity():
    if 'id' in session:
        product_id = request.form['product_id']
        if product_id in inventory_data:
            product = inventory_data[product_id]
            quantity = int(product['quantity'])

            if quantity > 0:
                product['quantity'] = quantity - 1
                save_inventory_data()
                flash('Quantity decreased successfully!', 'success')
            else:
                flash('Cannot decrease quantity. It is already zero.', 'warning')
        else:
            flash('Product not found', 'danger')
    else:
        return redirect(url_for('dashboard'))

    return redirect(url_for('inventory'))


@app.route('/increase_quantity', methods=['POST'])
def increase_quantity():
    if 'id' in session:
        product_id = request.form['product_id']
        if product_id in inventory_data:
            product = inventory_data[product_id]
            product['quantity'] = int(product['quantity']) + 1
            save_inventory_data()

            flash('Quantity increased successfully!', 'success')
        else:
            flash('Product not found', 'danger')
    else:
        return redirect(url_for('dashboard'))

    return redirect(url_for('inventory'))

from datetime import datetime, timedelta

reservation_counter = {}

@app.route('/reservation', methods=['POST'])
def create_reservation():
    name = request.form.get('name')
    email = request.form.get('email')
    datetime_str = request.form.get('Datetime')
    select1 = request.form.get('select1')

    # Convert the selected datetime string to a datetime object
    selected_datetime = datetime.fromisoformat(datetime_str.replace('T', ' '))

    # Calculate the end time for the selected reservation
    end_datetime = selected_datetime + timedelta(hours=2)

    # Check if the maximum limit of reservations within the 2-hour time frame has been reached
    available_tables = list(range(1, 7))  # List of available table numbers
    for dt in reservation_counter:
        if dt >= selected_datetime and dt < end_datetime:
            if reservation_counter[dt] >= 6:
                # Remove already reserved table numbers from the available_tables list
                reserved_table_numbers = set()
                for reservation in reservation_data.values():
                    if datetime.fromisoformat(reservation['datetime'].replace('T', ' ')) == dt:
                        reserved_table_numbers.add(reservation['table_number'])

                # If all tables are reserved, return a response indicating unavailability
                if len(reserved_table_numbers) == 6:
                    return '''
                    <script>
                        alert("Reservation is not available for the selected date and time.");
                        window.history.back();
                    </script>
                    '''
                # Remove the reserved table numbers from the available_tables list
                available_tables = list(set(available_tables) - reserved_table_numbers)
    
    # Assign a random table number from the available_tables list
    table_number = random.choice(available_tables)

    # Increment the counter for each reservation slot within the 2-hour time frame
    current_datetime = selected_datetime
    while current_datetime < end_datetime:
        reservation_counter[current_datetime] = reservation_counter.get(current_datetime, 0) + 1
        current_datetime += timedelta(minutes=30)

    # Create a reservation object
    reservation = {
        'name': name,
        'email': email,
        'datetime': datetime_str,
        'select1': select1,
        'table_number': table_number
    }

    # Generate a unique reservation ID
    reservation_id = generate_reservation_id()

    # Store the reservation in the reservation data dictionary using the ID as the key
    reservation_data[reservation_id] = reservation

    # Save the reservation data and limits to the JSON files
    save_reservation_data()

    # Redirect to the reservation success page
    return '''
                    <script>
                        alert("Reservation success");
                        window.history.back();
                    </script>
                    '''

def generate_reservation_id():
    # Implement your logic to generate a unique reservation ID
    # You can use a library like uuid or generate a random string
    # Here's an example of generating a random string of 8 characters
    return secrets.token_hex(4)


def load_reservation_data():
    global reservation_data
    if os.path.exists(reservation_file):
        with open(reservation_file, 'r') as f:
            reservation_data = json.load(f)
    else:
        reservation_data = {}  # Initialize as an empty dictionary if the file doesn't exist


def save_reservation_data():
    with open(reservation_file, 'w') as f:
        json.dump(reservation_data, f,indent=4)



@app.route('/cancel_reservation', methods=['POST'])
def cancel_reservation():
    # Check if the reservation_data dictionary is not empty
    if reservation_data:
        # Get the last reservation ID
        last_reservation_id = list(reservation_data.keys())[-1]

        # Delete the last reservation entry
        del reservation_data[last_reservation_id]
        
        # Save the updated reservation data to the file
        save_reservation_data()

        flash('Last reservation canceled successfully!', 'success')
    else:
        flash('No reservations found', 'danger')

    return redirect(url_for('booking'))



def get_latest_reservation_id():
    if reservation_data:
        return max(reservation_data.keys())
    else:
        return None

@app.route('/view_reservation')
def view_reservations():
    if 'employee_id' in session or 'id' in session:
        return render_template('reservation.html', reservations=reservation_data)
    else:
        return redirect(url_for('dashboard'))

@app.route('/delete_reservation', methods=['POST'])
def delete_reservation():
    if 'id' in session:
        reservation_id = request.form['reservation_id']
        if reservation_id in reservation_data:
            del reservation_data[reservation_id]
            save_reservation_data()
            flash('Reservation deleted successfully!', 'success')
        else:
            flash('Reservation not found', 'danger')
    else:
        return redirect(url_for('dashboard'))

    return redirect(url_for('view_reservations'))


@app.route('/')
def home():
    if 'employee_id' in session or 'id' in session:
        return redirect(url_for('dashboard'))
    else:
        return render_template('index.html')


@app.route('/booking')
def booking():
    return render_template('booking.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/dashboard')
def dashboard():
    if 'employee_id' in session:
        if os.path.exists(db_file):
            with open(db_file, 'r') as f:
                tree = json.load(f)
        else:
            tree = {}
        return render_template('dashboard.html', data=tree)
    else:
        return redirect(url_for('signin'))


@app.route('/employee')
def employee():
    return render_template('view.html')


@app.route('/delete_employee', methods=['POST'])
def delete_employee():
    if 'id' in session:
        employee_id = request.form['employee_id']
        if os.path.exists(db_file):
            with open(db_file, 'r') as f:
                tree = json.load(f)
        else:
            tree = {}

        if employee_id in tree:
            del tree[employee_id]
            save_employee_data(tree)
            flash('Employee deleted successfully!', 'success')
        else:
            flash('Employee not found', 'danger')
    else:
        return redirect(url_for('dashboard'))

    return redirect(url_for('view'))


def save_employee_data(tree):
    with open(db_file, 'w') as f:
        json.dump(tree, f,indent=4)


@app.route('/orders')
def order():
    return render_template('order.html')

@app.route('/menu')
def menu():
    return render_template('menu.html')

@app.route('/payment_form')
def payment():
    return render_template('payment_form.html')


@app.route('/signup')
def signup():
    return render_template('registration.html')


@app.route('/register', methods=['POST'])
def process_registration():
    try:
        employee_id = request.form['employee_id']
        name = request.form['name']
        mobile_number = request.form['mobile_number']
        password = request.form['password']

        if os.path.exists(db_file):
            with open(db_file, 'r') as f:
                tree = json.load(f)
        else:
            tree = {}

        tree[employee_id] = {
            'name': name,
            'mobile_number': mobile_number,
            'password': password
        }

        with open(db_file, 'w') as f:
            json.dump(tree, f,indent=4)

        return 'Registration successful!'
    except Exception as e:
        return f'An error occurred: {str(e)}'



@app.route('/view')
def view():
    if os.path.exists(db_file):
        with open(db_file, 'r') as f:
            tree = json.load(f)
    else:
        tree = {}

    return render_template('view.html', data=tree)


@app.route('/signin')
def signin():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    try:
        employee_id = request.form['employee_id']
        password = request.form['password']

        if os.path.exists(db_file):
            with open(db_file, 'r') as f:
                tree = json.load(f)

            if employee_id in tree and tree[employee_id]['password'] == password:
                session['employee_id'] = employee_id  # Store employee ID in session
                return redirect(url_for('dashboard'))
            else:
                return 'Invalid employee ID or password'
        else:
            return 'No registered employees found'
    except Exception as e:
        return f'An error occurred: {str(e)}'
    
@app.route('/manlogin')
def msignin():
    return render_template('mlogin.html')
@app.route('/mlogin', methods=['POST'])
def mlogin():
    try:
        id = request.form['id']
        password = request.form['password']

        if os.path.exists(manager_file):
            with open(manager_file, 'r') as f:
                tree = json.load(f)

            if id in tree and tree[id]['password'] == password:
                session['id'] = id  # Store employee ID in session
                return redirect(url_for('mdashboard'))
            else:
                return 'Invalid ID or password'
        else:
            return 'No registered manager found'
    except Exception as e:
        return f'An error occurred: {str(e)}'

@app.route('/mdashboard')
def mdashboard():
    if 'id' in session:
        if os.path.exists(manager_file):
            with open(manager_file, 'r') as f:
                tree = json.load(f)
        else:
            tree = {}
        return render_template('mdash.html', data=tree)
    else:
        return redirect(url_for('manlogin'))

@app.route('/signout')
def signout():
    return render_template('logout.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('employee_id', None)  # Remove employee ID from session
    return render_template('login.html')

@app.route('/msignout')
def esignout():
    return render_template('mlogout.html')

@app.route('/mlogout', methods=['POST'])
def manlogout():
    session.pop('id', None)
    return render_template('mlogin.html')

@app.route('/payment', methods=['GET', 'POST'])
def payment_form():
    if request.method == 'POST':
        cardno = request.form['cardno']
        exp = request.form['exp']
        cvv = request.form['cvv']
        # Process the payment details and perform any necessary actions

        return redirect('/psuccess')  # Redirect to payment success page

    return render_template('payment_form.html')


@app.route('/psuccess')
def payment_success():
    return render_template('psuccess.html')


@app.route('/cancel')
def cancel_payment():
    # Handle cancellation logic here
    return redirect('/')

@app.route('/billing')
def billing():
        # Load data from the bills.json file
    with open('bills.json', 'r') as file:
        bills_data = json.load(file)

    # Pass the data to the template for rendering
    return render_template('billing.html', bills=bills_data)

@app.route('/send_message', methods=['POST'])
def send_message():
    name = request.form['name']
    email = request.form['email']
    subject = request.form['subject']
    message = request.form['message']

    # Create a dictionary with contact details
    contact = {
        'name': name,
        'email': email,
        'subject': subject,
        'message': message
    }

        # Generate a unique reservation ID (you can use a library like uuid for this)
    contact_id = generate_reservation_id()

    # Store the reservation in the reservation data dictionary using the ID as the key
    contact_data[contact_id] = contact

    # Save the reservation data to a JSON file
    save_contact_data()

    return redirect('/')

    
def load_contact_data():
    global contact_data
    if os.path.exists(contact_file):
        with open(contact_file, 'r') as f:
            contact_data = json.load(f)
    else:
        contact_data = {}  # Initialize as an empty dictionary if the file doesn't exist

def save_contact_data():
    with open(contact_file, 'w') as f:
        json.dump(contact_data, f,indent=4)

@app.route('/generate-bill', methods=['POST'])
def generate_bill():
    data = request.json

    # Generate a random bill number
    bill_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))

    # Extract the table number and total amount from the data
    table_number = data['table_number']
    total_amount = data['total_amount']

    # Add the bill number to the data
    data['bill_number'] = bill_number

    # Add the payment status as "not received" to the data
    data['payment_status'] = 'Not Received'

    # Create the bills.json file if it doesn't exist
    if not os.path.exists('bills.json'):
        open('bills.json', 'w').close()

    # Load existing data from the file
    existing_data = []
    if os.path.getsize('bills.json') > 0:
        try:
            with open('bills.json', 'r') as file:
                existing_data = json.load(file)
        except json.JSONDecodeError:
            # Invalid JSON data, treat it as an empty list
            existing_data = []

    # Append the new data to the existing data
    existing_data.append(data)

    # Save the updated data to the JSON file
    with open('bills.json', 'w') as file:
        json.dump(existing_data, file, indent=4)

    return jsonify({'message': 'Bill generated successfully', 'bill_number': bill_number})

@app.route('/display-bills')
def display_bills():
    # Load data from the bills.json file
    with open('bills.json', 'r') as file:
        bills_data = json.load(file)

    # Pass the data to the template for rendering
    return render_template('bills.html', bills=bills_data)

@app.route('/mark-as-paid', methods=['POST'])
def mark_as_paid():
    bill_number = request.form.get('bill_number')

    # Load data from the bills.json file
    with open('bills.json', 'r') as file:
        bills_data = json.load(file)

    # Find the bill with the given bill number and update its payment status
    for bill in bills_data:
        if bill['bill_number'] == bill_number:
            bill['payment_status'] = 'Received'
            break

    # Save the updated data to the JSON file
    with open('bills.json', 'w') as file:
        json.dump(bills_data, file, indent=4)

    return '''
                    <script>
                        alert("Payment marked as received");
                        window.history.back();
                    </script>
                    '''

if __name__ == '__main__':
    load_inventory_data()
    load_reservation_data()
    load_contact_data()
    app.run(debug=True)
