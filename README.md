#Task 2: Real-Time Data Processing System for Weather Monitoring with Rollups and Aggregates 
Steps to Start 
1.	Install Python make sure Environment is set up.
2.	Now open Terminal and Install Flask and Request use following Code to do so.

pip install requests
pip install Flask

3.	 Now Download from arihantjain-aj/Weather-Application 
4.	Extract the File and open Terminal in that folder. Run This Command on it 

Python weather.py
5.	DONE!

Files in the Assignment with Code 

1.	Weather.py

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


2.	Weather.html

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weather for {{ city }}</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">

    <!-- Include Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <!-- Include Luxon -->
    <script src="https://cdn.jsdelivr.net/npm/luxon"></script>
    <!-- Include Luxon adapter for Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-luxon"></script>
    
</head>
<body>
     <div class="parallax">
        <div class="container mt-5 weather-container">
            <h1 class="text-center weather-title" style="color: white;">Weather in {{ city }}</h1>

            <div class="card mt-3 weather-card">
                <div class="card-body">
                    <h1 class="text-center weather-temp">{{ weather_data.temperature }}°{{ temperature_unit[0]|upper }}</h1>
                    <h5 class="text-center">
                        Feels Like : {{ weather_data.feels_like }}°{{ temperature_unit[0]|upper }}
                    </h5>
                    <h5 class="text-center">
                        Min\Max : {{ min_temp }}°{{ temperature_unit[0]|upper }} \{{ max_temp }}°{{ temperature_unit[0]|upper }}
                         &nbsp; &nbsp; Avg : {{ avg_temp }}°{{ temperature_unit[0]|upper }}
                    </h5>
                    <h5 class="text-center">
                        Condition : {{ weather_data.weather }} 
                        <img src="{{ weather_data.icon_url }}" alt="Weather Icon" class="weather-icon">
                        &nbsp; &nbsp; Air Quality: {{ pollution_data.aqi }}
                    </h5>            
                </div>
            </div>
        
        <!-- Create a canvas element for Chart.js -->
        <div class="mt-5">
            <h3 class="text-center" style="color: white;">Weather Updates for {{ city }} (5 Days)</h3>
            <canvas id="weatherChart" width="350" height="175"></canvas>
        </div>

        <div class="mt-5 text-center">
                <h3 style="color: white;">Weather Map</h3>
                <iframe src="https://openweathermap.org/weathermap?basemap=map&cities=true&layer=temperature&lat={{ lat }}&lon={{ lon }}&zoom=10" width="600" height="400"></iframe>
            </div>

            <a href="/" class="btn btn-secondary mt-3">Back</a>
        </div>
    </div>

    <!-- JavaScript to fetch data and display the chart -->
    <script>
        document.addEventListener("DOMContentLoaded", function() {
                // Get the city name dynamically from the Flask template
            const city = "{{ city }}";  // Fetch the city from the Flask template context

            // Fetch weather data from the Flask route
            fetch(`/get_weather_data?city=${city}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                    alert(data.error);  // Handle errors
                    return;
                    }

                    // Create the chart
                    const ctx = document.getElementById('weatherChart').getContext('2d');
                    const weatherChart = new Chart(ctx, {
                        type: 'line',  // Line chart
                        data: {
                            labels: data.timestamps.map(ts => new Date(ts)),  // Convert timestamps to Date objects
                            datasets: [{
                                label: 'Temperature (°C)',
                                data: data.temperatures,  // Temperature data
                                borderColor: 'rgba(255, 255, 255, 1)',
                                backgroundColor: 'rgba(255, 255, 255, 0.3)',
                                borderWidth: 4,
                                pointStyle: 'circle',
                                pointRadius: 5,
                                fill: true
                            }]
                        },
                        options: {
                            scales: {
                                x: {
                                    type: 'time',
                                    time: {
                                        unit: 'day',  // Display as days
                                        tooltipFormat: 'MMM D, h:mm a',
                                        displayFormats: {
                                            //hour: 'hA',  // Show hours within the days
                                            day: 'MMM D'
                                        }
                                    },
                                    title: {
                                        display: true,
                                        text: 'Date and Time (3-hour intervals)'
                                    },
                                    grid: {
                                        color: 'rgba(200, 200, 200, 1' // Adjust the color and opacity as needed
                                    }
                                },
                                y: {
                                    title: {
                                        display: true,
                                        text: 'Temperature (°C)'
                                    },
                                    grid: {
                                        color: 'rgba(200, 200, 200, 1)' // Adjust the color and opacity as needed
                                    }
                                }
                            }
                        }
                    });
                });
        });
    </script>
</body>
</html>

3.	Index.html 

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Weather App</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
  <h1 class="text-center" style="margin-top: 110px; color: white;">Weather Monitoring System</h1>
  <<div class="container weather-form text-center" style="max-width: 400px;">
    
    <form action="/weather" method="POST" class="mt-3">
      <div class="form-group d-flex flex-column align-items-center">
        <label for="city">Enter City Name:</label>
        <input type="text" class="form-control" id="city" name="city" required style="width: 200px;">
      </div>
       <div class="form-group d-flex flex-column align-items-center">
        <label for="temperature_unit">Choose Temperature Unit:</label>
        <select class="form-control" id="temperature_unit" name="temperature_unit">
          <option value="celsius">Celsius</option>
          <option value="fahrenheit">Fahrenheit</option>
          <option value="kelvin">Kelvin</option>
        </select>  
      </div>
      <button type="submit" class="btn btn-primary">Get Weather</button>
    </form>
  </div>
</body>
</html>

4.	Error.html

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
    <div class="container mt-5">
        <h1 class="text-center text-danger">{{ message }}</h1>
        <a href="/" class="btn btn-secondary mt-3">Back</a>
    </div>
</body>
</html>

5.	Style.css

.weather-icon {
    width: 70px;
    height: 70px;
    vertical-align: middle;
}
body {
    background-image: url('../static/BG.JPEG');
    background-size: cover;
    background-repeat: no-repeat;
}
h1 {
  font-size: 50px; /* Adjust the size as needed */
}
.weather-form {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background-color: #f8f8f8;
      padding: 10px;
      border-radius: 50px;
      box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.2);
}
.form-group {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.btn-primary {
  display: block; /* Make the button block-level to center it */
  margin: 0 auto; /* Center the button horizontally */
}
.form-control {
  width: 200px; /* Adjust width as needed */
}
.weather-info {
    background-color: #333; /* Adjust color for darkness */
    color: #fff; /* Text color for readability */
    padding: 20px; /* Add padding for spacing */
}
/* Assuming your canvas element has a class of 'myChart' */
.myChart {
  /* Style axis titles */
  .chart-title {
    color: white;
    font-size: 14px;
  }

  /* Style axis labels */
  .chart-label {
    color: white;
    font-size: 12px;
  }
}

