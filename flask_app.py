from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from functools import wraps
import pandas as pd
import pickle
import requests
import random
import os
from twilio.rest import Client
from datetime import datetime
import threading
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# Admin credentials (hardcoded)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'  # Change this to a secure password

# Twilio credentials - loaded from environment variables
# Set these in your environment or Render dashboard:
# TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')

# Set to True to simulate SMS (no real Twilio send). Use when Twilio is not set up or trial limits.
# Default is now FALSE so real SMS are sent unless DEMO_SMS is explicitly set to true.
DEMO_SMS = os.environ.get('DEMO_SMS', 'false').lower() in ('1', 'true', 'yes')

# Global model variables
gb_disease = gb_risk = le_disease = le_risklevel = precautions_tab = None

def auto_train_model():
    """Automatically train the health risk model"""
    global gb_disease, gb_risk, le_disease, le_risklevel, precautions_tab
    dataset_file = 'climate_health_precaution_dataset_500.csv'
    
    if not os.path.exists(dataset_file):
        print(f"Error: Dataset file '{dataset_file}' not found. Cannot train model automatically.")
        return False
    
    try:
        print("Training model automatically...")
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.preprocessing import LabelEncoder
        
        df = pd.read_csv(dataset_file)
        df.columns = ['City', 'Temperature', 'Humidity', 'AQI', 'Rainfall', 'WindSpeed', 'Pressure', 'Date', 'DayType',
                      'Disease_Risk', 'Risk_Level', 'Precaution_1', 'Precaution_2', 'Precaution_3']
        
        features = ['Temperature', 'Humidity', 'AQI', 'Rainfall', 'WindSpeed', 'Pressure']
        X = df[features]
        le_disease_local = LabelEncoder()
        le_risklevel_local = LabelEncoder()
        y_disease = le_disease_local.fit_transform(df['Disease_Risk'])
        y_risklevel = le_risklevel_local.fit_transform(df['Risk_Level'])
        
        gb_disease_local = GradientBoostingClassifier(n_estimators=100, random_state=42)
        gb_disease_local.fit(X, y_disease)
        gb_risk_local = GradientBoostingClassifier(n_estimators=100, random_state=42)
        gb_risk_local.fit(X, y_risklevel)
        
        precautions = df[['Disease_Risk', 'Risk_Level', 'Precaution_1', 'Precaution_2', 'Precaution_3']].drop_duplicates()
        
        bundle = {
            'gb_disease': gb_disease_local,
            'gb_risk': gb_risk_local,
            'le_disease': le_disease_local,
            'le_risklevel': le_risklevel_local,
            'precautions': precautions
        }
        
        with open('health_model.pkl', 'wb') as file:
            pickle.dump(bundle, file)
        
        # Load the newly trained model
        gb_disease = bundle['gb_disease']
        gb_risk = bundle['gb_risk']
        le_disease = bundle['le_disease']
        le_risklevel = bundle['le_risklevel']
        precautions_tab = bundle['precautions']
        
        print("Model trained and loaded successfully!")
        return True
    except Exception as e:
        print(f"Error training model automatically: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def load_model():
    """Load or reload the health risk model, auto-train if not found"""
    global gb_disease, gb_risk, le_disease, le_risklevel, precautions_tab
    MODEL_FILE = 'health_model.pkl'
    
    if os.path.exists(MODEL_FILE):
        try:
            with open(MODEL_FILE, 'rb') as file:
                bundle = pickle.load(file)
            gb_disease = bundle['gb_disease']
            gb_risk = bundle['gb_risk']
            le_disease = bundle['le_disease']
            le_risklevel = bundle['le_risklevel']
            precautions_tab = bundle['precautions']
            print("Model loaded successfully!")
            return True
        except (ModuleNotFoundError, ImportError, AttributeError, KeyError) as e:
            print(f"Warning: Could not load model file due to compatibility issue: {e}")
            print("Attempting to automatically retrain the model...")
            if auto_train_model():
                return True
            gb_disease = gb_risk = le_disease = le_risklevel = precautions_tab = None
            return False
        except Exception as e:
            print(f"Warning: Could not load model file: {e}")
            print("Attempting to automatically retrain the model...")
            if auto_train_model():
                return True
            gb_disease = gb_risk = le_disease = le_risklevel = precautions_tab = None
            return False
    else:
        print("Model file not found. Training model automatically...")
        if auto_train_model():
            return True
        gb_disease = gb_risk = le_disease = le_risklevel = precautions_tab = None
        return False

# Load model on startup
load_model()

# Store OTPs temporarily (in production, use Redis or database)
otp_store = {}

def send_sms(phone, msg):
    """Send SMS via Twilio (or simulate when DEMO_SMS is True)"""
    # Validate phone number format before sending
    if not phone or len(phone) < 10:
        error_info = {
            'type': 'ValidationError',
            'message': f'Invalid phone number: {phone}',
            'user_message': f'Invalid phone number format: {phone}. Phone number must be at least 10 digits.'
        }
        print(f"ERROR: {error_info['user_message']}")
        return error_info

    if DEMO_SMS:
        print(f"\n[DEMO SMS] Would send to {phone}:")
        print("-" * 40)
        print(msg[:200] + ("..." if len(msg) > 200 else ""))
        print("-" * 40)
        return "DEMO_" + str(int(time.time()))

    try:
        print(f"\n{'='*60}")
        print(f"ATTEMPTING TO SEND SMS")
        print(f"{'='*60}")
        print(f"To: {phone}")
        print(f"From: {TWILIO_PHONE_NUMBER}")
        print(f"Message length: {len(msg)} characters")
        print(f"Account SID: {TWILIO_ACCOUNT_SID[:10]}...")
        
        if not phone or len(phone) < 10:
            error_info = {
                'type': 'ValidationError',
                'message': f'Invalid phone number: {phone}',
                'user_message': f'Invalid phone number format: {phone}. Phone number must be at least 10 digits.'
            }
            print(f"ERROR: {error_info['user_message']}")
            return error_info
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        print("Twilio client created successfully")
        
        message = client.messages.create(
            body=msg,
            from_=TWILIO_PHONE_NUMBER,
            to=phone
        )
        
        print(f"{'='*60}")
        print(f"SMS SENT SUCCESSFULLY!")
        print(f"Message SID: {message.sid}")
        print(f"Message status: {message.status}")
        print(f"Message price: {getattr(message, 'price', 'N/A')}")
        print(f"{'='*60}\n")
        return message.sid
        
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        error_code = getattr(e, 'code', None)
        
        print(f"\n{'!'*60}")
        print(f"SMS SENDING FAILED")
        print(f"{'!'*60}")
        print(f"Error type: {error_type}")
        print(f"Error code: {error_code}")
        print(f"Error message: {error_msg}")
        print(f"Phone number: {phone}")
        
        # Check for specific Twilio errors and return detailed error info
        error_info = {'type': error_type, 'message': error_msg, 'code': error_code}
        
        error_lower = error_msg.lower()
        
        if "exceeded" in error_lower and ("daily" in error_lower or "limit" in error_lower or "50" in error_msg):
            print("→ Issue: Twilio daily message limit exceeded (50 messages/day for trial accounts)")
            error_info['user_message'] = "Daily message limit exceeded. Twilio trial accounts are limited to 50 messages per day. Please upgrade your account or wait until tomorrow."
        elif "not a valid phone number" in error_lower or "invalid" in error_lower or error_code == 21211:
            print("→ Issue: Invalid phone number format")
            error_info['user_message'] = f"Invalid phone number format: {phone}. Please ensure it's in E.164 format (e.g., +91XXXXXXXXXX)."
        elif "authentication" in error_lower or "unauthorized" in error_lower or error_code == 20003:
            print("→ Issue: Twilio authentication failed - check credentials")
            error_info['user_message'] = "Twilio authentication failed. Please check your Twilio Account SID and Auth Token."
        elif "insufficient" in error_lower or "balance" in error_lower or error_code == 20005:
            print("→ Issue: Insufficient Twilio account balance")
            error_info['user_message'] = "Insufficient Twilio account balance. Please add funds to your Twilio account."
        elif "unverified" in error_lower or (error_code == 21610):
            print("→ Issue: Phone number not verified in Twilio (trial account)")
            error_info['user_message'] = f"Phone number {phone} is not verified in your Twilio account. For trial accounts, you must verify recipient numbers at https://console.twilio.com/us1/develop/phone-numbers/manage/verified"
        elif "permission" in error_lower or "not allowed" in error_lower:
            print("→ Issue: Permission denied")
            error_info['user_message'] = "Permission denied. Check your Twilio account settings and phone number permissions."
        elif error_code == 21408:
            print("→ Issue: Permission to send SMS to this number denied")
            error_info['user_message'] = f"Permission denied to send SMS to {phone}. This number may be blocked or not verified in your Twilio account."
        else:
            error_info['user_message'] = f"Failed to send SMS: {error_msg} (Code: {error_code})"
        
        print(f"User-friendly message: {error_info['user_message']}")
        print(f"{'!'*60}\n")
        
        return error_info

def fetch_weather_for_city(city, api_key='ac9ea2b0cba9ab0943058f803c7f6e68'):
    """Fetch weather data for a city"""
    url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric'
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        if data.get('cod') != 200:
            return None
        return {
            'Temperature': data['main']['temp'],
            'Humidity': data['main']['humidity'],
            'AQI': 100,  # Default or connect to AQI API
            'Rainfall': data.get('rain', {}).get('1h', 0),
            'WindSpeed': data['wind']['speed'],
            'Pressure': data['main']['pressure']
        }
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None

def build_health_alert_message(city, weather_data, disease, risk, precautions):
    """Build SMS alert message based on current weather/climate data - exact format for Twilio."""
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    return (
        f"HEALTH ALERT - {city}\n"
        f"==================\n\n"
        f"Based on current conditions at {now_str}\n\n"
        f"CLIMATE DATA:\n"
        f"Temperature: {weather_data['Temperature']} C\n"
        f"Humidity: {weather_data['Humidity']}%\n"
        f"AQI: {weather_data['AQI']}\n"
        f"Rainfall: {weather_data['Rainfall']} mm\n"
        f"Wind Speed: {weather_data['WindSpeed']} m/s\n"
        f"Pressure: {weather_data['Pressure']} hPa\n\n"
        f"HEALTH RISK:\n"
        f"Disease Risk: {disease}\n"
        f"Risk Level: {risk}\n\n"
        f"PRECAUTIONS:\n"
        f"1. {precautions[0]}\n"
        f"2. {precautions[1]}\n"
        f"3. {precautions[2]}\n\n"
        f"Stay safe! - Aegis Health"
    )

def check_phone_format(phone):
    """Format phone number - handles various formats"""
    if phone is None:
        return None
    
    # Convert to string and clean up
    phone_str = str(phone).strip()
    
    # Handle float conversion (e.g., if stored as 9.123456789e+09 in CSV)
    if '.' in phone_str and 'e' not in phone_str.lower():
        # Remove decimal point and everything after it
        phone_str = phone_str.split('.')[0]
    
    # Remove all non-digit characters except +
    phone_digits = ''.join(c for c in phone_str if c.isdigit() or c == '+')
    
    # Format based on patterns
    if phone_digits.startswith('+'):
        # Already has country code
        if phone_digits.startswith('+91') and len(phone_digits) == 13:
            return phone_digits  # +91XXXXXXXXXX (13 chars)
        elif len(phone_digits) >= 10:
            return phone_digits  # Other country codes
        else:
            return None
    elif phone_digits.startswith('91') and len(phone_digits) == 12:
        return '+' + phone_digits  # 91XXXXXXXXXX -> +91XXXXXXXXXX
    elif len(phone_digits) == 10:
        return '+91' + phone_digits  # XXXXXXXXXX -> +91XXXXXXXXXX
    elif len(phone_digits) == 11 and phone_digits.startswith('0'):
        # Handle numbers starting with 0 (like 0XXXXXXXXXX)
        return '+91' + phone_digits[1:]  # 0XXXXXXXXXX -> +91XXXXXXXXXX
    else:
        # Try to extract last 10 digits if longer (handles cases with extra digits)
        if len(phone_digits) > 10:
            last_10 = phone_digits[-10:]
            if last_10.isdigit() and len(last_10) == 10:
                return '+91' + last_10
        return None

def predict_health_risk(weather_data):
    """Predict health risk from weather data"""
    if gb_disease is None or gb_risk is None:
        return None, None, []
    
    input_df = pd.DataFrame([weather_data], columns=['Temperature', 'Humidity', 'AQI', 'Rainfall', 'WindSpeed', 'Pressure'])
    y_d_pred = le_disease.inverse_transform(gb_disease.predict(input_df))[0]
    y_r_pred = le_risklevel.inverse_transform(gb_risk.predict(input_df))[0]
    
    result = precautions_tab[
        (precautions_tab['Disease_Risk'] == y_d_pred) & 
        (precautions_tab['Risk_Level'] == y_r_pred)
    ]
    
    if result.empty:
        result = precautions_tab[precautions_tab['Disease_Risk'] == y_d_pred]
    
    prc = result.iloc[0][['Precaution_1', 'Precaution_2', 'Precaution_3']].tolist() if not result.empty else ["No data"] * 3
    
    return y_d_pred, y_r_pred, prc

# Admin authentication decorator
def admin_required(f):
    """Decorator to require admin login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Admin access required. Please login first.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if session.get('admin_logged_in'):
        return redirect(url_for('alerts'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash('Admin login successful!', 'success')
            return redirect(url_for('alerts'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash('Admin logged out successfully', 'success')
    return redirect(url_for('admin_login'))

@app.route('/')
def index():
    """Main dashboard"""
    users_file = 'users.csv'
    if os.path.exists(users_file):
        df = pd.read_csv(users_file, dtype={'phone': str})
        users_count = len(df)
    else:
        users_count = 0
    
    model_loaded = os.path.exists('health_model.pkl')
    alerts_active = os.path.exists('alert_process.pid')  # Simple check
    
    return render_template('dashboard.html', 
                         users_count=users_count,
                         model_loaded=model_loaded,
                         alerts_active=alerts_active)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration with OTP"""
    if request.method == 'POST':
        try:
            print(f"\n{'='*60}")
            print("REGISTRATION REQUEST RECEIVED")
            print(f"{'='*60}")
            
            phone = request.form.get('phone', '').strip()
            password = request.form.get('password', '').strip()
            city = request.form.get('city', '').strip()
            
            print(f"Raw input - Phone: {phone}, City: {city}, Password: {'*' * len(password)}")
            
            if not all([phone, password, city]):
                flash('Please fill all fields', 'error')
                print("ERROR: Missing fields")
                return redirect(url_for('register'))
            
            original_phone = phone
            phone = check_phone_format(phone)
            
            print(f"Formatted phone: {phone}")
            
            if not phone:
                flash('Invalid phone number format. Please use format: +91XXXXXXXXXX or XXXXXXXXXX', 'error')
                print(f"ERROR: Invalid phone format for {original_phone}")
                return redirect(url_for('register'))
            
            # Generate OTP
            otp = f"{random.randint(100000, 999999)}"
            print(f"Generated OTP: {otp}")
            
            otp_store[phone] = {'otp': otp, 'password': password, 'city': city, 'timestamp': time.time()}
            print(f"OTP stored for {phone}")
            
            # Send OTP
            msg = f"Your OTP for Health Alert registration is: {otp}"
            print(f"Sending OTP SMS to {phone}...")
            print(f"Message: {msg}")
            
            result = send_sms(phone, msg)
            
            if result and isinstance(result, str):
                # Success - result is message SID
                print(f"SUCCESS! OTP sent. Message SID: {result}")
                session['pending_phone'] = phone
                flash(f'OTP sent successfully to {phone}! Please check your phone.', 'success')
                print(f"{'='*60}\n")
                return redirect(url_for('verify_otp'))
            elif result and isinstance(result, dict):
                # Error - result is error_info dictionary
                error_msg = result.get('user_message', result.get('message', 'Unknown error'))
                print(f"FAILED! Error: {error_msg}")
                flash(f'Failed to send OTP: {error_msg}', 'error')
                print(f"{'='*60}\n")
                return redirect(url_for('register'))
            else:
                print(f"FAILED! Could not send OTP to {phone}")
                flash('Failed to send OTP. Please check your phone number and try again. Check console for details.', 'error')
                print(f"{'='*60}\n")
                return redirect(url_for('register'))
                
        except Exception as e:
            error_msg = f"Unexpected error in registration: {str(e)}"
            print(f"\n{'!'*60}")
            print(f"EXCEPTION: {error_msg}")
            print(f"Exception type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            print(f"{'!'*60}\n")
            flash(f'Registration error: {str(e)}', 'error')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/register_direct', methods=['GET', 'POST'])
def register_direct():
    """Register user directly without OTP (works when Twilio SMS is not available)"""
    if request.method == 'POST':
        try:
            phone = request.form.get('phone', '').strip()
            password = request.form.get('password', '').strip()
            city = request.form.get('city', '').strip()

            if not all([phone, password, city]):
                flash('Please fill all fields', 'error')
                return redirect(url_for('register'))

            formatted_phone = check_phone_format(phone)
            if not formatted_phone:
                flash('Invalid phone number format. Use +91XXXXXXXXXX or 10-digit number.', 'error')
                return redirect(url_for('register'))

            users_file = 'users.csv'
            user_data = pd.DataFrame([[formatted_phone, password, city]],
                                     columns=['phone', 'password', 'city'])
            if os.path.exists(users_file):
                df = pd.read_csv(users_file, dtype={'phone': str})
                if formatted_phone in df['phone'].astype(str).values:
                    flash('This phone number is already registered.', 'warning')
                    return redirect(url_for('register'))
                user_data.to_csv(users_file, mode='a', header=False, index=False)
            else:
                user_data.to_csv(users_file, index=False)

            flash('Registration successful! You will receive health alerts. (Registered without SMS verification.)', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Registration error: {str(e)}', 'error')
            return redirect(url_for('register'))

    return redirect(url_for('register'))

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    """Verify OTP and complete registration"""
    if 'pending_phone' not in session:
        flash('Please register first', 'error')
        print("ERROR: No pending phone in session")
        return redirect(url_for('register'))
    
    phone = session['pending_phone']
    print(f"\nOTP Verification - Phone: {phone}")
    
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        print(f"OTP entered: {otp}")
        
        if phone in otp_store:
            stored_data = otp_store[phone]
            stored_otp = stored_data['otp']
            print(f"Stored OTP: {stored_otp}")
            
            # OTP expires after 10 minutes
            elapsed_time = time.time() - stored_data['timestamp']
            print(f"Time elapsed: {elapsed_time:.0f} seconds")
            
            if elapsed_time > 600:
                del otp_store[phone]
                session.pop('pending_phone', None)
                flash('OTP expired. Please register again.', 'error')
                print("ERROR: OTP expired")
                return redirect(url_for('register'))
            
            if otp == stored_otp:
                print("OTP verified successfully!")
                # Save user
                user_data = pd.DataFrame([[phone, stored_data['password'], stored_data['city']]],
                                       columns=['phone', 'password', 'city'])
                users_file = 'users.csv'
                if os.path.exists(users_file):
                    user_data.to_csv(users_file, mode='a', header=False, index=False)
                else:
                    user_data.to_csv(users_file, index=False)
                
                print(f"User saved: {phone}, {stored_data['city']}")
                
                del otp_store[phone]
                session.pop('pending_phone', None)
                flash('Registration successful! You will receive hourly health alerts.', 'success')
                return redirect(url_for('index'))
            else:
                print(f"ERROR: OTP mismatch. Expected: {stored_otp}, Got: {otp}")
                flash('Invalid OTP. Please try again.', 'error')
        else:
            print(f"ERROR: No OTP found for {phone}")
            flash('OTP expired. Please register again.', 'error')
            return redirect(url_for('register'))
    
    return render_template('verify_otp.html', phone=phone)

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    """Health risk prediction"""
    if request.method == 'POST':
        city = request.form.get('city', '').strip()
        use_weather = request.form.get('use_weather') == 'true'
        
        if use_weather and city:
            weather_data = fetch_weather_for_city(city)
            if not weather_data:
                flash(f'Could not fetch weather data for {city}. Please enter values manually.', 'warning')
                return render_template('predict.html', city=city, weather_data=None)
        else:
            # Manual input
            weather_data = {
                'Temperature': float(request.form.get('temperature', 0)),
                'Humidity': float(request.form.get('humidity', 0)),
                'AQI': float(request.form.get('aqi', 0)),
                'Rainfall': float(request.form.get('rainfall', 0)),
                'WindSpeed': float(request.form.get('windspeed', 0)),
                'Pressure': float(request.form.get('pressure', 0))
            }
        
        disease, risk, precautions = predict_health_risk(weather_data)
        
        if disease is None:
            flash('Model not loaded. Attempting to train automatically...', 'warning')
            if auto_train_model():
                # Retry prediction after training
                disease, risk, precautions = predict_health_risk(weather_data)
                if disease is None:
                    flash('Model training completed but prediction failed. Please try again.', 'error')
                    return render_template('predict.html')
            else:
                flash('Failed to train model automatically. Please check the dataset file.', 'error')
                return render_template('predict.html')
        
        return render_template('predict.html', 
                             city=city if use_weather else 'Manual Input',
                             weather_data=weather_data,
                             disease=disease,
                             risk=risk,
                             precautions=precautions)
    
    return render_template('predict.html')

@app.route('/fetch_weather', methods=['POST'])
def fetch_weather():
    """API endpoint to fetch weather"""
    city = request.json.get('city', '').strip()
    if not city:
        return jsonify({'error': 'City is required'}), 400
    
    weather_data = fetch_weather_for_city(city)
    if weather_data:
        return jsonify(weather_data)
    else:
        return jsonify({'error': 'Could not fetch weather data'}), 404

@app.route('/users')
def users():
    """View registered users"""
    users_file = 'users.csv'
    if os.path.exists(users_file):
        df = pd.read_csv(users_file, dtype={'phone': str})
        users_list = df.to_dict('records')
    else:
        users_list = []
    return render_template('users.html', users=users_list)


@app.route('/alerts')
@admin_required
def alerts():
    """View alert system status"""
    users_file = 'users.csv'
    if os.path.exists(users_file):
        df = pd.read_csv(users_file, dtype={'phone': str})
        total_users = len(df)
        users_list = df.to_dict('records')
    else:
        total_users = 0
        users_list = []
    
    # Check if alert system is running
    # Method 1: Check for PID file (created by send_alerts.py when running)
    alert_running = os.path.exists('alert_process.pid')
    
    # Method 2: If PID file doesn't exist but we have users, show as "ready" (can send manual alerts)
    # The automated system requires send_alerts.py to be running separately
    if not alert_running and total_users > 0:
        # System is configured and ready, but automated alerts not running
        # Show as active since manual alerts can be sent
        alert_running = True
    
    return render_template('alerts.html', total_users=total_users, alert_running=alert_running, users=users_list)

@app.route('/send_alert/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def send_alert(user_id):
    """Send real-time alert to a specific user"""
    # Reload model to ensure it's up to date
    load_model()
    
    try:
        print(f"\n{'='*60}")
        print(f"ALERT REQUEST RECEIVED - User ID: {user_id}")
        print(f"Request method: {request.method}")
        print(f"{'='*60}")
        
        users_file = 'users.csv'
        if not os.path.exists(users_file):
            flash('No users found', 'error')
            print("ERROR: users.csv not found")
            return redirect(url_for('alerts'))
        
        df = pd.read_csv(users_file, dtype={'phone': str})
        print(f"Total users in file: {len(df)}")
        
        if user_id < 0 or user_id >= len(df):
            flash('Invalid user ID', 'error')
            print(f"ERROR: Invalid user_id {user_id}")
            return redirect(url_for('alerts'))
        
        user = df.iloc[user_id]
        print(f"User data: {user.to_dict()}")
        print(f"Raw phone from CSV: {user['phone']} (type: {type(user['phone'])})")
        
        raw_phone = str(user['phone'])
        phone = check_phone_format(raw_phone)
        city = user['city']
        
        print(f"Formatted phone: {phone}")
        print(f"City: {city}")
        
        if not phone:
            flash(f'Invalid phone number format: {raw_phone}. Please ensure the number is in format +91XXXXXXXXXX or XXXXXXXXXX', 'error')
            print(f"ERROR: Phone number format invalid - Raw: {raw_phone}, Type: {type(raw_phone)}")
            return redirect(url_for('alerts'))
        
        if gb_disease is None or gb_risk is None:
            flash('Model not loaded. Attempting to train automatically...', 'warning')
            print("WARNING: Model not loaded, attempting auto-training...")
            if auto_train_model():
                print("Model trained successfully!")
            else:
                flash('Failed to train model automatically. Please check the dataset file.', 'error')
                print("ERROR: Failed to train model")
                return redirect(url_for('alerts'))
        
        print("Model is loaded, proceeding...")
        
        # Fetch weather data
        print(f"Fetching weather for {city}...")
        weather_data = fetch_weather_for_city(city)
        if not weather_data:
            flash(f'Could not fetch weather data for {city}', 'error')
            print(f"ERROR: Could not fetch weather for {city}")
            return redirect(url_for('alerts'))
        
        print(f"Weather data fetched: {weather_data}")
        
        # Predict health risk
        print("Predicting health risk...")
        disease, risk, precautions = predict_health_risk(weather_data)
        
        if disease is None:
            flash('Error predicting health risk', 'error')
            print("ERROR: Health risk prediction failed")
            return redirect(url_for('alerts'))
        
        print(f"Prediction - Disease: {disease}, Risk: {risk}")
        print(f"Precautions: {precautions}")
        
        # Build alert message from current climate data (same format as Twilio alert)
        alert_msg = build_health_alert_message(city, weather_data, disease, risk, precautions)
        
        print(f"\nMessage to send ({len(alert_msg)} chars):")
        print("-" * 60)
        print(alert_msg)
        print("-" * 60)
        
        # Send SMS
        print(f"\nCalling send_sms() for {phone}...")
        result = send_sms(phone, alert_msg)
        
        if result and isinstance(result, str):
            # Success - result is message SID
            print(f"SUCCESS! Message SID: {result}")
            flash(f'Alert sent successfully to {phone} for {city}! Message ID: {result[:20]}...', 'success')
        elif result and isinstance(result, dict):
            # Error - result is error_info dictionary
            error_msg = result.get('user_message', result.get('message', 'Unknown error'))
            print(f"FAILED! Error: {error_msg}")
            flash(f'Failed to send alert to {phone}: {error_msg}', 'error')
        else:
            # Unexpected return value
            print("FAILED! send_sms() returned unexpected value")
            flash(f'Failed to send alert to {phone}. Check console for details.', 'error')
        
        print(f"{'='*60}\n")
        return redirect(url_for('alerts'))
        
    except Exception as e:
        error_msg = f"Unexpected error in send_alert: {str(e)}"
        print(f"\n{'!'*60}")
        print(f"EXCEPTION: {error_msg}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        print(f"{'!'*60}\n")
        flash(f'Error sending alert: {str(e)}', 'error')
        return redirect(url_for('alerts'))

@app.route('/send_alert_all', methods=['POST'])
@admin_required
def send_alert_all():
    """Send real-time alert to all registered users"""
    try:
        print(f"\n{'='*60}")
        print("SEND ALERT TO ALL USERS - STARTED")
        print(f"{'='*60}")
        
        users_file = 'users.csv'
        if not os.path.exists(users_file):
            flash('No users found', 'error')
            print("ERROR: users.csv not found")
            return redirect(url_for('alerts'))
        
        if gb_disease is None or gb_risk is None:
            flash('Model not loaded. Attempting to train automatically...', 'warning')
            print("WARNING: Model not loaded, attempting auto-training...")
            if auto_train_model():
                print("Model trained successfully!")
            else:
                flash('Failed to train model automatically. Please check the dataset file.', 'error')
                print("ERROR: Failed to train model")
                return redirect(url_for('alerts'))
        
        df = pd.read_csv(users_file, dtype={'phone': str})
        total_users = len(df)
        print(f"Total users to send alerts to: {total_users}")
        
        success_count = 0
        fail_count = 0
        
        for idx, row in df.iterrows():
            print(f"\n--- Processing user {idx + 1}/{total_users} ---")
            raw_phone = str(row['phone'])
            print(f"Raw phone from CSV: {raw_phone} (type: {type(row['phone'])})")
            phone = check_phone_format(raw_phone)
            city = row['city']
            
            print(f"Phone: {phone}, City: {city}")
            
            if not phone:
                print(f"ERROR: Invalid phone format for {raw_phone}")
                fail_count += 1
                continue
            
            # Fetch weather data
            print(f"Fetching weather for {city}...")
            weather_data = fetch_weather_for_city(city)
            if not weather_data:
                print(f"ERROR: Could not fetch weather for {city}")
                fail_count += 1
                continue
            
            print(f"Weather data: {weather_data}")
            
            # Predict health risk
            print("Predicting health risk...")
            disease, risk, precautions = predict_health_risk(weather_data)
            
            if disease is None:
                print("ERROR: Health risk prediction failed")
                fail_count += 1
                continue
            
            print(f"Prediction - Disease: {disease}, Risk: {risk}")
            
            # Build alert message from current climate data (same format as Twilio alert)
            alert_msg = build_health_alert_message(city, weather_data, disease, risk, precautions)
            
            print(f"Message length: {len(alert_msg)} characters")
            print(f"Sending SMS to {phone}...")
            
            # Send SMS
            result = send_sms(phone, alert_msg)
            if result and isinstance(result, str):
                # Success - result is message SID
                print(f"SUCCESS! Message SID: {result}")
                success_count += 1
            else:
                # Error - result is error_info dictionary or None
                if isinstance(result, dict):
                    error_msg = result.get('user_message', result.get('message', 'Unknown error'))
                    print(f"FAILED! Error: {error_msg}")
                else:
                    print(f"FAILED! Could not send SMS to {phone}")
                fail_count += 1
            
            # Small delay to avoid rate limiting (1 second between messages)
            if idx < len(df) - 1:  # Don't delay after last message
                time.sleep(1)
        
        print(f"\n{'='*60}")
        print(f"COMPLETED: {success_count} successful, {fail_count} failed")
        print(f"{'='*60}\n")
        
        flash(f'Alerts sent: {success_count} successful, {fail_count} failed', 'success' if success_count > 0 else 'error')
        return redirect(url_for('alerts'))
        
    except Exception as e:
        error_msg = f"Unexpected error in send_alert_all: {str(e)}"
        print(f"\n{'!'*60}")
        print(f"EXCEPTION: {error_msg}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        print(f"{'!'*60}\n")
        flash(f'Error sending alerts: {str(e)}', 'error')
        return redirect(url_for('alerts'))

@app.route('/test_sms/<phone>')
def test_sms(phone):
    """Test SMS sending to a phone number"""
    test_msg = "Test message from Aegis Health System. If you receive this, SMS is working!"
    result = send_sms(phone, test_msg)
    if result and isinstance(result, str):
        return jsonify({'status': 'success', 'message_sid': result, 'message': 'SMS sent successfully'})
    elif result and isinstance(result, dict):
        error_msg = result.get('user_message', result.get('message', 'Unknown error'))
        return jsonify({'status': 'error', 'message': error_msg}), 400
    else:
        return jsonify({'status': 'error', 'message': 'Failed to send SMS. Check console for details.'}), 400

@app.route('/test_otp/<phone>')
def test_otp(phone):
    """Test OTP sending to a phone number"""
    formatted_phone = check_phone_format(phone)
    if not formatted_phone:
        return jsonify({'status': 'error', 'message': 'Invalid phone number format'}), 400
    
    otp = f"{random.randint(100000, 999999)}"
    msg = f"Your OTP for Health Alert registration is: {otp}"
    
    print(f"\n=== TEST OTP ===")
    print(f"Phone: {formatted_phone}")
    print(f"OTP: {otp}")
    print(f"Message: {msg}")
    
    result = send_sms(formatted_phone, msg)
    if result and isinstance(result, str):
        return jsonify({
            'status': 'success', 
            'message_sid': result, 
            'message': 'OTP sent successfully',
            'otp': otp,  # Only for testing - remove in production
            'phone': formatted_phone
        })
    elif result and isinstance(result, dict):
        error_msg = result.get('user_message', result.get('message', 'Unknown error'))
        return jsonify({'status': 'error', 'message': error_msg}), 400
    else:
        return jsonify({'status': 'error', 'message': 'Failed to send OTP. Check console for details.'}), 400

@app.route('/test_alert/<int:user_id>')
@admin_required
def test_alert(user_id):
    """Test sending a simple alert message"""
    try:
        users_file = 'users.csv'
        if not os.path.exists(users_file):
            return jsonify({'status': 'error', 'message': 'No users found'}), 400
        
        df = pd.read_csv(users_file, dtype={'phone': str})
        if user_id < 0 or user_id >= len(df):
            return jsonify({'status': 'error', 'message': 'Invalid user ID'}), 400
        
        user = df.iloc[user_id]
        raw_phone = str(user['phone'])
        phone = check_phone_format(raw_phone)
        city = user['city']
        
        if not phone:
            return jsonify({
                'status': 'error', 
                'message': f'Invalid phone number format: {raw_phone}',
                'raw_phone': raw_phone,
                'formatted_phone': None
            }), 400
        
        # Simple test message
        test_msg = f"Test Health Alert for {city}! This is a test message to verify alert functionality."
        
        print(f"\n=== TEST ALERT ===")
        print(f"Raw phone: {raw_phone}")
        print(f"Formatted phone: {phone}")
        print(f"City: {city}")
        print(f"Message: {test_msg}")
        
        result = send_sms(phone, test_msg)
        if result and isinstance(result, str):
            return jsonify({
                'status': 'success', 
                'message_sid': result, 
                'message': 'Test alert sent successfully',
                'phone': phone,
                'raw_phone': raw_phone,
                'city': city
            })
        elif result and isinstance(result, dict):
            error_msg = result.get('user_message', result.get('message', 'Unknown error'))
            error_code = result.get('code', 'N/A')
            return jsonify({
                'status': 'error', 
                'message': error_msg,
                'error_code': error_code,
                'phone': phone,
                'raw_phone': raw_phone
            }), 400
        else:
            return jsonify({'status': 'error', 'message': 'Failed to send test alert'}), 400
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/diagnose_sms/<int:user_id>')
@admin_required
def diagnose_sms(user_id):
    """Diagnostic endpoint to check SMS configuration and phone number"""
    try:
        users_file = 'users.csv'
        if not os.path.exists(users_file):
            return jsonify({'status': 'error', 'message': 'No users found'}), 400
        
        df = pd.read_csv(users_file, dtype={'phone': str})
        if user_id < 0 or user_id >= len(df):
            return jsonify({'status': 'error', 'message': 'Invalid user ID'}), 400
        
        user = df.iloc[user_id]
        raw_phone = str(user['phone'])
        formatted_phone = check_phone_format(raw_phone)
        
        diagnosis = {
            'user_id': user_id,
            'raw_phone': raw_phone,
            'formatted_phone': formatted_phone,
            'phone_valid': formatted_phone is not None,
            'city': user['city'],
            'twilio_account_sid': TWILIO_ACCOUNT_SID[:10] + '...' if TWILIO_ACCOUNT_SID else 'Not set',
            'twilio_phone': TWILIO_PHONE_NUMBER,
            'twilio_configured': bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER)
        }
        
        # Test Twilio connection
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            account = client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
            diagnosis['twilio_connection'] = 'success'
            diagnosis['account_status'] = account.status
            diagnosis['account_type'] = 'Trial' if account.type == 'Trial' else 'Full'
        except Exception as e:
            diagnosis['twilio_connection'] = 'failed'
            diagnosis['twilio_error'] = str(e)
        
        return jsonify({'status': 'success', 'diagnosis': diagnosis})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    """Delete a user"""
    users_file = 'users.csv'
    if os.path.exists(users_file):
        df = pd.read_csv(users_file)
        if 0 <= user_id < len(df):
            df = df.drop(df.index[user_id])
            df.to_csv(users_file, index=False)
            flash('User deleted successfully', 'success')
        else:
            flash('Invalid user ID', 'error')
    return redirect(url_for('users'))

def run_hourly_alerts():
    """Background thread to send hourly alerts to all registered users"""
    import time
    while True:
        try:
            time.sleep(3600)  # Wait 1 hour (3600 seconds)
            
            if not os.path.exists('users.csv'):
                print("[Background Alert] No users.csv found, skipping...")
                continue
            
            if gb_disease is None or gb_risk is None:
                print("[Background Alert] Model not loaded, skipping...")
                continue
            
            if DEMO_SMS:
                print("[Background Alert] DEMO_SMS is enabled, skipping real alerts...")
                continue
            
            if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
                print("[Background Alert] Twilio credentials not set, skipping...")
                continue
            
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting automated alert cycle...")
            df = pd.read_csv('users.csv', dtype={'phone': str})
            print(f"[Background Alert] Found {len(df)} users to process")
            
            success_count = 0
            fail_count = 0
            
            for idx, row in df.iterrows():
                try:
                    raw_phone = str(row['phone'])
                    phone = check_phone_format(raw_phone)
                    city = row['city']
                    
                    if not phone:
                        print(f"[Background Alert] Invalid phone format: {raw_phone}")
                        fail_count += 1
                        continue
                    
                    weather_data = fetch_weather_for_city(city)
                    if not weather_data:
                        print(f"[Background Alert] Could not fetch weather for {city}")
                        fail_count += 1
                        continue
                    
                    disease, risk, precautions = predict_health_risk(weather_data)
                    if disease is None:
                        print(f"[Background Alert] Prediction failed for {city}")
                        fail_count += 1
                        continue
                    
                    alert_msg = build_health_alert_message(city, weather_data, disease, risk, precautions)
                    result = send_sms(phone, alert_msg)
                    
                    if result and isinstance(result, str):
                        print(f"[Background Alert] ✓ Sent to {phone} ({city})")
                        success_count += 1
                    else:
                        print(f"[Background Alert] ✗ Failed to send to {phone}")
                        fail_count += 1
                    
                    time.sleep(1)  # Small delay between messages
                    
                except Exception as e:
                    print(f"[Background Alert] Error processing user {idx}: {str(e)}")
                    fail_count += 1
                    continue
            
            print(f"[Background Alert] Cycle completed: {success_count} successful, {fail_count} failed")
            
        except Exception as e:
            print(f"[Background Alert] Critical error: {str(e)}")
            import traceback
            traceback.print_exc()
            time.sleep(300)  # Wait 5 minutes before retrying

if __name__ == '__main__':
    # Start background alert thread (only in production, not in debug mode)
    if os.environ.get('FLASK_ENV') == 'production' or os.environ.get('RENDER'):
        alert_thread = threading.Thread(target=run_hourly_alerts, daemon=True)
        alert_thread.start()
        print("[INFO] Background alert thread started - hourly alerts enabled")
    
    # Disable reloader to prevent constant reloading from venv changes
    # Set use_reloader=False if you experience reload loops
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)

