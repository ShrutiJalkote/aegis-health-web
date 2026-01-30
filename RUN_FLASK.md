# Running the Flask Application

## Quick Start

1. **Activate virtual environment** (if using venv):
   ```bash
   .\venv\Scripts\Activate.ps1  # Windows PowerShell
   # or
   .\venv\Scripts\activate.bat   # Windows CMD
   ```

2. **Install dependencies** (if not already installed):
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Flask application:**
   ```bash
   python flask_app.py
   ```

4. **Access the dashboard:**
   Open your browser and navigate to: `http://localhost:5000`

## Admin Login

To access the alert management system:

1. Go to: `http://localhost:5000/admin/login`
2. Login with:
   - **Username**: `admin`
   - **Password**: `admin123`

After login, you'll be redirected to the alerts page where you can send health alerts to registered users.

**Important**: Change the admin credentials in `flask_app.py` before deploying to production.

## Features Available

- **Dashboard** (`/`): Overview of system status and statistics
- **Predict** (`/predict`): Health risk prediction with weather data integration
- **Register** (`/register`): User registration with OTP verification or direct registration
- **Users** (`/users`): View and manage registered users
- **Alerts** (`/alerts`): Admin-only alert management and sending (requires login)

## Starting the Automated Alert System

To run automated hourly alerts in a separate terminal:

```bash
python send_alerts.py
```

This will:
- Send health alerts to all registered users every hour
- Use current weather data for each user's city
- Continue running until stopped (Ctrl+C)

## Troubleshooting

### SMS Not Sending

1. **Twilio Trial Account**: Verify recipient phone numbers at:
   https://console.twilio.com/us1/develop/phone-numbers/manage/verified

2. **Daily Limit**: Trial accounts are limited to 50 messages/day

3. **Demo Mode**: Set `DEMO_SMS=true` environment variable to skip real SMS (for testing)

### Model Not Loading

- The app will automatically train the model if `health_model.pkl` is missing
- Ensure `climate_health_precaution_dataset_500.csv` exists in the project directory

### Port Already in Use

If port 5000 is already in use:
- Stop the existing Flask process
- Or change the port in `flask_app.py`:
  ```python
  app.run(debug=True, host='0.0.0.0', port=5001)  # Change port
  ```

## Notes

- The app runs in debug mode by default (auto-reload disabled to prevent reload loops)
- Model is automatically loaded/trained on startup
- User data is stored in `users.csv`
- Alert messages use current weather data from OpenWeatherMap API
