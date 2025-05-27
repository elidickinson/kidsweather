#!/usr/bin/env python3
"""
Integration tests for weather processor LLM context generation.
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add the project directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from weather_processor import format_weather_for_llm


def load_test_data(filename):
    """Load test data from test_data directory."""
    test_file = Path(__file__).parent / 'test_data' / filename
    with open(test_file, 'r') as f:
        return json.load(f)


def test_llm_context_contains_all_required_sections():
    """Test that the LLM context contains all required sections."""
    # Load test data
    test_data = load_test_data('dc1.json')
    
    # Generate LLM context
    context = format_weather_for_llm(test_data)
    
    # Define required sections
    required_sections = [
        "Current Date and Time:",
        "Weather Forecast for location",
        "TODAY'S FORECAST:",
        "Right Now:",
        "Current Precipitation:",
        "Current Wind:",
        "Current UV Index:",
        "Sunrise:",
        "Overall for Today",
        "NEXT 8 HOURS:",
        "NEXT FEW DAYS"
    ]
    
    # Check each required section
    missing_sections = []
    for section in required_sections:
        if section not in context:
            missing_sections.append(section)
    
    # Report results
    if missing_sections:
        print(f"❌ FAILED: Missing sections in LLM context:")
        for section in missing_sections:
            print(f"   - {section}")
        return False
    else:
        print("✅ PASSED: All required sections present in LLM context")
        return True


def test_next_8_hours_has_data():
    """Test that NEXT 8 HOURS section contains actual hourly data."""
    # Load test data
    test_data = load_test_data('dc1.json')
    
    # Generate LLM context
    context = format_weather_for_llm(test_data)
    
    # Find the NEXT 8 HOURS section
    lines = context.split('\n')
    next_8_hours_index = None
    for i, line in enumerate(lines):
        if "NEXT 8 HOURS:" in line:
            next_8_hours_index = i
            break
    
    if next_8_hours_index is None:
        print("❌ FAILED: NEXT 8 HOURS section not found")
        return False
    
    # Check for hourly data (should have at least some lines with time format)
    hourly_count = 0
    for i in range(next_8_hours_index + 1, min(next_8_hours_index + 10, len(lines))):
        if ':' in lines[i] and ('AM' in lines[i] or 'PM' in lines[i]):
            hourly_count += 1
    
    if hourly_count == 0:
        print("❌ FAILED: NEXT 8 HOURS section has no hourly data")
        return False
    else:
        print(f"✅ PASSED: NEXT 8 HOURS section contains {hourly_count} hours of data")
        return True


def test_yesterday_weather_included():
    """Test that yesterday's weather is included when provided."""
    # Load test data
    test_data = load_test_data('dc1.json')
    
    # Mock yesterday data
    yesterday_data = {
        'date': 'Monday, January 26',
        'avg_temp': 45,
        'avg_feels_like': 42,
        'high_temp': 52,
        'low_temp': 38,
        'main_condition': 'Partly cloudy',
        'conditions_breakdown': {
            'Clear': 6,
            'Partly cloudy': 12,
            'Cloudy': 6
        }
    }
    
    # Generate LLM context with yesterday data
    context = format_weather_for_llm(test_data, yesterday_data)
    
    # Check for yesterday's weather section
    if "YESTERDAY'S WEATHER" in context:
        print("✅ PASSED: Yesterday's weather section included when data provided")
        return True
    else:
        print("❌ FAILED: Yesterday's weather section missing")
        return False


def test_alerts_section():
    """Test that alerts are properly formatted when present."""
    # Load test data with alerts
    test_data = load_test_data('dcalert.json')
    
    # Generate LLM context
    context = format_weather_for_llm(test_data)
    
    # Check for alerts section
    if "ACTIVE WEATHER ALERTS:" in context:
        print("✅ PASSED: Alerts section present when alerts exist")
        return True
    else:
        print("❌ FAILED: Alerts section missing despite alerts in data")
        return False


def test_daily_forecast_days():
    """Test that daily forecast includes correct day names."""
    # Load test data
    test_data = load_test_data('dc1.json')
    
    # Generate LLM context
    context = format_weather_for_llm(test_data)
    
    # Check for day names in NEXT FEW DAYS section
    days_found = 0
    for day_name in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
        if day_name in context:
            days_found += 1
    
    if days_found >= 4:  # Should have at least 4 days in forecast
        print(f"✅ PASSED: Found {days_found} day names in daily forecast")
        return True
    else:
        print(f"❌ FAILED: Only found {days_found} day names in daily forecast (expected at least 4)")
        return False


def main():
    """Run all integration tests."""
    print("Running Weather Processor Integration Tests")
    print("=" * 50)
    
    tests = [
        test_llm_context_contains_all_required_sections,
        test_next_8_hours_has_data,
        test_yesterday_weather_included,
        test_alerts_section,
        test_daily_forecast_days
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"\nRunning {test.__name__}...")
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ ERROR: {test.__name__} raised exception: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Tests completed: {passed} passed, {failed} failed")
    
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()