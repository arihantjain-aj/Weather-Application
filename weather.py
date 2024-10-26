import requests
import time
import sqlite3
import json
import webbrowser

from flask import Flask, render_template, request, jsonify

# Your API key here
API_KEY = '7a081c0107a7fcd986ea1401833d3391'  
# API endpoint for 5-day/3-hour forecast
FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast?"
AIR_POLLUTION_URL = "http://api.openweathermap.org/data/2.5/air_pollution"
GEO_URL = "http://api.openweathermap.org/geo/1.0/direct"

# API endpoint
BASE_URL = "http://api.openweathermap.org/data/2.5/weather?"

app = Flask(__name__)

def setup_database():
    conn = sqlite3.connect('weather_data.db')
    cursor = conn.cursor()
    
    # Create a table to store weather data
    cursor.execute('''CREATE TABLE IF NOT EXISTS weather (
        city TEXT,
        temperature REAL,
        feels_like REAL,
        weather TEXT,
        timestamp INTEGER
        min_temp REAL,
        max_temp REAL,
        avg_temp REAL
    )''')
    
    conn.commit()
    conn.close()

setup_database()

def get_weather(city, temperature_unit):
    # Build the URL for the API call
    url = f"{BASE_URL}q={city}&appid={API_KEY}"
    
    # Send GET request
    response = requests.get(url)
    
    # If the response status code is 200, the request was successful
    if response.status_code == 200:
        data = response.json()
        
        # Extract relevant weather information
        main = data['main']
        # Convert temperature based on the chosen unit
        if temperature_unit == 'celsius':
            temperature = round(main['temp'] - 273.15, 1)
            feels_like = round(main['feels_like'] - 273.15, 1)
        elif temperature_unit == 'fahrenheit':
            temperature = round((main['temp'] - 273.15) * 9/5 + 32, 1)
            feels_like = round((main['feels_like'] - 273.15) * 9/5 + 32, 1)
        elif temperature_unit == 'kelvin':
            temperature = main['temp']
            feels_like = main['feels_like']
        else:
            # Handle invalid unit
            return None
        weather_condition = data['weather'][0]['description']
        icon = data['weather'][0]['icon']  # Get the icon code
        icon_url = f"http://openweathermap.org/img/wn/{icon}.png"  # Create the icon URL
        dt = data['dt']
        
        return {
            "temperature": temperature,
            "feels_like": feels_like,
            "weather": weather_condition,
            "icon_url": icon_url,  # Include icon URL in the data
            "timestamp": dt
        }
    else:
        return None

@app.route('/get_weather_data', methods=['GET'])
def get_weather_data():
    city = request.args.get('city')
    forecast_data = get_forecast(city)

    if forecast_data:
        # Calculate min, max, and average temperatures from forecast data
        temperatures = [entry['temperature'] for entry in forecast_data]
        min_temp = min(temperatures)
        max_temp = max(temperatures)
        avg_temp = round(sum(temperatures) / len(temperatures), 1)

        data = {
            "timestamps": [entry['timestamp'] * 1000 for entry in forecast_data],
            "temperatures": temperatures,
            "min_temp": min_temp,
            "max_temp": max_temp,
            "avg_temp": avg_temp
        }
        return jsonify(data)
    else:
        return jsonify({"error": "Could not retrieve forecast data."}), 400


def get_forecast(city):
    # Build the URL for the 5-day forecast API call dynamically based on the city
    url = f"{FORECAST_URL}q={city}&appid={API_KEY}"
    
    # Send GET request
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()

        forecast_data = []
        for entry in data['list']:
            # Extract the relevant data for each 3-hour forecast
            temperature = round(entry['main']['temp'] - 273.15, 1)  # Convert Kelvin to Celsius
            feels_like = round(entry['main']['feels_like'] - 273.15, 1)
            weather_condition = entry['weather'][0]['description']
            timestamp = entry['dt']  # Unix timestamp

            forecast_data.append({
                "temperature": temperature,
                "feels_like": feels_like,
                "weather": weather_condition,
                "timestamp": timestamp
            })
        
        return forecast_data  # Return a list of forecast data (every 3 hours for 5 days)
    
    else:
        return None

def store_weather_data(city, weather_data):
    conn = sqlite3.connect('weather_data.db')
    cursor = conn.cursor()
    
    # Insert data into the table
    cursor.execute('''INSERT INTO weather (city, temperature, feels_like, weather, timestamp)
                      VALUES (?, ?, ?, ?, ?)''', 
                      (city, weather_data['temperature'], weather_data['feels_like'], weather_data['weather'], weather_data['timestamp']))
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')  # Render the HTML form for city input

def get_coordinates(city):
    url = f"{GEO_URL}?q={city}&limit=1&appid={API_KEY}"
    response = requests.get(url)
    data = response.json()
    if data:
        return data[0]['lat'], data[0]['lon']
    return None, None

def get_air_quality(lat, lon):
    url = f"{AIR_POLLUTION_URL}?lat={lat}&lon={lon}&appid={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        aqi = data['list'][0]['main']['aqi']

        # Mapping AQI to description
        if aqi == 1:
            aqi_desc = "Good"
        elif aqi == 2:
            aqi_desc = "Fair"
        elif aqi == 3:
            aqi_desc = "Moderate"
        elif aqi == 4:
            aqi_desc = "Poor"
        elif aqi == 5:
            aqi_desc = "Very Poor"
        else:
            aqi_desc = "Unknown"

        return {
            "aqi": f"{aqi_desc}"  # Format AQI with description
        }
    else:
        return None

@app.route('/weather', methods=['POST'])
def weather():
    city = request.form['city'].strip().capitalize()
    temperature_unit = request.form['temperature_unit']
    lat, lon = get_coordinates(city)
    weather_data = get_weather(city, temperature_unit)
    pollution_data = get_air_quality(lat, lon)
    forecast_data = get_forecast(city)  # Get forecast data

    if weather_data:
        # Calculate min, max, and average temperatures from forecast data
        temperatures = [forecast['temperature'] for forecast in forecast_data]
        min_temp = min(temperatures)
        max_temp = max(temperatures)
        avg_temp = round(sum(temperatures) / len(temperatures), 1)

        return render_template('weather.html', city=city, weather_data=weather_data, pollution_data=pollution_data, lat=lat, lon=lon, temperature_unit=temperature_unit, min_temp=min_temp, max_temp=max_temp, avg_temp=avg_temp)
    else:
        return render_template('error.html', message=f"Could not retrieve data for {city}")

def collect_weather_data_with_alerts(city, interval=300, threshold=None):
    """Collect weather data at intervals and check against thresholds."""
    consecutive_alerts = 0  # Track consecutive alerts
    
    while True:
        weather_data = get_weather(city)
        
        if weather_data:
            print(f"Collected weather data for {city}")
            store_weather_data(city, weather_data)
            
            if threshold:
                if check_thresholds(weather_data, threshold):
                    consecutive_alerts += 1
                    if consecutive_alerts == 2:  # Trigger alert after 2 consecutive breaches
                        print(f"ALERT TRIGGERED: Weather condition exceeded threshold for {city}")
                else:
                    consecutive_alerts = 0  # Reset counter if the condition is not met
        else:
            print(f"Failed to get weather data for {city}")
        
        # Wait for the specified interval
        time.sleep(interval)

def check_thresholds(weather_data, threshold):
    """Check if the current weather data exceeds the defined thresholds."""
    exceeded = False
    
    if 'temperature' in threshold and weather_data['temperature'] > threshold['temperature']:
        print(f"ALERT! Temperature has exceeded the threshold of {threshold['temperature']}°C")
        exceeded = True
    
    return exceeded

if __name__ == '__main__':
    # Automatically open the browser
    webbrowser.open('http://127.0.0.1:5000/')
    
    # Start the Flask app
    app.run(debug=True)
