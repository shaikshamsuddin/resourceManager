"""
Server Configuration API Module
Handles server configuration endpoints.
"""

from flask import Blueprint, request, jsonify

# Create blueprint
server_config_bp = Blueprint('server_config', __name__, url_prefix='/api/server-config')

@server_config_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for server configuration API."""
    return jsonify({
        "status": "healthy",
        "service": "server-configuration-api",
        "message": "Server configuration API is running"
    })

@server_config_bp.route('/config', methods=['GET'])
def get_config():
    """Get server configuration."""
    return jsonify({
        "message": "Server configuration endpoint",
        "status": "available"
    })

@server_config_bp.route('/reconnect', methods=['POST'])
def reconnect_servers():
    """Reconnect servers by reloading server manager config."""
    try:
        from core.server_manager import server_manager
        server_manager.reload_config()
        return jsonify({
            "status": "success",
            "message": "Servers reconnected successfully."
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to reconnect servers: {str(e)}"
        }), 500 