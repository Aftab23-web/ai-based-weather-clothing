from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, Response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import mysql, User, get_user_by_email, create_user, save_history, get_history
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
import requests, smtplib, joblib, csv, os, json, random
from io import StringIO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
import pandas as pd
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message = None
login_manager.init_app(app)

app.secret_key = os.getenv('SECRET_KEY')
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
mysql.init_app(app)

WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

model = joblib.load('ml/outfit_model.pkl')

with open('data/shopping_data.json') as f:
    shopping_data = json.load(f)

@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, email, password, name, whatsapp, gender, age, is_admin, role FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    return User(*row) if row else None


# ---------- Helpers ----------

def normalize_weather(weather_main):
    mapping = {
        "clear": "clear",
        "clouds": "clear",
        "rain": "rainy",
        "drizzle": "rainy",
        "thunderstorm": "rainy",
        "snow": "snowy",
        "mist": "foggy",
        "fog": "foggy",
        "haze": "foggy"
    }
    return mapping.get(weather_main.lower(), "clear")

def get_temp_category(temp):
    if temp < 10:
        return 'cold'
    elif 10 <= temp < 20:
        return 'mild'
    elif 20 <= temp < 30:
        return 'warm'
    else:
        return 'hot'

def get_age_group(age):
    try:
        age = int(current_user.age)
    except ValueError:
        print(f"[DEBUG] Invalid age passed: {age}")
        return "adult"  # fallback if invalid
    
    if age < 13:
        return "child"
    elif age < 20:
        return "teen"
    elif age < 60:
        return "adult"
    else:
        return "senior"


def generate_safety_tips(temp, weather):
    temp = float(temp)
    tips = []
    if 'rain' in weather.lower():
        tips += ["Carry an umbrella.", "Wear waterproof shoes.", "Be cautious of slippery roads."]
    if temp < 10:
        tips += ["Wear warm clothes.", "Use gloves and caps."]
    elif 10 <= temp <= 25:
        tips += ["Wear light layers.", "Carry a jacket if needed."]
    else:
        tips += ["Use sunscreen.", "Wear breathable clothes."]
    return tips

def get_outfit_from_data(gender, age_group, weather, temp_level, preference):
    try:
        with open('data/shopping_data.json') as f:
            data = json.load(f)
        return data[gender][age_group][weather][temp_level][preference]
    except KeyError:
        print(f"[DEBUG] Missing combo: {gender}, {age_group}, {weather}, {temp_level}, {preference}")
        return []



def load_shopping_recommendation(gender, weather, temp_level, preference, age):
    try:
        age_group = get_age_group(age)
        with open('data/shopping_data.json') as f:
            data = json.load(f)

        return data[gender][age_group][weather][temp_level][preference]
    except KeyError:
        print(f"[DEBUG] Missing combo: {gender}, {age_group}, {weather}, {temp_level}, {preference}")
        # Fallback to casual if preference fails
        if preference != 'casual':
            try:
                return data[gender][age_group][weather][temp_level]['casual']
            except:
                return []
        return []


def predict_outfit(temp, humidity, weather_main):
    gender = current_user.gender
    temp_level = get_temp_category(temp)
    return []

# ---------- Routes ----------

@app.route('/')
@login_required
def index():
    return render_template('index.html', name=current_user.name)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        gender = request.form.get('gender')
        age = request.form.get('age')
        password = request.form.get('password')
        whatsapp = request.form.get('whatsapp')

        existing_user = get_user_by_email(email)
        
        if existing_user:
            flash('Email already registered. Please log in.')
            return redirect(url_for('login'))  #  redirect to login if user exists

        #  Create new user and login automatically
        create_user(email, password, name, gender, age, whatsapp)
        user = get_user_by_email(email)
        login_user(user)
        flash('Account created successfully. You are now logged in.')
        return redirect(url_for('index'))  # redirect to home/index

    return render_template('signup.html')


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = get_user_by_email(email)

        if user:
            if user.check_password(password):
                login_user(user)
                return redirect(url_for('index'))
            else:
                flash('Incorrect password. Please try again.')
        else:
            # flash('Email not registered. Redirecting to signup...')
            return redirect(url_for('signup'))

    return render_template('login.html')
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = get_user_by_email(email)
        if user:
            otp = str(random.randint(100000, 999999))
            session['reset_email'] = email
            session['reset_otp'] = otp
            # Send reset email
            def send_reset_email(recipient_email, subject, body):
                msg = MIMEMultipart()
                msg['From'] = formataddr(("Weather Clothing Assistant", EMAIL_ADDRESS))
                msg['To'] = recipient_email
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))
                with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
                    smtp.starttls()
                    smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                    smtp.send_message(msg)

            send_reset_email(email, "Password Reset Code", f"Your reset code is: {otp}")
            flash("Reset code sent to your email.")
            return redirect(url_for('reset_password'))
        else:
            flash("Email not found.")
    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        otp_input = request.form['otp']
        new_password = request.form['new_password']

        if otp_input == session.get('reset_otp'):
            email = session.get('reset_email')

            if email:
                hashed_password = generate_password_hash(new_password)
                cur = mysql.connection.cursor()
                cur.execute("UPDATE users SET password=%s WHERE email=%s", (hashed_password, email))
                mysql.connection.commit()
                cur.close()

                # Clear session data
                session.pop('reset_otp', None)
                session.pop('reset_email', None)

                flash("Password updated successfully.")
                return redirect(url_for('login'))
            else:
                flash("Session expired. Please try again.")
                return redirect(url_for('forgot_password'))

        else:
            flash("Invalid OTP. Please try again.")

    return render_template('reset_password.html')

def send_html_email(to_email, subject, html_body):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = formataddr(("Clothing App", EMAIL_ADDRESS))
    msg['To'] = to_email
    msg.attach(MIMEText(html_body, 'html'))

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

def send_weekly_planner_email(to_email, city, forecast):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Weekly Outfit Planner for {city.title()}"
    msg['From'] = formataddr(("Weather Clothing Assistant", EMAIL_ADDRESS))
    msg['To'] = to_email

    html = f"""
    <html>
    <body style="font-family: Arial; padding: 20px;">
        <h2>Your Weekly Travel Packing Planner for <b>{city.title()}</b></h2>
        <hr>
    """

    for date, data in forecast.items():
        html += f"""
        <h3>{date}</h3>
        <p><b>Weather:</b> {data['weather'].capitalize()} | <b>Temp:</b> {data['temp']}°C</p>
        """

        if data.get('outfits'):
            for item in data['outfits']:
                html += f"""
                <div style="margin-bottom: 15px;">
                    <p><b>{item['text']}</b></p>
                    <a href="{item['link']}" target="_blank">
                        <img src="{item['image']}" width="130" style="border-radius:6px;border:1px solid #ccc;">
                    </a>
                </div>
                """
        else:
            html += "<p>No outfit recommendation available.</p>"

        html += "<hr>"

    html += """
        <p>Stay safe and travel smart!<br>Weather Clothing Assistant Team</p>
    </body>
    </html>
    """

    msg.attach(MIMEText(html, 'html'))

    # Send the email once for the full week
    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)


def send_recommendation_email(recipient_email, city, temp, weather, recommendation, tips):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Outfit Recommendation for {city}"
    msg['From'] = formataddr(("Weather Clothing Assistant", EMAIL_ADDRESS))
    msg['To'] = recipient_email

    # Compose HTML content
    html_items = ""
    for item in recommendation["items"]:
        html_items += f"""
        <div style="margin-bottom: 20px;">
            <p><strong>{item['text']}</strong></p>
            <a href="{item['link']}" target="_blank">
                <img src="{item['image']}" width="150">
            </a>
        </div>
        """

    tip_html = "<ul>" + "".join([f"<li>{tip}</li>" for tip in tips]) + "</ul>"

    html = f"""
    <html>
      <body style="font-family: Arial; padding: 20px;">
        <h2> Your Personalized Outfit Recommendation</h2>
        <p><strong>Location:</strong> {city}</p>
        <p><strong>Temperature:</strong> {temp}°C</p>
        <p><strong>Weather:</strong> {weather}</p>
        <hr>
        <h3> Recommended Items:</h3>
        {html_items}
        <hr>
        <h3> Safety Tips:</h3>
        {tip_html}
        <p>Stay safe and dress smart!<br>- Weather Clothing Assistant</p>
      </body>
    </html>
    """

    msg.attach(MIMEText(html, 'html'))

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)


@app.route('/recommend', methods=['POST'])
@login_required
def recommend():
    data = request.get_json()
    city = data['city']
    preference = data.get('preference', 'casual')

    gender = current_user.gender.strip().lower()
    age = int(current_user.age)
    age_group = get_age_group(age)

    res = requests.get("http://api.openweathermap.org/data/2.5/weather", params={
        'q': city, 'appid': WEATHER_API_KEY, 'units': 'metric'
    }).json()
    
    if res.get("cod") != 200:
        return jsonify({'error': 'Weather data could not be fetched. Please check the city name and try again.'}), 400

    if res.get('main') and res.get('weather'):
        temp = res['main']['temp']
        humidity = res['main']['humidity']
        pressure = res['main']['pressure']
        weather_main = res['weather'][0]['main'].lower()
        wind_speed = res['wind']['speed']
        weather_icon = res['weather'][0]['icon']

        temp_level = get_temp_category(temp)
        outfit_items = get_outfit_from_data(gender, age_group, weather_main, temp_level, preference)

        recommendation = {
            "text": "Here's what we recommend based on weather:",
            "items": outfit_items
        }

        tips = generate_safety_tips(temp, weather_main)

        send_recommendation_email(
            recipient_email=current_user.email,
            city=city,
            temp=temp,
            weather=weather_main,
            recommendation=recommendation,
            tips=tips
        )

        session['latest_result'] = {
            'city': city,
            'temp': temp,
            'humidity': humidity,
            'pressure': pressure,
            'weather': weather_main,
            'wind_speed': wind_speed,
            'weather_icon': weather_icon,
            'recommendation': recommendation,
            'tips': tips
        }

        save_history(
            user_id=current_user.id,
            city=city,
            weather=weather_main,
            temp=temp,
            rec=", ".join([item["text"] for item in outfit_items])
        )

        return jsonify({'redirect': url_for('result')})

    # fallback for failed API
    return jsonify({'error': 'Could not fetch weather'}), 400

@app.route('/result')
@login_required
def result():
    if 'latest_result' not in session:
        return redirect(url_for('index'))
    return render_template('result.html', **session['latest_result'])

@app.route('/planner', methods=['GET', 'POST'])
@login_required
def planner():
    if request.method == 'POST':
        city = request.form.get("city")
        preference = request.form.get("preference", "casual")  #  fix this line
        session['planner_city'] = city
        session['planner_preference'] = preference
        return redirect(url_for('planner_result'))

    return render_template('planner.html')

@app.route('/planner-result', methods=['GET', 'POST'])
@login_required
def planner_result():
    city = session.get('planner_city')
    if not city:
        flash("Please enter your trip details.")
        return redirect(url_for('planner'))

    # ⏱ Use existing session data if available
    if 'weekly_planner' in session and session['weekly_planner'].get('city') == city:
        forecast = session['weekly_planner']['forecast']
        return render_template("planner_result.html", city=city, forecast=forecast)

    # User context
    try:
        age = int(current_user.age)
    except (ValueError, TypeError):
        age = 25
    age_group = get_age_group(age)
    gender = current_user.gender
    preference = session.get('planner_preference', 'casual')

    # Fetch forecast once
    res = requests.get("http://api.openweathermap.org/data/2.5/forecast", params={
        'q': city, 'appid': WEATHER_API_KEY, 'units': 'metric'
    }).json()
    
    if res.get("cod") == "404":
        flash(" City not found. Please enter a valid city.")
        return redirect(url_for('planner'))

    forecast = {}
    seen_dates = set()

    for entry in res.get("list", []):
        date = entry['dt_txt'][:10]
        if date in seen_dates:
            continue
        seen_dates.add(date)

        temp = entry['main']['temp']
        weather = entry['weather'][0]['main'].lower()
        normalized_weather = normalize_weather(weather)
        temp_category = get_temp_category(temp)

        outfits = get_outfit_from_data(gender, age_group, normalized_weather, temp_category, preference)

        forecast[date] = {
            'temp': temp,
            'weather': normalized_weather,
            'outfits': outfits
        }

    session['weekly_planner'] = {
        "city": city,
        "forecast": forecast
    }

    # Send email once after all processing
    send_weekly_planner_email(current_user.email, city, forecast)
    flash("Weekly outfit planner sent to your email.")

    return render_template("planner_result.html", city=city, forecast=forecast)

@app.route('/download_planner')
@login_required
def download_planner():
    planner_data = session.get('weekly_planner')
    if not planner_data:
        flash("No planner data found.")
        return redirect(url_for('planner'))

    city = planner_data["city"]
    forecast = planner_data["forecast"]

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Temperature (°C)', 'Weather', 'Outfit Text', 'Link'])

    for date, data in forecast.items():
        if data['outfits']:
            for item in data['outfits']:
                writer.writerow([date, data['temp'], data['weather'], item['text'], item['link']])
        else:
            writer.writerow([date, data['temp'], data['weather'], "No outfit", ""])

    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment;filename={city}_weekly_planner.csv"}
    )

@app.route('/history')
@login_required
def history():
    user_history = get_history(current_user.id)
    return render_template('history.html', history=user_history)

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return "Access denied", 403

    cur = mysql.connection.cursor()

    # ✅ Total users
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    # ✅ Top cities searched
    cur.execute("""
        SELECT city, COUNT(*) as count
        FROM history
        GROUP BY city
        ORDER BY count DESC
        LIMIT 10
    """)
    top_cities = cur.fetchall()

    # ✅ Most common weather for outfit
    cur.execute("""
        SELECT weather, COUNT(*) as count
        FROM history
        GROUP BY weather
        ORDER BY count DESC
        LIMIT 10
    """)
    weather_stats = cur.fetchall()

    # ✅ Planner Usage (city-wise outfit recommendations)
    cur.execute("""
        SELECT city, COUNT(*) as count
        FROM history
        WHERE rec LIKE '%Buy%'
        GROUP BY city
        ORDER BY count DESC
        LIMIT 10
    """)
    planner_usage = cur.fetchall()

    cur.close()

    return render_template(
        'admin.html',
        total_users=total_users,
        top_cities=top_cities,
        weather_stats=weather_stats,
        planner_usage=planner_usage  # ✅ include this
    )

@app.route('/admin/download')
@login_required
def download_admin_report():
    if not current_user.is_admin:
        return "Access denied", 403

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT users.name, users.email, history.city, history.weather, history.temp, history.rec, history.timestamp 
        FROM history JOIN users ON users.id = history.user_id 
        ORDER BY timestamp DESC
    """)
    rows = cur.fetchall()
    cur.close()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Email', 'City', 'Weather', 'Temp', 'Recommendation', 'Timestamp'])

    for row in rows:
        writer.writerow(row)  # Write as-is (no JSON parsing)

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=admin_full_report.csv"}
    )
    
if __name__ == "__main__":
    app.run(debug=True)
