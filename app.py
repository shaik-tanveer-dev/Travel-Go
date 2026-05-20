import os
from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from bson.objectid import ObjectId # Import ObjectId for MongoDB _id handling
import uuid # For generating unique IDs for dummy data

# --- IMPORTANT: This loads environment variables from your .env file ---
from dotenv import load_dotenv
load_dotenv() 
# --- END IMPORTANT ---

# Assume config.py exists and contains a Config class
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# MongoDB Connection
# MONGO_URI is now loaded from your .env file via Config class
client = MongoClient(app.config['MONGO_URI'])
db = client.travelgo_db # Your database name (as specified in MONGO_URI or default if not)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect to login if user tries to access a protected page
login_manager.login_message_category = "info" # Category for flash message when login is required

class User(UserMixin):
    def __init__(self, username, email, password, user_id):
        self.username = username
        self.email = email
        self.password = password  # This should be the HASHED password
        self.id = str(user_id)    # Flask-Login expects 'id' as a string

    @staticmethod
    def get(user_id):
        # When Flask-Login loads a user, user_id might be a string.
        # MongoDB's ObjectId needs to be converted back for query if it was stored as ObjectId.
        try:
            # Attempt to convert to ObjectId, if it's a valid ObjectId string
            obj_id = ObjectId(user_id)
        except Exception:
            # If not a valid ObjectId string, it means the user_id is malformed or doesn't exist
            return None
            
        user_data = db.users.find_one({"_id": obj_id})
        if user_data:
            return User(user_data['username'], user_data['email'], user_data['password'], user_data['_id'])
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email')
        password = request.form.get('password')

        # Try to find user by username first, then by email
        user = db.users.find_one({"username": username_or_email})
        if not user:
            user = db.users.find_one({"email": username_or_email})

        if user and check_password_hash(user['password'], password):
            user_obj = User(user['username'], user['email'], user['password'], user['_id'])
            login_user(user_obj)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next') # Redirect to the page user was trying to access
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username/email or password.', 'danger')
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Basic validation
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))
        
        if db.users.find_one({"username": username}):
            flash('Username already exists. Please choose another.', 'danger')
            return redirect(url_for('register'))
        
        if db.users.find_one({"email": email}):
            flash('Email already registered. Please use another or log in.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        db.users.insert_one({
            "username": username,
            "email": email,
            "password": hashed_password,
            "created_at": datetime.now()
        })
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/my_bookings')
@login_required
def my_bookings():
    # Fetch bookings for the current logged-in user
    # current_user.id is a string, which matches how we store it in booking_details["user_id"]
    user_bookings = db.bookings.find({"user_id": current_user.id}).sort("booking_date", -1)
    
    return render_template('my_bookings.html', bookings=list(user_bookings))

# --- DEDICATED SEARCH PAGES ROUTES ---
@app.route('/flights')
def flights_page():
    return render_template('flight.html')

@app.route('/hotels')
def hotels_page():
    return render_template('hotel.html')

@app.route('/trains')
def trains_page():
    return render_template('trains.html')

@app.route('/buses')
def buses_page():
    return render_template('bus.html')


# --- Search Results Routes (using dummy data for now) ---

@app.route('/search/flights', methods=['POST'])
def search_flights():
    from_city = request.form.get('flightFrom')
    to_city = request.form.get('flightTo')
    departure_date = request.form.get('flightDeparture')
    return_date = request.form.get('flightReturn')
    passengers = request.form.get('flightPassengers')

    # Simulate fetching flight data
    dummy_flights = []
    for i in range(1, 6): # Generate 5 dummy flights
        flight_id = str(uuid.uuid4()) # Unique ID for each dummy flight
        dummy_flights.append({
            'id': flight_id,
            'airline': f'Airline {i}',
            'from': from_city,
            'to': to_city,
            'departure_date': departure_date,
            'return_date': return_date if return_date else 'N/A',
            'departure_time': f'{8 + i}:00 AM',
            'arrival_time': f'{10 + i}:00 AM',
            'duration': f'{2 + (i*0.5)}h',
            'price': 100 + (i * 25),
            'stops': 0 if i % 2 == 0 else 1
        })
    
    flash(f"Searching flights from {from_city} to {to_city} on {departure_date}...", "info")
    return render_template('search_results/flights_results.html', flights=dummy_flights, search_params=request.form)

@app.route('/search/hotels', methods=['POST'])
def search_hotels():
    destination = request.form.get('hotelDestination')
    checkin_date = request.form.get('hotelCheckin')
    checkout_date = request.form.get('hotelCheckout')
    guests = request.form.get('hotelGuests')

    dummy_hotels = []
    for i in range(1, 6):
        hotel_id = str(uuid.uuid4())
        dummy_hotels.append({
            'id': hotel_id,
            'name': f'Hotel {i} {destination}',
            'location': destination,
            'checkin': checkin_date,
            'checkout': checkout_date,
            'guests': guests,
            'price_per_night': 80 + (i * 15),
            'rating': round(3.5 + (i * 0.2), 1),
            'image': f'/static/images/hotel{i}.jpg' # Placeholder image
        })
    flash(f"Searching hotels in {destination} from {checkin_date} to {checkout_date}...", "info")
    return render_template('search_results/hotels_results.html', hotels=dummy_hotels, search_params=request.form)

@app.route('/search/trains', methods=['POST'])
def search_trains():
    from_station = request.form.get('trainFrom')
    to_station = request.form.get('trainTo')
    travel_date = request.form.get('trainDate')
    train_class = request.form.get('trainClass')
    passengers = request.form.get('trainPassengers')

    dummy_trains = []
    for i in range(1, 6):
        train_id = str(uuid.uuid4())
        dummy_trains.append({
            'id': train_id,
            'train_number': f'TRN{100 + i}',
            'from': from_station,
            'to': to_station,
            'departure_date': travel_date,
            'departure_time': f'{6 + i}:30 AM',
            'arrival_time': f'{12 + i}:00 PM',
            'travel_class': train_class,
            'price': 50 + (i * 10)
        })
    flash(f"Searching trains from {from_station} to {to_station} on {travel_date}...", "info")
    return render_template('search_results/trains_results.html', trains=dummy_trains, search_params=request.form)


@app.route('/search/buses', methods=['POST'])
def search_buses():
    from_city = request.form.get('busFrom')
    to_city = request.form.get('busTo')
    travel_date = request.form.get('busDate')
    passengers = request.form.get('busPassengers')

    dummy_buses = []
    for i in range(1, 6):
        bus_id = str(uuid.uuid4())
        dummy_buses.append({
            'id': bus_id,
            'operator': f'BusCo {i}',
            'from': from_city,
            'to': to_city,
            'departure_date': travel_date,
            'departure_time': f'{7 + i}:15 AM',
            'arrival_time': f'{11 + i}:45 AM',
            'price': 30 + (i * 5)
        })
    flash(f"Searching buses from {from_city} to {to_city} on {travel_date}...", "info")
    return render_template('search_results/buses_results.html', buses=dummy_buses, search_params=request.form)

# --- Selection Routes ---

@app.route('/select_flight_seats/<string:flight_id>', methods=['GET'])
@login_required
def select_flight_seats(flight_id):
    # Use request.args to get the details passed from the search results page
    search_params = request.args 
    
    selected_flight = {
        'id': flight_id, # Use the actual ID passed from the form
        'airline': search_params.get('airline', 'Unknown Airline'),
        'from': search_params.get('from'),
        'to': search_params.get('to'),
        'departure_date': search_params.get('departure_date'),
        'return_date': search_params.get('return_date') if search_params.get('return_date') else 'N/A',
        'departure_time': search_params.get('departure_time', 'N/A'),
        'arrival_time': search_params.get('arrival_time', 'N/A'),
        'duration': search_params.get('duration', 'N/A'),
        'price': float(search_params.get('price', 0)), # Convert price to float
        'stops': int(search_params.get('stops', 0))
    }
    
    return render_template('selection/flight_selection.html', flight=selected_flight, search_params=search_params)

@app.route('/select_hotel_room/<string:hotel_id>', methods=['GET'])
@login_required
def select_hotel_room(hotel_id):
    search_params = request.args
    
    selected_hotel = {
        'id': hotel_id,
        'name': search_params.get('name', 'Unknown Hotel'),
        'location': search_params.get('location'),
        'checkin': search_params.get('checkin'),
        'checkout': search_params.get('checkout'),
        'guests': search_params.get('guests'),
        'price_per_night': float(search_params.get('price_per_night', 0)),
        'rating': float(search_params.get('rating', 0.0)),
        'image': search_params.get('image', '')
    }

    return render_template('selection/hotel_selection.html', hotel=selected_hotel, search_params=search_params)

@app.route('/select_train_seats/<string:train_id>', methods=['GET'])
@login_required
def select_train_seats(train_id):
    search_params = request.args
    
    selected_train = {
        'id': train_id,
        'train_number': search_params.get('train_number', 'N/A'),
        'from': search_params.get('from'),
        'to': search_params.get('to'),
        'departure_date': search_params.get('departure_date'),
        'departure_time': search_params.get('departure_time', 'N/A'),
        'arrival_time': search_params.get('arrival_time', 'N/A'),
        'travel_class': search_params.get('travel_class', 'N/A'),
        'price': float(search_params.get('price', 0))
    }
    return render_template('selection/train_selection.html', train=selected_train, search_params=search_params)

@app.route('/select_bus_seats/<string:bus_id>', methods=['GET'])
@login_required
def select_bus_seats(bus_id):
    search_params = request.args
    
    selected_bus = {
        'id': bus_id,
        'operator': search_params.get('operator', 'N/A'),
        'from': search_params.get('from'),
        'to': search_params.get('to'),
        'departure_date': search_params.get('departure_date'),
        'departure_time': search_params.get('departure_time', 'N/A'),
        'arrival_time': search_params.get('arrival_time', 'N/A'),
        'price': float(search_params.get('price', 0))
    }
    return render_template('selection/bus_selection.html', bus=selected_bus, search_params=search_params)


# --- Booking Confirmation Routes (modified to accept selection) ---

@app.route('/confirm_booking/<string:booking_type>/<string:item_id>', methods=['POST'])
@login_required
def confirm_booking(booking_type, item_id):
    # Retrieve details from the form submission (hidden inputs on search results page)
    booking_details = {
        "user_id": current_user.id,
        "booking_type": booking_type,
        "item_id": item_id,
        "booking_date": datetime.now(),
        "status": "confirmed", # Initial status is confirmed
        "details": request.form.to_dict() # Store all form data for details
    }
    
    # Remove Flask-specific internal fields that might be passed from forms
    booking_details["details"].pop('csrf_token', None) 

    # Add selected seat/room to details if present
    if booking_type == 'flight':
        selected_seat = request.form.get('selected_seat')
        if selected_seat:
            booking_details['details']['selected_seat'] = selected_seat
        else:
            flash("Please select a seat for your flight.", "danger")
            # Redirect back to selection page with existing data
            return redirect(url_for('select_flight_seats', flight_id=item_id, **request.form))
    elif booking_type == 'hotel':
        selected_room_type = request.form.get('selected_room_type')
        if selected_room_type:
            booking_details['details']['selected_room_type'] = selected_room_type
        else:
            flash("Please select a room type for your hotel.", "danger")
            return redirect(url_for('select_hotel_room', hotel_id=item_id, **request.form))
    elif booking_type == 'train':
        selected_train_seat = request.form.get('selected_train_seat')
        if selected_train_seat:
            booking_details['details']['selected_train_seat'] = selected_train_seat
        else:
            flash("Please select a seat for your train.", "danger")
            return redirect(url_for('select_train_seats', train_id=item_id, **request.form))
    elif booking_type == 'bus':
        selected_bus_seat = request.form.get('selected_bus_seat')
        if selected_bus_seat:
            booking_details['details']['selected_bus_seat'] = selected_bus_seat
        else:
            flash("Please select a seat for your bus.", "danger")
            return redirect(url_for('select_bus_seats', bus_id=item_id, **request.form))
    
    db.bookings.insert_one(booking_details)
    flash(f'Your {booking_type} booking (ID: {item_id[:8]}...) has been confirmed!', 'success')
    return redirect(url_for('my_bookings'))

# --- Cancel Booking Route ---
@app.route('/cancel_booking/<string:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    try:
        # Convert the string booking_id back to MongoDB's ObjectId
        obj_booking_id = ObjectId(booking_id)
    except Exception:
        flash('Invalid booking ID.', 'danger')
        return redirect(url_for('my_bookings'))

    # Find the booking and ensure it belongs to the current user
    booking = db.bookings.find_one({"_id": obj_booking_id, "user_id": current_user.id})

    if not booking:
        flash('Booking not found or you do not have permission to cancel it.', 'danger')
        return redirect(url_for('my_bookings'))

    if booking['status'] == 'cancelled':
        flash('This booking is already cancelled.', 'info')
        return redirect(url_for('my_bookings'))

    # Update the booking status to 'cancelled'
    result = db.bookings.update_one(
        {"_id": obj_booking_id},
        {"$set": {"status": "cancelled", "cancellation_date": datetime.now()}}
    )

    if result.modified_count == 1:
        flash(f'Booking (ID: {booking_id[:8]}...) has been successfully cancelled.', 'success')
    else:
        flash('Failed to cancel booking. Please try again.', 'danger')

    return redirect(url_for('my_bookings'))


if __name__ == '__main__':
    # You can set the SECRET_KEY in your .env file or directly here for development
    # Make sure to set a strong, unique key in production
    app.run(debug=True)