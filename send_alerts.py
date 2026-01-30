import pandas as pd
from twilio.rest import Client
import time
import pickle
import requests
import os
from datetime import datetime

# Twilio credentials - loaded from environment variables
# Set these in your environment or Render dashboard:
# TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')

def send_sms(phone, msg):
    """Send SMS via Twilio with error handling"""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=msg,
            from_=TWILIO_PHONE_NUMBER,
            to=phone
        )
        print(f"[SUCCESS] SMS sent to {phone}. Message SID: {message.sid}")
        return True
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        print(f"[ERROR] Failed to send SMS to {phone}")
        print(f"  Error type: {error_type}")
        print(f"  Error message: {error_msg}")
        
        # Provide specific error guidance
        if "exceeded" in error_msg.lower() and ("daily" in error_msg.lower() or "limit" in error_msg.lower() or "50" in error_msg):
            print(f"  → Issue: Twilio daily message limit exceeded (50 messages/day for trial accounts)")
            print(f"  → Solution: Upgrade Twilio account or wait until tomorrow")
        elif "not a valid phone number" in error_msg.lower() or "invalid" in error_msg.lower():
            print(f"  → Issue: Invalid phone number format: {phone}")
        elif "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
            print(f"  → Issue: Twilio authentication failed - check credentials")
        elif "insufficient" in error_msg.lower() or "balance" in error_msg.lower():
            print(f"  → Issue: Insufficient Twilio account balance")
        elif "unverified" in error_msg.lower() or "trial" in error_msg.lower():
            print(f"  → Issue: Phone number {phone} not verified in Twilio (trial account)")
        elif "permission" in error_msg.lower() or "not allowed" in error_msg.lower():
            print(f"  → Issue: Permission denied - check Twilio account settings")
        
        return False

# Create PID file to indicate alert system is running
PID_FILE = 'alert_process.pid'
try:
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    print(f"[INFO] Alert system started. PID file created: {PID_FILE}")
except Exception as e:
    print(f"[WARNING] Could not create PID file: {e}")

# Cleanup function to remove PID file on exit
import atexit
def cleanup():
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
            print(f"[INFO] PID file removed: {PID_FILE}")
    except:
        pass

atexit.register(cleanup)

with open('health_model.pkl', 'rb') as file:
    bundle = pickle.load(file)
gb_disease = bundle['gb_disease']
gb_risk = bundle['gb_risk']
le_disease = bundle['le_disease']
le_risklevel = bundle['le_risklevel']
precautions_tab = bundle['precautions']

def fetch_weather_for_city(city, api_key='ac9ea2b0cba9ab0943058f803c7f6e68'):
    url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric'
    res = requests.get(url)
    data = res.json()
    if data.get('cod') != 200:
        return None
    return {
        'Temperature': data['main']['temp'],
        'Humidity': data['main']['humidity'],
        'AQI': 100,
        'Rainfall': data.get('rain', {}).get('1h', 0),
        'WindSpeed': data['wind']['speed'],
        'Pressure': data['main']['pressure']
    }

def check_phone_format(phone):
    # Accepts +91XXXXXXXXXX, 91XXXXXXXXXX, or XXXXXXXXXX
    phone_digits = str(phone).strip().replace(" ", "").replace("-", "")
    if phone_digits.startswith('+'):
        return phone_digits
    elif phone_digits.startswith('91') and len(phone_digits)==12:
        return '+' + phone_digits
    elif len(phone_digits)==10:
        return '+91' + phone_digits
    else:
        return None

while True:
    try:
        if not os.path.exists('users.csv'):
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] No users.csv found, waiting...")
            time.sleep(3600)
            continue
        
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting alert cycle...")
        users = pd.read_csv('users.csv')
        print(f"Found {len(users)} users to process")
        
        for idx, row in users.iterrows():
            try:
                phone, _, city = row['phone'], row['password'], row['city']
                phone = check_phone_format(phone)
                if not phone:
                    print(f"  → Skipping invalid phone number: {row['phone']}")
                    continue  # Skip invalid/blank phone numbers
                
                weather_data = fetch_weather_for_city(city)
                if not weather_data:
                    print(f"  → Could not fetch weather for {city}, skipping")
                    continue
                
                input_df = pd.DataFrame([weather_data], columns=['Temperature', 'Humidity', 'AQI', 'Rainfall', 'WindSpeed', 'Pressure'])
                y_d_pred = le_disease.inverse_transform(gb_disease.predict(input_df))[0]
                y_r_pred = le_risklevel.inverse_transform(gb_risk.predict(input_df))[0]
                result = precautions_tab[
                    (precautions_tab['Disease_Risk'] == y_d_pred) & (precautions_tab['Risk_Level'] == y_r_pred)
                ]
                prc = result.iloc[0][['Precaution_1', 'Precaution_2', 'Precaution_3']].tolist() if not result.empty else ["No data"]*3
                
                # Build alert message in same format as flask_app.py
                now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
                alert_msg = (
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
                    f"Disease Risk: {y_d_pred}\n"
                    f"Risk Level: {y_r_pred}\n\n"
                    f"PRECAUTIONS:\n"
                    f"1. {prc[0]}\n"
                    f"2. {prc[1]}\n"
                    f"3. {prc[2]}\n\n"
                    f"Stay safe! - Aegis Health"
                )
                print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Processing alert for {phone} ({city})")
                success = send_sms(phone, alert_msg)
                if not success:
                    print(f"  → Alert failed for {phone}, will retry in next cycle")
            except Exception as e:
                print(f"[ERROR] Error processing user {idx}: {str(e)}")
                print(f"  Error type: {type(e).__name__}")
                continue  # Continue with next user
        
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Alert cycle completed. Waiting 1 hour...")
        time.sleep(3600)
    except KeyboardInterrupt:
        print("\n[INFO] Alert service stopped by user")
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
                print(f"[INFO] PID file removed: {PID_FILE}")
        except:
            pass
        break
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Alert service error: {str(e)}")
        print(f"  Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        print("  Waiting 5 minutes before retrying...")
        time.sleep(300)  # Wait 5 minutes before retryi