"""Load PII configuration from YAML file."""

import yaml
from pathlib import Path
from typing import Dict, List
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ConfigLoader:
    """Loads and manages PII configuration."""

    def __init__(self, config_path: Path = Path("config.yaml")):
        """
        Initialize config loader.

        Args:
            config_path: Path to config.yaml file
        """
        self.config_path = Path(config_path)
        self.config = None
        self.pii_categories = {}
        self._load_config()

    def _load_config(self):
        """Load configuration from YAML file."""
        logger.info(f"Loading config from {self.config_path}")

        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Extract PII categories
        self.pii_categories = self.config.get('pii_categories', {})
        logger.info(f"Loaded {len(self.pii_categories)} PII categories")

    def get_category(self, category_name: str) -> Dict:
        """
        Get a specific PII category configuration.

        Args:
            category_name: Name of category (e.g., 'days', 'cities')

        Returns:
            Dictionary with category config (items, tag, case_sensitive)
        """
        return self.pii_categories.get(category_name, {})

    def get_all_categories(self) -> Dict[str, Dict]:
        """
        Get all PII categories.

        Returns:
            Dictionary of all PII categories
        """
        return self.pii_categories

    def get_category_items(self, category_name: str) -> List[str]:
        """
        Get list of items for a category.

        Args:
            category_name: Name of category

        Returns:
            List of PII items in that category
        """
        category = self.get_category(category_name)
        return category.get('items', []) if isinstance(category, dict) else category

    def get_category_tag(self, category_name: str) -> str:
        """
        Get replacement tag for a category.

        Args:
            category_name: Name of category

        Returns:
            Replacement tag (e.g., '[CITY]')
        """
        category = self.get_category(category_name)
        if isinstance(category, dict):
            return category.get('tag', f'[{category_name.upper()}]')
        # If category is just a list, derive tag from name
        return f'[{category_name.upper().rstrip("S")}]'  # cities -> [CITY]


def main():
    """Test the config loader."""
    from ..utils.logger import setup_logger

    # Setup logging
    setup_logger(__name__, level=20)  # INFO level

    # Load config
    loader = ConfigLoader()

    # Display categories
    print("\n=== PII Categories ===")
    for category_name, category_data in loader.get_all_categories().items():
        items = loader.get_category_items(category_name)
        tag = loader.get_category_tag(category_name)
        print(f"\n{category_name.upper()}: {tag}")
        print(f"  Items: {len(items)}")
        if items:
            print(f"  Sample: {', '.join(items[:5])}")


if __name__ == "__main__":
    main()
