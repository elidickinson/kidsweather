#!/usr/bin/env python3
"""Flask web application for Kids Weather."""
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

from flask import Flask, jsonify, render_template
from dotenv import load_dotenv
import sys

from ..core.settings import load_settings
from ..core.service import build_default_service

app = Flask(__name__)

_service = None


def _get_service():
    global _service
    if _service is None:
        load_settings()
        _service = build_default_service()
    return _service


@app.route('/')
def home():
    service = _get_service()
    weather = service.build_report(
        latitude=None,
        longitude=None,
        log_interaction=True,
        source='flask',
    )
    return render_template('weather.html', weather=weather)


@app.route('/weather.json')
def weather_json():
    service = _get_service()
    weather = service.build_report(
        latitude=None,
        longitude=None,
        log_interaction=True,
        source='flask',
    )
    return jsonify(weather)


@app.route('/weather.txt')
def weather_txt():
    service = _get_service()
    weather = service.build_report(
        latitude=None,
        longitude=None,
        log_interaction=True,
        source='flask',
    )
    return weather['description'], {'Content-Type': 'text/plain'}


def render_to_file(output_file='output.html'):
    service = _get_service()
    with app.app_context():
        weather = service.build_report(
            latitude=None,
            longitude=None,
            log_interaction=False,
            source='render',
        )
        rendered_html = render_template('weather.html', weather=weather)
    with open(output_file, 'w') as fh:
        fh.write(rendered_html)


if __name__ == '__main__':
    load_dotenv()
    if len(sys.argv) > 1 and sys.argv[1] == '--render':
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'output.html'
        render_to_file(output_file)
    else:
        app.run(debug=True, port=5001)
