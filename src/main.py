"""
Star Citizen Profile Editor
Main entry point for the application
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication, QMessageBox
from src.gui.main_window import MainWindow
from src.gui.theme import apply_theme, load_application_fonts
from src.utils.settings import AppSettings
from src.utils.single_instance import SingleInstanceManager


def setup_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Initialize and run the application"""
    # Setup logging first
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Star Citizen Profile Editor")

    # Initialize action registry (loads UNBIND_ALL.xml with 1,085 actions)
    try:
        from src.registry.action_registry import get_action_registry
        registry = get_action_registry()
        logger.info(f"Action Registry loaded: {registry.get_action_count()} actions across {registry.get_actionmap_count()} actionmaps")
    except Exception as e:
        logger.error(f"Failed to initialize action registry: {e}", exc_info=True)
        logger.warning("Continuing without action registry - profile loading may be incomplete")

    app = QApplication(sys.argv)
    app.setApplicationName("Star Citizen Profile Editor")
    app.setOrganizationName("SC Tools")

    # Register branded display font and apply persisted theme. Must happen
    # before any widgets are constructed so they pick up the palette and
    # font on first paint rather than flashing the system default.
    load_application_fonts()
    apply_theme(app, AppSettings().get_theme())

    # Check for single instance
    instance_manager = SingleInstanceManager("SC-Profile-Editor")
    if not instance_manager.start_server():
        # Another instance is already running
        QMessageBox.warning(
            None,
            "Application Already Running",
            "SC Profile Editor is already running.\n\nOnly one instance of the application can run at a time.",
            QMessageBox.StandardButton.Ok
        )
        sys.exit(0)

    window = MainWindow()
    window.show()

    # Connect signal to bring window to focus if another instance tries to start
    instance_manager.another_instance_requested.connect(
        lambda: (window.raise_(), window.activateWindow())
    )

    try:
        sys.exit(app.exec())
    finally:
        # Clean up the instance manager
        instance_manager.cleanup()


if __name__ == "__main__":
    main()
