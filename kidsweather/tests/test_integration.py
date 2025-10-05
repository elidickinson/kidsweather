"""Integration tests for the Kids Weather application."""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch

from ..core.service import WeatherReportService, build_default_service
from ..core.settings import load_settings
from ..formatting.weather import format_for_llm, extract_display_data
from ..utils.file_utils import load_weather_data


class TestWeatherServiceIntegration:
    """Integration tests for the weather service."""

    def test_load_settings(self):
        """Test that settings can be loaded successfully."""
        settings = load_settings()
        assert settings is not None
        assert settings.default_lat == 38.9541848
        assert settings.default_lon == -77.0832061
        assert settings.default_location == "Washington, DC"

    @patch('kidsweather.clients.weather.requests.get')
    @patch('kidsweather.clients.llm.requests.post')
    def test_build_report_with_mock_data(self, mock_llm_post, mock_weather_get):
        """Test building a weather report with mocked API responses."""
        # Mock weather API response
        mock_weather_response = Mock()
        mock_weather_response.json.return_value = self._get_mock_weather_data()
        mock_weather_response.raise_for_status.return_value = None
        mock_weather_get.return_value = mock_weather_response

        # Mock LLM response
        mock_llm_response = Mock()
        mock_llm_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"description": "Sunny and warm day perfect for playing outside!", "daily_forecasts": {"Monday": "Great day for outdoor activities", "Tuesday": "Partly cloudy with mild temperatures"}}'
                }
            }]
        }
        mock_llm_response.raise_for_status.return_value = None
        mock_llm_post.return_value = mock_llm_response

        # Build service and report
        service = build_default_service()
        report = service.build_report(
            latitude=38.9,
            longitude=-77.0,
            log_interaction=False
        )

        # Verify report structure
        assert 'description' in report
        assert 'temperature' in report
        assert 'conditions' in report
        assert 'high_temp' in report
        assert 'low_temp' in report
        assert 'last_updated' in report

    def test_format_for_llm(self):
        """Test weather data formatting for LLM consumption."""
        weather_data = self._get_mock_weather_data()
        formatted = format_for_llm(weather_data)

        assert isinstance(formatted, str)
        assert "Current Date and Time:" in formatted
        assert "TODAY'S FORECAST:" in formatted
        assert "Right Now:" in formatted
        assert "NEXT 8 HOURS:" in formatted

    def test_extract_display_data(self):
        """Test extraction of display data from weather response."""
        weather_data = self._get_mock_weather_data()
        display_data = extract_display_data(weather_data)

        assert 'current' in display_data
        assert 'forecast' in display_data
        assert 'alerts' in display_data
        assert 'daily_forecast_raw' in display_data

        current = display_data['current']
        assert 'temp' in current
        assert 'feels_like' in current
        assert 'conditions' in current

    def test_load_weather_data(self):
        """Test loading weather data from test fixtures."""
        # Try to load existing test data
        test_data_dir = Path(__file__).parent.parent.parent / "test_data"
        if test_data_dir.exists():
            test_files = list(test_data_dir.glob("*.json"))
            if test_files:
                data = load_weather_data(str(test_files[0]))
                assert isinstance(data, dict)
                assert 'current' in data or 'lat' in data

    def _get_mock_weather_data(self):
        """Get mock weather data for testing."""
        return {
            "lat": 38.9,
            "lon": -77.0,
            "timezone": "America/New_York",
            "timezone_offset": -18000,
            "current": {
                "dt": 1634567890,
                "temp": 72.5,
                "feels_like": 74.2,
                "weather": [{"description": "clear sky", "main": "Clear"}],
                "wind_speed": 5.2,
                "uvi": 3.5,
                "sunrise": 1634521200,
                "sunset": 1634563200
            },
            "daily": [
                {
                    "dt": 1634567890,
                    "temp": {"max": 78.0, "min": 65.0},
                    "weather": [{"description": "clear sky", "main": "Clear"}],
                    "pop": 0.1,
                    "wind_speed": 5.2,
                    "summary": "Clear skies throughout the day"
                }
            ],
            "hourly": [
                {
                    "dt": 1634567890,
                    "temp": 72.5,
                    "weather": [{"description": "clear sky"}],
                    "pop": 0.0,
                    "uvi": 3.5
                }
            ]
        }


class TestWeatherClientIntegration:
    """Integration tests for weather client."""

    @patch('kidsweather.clients.weather.requests.get')
    def test_weather_client_caching(self, mock_get):
        """Test that weather client properly handles caching."""
        from ..clients.weather import WeatherClient
        from ..core.settings import WeatherAPISettings
        from ..infrastructure.cache import create_cache
        from pathlib import Path
        import tempfile

        # Create temporary cache directory
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = create_cache(Path(temp_dir))
            
            # Mock weather API response
            mock_response = Mock()
            mock_response.json.return_value = self._get_mock_weather_data()
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # Create client with cache
            settings = WeatherAPISettings(
                api_url="https://api.openweathermap.org/data/3.0/onecall",
                timemachine_url="https://api.openweathermap.org/data/3.0/onecall/timemachine",
                units="imperial",
                cache_ttl_seconds=600,
                api_key="test_key"
            )
            client = WeatherClient(settings, cache=cache)

            # First call should hit API
            result1 = client.fetch_current(38.9, -77.0)
            assert mock_get.call_count == 1

            # Second call should use cache
            result2 = client.fetch_current(38.9, -77.0)
            assert mock_get.call_count == 1  # No additional API calls

            # Results should be identical
            assert result1 == result2

    def _get_mock_weather_data(self):
        """Get mock weather data for testing."""
        return {
            "lat": 38.9,
            "lon": -77.0,
            "timezone": "America/New_York",
            "timezone_offset": -18000,
            "current": {
                "dt": 1634567890,
                "temp": 72.5,
                "feels_like": 74.2,
                "weather": [{"description": "clear sky", "main": "Clear"}],
                "wind_speed": 5.2,
                "uvi": 3.5,
                "sunrise": 1634521200,
                "sunset": 1634563200
            },
            "daily": [
                {
                    "dt": 1634567890,
                    "temp": {"max": 78.0, "min": 65.0},
                    "weather": [{"description": "clear sky", "main": "Clear"}],
                    "pop": 0.1,
                    "wind_speed": 5.2,
                    "summary": "Clear skies throughout the day"
                }
            ],
            "hourly": [
                {
                    "dt": 1634567890,
                    "temp": 72.5,
                    "weather": [{"description": "clear sky"}],
                    "pop": 0.0,
                    "uvi": 3.5
                }
            ]
        }


if __name__ == "__main__":
    pytest.main([__file__])