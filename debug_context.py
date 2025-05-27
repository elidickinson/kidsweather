#!/usr/bin/env python3
"""Debug script to check LLM context generation."""
import json
from pathlib import Path
from weather_processor import format_weather_for_llm

# Load test data
test_file = Path('test_data/dc1.json')
with open(test_file, 'r') as f:
    test_data = json.load(f)

# Generate LLM context
context = format_weather_for_llm(test_data)

# Check for NEXT 8 HOURS section
print("=== CHECKING LLM CONTEXT ===")
print(f"Total context length: {len(context)} characters")
print()

# Find and print the NEXT 8 HOURS section
lines = context.split('\n')
found_next_8 = False
for i, line in enumerate(lines):
    if "NEXT 8 HOURS:" in line:
        found_next_8 = True
        print("Found NEXT 8 HOURS section at line", i+1)
        print("Content:")
        print(line)
        # Print the next 10 lines or until we hit another section
        for j in range(i+1, min(i+11, len(lines))):
            if lines[j].strip() and not lines[j].startswith('  '):
                break
            print(lines[j])
        break

if not found_next_8:
    print("❌ NEXT 8 HOURS section NOT FOUND in context!")
else:
    print("\n✅ NEXT 8 HOURS section is present in the context")

# Also check what's in the hourly data
hourly_data = test_data.get('hourly', [])
print(f"\n📊 Raw data check: Found {len(hourly_data)} hours in API data")