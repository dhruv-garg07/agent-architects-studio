"""
GitMem WebSocket Events - Flask-SocketIO handlers for real-time updates.

This module sets up WebSocket namespaces and handlers for the GitMem
real-time dashboard. Clients connect here to receive live updates.
"""

from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request
from ..core.event_bus import event_bus, EventType
from datetime import datetime


import time
from collections import defaultdict

_last_stats_request = defaultdict(float)

def init_websocket(socketio: SocketIO):
    """
    Initialize WebSocket event handlers for GitMem.
    Call this from your main Flask app after creating SocketIO instance.
    """
    
    # Connect event bus to SocketIO for broadcasting
    event_bus.set_socketio(socketio)
    
    @socketio.on('connect', namespace='/gitmem')
    def handle_connect():
        """Handle new WebSocket connection."""
        client_id = request.sid
        print(f"[GitMem WS] Client connected: {client_id}")
        
        # Send initial state to new client
        emit('connection_established', {
            'status': 'connected',
            'client_id': client_id,
            'timestamp': datetime.now().isoformat()
        })
        
        # Join the global room for broadcasts
        join_room('gitmem_global')
    
    @socketio.on('disconnect', namespace='/gitmem')
    def handle_disconnect():
        """Handle WebSocket disconnection."""
        client_id = request.sid
        print(f"[GitMem WS] Client disconnected: {client_id}")
        leave_room('gitmem_global')
        if client_id in _last_stats_request:
            del _last_stats_request[client_id]
    
    @socketio.on('subscribe_agent', namespace='/gitmem')
    def handle_subscribe_agent(data):
        """Subscribe to events for a specific agent."""
        agent_id = data.get('agent_id')
        if agent_id:
            room_name = f"agent:{agent_id}"
            join_room(room_name)
            emit('subscribed', {
                'type': 'agent',
                'agent_id': agent_id,
                'message': f'Subscribed to events for agent {agent_id}'
            })
    
    @socketio.on('unsubscribe_agent', namespace='/gitmem')
    def handle_unsubscribe_agent(data):
        """Unsubscribe from agent-specific events."""
        agent_id = data.get('agent_id')
        if agent_id:
            room_name = f"agent:{agent_id}"
            leave_room(room_name)
            emit('unsubscribed', {
                'type': 'agent',
                'agent_id': agent_id
            })
    
    @socketio.on('request_stats', namespace='/gitmem')
    def handle_request_stats():
        """Client requests current stats (for initial load or refresh)."""
        client_id = request.sid
        current_time = time.time()
        
        # Rate limit: max 1 request every 5 seconds per client
        if current_time - _last_stats_request[client_id] < 5.0:
            return
            
        _last_stats_request[client_id] = current_time

        # Import here to avoid circular imports
        from .routes import store, vector_engine, agent_manager
        
        stats = {
            'agent_count': agent_manager.get_agent_count(),
            'total_memories': store.count_memories(),
            'index_stats': vector_engine.get_stats(),
            'commits_count': len(store.get_commits()),
            'timestamp': datetime.now().isoformat()
        }
        emit('stats_update', stats)
    
    @socketio.on('request_activity_feed', namespace='/gitmem')
    def handle_request_activity_feed(data=None):
        """Client requests activity feed."""
        from .routes import store
        
        limit = 10
        if data and 'limit' in data:
            limit = min(data['limit'], 50)  # Cap at 50
        
        feed = store.get_activity_feed(limit=limit)
        
        # Serialize timestamps
        for item in feed:
            if 'timestamp' in item and hasattr(item['timestamp'], 'isoformat'):
                item['timestamp'] = item['timestamp'].isoformat()
        
        emit('activity_feed', {'items': feed})
    
    @socketio.on('request_recent_events', namespace='/gitmem')
    def handle_request_recent_events(data=None):
        """Client requests recent events from the event bus."""
        limit = 20
        if data and 'limit' in data:
            limit = min(data['limit'], 100)
        
        events = event_bus.get_recent_events(limit=limit)
        emit('recent_events', {
            'events': [e.to_dict() for e in events]
        })
    
    @socketio.on('ping', namespace='/gitmem')
    def handle_ping():
        """Simple ping/pong for connection health check."""
        emit('pong', {'timestamp': datetime.now().isoformat()})
    
    print("[GitMem WS] WebSocket handlers initialized")
    return socketio


def broadcast_to_agent_subscribers(agent_id: str, event_type: str, data: dict):
    """
    Broadcast an event to all clients subscribed to a specific agent.
    Call this from anywhere in the application.
    """
    if event_bus._socketio:
        room_name = f"agent:{agent_id}"
        event_bus._socketio.emit(
            event_type,
            data,
            room=room_name,
            namespace='/gitmem'
        )


def broadcast_stats_update(stats: dict):
    """Broadcast stats update to all connected clients."""
    if event_bus._socketio:
        event_bus._socketio.emit(
            'stats_update',
            stats,
            room='gitmem_global',
            namespace='/gitmem'
        )
