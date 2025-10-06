"""HTML rendering for weather reports using Jinja2."""
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape


def render_weather_html(weather_data: Dict[str, Any], template_name: str = "weather.html") -> str:
    """Render weather data to HTML using Jinja2 templates.

    Args:
        weather_data: Weather report dictionary from WeatherReportService
        template_name: Name of the template file to use

    Returns:
        Rendered HTML string
    """
    # Determine template directory - it's in kidsweather/templates/
    template_dir = Path(__file__).parent.parent / "templates"

    # Create Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )

    # Load and render template
    template = env.get_template(template_name)
    return template.render(weather=weather_data)


def render_to_file(weather_data: Dict[str, Any], output_file: str, template_name: str = "weather.html") -> None:
    """Render weather data to an HTML file.

    Args:
        weather_data: Weather report dictionary from WeatherReportService
        output_file: Path to output HTML file
        template_name: Name of the template file to use
    """
    html_content = render_weather_html(weather_data, template_name)
    with open(output_file, 'w') as fh:
        fh.write(html_content)
