"""
Single instance checker for SC Profile Editor

Prevents multiple instances of the application from running simultaneously.
Uses Qt's QLocalServer for cross-platform support.
"""

import logging
from PyQt6.QtCore import QByteArray, pyqtSignal, QObject
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

logger = logging.getLogger(__name__)


class SingleInstanceManager(QObject):
    """
    Manages single instance enforcement for the application.

    Signals:
        another_instance_requested: Emitted when another instance tries to start
    """

    another_instance_requested = pyqtSignal()

    def __init__(self, app_name: str = "SC-Profile-Editor"):
        """
        Initialize the single instance manager

        Args:
            app_name: Unique identifier for the application
        """
        super().__init__()
        self.app_name = app_name
        self.server = None
        self.is_running = False

    def start_server(self) -> bool:
        """
        Start the local server for this instance.

        Returns:
            True if this is the first (primary) instance
            False if another instance is already running
        """
        # Try to connect to existing server
        socket = QLocalSocket()
        socket.connectToServer(self.app_name)

        if socket.waitForConnected(500):
            # Another instance is already running
            logger.info("Another instance of the application is already running")
            socket.disconnectFromServer()
            socket.deleteLater()
            return False

        # No existing server, create one
        self.server = QLocalServer()
        self.server.newConnection.connect(self._handle_connection)

        # Remove old socket file if it exists
        QLocalServer.removeServer(self.app_name)

        if not self.server.listen(self.app_name):
            logger.error(f"Failed to start local server: {self.server.serverError()}")
            return False

        self.is_running = True
        logger.info("Started as primary instance")
        return True

    def _handle_connection(self):
        """Handle connection from another instance trying to start"""
        connection = self.server.nextPendingConnection()
        if connection:
            # Another instance tried to start - emit signal to bring window to front
            self.another_instance_requested.emit()
            connection.disconnectFromServer()
            connection.deleteLater()
            logger.info("Received connection from another instance - bringing window to front")

    def cleanup(self):
        """Clean up the server on shutdown"""
        if self.server:
            self.server.close()
            QLocalServer.removeServer(self.app_name)
            self.server.deleteLater()
            self.server = None
