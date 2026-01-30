# Aegis Health Alert System

A Flask-based health alert system that predicts health risks based on current weather conditions and sends SMS alerts to registered users.

## Features

- **Health Risk Prediction**: Uses machine learning to predict disease risk and risk level based on climate data
- **User Registration**: Register users with phone verification via OTP (or direct registration without SMS)
- **SMS Alerts**: Send health alerts via Twilio SMS with current weather data and precautions
- **Admin Panel**: Secure admin login to manage and send alerts
- **Real-time Weather**: Fetches current weather data from OpenWeatherMap API
- **Automated Alerts**: Optional automated hourly alert system

## Project Structure

```
codecraft/
├── flask_app.py              # Main Flask application
├── send_alerts.py            # Automated hourly alert script
├── requirements.txt          # Python dependencies
├── climate_health_precaution_dataset_500.csv  # Training dataset
├── health_model.pkl          # Trained ML model
├── users.csv                 # Registered users database
├── templates/                # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── register.html
│   ├── verify_otp.html
│   ├── predict.html
│   ├── users.html
│   ├── alerts.html
│   └── admin_login.html
└── static/                   # CSS and JavaScript
    ├── style.css
    └── script.js
```

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Ensure required files exist:**
   - `climate_health_precaution_dataset_500.csv` - Training dataset
   - `health_model.pkl` - Trained model (will be auto-generated if missing)

## Usage

### Running the Flask App

```bash
python flask_app.py
```

Access the dashboard at: `http://localhost:5000`

### Admin Access

- **URL**: `http://localhost:5000/admin/login`
- **Username**: `admin`
- **Password**: `admin123`

**Note**: Change admin credentials in `flask_app.py` for production use.

### Automated Alert System

To run automated hourly alerts in the background:

```bash
python send_alerts.py
```

This script sends health alerts to all registered users every hour based on current weather conditions.

## Configuration

### Twilio SMS Setup

1. Get Twilio credentials from https://www.twilio.com/
2. Update credentials in `flask_app.py`:
   ```python
   TWILIO_ACCOUNT_SID = 'your_account_sid'
   TWILIO_AUTH_TOKEN = 'your_auth_token'
   TWILIO_PHONE_NUMBER = '+your_twilio_number'
   ```

3. **For Trial Accounts**: Verify recipient phone numbers at:
   https://console.twilio.com/us1/develop/phone-numbers/manage/verified

### Demo Mode (No SMS)

Set environment variable to skip real SMS sending:
```bash
set DEMO_SMS=true
python flask_app.py
```

## Features Overview

- **Dashboard**: System overview and statistics
- **Predict**: Manual health risk prediction with weather data
- **Register**: User registration with OTP or direct registration
- **Users**: View and manage registered users
- **Alerts**: Admin-only alert management and sending

## Requirements

- Python 3.7+
- Flask
- pandas
- scikit-learn
- Twilio (for SMS)
- requests (for weather API)

See `requirements.txt` for complete list.

## License

Copyright © 2025 Aegis Health System. All rights reserved.
