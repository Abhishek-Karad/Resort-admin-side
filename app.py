from flask import Flask, render_template,flash,session, request, redirect, url_for, jsonify
from flask_pymongo import PyMongo
from config import MONGO_URI, ADMIN_PASSWORD, SECRET_KEY
from datetime import datetime
from bson.objectid import ObjectId

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["MONGO_URI"] = MONGO_URI
app.secret_key = SECRET_KEY
mongo = PyMongo(app)
@app.before_request
def require_login():
    allowed_routes = {'login', 'static', 'create_admin', 'calendar_data'}
    if request.endpoint is None:
        return
    if request.endpoint not in allowed_routes and 'user' not in session:
        return redirect(url_for('login'))

@app.route('/create-admin')
def create_admin():
    hashed_pw = generate_password_hash(ADMIN_PASSWORD)
    mongo.db.users.insert_one({'username': 'admin', 'password': hashed_pw})
    return "Admin user created"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].lower()
        password = request.form['password']
        user = mongo.db.users.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['user'] = username
            return redirect(url_for('dashboard'))
        flash("Invalid username or password.")
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("You have been logged out.")
    return redirect(url_for('login'))




@app.route('/')
def dashboard():
    bookings_count = mongo.db.bookings.count_documents({})

    total_income = 0
    total_expense = 0

    for e in mongo.db.expenses.find():
        t = e.get('type')  
        amt = e.get('amount', 0) 

        if t == 'credit':
            total_income += amt
        else :
            total_expense += amt
 
    # For upcoming bookings
    today = datetime.today().strftime('%Y-%m-%d')
    upcoming_bookings = mongo.db.bookings.find({"checkin": {"$gt": today}}).sort("checkin", 1)

    # For latest bookings (most recent check-ins first)
    latest_bookings = mongo.db.bookings.find().sort("checkin", -1).limit(5)

    return render_template('dashboard.html',
                           bookings=bookings_count,
                           income=total_income,
                           expense=total_expense,
                           upcoming=list(upcoming_bookings),
                           latest=list(latest_bookings))

@app.route('/bookings', methods=['GET', 'POST'])
def bookings():
    if request.method == 'POST':
        amount_stay = float(request.form.get('price-stay', 0) or 0)
        amount_food = float(request.form.get('price-food', 0) or 0)
        total_bill = amount_stay + amount_food
        name = request.form.get('name')
        rooms = request.form.get('rooms')

        booking = {
            "name": name,
            "checkin": request.form['datein'],
            "checkout": request.form['dateout'],
            "Nights": request.form['stay'],
            "Category": request.form['category'],
            "rooms": int(rooms) if rooms and rooms.isdigit() else None,
            "food": request.form['food'],
            "Amountstay": amount_stay,
            "Amountfood": amount_food,
            "TotalBill": total_bill
        }

        # Create booking first
        insert_result = mongo.db.bookings.insert_one(booking)

        # Also log income into expenses and store reference on booking
        expense_result = mongo.db.expenses.insert_one({
            "description": name,
            "amount": total_bill,
            "type": "credit"
        })
        mongo.db.bookings.update_one(
            {"_id": insert_result.inserted_id},
            {"$set": {"expense_id": expense_result.inserted_id}}
        )

        return redirect(url_for('bookings'))

    # GET request - show latest bookings first
    bookings = mongo.db.bookings.find().sort("checkin", -1)
    return render_template('bookings.html', bookings=bookings)

@app.route('/bookings/<booking_id>/edit', methods=['GET', 'POST'])
def edit_booking(booking_id):
    b = mongo.db.bookings.find_one({"_id": ObjectId(booking_id)})
    if not b:
        return "Booking not found", 404

    if request.method == 'POST':
        amount_stay = float(request.form.get('price-stay', 0) or 0)
        amount_food = float(request.form.get('price-food', 0) or 0)
        total_bill = amount_stay + amount_food
        name = request.form.get('name')
        rooms = request.form.get('rooms')

        updated_fields = {
            "name": name,
            "checkin": request.form['datein'],
            "checkout": request.form['dateout'],
            "Nights": request.form['stay'],
            "Category": request.form['category'],
            "rooms": int(rooms) if rooms and str(rooms).isdigit() else None,
            "food": request.form['food'],
            "Amountstay": amount_stay,
            "Amountfood": amount_food,
            "TotalBill": total_bill
        }

        mongo.db.bookings.update_one({"_id": ObjectId(booking_id)}, {"$set": updated_fields})

        # Update or create linked expense entry
        expense_id = b.get('expense_id')
        if expense_id:
            mongo.db.expenses.update_one(
                {"_id": expense_id},
                {"$set": {"description": name, "amount": total_bill, "type": "credit"}}
            )
        else:
            expense_result = mongo.db.expenses.insert_one({
                "description": name,
                "amount": total_bill,
                "type": "credit"
            })
            mongo.db.bookings.update_one(
                {"_id": ObjectId(booking_id)},
                {"$set": {"expense_id": expense_result.inserted_id}}
            )

        return redirect(url_for('bookings'))

    return render_template('edit_booking.html', booking=b)

@app.route('/expenses', methods=['GET', 'POST'])
def expenses():
    if request.method == 'POST':
        expense = {
            "description": request.form['description'],
            "amount": float(request.form['amount']),
            "type": request.form['type'],
            "date": request.form['date']
        }
        mongo.db.expenses.insert_one(expense)
        return redirect(url_for('expenses'))
    
    # Show latest expenses first
    expenses = mongo.db.expenses.find().sort("date", -1)
    return render_template('expenses.html', expenses=expenses)

@app.route('/expenses/<expense_id>/edit', methods=['GET', 'POST'])
def edit_expense(expense_id):
    e = mongo.db.expenses.find_one({"_id": ObjectId(expense_id)})
    if not e:
        return "Expense not found", 404
    if request.method == 'POST':
        updated_fields = {
            "description": request.form['description'],
            "amount": float(request.form['amount']),
            "type": request.form['type'],
            "date": request.form['date']
        }
        mongo.db.expenses.update_one({"_id": ObjectId(expense_id)}, {"$set": updated_fields})
        return redirect(url_for('expenses'))
    return render_template('edit_expense.html', expense=e)

@app.route('/expenses/<expense_id>/delete', methods=['POST'])
def delete_expense(expense_id):
    mongo.db.expenses.delete_one({"_id": ObjectId(expense_id)})
    return redirect(url_for('expenses'))

@app.route('/calendar')
def calendar():
    return render_template('calendar.html')

@app.route('/calendar-data')
def calendar_data():
    bookings = mongo.db.bookings.find()
    events = [
        {
            # Keep title simple; render details via extendedProps on the frontend
            "title": f"{b.get('name', 'Unknown')} - {b.get('Category', 'N/A')}",
            "start": b.get("checkin"),
            "end": b.get("checkout"),
            "extendedProps": {
                "rooms": b.get("rooms"),
                "category": b.get("Category"),
                "name": b.get("name")
            }
        }
        for b in bookings if "checkin" in b and "checkout" in b
    ]

    return jsonify(events)

@app.route('/delete-booking/<booking_id>', methods=['POST'])
def delete_booking(booking_id):
    try:
        mongo.db.bookings.delete_one({"_id": ObjectId(booking_id)})
        return redirect(url_for('bookings'))
    except Exception as e:
        return f"An error occurred: {e}", 500


if __name__ == '__main__':
    app.run(debug=True)