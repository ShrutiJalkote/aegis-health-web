# Aegis Health Alert System

A Flask-based health alert system that predicts health risks based on current weather conditions and sends SMS alerts to registered users.

## Website Link

https://aegis-health-web.onrender.com

## Features

- **Health Risk Prediction**: Uses machine learning to predict disease risk and risk level based on climate data
- **User Registration**: Register users with phone verification via OTP (or direct registration without SMS)
- **SMS Alerts**: Send health alerts via Twilio SMS with current weather data and precautions
- **Admin Panel**: Secure admin login to manage and send alerts
- **Real-time Weather**: Fetches current weather data from OpenWeatherMap API
- **Automated Alerts**: Optional automated hourly alert system

## This project uses Twilio SMS service for sending health alert messages.

Currently, the project is running on Twilio Free Trial Plan, which has a limitation:

SMS messages can be sent only to verified phone numbers added in the Twilio account.

If a user registers with an unverified number, OTP and alert messages will not be delivered.

### Verified Numbers in This Project

The following numbers are already verified in my Twilio account and will receive SMS alerts correctly:

7350512745

7058050251

If you try to register using any other number, SMS delivery will fail because that number is not registered in Twilio trial account.

To test alerts properly, please use one of the above verified numbers.

### Screenshots

For reference, I have also added screenshots at last showing:

Complete Dashboard

User Registration

OTP Verification

Alert Messages Sent via Twilio

These screenshots help verify that the system and SMS alerts are working correctly.

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

## Deployment on Render

### Quick Deploy (Recommended)

1. **Push to GitHub** (already done):
   - Repository: `https://github.com/ShrutiJalkote/aegis-health-web`

2. **Connect to Render**:
   - Go to https://render.com
   - Sign up/Login with GitHub
   - Click **New +** → **Blueprint** (or **Web Service**)
   - Connect your GitHub repo: `ShrutiJalkote/aegis-health-web`
   - Render will auto-detect `render.yaml` and create both services

3. **Set Environment Variables** in Render Dashboard:
   - Go to each service → **Environment** tab
   - Add these variables:
     ```
     TWILIO_ACCOUNT_SID = your_twilio_account_sid
     TWILIO_AUTH_TOKEN = your_twilio_auth_token
     TWILIO_PHONE_NUMBER = +14793424450 (your Twilio number)
     DEMO_SMS = false
     ```

4. **Deploy**:
   - Click **Create** or **Apply** - Render will build and deploy automatically
   - Your app will be live at: `https://aegis-health-web.onrender.com`

### Manual Deploy (Without render.yaml)

**Web Service:**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn "flask_app:app" --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

**Background Worker:**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python send_alerts.py`

## Configuration

### Twilio SMS Setup

1. Get Twilio credentials from https://www.twilio.com/
2. Set environment variables (NOT in code):
   ```
   TWILIO_ACCOUNT_SID = your_account_sid
   TWILIO_AUTH_TOKEN = your_auth_token
   TWILIO_PHONE_NUMBER = +your_twilio_number
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

## Dashboard Screenshot



<img width="1919" height="1023" alt="Screenshot 2026-01-31 163933" src="https://github.com/user-attachments/assets/0a65b324-7db2-4198-8c8c-11f870545ef7" />

<img width="1896" height="1021" alt="Screenshot 2026-01-31 164012" src="https://github.com/user-attachments/assets/3d99677e-36ec-4c22-ad70-c58e624cbbee" />

<img width="1906" height="1016" alt="Screenshot 2026-01-31 164037" src="https://github.com/user-attachments/assets/229622ff-9379-46de-aacb-6aa8739da4de" />

<img width="1919" height="1019" alt="Screenshot 2026-01-31 164445" src="https://github.com/user-attachments/assets/2679dc9c-0426-45d2-b690-9309f950a0c8" />

<img width="1916" height="1019" alt="Screenshot 2026-01-31 164907" src="https://github.com/user-attachments/assets/bf106c07-d40e-403c-ab0e-e918c4ff4667" />

<img width="1908" height="1020" alt="Screenshot 2026-01-31 164949" src="https://github.com/user-attachments/assets/8f0a52ed-29e1-494d-b803-bc22d1a4d901" />

<img width="1901" height="1020" alt="Screenshot 2026-01-31 165008" src="https://github.com/user-attachments/assets/ee777adf-8810-4fd5-98bc-1a2f81554c44" />

<img width="1902" height="1024" alt="Screenshot 2026-01-31 165038" src="https://github.com/user-attachments/assets/02efa064-edfc-431c-83db-810c86910d05" />

<img width="1900" height="1026" alt="Screenshot 2026-01-31 165059" src="https://github.com/user-attachments/assets/1bca8964-557d-4a80-9a28-5447727484c4" />

<img width="1917" height="1013" alt="Screenshot 2026-01-31 165129" src="https://github.com/user-attachments/assets/eed63583-0445-434a-b9ba-93e0ca2785d5" />

<img width="1902" height="1015" alt="Screenshot 2026-01-31 165201" src="https://github.com/user-attachments/assets/2ffc1476-b458-46f1-9241-95c007475fdb" />

<img width="1895" height="1018" alt="Screenshot 2026-01-31 165223" src="https://github.com/user-attachments/assets/7bf349f8-8f4c-4129-855b-38c2792d3f1e" />

<img width="1903" height="1013" alt="Screenshot 2026-01-31 165247" src="https://github.com/user-attachments/assets/e9a1e355-ecc7-4a0e-9235-c747bac57ba0" />

### OTP and Alert msg screnshot


![otp_alert_msg_1](https://github.com/user-attachments/assets/6beed329-37b7-463f-8231-0b48772e04f6)


![otp_alert_msg](https://github.com/user-attachments/assets/3bbc0327-15fb-4e82-8a24-9349b3a3a43a)

## License

Copyright © 2025 Aegis Health System. All rights reserved.
