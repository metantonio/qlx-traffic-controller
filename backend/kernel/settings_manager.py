import os
import json
import logging
from typing import Any, Dict, Optional
from backend.core.config import settings

logger = logging.getLogger("QLX-TC.Kernel.Settings")

class SettingsManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self._ensure_config_exists()
        self.cached_settings: Dict[str, Any] = self._load()

    def _ensure_config_exists(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        if not os.path.exists(self.config_path):
            # Seed with current runtime settings if file doesn't exist
            initial = {
                "VISION_MODEL": settings.VISION_MODEL,
                # Add other configurable settings here later
            }
            with open(self.config_path, 'w') as f:
                json.dump(initial, f, indent=4)

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load settings from {self.config_path}: {e}")
            return {}

    def get(self, key: str, default: Any = None) -> Any:
        """Gets a setting from the persistent JSON store, falling back to core config or provided default."""
        val = self.cached_settings.get(key)
        if val is not None:
            return val
        
        # Fallback to backend.core.config.settings (runtime/env)
        return getattr(settings, key, default)

    def update(self, key: str, value: Any):
        """Updates a setting and persists it to JSON."""
        self.cached_settings[key] = value
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.cached_settings, f, indent=4)
            logger.info(f"Setting '{key}' updated and persisted to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save setting '{key}': {e}")

    def get_all(self) -> Dict[str, Any]:
        """Returns all persisted settings merged with their current runtime values if not persisted."""
        # For now, we only care about a few specific ones we want to expose to the UI
        exposed_keys = ["VISION_MODEL"]
        return {k: self.get(k) for k in exposed_keys}

# Singleton instance
settings_manager = SettingsManager(os.path.join(os.path.dirname(__file__), "..", "data", "settings_ui.json"))
