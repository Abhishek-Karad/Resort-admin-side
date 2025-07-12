from flask import Flask, render_template,flash,session, request, redirect, url_for, jsonify
from flask_pymongo import PyMongo
from config import MONGO_URI
from datetime import datetime
from bson.objectid import ObjectId

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["MONGO_URI"] = MONGO_URI
app.secret_key='Abhishekisgr8'
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
    hashed_pw = generate_password_hash('admin123')
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

        booking = {
            "name": name,
            "checkin": request.form['datein'],
            "checkout": request.form['dateout'],
            "Nights": request.form['stay'],
            "Category": request.form['category'],
            "food": request.form['food'],
            "Amountstay": amount_stay,
            "Amountfood": amount_food,
            "TotalBill": total_bill
        }

        mongo.db.bookings.insert_one(booking)

        # Also log income into expenses
        mongo.db.expenses.insert_one({
            "description": name,
            "amount": total_bill,
            "type": "credit" 
        })

        return redirect(url_for('bookings'))

    # GET request - show latest bookings first
    bookings = mongo.db.bookings.find().sort("checkin", -1)
    return render_template('bookings.html', bookings=bookings)

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

@app.route('/calendar')
def calendar():
    return render_template('calendar.html')

@app.route('/calendar-data')
def calendar_data():
    bookings = mongo.db.bookings.find()
    events = [
        {
            "title": f"{b.get('name', 'Unknown')} - {b.get('Category', 'N/A')}",
            "start": b.get("checkin"),
            "end": b.get("checkout")
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