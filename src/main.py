"""
Star Citizen Profile Editor
Main entry point for the application
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow


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

    app = QApplication(sys.argv)
    app.setApplicationName("Star Citizen Profile Editor")
    app.setOrganizationName("SC Tools")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
