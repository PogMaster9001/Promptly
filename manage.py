"""Convenience entry-point for running the application with Socket.IO."""
from app import create_app
from app.extensions import socketio

app = create_app()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5050)
