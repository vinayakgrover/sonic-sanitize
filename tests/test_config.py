"""Test configuration loading."""

import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.deid.config_loader import ConfigLoader


def test_config_file_exists():
    """Test that config.yaml exists."""
    config_path = Path("config.yaml")
    assert config_path.exists(), "config.yaml not found"


def test_config_loads():
    """Test that config loads without errors."""
    loader = ConfigLoader()
    assert loader.config is not None
    assert loader.pii_categories is not None


def test_all_categories_load():
    """Test that all expected PII categories load correctly."""
    loader = ConfigLoader()

    expected_categories = ['days', 'months', 'colors', 'cities', 'states']

    for category in expected_categories:
        items = loader.get_category_items(category)
        tag = loader.get_category_tag(category)

        # Check items loaded
        assert len(items) > 0, f"{category} has no items"
        assert isinstance(items, list), f"{category} items is not a list"

        # Check tag format
        assert tag.startswith('['), f"{category} tag doesn't start with ["
        assert tag.endswith(']'), f"{category} tag doesn't end with ]"
        # Check tag is related to category (lenient - just check first few chars)
        assert category.upper()[:3] in tag, f"{category} tag doesn't match category name"


def test_days_category():
    """Test days category specifically."""
    loader = ConfigLoader()
    days = loader.get_category_items('days')
    tag = loader.get_category_tag('days')

    assert len(days) == 7, f"Expected 7 days, got {len(days)}"
    assert 'Monday' in days
    assert 'Friday' in days
    assert tag == '[DAY]'


def test_cities_category():
    """Test cities category."""
    loader = ConfigLoader()
    cities = loader.get_category_items('cities')
    tag = loader.get_category_tag('cities')

    assert len(cities) > 10, "Expected at least 10 cities"
    assert 'Dallas' in cities
    assert 'Houston' in cities
    assert 'New York' in cities  # Multi-word city
    assert tag == '[CITY]'


def test_states_category():
    """Test states category."""
    loader = ConfigLoader()
    states = loader.get_category_items('states')
    tag = loader.get_category_tag('states')

    assert len(states) > 10, "Expected at least 10 states"
    assert 'Texas' in states
    assert 'California' in states
    assert 'New York' in states  # Multi-word state
    assert tag == '[STATE]'


def test_months_category():
    """Test months category."""
    loader = ConfigLoader()
    months = loader.get_category_items('months')
    tag = loader.get_category_tag('months')

    assert len(months) == 12, f"Expected 12 months, got {len(months)}"
    assert 'January' in months
    assert 'December' in months
    assert tag == '[MONTH]'


def test_colors_category():
    """Test colors category."""
    loader = ConfigLoader()
    colors = loader.get_category_items('colors')
    tag = loader.get_category_tag('colors')

    assert len(colors) > 5, "Expected at least 5 colors"
    assert 'red' in colors
    assert 'blue' in colors
    assert tag == '[COLOR]'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
