from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_pymongo import PyMongo
from config import MONGO_URI
from datetime import datetime

app = Flask(__name__)
app.config["MONGO_URI"] = MONGO_URI
mongo = PyMongo(app)

@app.route('/')
def dashboard():
    bookings_count = mongo.db.bookings.count_documents({})

    total_income = 0
    total_expense = 0

    for e in mongo.db.expenses.find():
        t = e.get('type')  
        amt = e.get('amount', 0)  # default to 0 if 'amount' is missing

        if t == 'credit':
            total_income += amt
        else :
            total_expense += amt
        # Optional: skip if type is missing or malformed

    # For upcoming bookings
    from datetime import datetime
    today = datetime.today().strftime('%Y-%m-%d')
    upcoming_bookings = mongo.db.bookings.find({"checkin": {"$gt": today}}).sort("checkin", 1)

    return render_template('dashboard.html',
                           bookings=bookings_count,
                           income=total_income,
                           expense=total_expense,
                           upcoming=list(upcoming_bookings))

#here we write a function get teh booking count total expense adn then retrun rendertemplate with the fields 

@app.route('/bookings', methods=['GET', 'POST'])
def bookings():
    if request.method == 'POST':
        amount_stay = float(request.form.get('price-stay', 0) or 0)
        amount_food = float(request.form.get('price-food', 0) or 0)
        total_bill = amount_stay + amount_food
        name=request.form.get('name')

        booking = {
            "name":name,
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
            "type": "credit"  # must match 'credit' in dashboard route
        })

        return redirect(url_for('bookings'))

    # GET request
    bookings = mongo.db.bookings.find()
    return render_template('bookings.html', bookings=bookings)
@app.route('/expenses', methods=['GET', 'POST'])
def expenses():
    if request.method == 'POST':
        expense = {
            "description": request.form['description'],
            "amount": float(request.form['amount']),
            "type":request.form['type'],
            "date":request.form['date']
        }
        mongo.db.expenses.insert_one(expense)
        return redirect(url_for('expenses'))
    expenses = mongo.db.expenses.find()
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
if __name__ == '__main__':
    app.run(debug=True)