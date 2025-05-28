#!/usr/bin/env python3
"""
Flask web application for Kids Weather.

This module provides a web interface to the weather processing system,
with endpoints for HTML, JSON, and plain text output formats.
"""
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "requests",
#     "python-dotenv",
#     "click",
#     "flask",
#     "diskcache",
# ]
# ///
import sys
from flask import Flask, render_template, jsonify
from dotenv import load_dotenv

from config import DEFAULT_LAT, DEFAULT_LON
from utils import init_llm_log_db
from weather_processor import get_weather_report

# Initialize Flask app
app = Flask(__name__)

def get_weather_data():
    """Helper function to fetch weather data for Flask routes."""
    # Use default location from config
    lat = DEFAULT_LAT
    lon = DEFAULT_LON

    # Get weather report with logging enabled
    weather_data = get_weather_report(
        lat,
        lon,
        log_interaction=True,  # Enable logging for Flask requests
        source='flask'         # Set source to 'flask'
    )

    return weather_data

@app.route('/')
def home():
    """Render HTML template with weather data."""
    # Get weather data
    weather_data = get_weather_data()

    return render_template('weather.html', weather=weather_data)

@app.route('/weather.json')
def weather_json():
    """Return weather data as JSON."""
    weather_data = get_weather_data()
    return jsonify(weather_data)

@app.route('/weather.txt')
def weather_txt():
    """Return weather description as plain text."""
    weather_data = get_weather_data()
    return weather_data['description'], {'Content-Type': 'text/plain'}

def render_to_file(output_file='output.html'):
    """Render the HTML template to a file."""
    with app.app_context():
        rendered_html = home()
        with open(output_file, 'w') as f:
            f.write(rendered_html)
        print(f"Rendered template to {output_file}")

if __name__ == '__main__':
    # Initialize environment and database
    load_dotenv()
    init_llm_log_db()

    if len(sys.argv) > 1 and sys.argv[1] == '--render':
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'output.html'
        render_to_file(output_file)
    else:
        app.run(debug=True, port=5001)
