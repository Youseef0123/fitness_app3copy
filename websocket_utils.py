"""
WebSocket utilities for AI Fitness Trainer
"""
import time
import threading
import cv2
import numpy as np
import base64
import os
from flask_socketio import emit

# Constants for session management
SESSION_TIMEOUT = 60  # Seconds of inactivity before a session is closed
MAX_SESSIONS_PER_IP = 3  # Maximum concurrent sessions per IP address
FRAME_RATE_LIMIT = 15  # Maximum frames per second to send

# Dictionary to track IP addresses and their session counts
ip_session_counts = {}
ip_session_locks = {}

# Lock for thread-safe session management
session_lock = threading.RLock()

class SessionManager:
    """
    Manages WebSocket sessions and resources
    """
    @staticmethod
    def init_session(session_id, exercise_id, request_ip):
        """
        Initialize a new session
        
        Args:
            session_id: WebSocket session ID
            exercise_id: ID of the exercise to track
            request_ip: IP address of the request
            
        Returns:
            bool: True if session was initialized, False if rejected
        """
        from app import active_sessions
        
        with session_lock:
            # Check if this IP has too many sessions
            if request_ip not in ip_session_counts:
                ip_session_counts[request_ip] = 1
                ip_session_locks[request_ip] = threading.RLock()
            else:
                with ip_session_locks[request_ip]:
                    if ip_session_counts[request_ip] >= MAX_SESSIONS_PER_IP:
                        print(f"Too many sessions for IP {request_ip}, rejecting new session")
                        return False
                    ip_session_counts[request_ip] += 1
            
            # Initialize session data
            active_sessions[session_id] = {
                'exercise_id': exercise_id,
                'stop_event': threading.Event(),
                'cap': None,
                'left_counter': 0,
                'right_counter': 0,
                'start_time': time.time(),
                'last_active': time.time(),
                'request_ip': request_ip,
                'frame_count': 0,
                'fps': 0,
                'frame_rate_limiter': FrameRateLimiter(FRAME_RATE_LIMIT)
            }
            
            return True
    
    @staticmethod
    def cleanup_session(session_id):
        """
        Clean up resources for a session
        
        Args:
            session_id: WebSocket session ID
        """
        from app import active_sessions
        
        with session_lock:
            if session_id in active_sessions:
                session_data = active_sessions[session_id]
                
                # Stop processing thread
                if 'stop_event' in session_data:
                    session_data['stop_event'].set()
                
                # Release camera
                if 'cap' in session_data and session_data['cap'] is not None:
                    try:
                        session_data['cap'].release()
                    except Exception as e:
                        print(f"Error releasing camera for session {session_id}: {str(e)}")
                
                # Decrement IP session count
                request_ip = session_data.get('request_ip')
                if request_ip and request_ip in ip_session_counts:
                    with ip_session_locks[request_ip]:
                        ip_session_counts[request_ip] = max(0, ip_session_counts[request_ip] - 1)
                
                # Remove session data
                del active_sessions[session_id]
    
    @staticmethod
    def update_activity(session_id):
        """
        Update the last activity timestamp for a session
        
        Args:
            session_id: WebSocket session ID
        """
        from app import active_sessions
        
        if session_id in active_sessions:
            active_sessions[session_id]['last_active'] = time.time()
    
    @staticmethod
    def is_session_expired(session_id):
        """
        Check if a session has expired due to inactivity
        
        Args:
            session_id: WebSocket session ID
            
        Returns:
            bool: True if session has expired, False otherwise
        """
        from app import active_sessions
        
        if session_id in active_sessions:
            session_data = active_sessions[session_id]
            current_time = time.time()
            return current_time - session_data.get('last_active', 0) > SESSION_TIMEOUT
        
        return True  # Session not found, consider expired
    
    @staticmethod
    def cleanup_all_expired_sessions():
        """
        Clean up all expired sessions
        """
        from app import active_sessions
        
        with session_lock:
            expired_sessions = []
            
            # Find expired sessions
            for session_id, session_data in active_sessions.items():
                current_time = time.time()
                if current_time - session_data.get('last_active', 0) > SESSION_TIMEOUT:
                    expired_sessions.append(session_id)
            
            # Clean up expired sessions
            for session_id in expired_sessions:
                print(f"Cleaning up expired session: {session_id}")
                SessionManager.cleanup_session(session_id)


class FrameRateLimiter:
    """
    Controls frame rate for WebSocket transmission
    """
    def __init__(self, max_fps=15):
        self.max_fps = max_fps
        self.last_frame_time = 0
        self.min_interval = 1.0 / max_fps
    
    def can_send_frame(self):
        """
        Check if enough time has passed to send the next frame
        
        Returns:
            bool: True if a frame can be sent, False otherwise
        """
        current_time = time.time()
        elapsed = current_time - self.last_frame_time
        
        if elapsed >= self.min_interval:
            self.last_frame_time = current_time
            return True
        
        return False


class ImageProcessor:
    """
    Handles image processing tasks for WebSocket video
    """
    @staticmethod
    def compress_frame(frame, quality=70):
        """
        Compress a video frame for efficient WebSocket transmission
        
        Args:
            frame: OpenCV frame
            quality: JPEG compression quality (0-100)
            
        Returns:
            str: Base64 encoded JPEG image
        """
        try:
            # Encode parameters for JPEG compression
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            
            # Encode image to JPEG format
            ret, buffer = cv2.imencode('.jpg', frame, encode_param)
            
            if not ret:
                raise Exception("Failed to encode frame")
            
            # Convert to base64 string
            frame_data = base64.b64encode(buffer).decode('utf-8')
            
            return frame_data
        except Exception as e:
            print(f"Error compressing frame: {str(e)}")
            return None
    
    @staticmethod
    def create_mock_frame(exercise_id, left_counter=0, right_counter=0, frame_count=0):
        """
        Create a mock frame when camera is not available
        
        Args:
            exercise_id: Type of exercise
            left_counter: Current left counter value
            right_counter: Current right counter value
            frame_count: Current frame count for animation
            
        Returns:
            ndarray: OpenCV image
        """
        # Create a black frame
        frame = np.zeros((480, 640, 3), np.uint8)
        
        # Add exercise name and instructions
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, f"Exercise: {exercise_id}", (50, 50), font, 1, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, "Simulation Mode", (50, 100), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Add exercise-specific instructions
        y_pos = 150
        instructions = get_exercise_instructions(exercise_id)
        for i, line in enumerate(instructions):
            cv2.putText(frame, line, (50, y_pos), font, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
            y_pos += 30
        
        # Display counters
        cv2.putText(frame, f'Left: {left_counter}', (10, 250), 
                   font, 1, (255, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, f'Right: {right_counter}', (10, 300), 
                   font, 1, (255, 0, 0), 2, cv2.LINE_AA)
        
        # Add animated progress bar
        completion = (frame_count % 100) / 100.0  # Cycle every 100 frames
        bar_width = int(540 * completion)
        cv2.rectangle(frame, (50, 350), (50 + bar_width, 380), (0, 255, 0), -1)
        cv2.rectangle(frame, (50, 350), (590, 380), (255, 255, 255), 2)
        
        # Add server timestamp
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        cv2.putText(frame, f"Server time: {timestamp}", (50, 420), font, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
        
        return frame


def get_exercise_instructions(exercise_id):
    """Get instructions for a specific exercise"""
    instructions = {
        "hummer": [
            "Stand with weights at your sides",
            "Curl the weights up to your shoulders",
            "Lower back down with control",
            "Keep elbows close to your body"
        ],
        "squat": [
            "Stand with feet shoulder-width apart",
            "Lower your body as if sitting in a chair",
            "Keep back straight and knees over toes",
            "Return to standing position"
        ],
        "front_raise": [
            "Stand with weights at your sides",
            "Raise arms forward to shoulder height",
            "Hold briefly at the top",
            "Lower with control"
        ],
        "push_ups": [
            "Start in plank position, arms extended",
            "Lower body until chest nearly touches floor",
            "Push back up to starting position",
            "Keep body in straight line throughout"
        ]
    }
    
    # Return specific instructions or default ones
    return instructions.get(exercise_id, ["See documentation for proper form"])


def send_frame_to_client(session_id, frame, left_counter=0, right_counter=0, feedback="", fps=0):
    """
    Send a video frame to a WebSocket client
    
    Args:
        session_id: WebSocket session ID
        frame: OpenCV frame
        left_counter: Current left counter value
        right_counter: Current right counter value
        feedback: Form feedback message
        fps: Current frames per second
    """
    from app import active_sessions, socketio
    
    try:
        # Check if session exists
        if session_id not in active_sessions:
            return False
        
        # Check if we should send a frame (rate limiting)
        session_data = active_sessions[session_id]
        if not session_data['frame_rate_limiter'].can_send_frame():
            return False
        
        # Compress the frame
        frame_data = ImageProcessor.compress_frame(frame)
        
        if not frame_data:
            return False
        
        # Update session last activity time
        session_data['last_active'] = time.time()
        
        # Send the frame and data
        socketio.emit('exercise_frame', {
            'frame': frame_data,
            'left_counter': left_counter,
            'right_counter': right_counter,
            'feedback': feedback,
            'fps': fps
        }, room=session_id)
        
        return True
    except Exception as e:
        print(f"Error sending frame to client {session_id}: {str(e)}")
        return False