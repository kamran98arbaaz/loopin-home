from flask import Blueprint, current_app, request
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
import json
from datetime import datetime, timezone
from models import Update, ReadLog, User
from extensions import db

bp = Blueprint("socketio", __name__)

def init_socketio(socketio, app):
    """Initialize Socket.IO with the Flask app"""
    
    @socketio.on('connect')
    def handle_connect(auth=None):
        """Handle client connection"""
        try:
            from flask_login import current_user
            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                # Join user-specific room for private notifications
                join_room(f"user_{current_user.id}")
                emit('connected', {
                    'user_id': current_user.id,
                    'username': current_user.username,
                    'message': 'Connected to real-time updates'
                })
            else:
                # Guest users join general room
                join_room('guests')
                emit('connected', {
                    'message': 'Connected as guest'
                })
        except Exception:
            # Fallback for test environments or when Flask-Login is not available
            join_room('guests')
            emit('connected', {
                'message': 'Connected as guest'
            })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        if current_user.is_authenticated:
            leave_room(f"user_{current_user.id}")
        leave_room('guests')
    
    @socketio.on('join_process_room')
    def handle_join_process(data):
        """Join a specific process room for updates"""
        process = data.get('process')
        if process:
            room_name = f"process_{process}"
            join_room(room_name)
            emit('joined_room', {
                'room': room_name,
                'message': f'Joined {process} updates room'
            })
    
    @socketio.on('leave_process_room')
    def handle_leave_process(data):
        """Leave a specific process room"""
        process = data.get('process')
        if process:
            room_name = f"process_{process}"
            leave_room(room_name)
            emit('left_room', {
                'room': room_name,
                'message': f'Left {process} updates room'
            })
    
    @socketio.on('mark_as_read')
    def handle_mark_read(data):
        """Mark an update as read for the current user"""
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
        
        update_id = data.get('update_id')
        if not update_id:
            emit('error', {'message': 'Update ID required'})
            return
        
        try:
            # Check if already marked as read
            existing_log = ReadLog.query.filter_by(
                update_id=update_id,
                user_id=current_user.id
            ).first()
            
            if not existing_log:
                # Get client IP address
                client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'Unknown'))
                if ',' in client_ip:
                    client_ip = client_ip.split(',')[0].strip()  # Get first IP if multiple

                # Get user agent
                user_agent = request.headers.get('User-Agent', 'Unknown')

                # Create new read log
                read_log = ReadLog(
                    update_id=update_id,
                    user_id=current_user.id,
                    timestamp=datetime.now(timezone.utc),
                    ip_address=client_ip,
                    user_agent=user_agent
                )
                db.session.add(read_log)
                db.session.commit()
                
                # Emit to all users that this update was read
                emit('update_read', {
                    'update_id': update_id,
                    'user_id': current_user.id,
                    'username': current_user.username,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, broadcast=True)
                
                emit('success', {'message': 'Update marked as read'})
            else:
                emit('info', {'message': 'Update already marked as read'})
                
        except Exception as e:
            emit('error', {'message': f'Error marking as read: {str(e)}'})
    
    @socketio.on('get_unread_count')
    def handle_get_unread_count():
        """Get unread count for current user"""
        if not current_user.is_authenticated:
            emit('unread_count', {'count': 0})
            return
        
        try:
            # Count updates that haven't been read by this user
            unread_count = db.session.query(Update).outerjoin(
                ReadLog, 
                (Update.id == ReadLog.update_id) & (ReadLog.user_id == current_user.id)
            ).filter(ReadLog.id.is_(None)).count()
            
            emit('unread_count', {'count': unread_count})
        except Exception as e:
            emit('error', {'message': f'Error getting unread count: {str(e)}'})
    
    @socketio.on('subscribe_to_updates')
    def handle_subscribe_updates(data=None):
        """Subscribe to real-time updates"""
        # Handle case where no data is sent
        if data is None:
            data = {}
            
        process_filter = data.get('process')
        
        if process_filter:
            # Join process-specific room
            room_name = f"process_{process_filter}"
            join_room(room_name)
            emit('subscribed', {
                'room': room_name,
                'message': f'Subscribed to {process_filter} updates'
            })
        else:
            # Join general updates room
            join_room('updates')
            emit('subscribed', {
                'room': 'updates',
                'message': 'Subscribed to all updates'
            })

def broadcast_update(update_data, process=None):
    """Broadcast an update to all connected clients"""
    from flask_socketio import emit
    
    # Emit to general updates room
    emit('new_update', update_data, room='updates', namespace='/')
    
    # Emit to process-specific room if specified
    if process:
        emit('new_update', update_data, room=f'process_{process}', namespace='/')
    
    # Emit to all authenticated users for notifications
    emit('notification', {
        'type': 'new_update',
        'title': 'New Update',
        'message': f'New update from {update_data.get("name", "Unknown")}',
        'update_id': update_data.get('id'),
        'timestamp': datetime.now(timezone.utc).isoformat()
    }, room='authenticated_users', namespace='/')

def broadcast_notification(notification_data, user_id=None):
    """Broadcast a notification to specific user or all users"""
    from flask_socketio import emit
    
    if user_id:
        # Send to specific user
        emit('notification', notification_data, room=f'user_{user_id}', namespace='/')
    else:
        # Send to all authenticated users
        emit('notification', notification_data, room='authenticated_users', namespace='/')
