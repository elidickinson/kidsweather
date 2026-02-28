"""Integration tests for the Kids Weather application."""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch

from ..core.service import WeatherReportService, build_default_service, fetch_cwg_forecast
from ..core.settings import load_settings
from ..formatting.weather import format_for_llm, extract_display_data


MOCK_WEATHER_DATA = {
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
        "sunset": 1634563200,
    },
    "daily": [
        {
            "dt": 1634567890,
            "temp": {"max": 78.0, "min": 65.0},
            "weather": [{"description": "clear sky", "main": "Clear"}],
            "pop": 0.1,
            "wind_speed": 5.2,
            "summary": "Clear skies throughout the day",
        }
    ],
    "hourly": [
        {
            "dt": 1634567890,
            "temp": 72.5,
            "weather": [{"description": "clear sky"}],
            "pop": 0.0,
            "uvi": 3.5,
        }
    ],
}


class TestWeatherServiceIntegration:
    """Integration tests for the weather service."""

    def test_load_settings(self):
        """Test that settings can be loaded successfully."""
        settings = load_settings()
        assert settings is not None
        assert settings.default_lat == 38.9541848
        assert settings.default_lon == -77.0832061
        assert settings.default_location == "Washington, DC"

    @patch('kidsweather.core.service.fetch_cwg_forecast', return_value=None)
    @patch('kidsweather.clients.weather.requests.get')
    @patch('kidsweather.clients.llm.requests.post')
    def test_build_report_with_mock_data(self, mock_llm_post, mock_weather_get, _mock_cwg):
        """Test building a weather report with mocked API responses."""
        mock_weather_response = Mock()
        mock_weather_response.json.return_value = MOCK_WEATHER_DATA
        mock_weather_response.raise_for_status.return_value = None
        mock_weather_get.return_value = mock_weather_response

        mock_llm_response = Mock()
        mock_llm_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"description": "Sunny and warm day perfect for playing outside!"}'
                }
            }]
        }
        mock_llm_response.raise_for_status.return_value = None
        mock_llm_post.return_value = mock_llm_response

        service = build_default_service()
        report = service.build_report(
            latitude=38.9,
            longitude=-77.0,
            log_interaction=False,
        )

        assert 'description' in report
        assert 'temperature' in report
        assert 'conditions' in report
        assert 'high_temp' in report
        assert 'low_temp' in report
        assert 'last_updated' in report

    def test_format_for_llm(self):
        """Test weather data formatting for LLM consumption."""
        formatted = format_for_llm(MOCK_WEATHER_DATA)

        assert isinstance(formatted, str)
        assert "Current Date and Time:" in formatted
        assert "TODAY'S FORECAST:" in formatted
        assert "Right Now:" in formatted
        assert "NEXT 8 HOURS:" in formatted

    def test_format_for_llm_with_cwg(self):
        """Test that CWG forecast is included in LLM context when provided."""
        formatted = format_for_llm(MOCK_WEATHER_DATA, cwg_forecast="Warm with sunny skies")
        assert "LOCAL WEATHER OUTLOOK" in formatted
        assert "Warm with sunny skies" in formatted

    def test_extract_display_data(self):
        """Test extraction of display data from weather response."""
        display_data = extract_display_data(MOCK_WEATHER_DATA)

        assert 'current' in display_data
        assert 'forecast' in display_data
        assert 'alerts' in display_data
        assert 'daily_forecast_raw' not in display_data

        current = display_data['current']
        assert 'temp' in current
        assert 'feels_like' in current
        assert 'conditions' in current


class TestCwgForecast:
    """Tests for the CWG forecast fetcher."""

    @patch('kidsweather.core.service.requests.get')
    def test_fetch_cwg_forecast_with_new_api_fields(self, mock_get):
        """Test that fetch_cwg_forecast uses latest_post_text and latest_post_age_hours."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "main_headline": "Warm and sunny through the weekend",
            "all_posts_html": "<h1>...</h1>",
            "latest_post_text": "Temperatures climbing into the upper 60s this afternoon.",
            "latest_post_updated_at": "2026-02-27T16:40:00-05:00",
            "latest_post_age_hours": 4.2,
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_cwg_forecast()

        assert result is not None
        assert "Warm and sunny through the weekend" in result
        assert "(Posted about 4 hours ago)" in result
        assert "Temperatures climbing into the upper 60s this afternoon." in result
        # Verify max_age_hours query param is sent
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        assert call_kwargs[1]["params"]["max_age_hours"] == 12

    @patch('kidsweather.core.service.requests.get')
    def test_fetch_cwg_forecast_stale_post_returns_none(self, mock_get):
        """Test that a stale post (nulled by server) returns None."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "main_headline": "Warm and sunny",
            "all_posts_html": "<h1>...</h1>",
            "latest_post_text": None,
            "latest_post_updated_at": "2026-02-26T08:00:00-05:00",
            "latest_post_age_hours": None,
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_cwg_forecast()
        assert result is None

    @patch('kidsweather.core.service.requests.get')
    def test_fetch_cwg_forecast_recent_post_age_label(self, mock_get):
        """Test age label for a post less than an hour old."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "main_headline": "Rain expected",
            "latest_post_text": "Showers moving in soon.",
            "latest_post_age_hours": 0.3,
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_cwg_forecast()
        assert result is not None
        assert "(Posted less than an hour ago)" in result

    @patch('kidsweather.core.service.requests.get')
    def test_fetch_cwg_forecast_api_error_returns_none(self, mock_get):
        """Test that API errors are handled gracefully."""
        mock_get.side_effect = Exception("connection refused")

        result = fetch_cwg_forecast()
        assert result is None


class TestWeatherClientIntegration:
    """Integration tests for weather client."""

    @patch('kidsweather.clients.weather.requests.get')
    def test_weather_client_caching(self, mock_get):
        """Test that weather client properly handles caching."""
        from ..clients.weather import WeatherClient
        from ..core.settings import AppSettings
        from pathlib import Path
        import tempfile
        import diskcache

        # Create temporary cache directory
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = diskcache.Cache(Path(temp_dir))

            # Mock weather API response
            mock_response = Mock()
            mock_response.json.return_value = self._get_mock_weather_data()
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # Create minimal settings for testing
            settings = AppSettings(
                root_dir=Path(temp_dir),
                cache_dir=Path(temp_dir) / "cache",
                prompt_dir=Path(temp_dir) / "prompts",
                test_data_dir=Path(temp_dir) / "test_data",
                llm_log_db=Path(temp_dir) / "llm_log.sqlite3",
                weather_api_url="https://api.openweathermap.org/data/3.0/onecall",
                weather_timemachine_url="https://api.openweathermap.org/data/3.0/onecall/timemachine",
                weather_units="imperial",
                weather_cache_ttl_seconds=600,
                weather_api_key="test_key",
                llm_api_url="http://test.com",
                llm_api_key="test",
                llm_model="test",
                llm_supports_json_mode=True,
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

if __name__ == "__main__":
    pytest.main([__file__])