from flask import Flask, Response, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import cv2
import os
import json
import pygame
import time
import base64
import traceback
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import threading
from flask_cors import CORS
import eventlet

# Patch for better WebSocket performance with eventlet
eventlet.monkey_patch()

# Import exercise modules
from utils import calculate_angle, mp_pose, pose, mp_drawing
from exercises.bicep_curl import hummer
from exercises.front_raise import dumbbell_front_raise
from exercises.squat import squat
from exercises.triceps_extension import triceps_extension
from exercises.lunges import lunges
from exercises.shoulder_press import shoulder_press
from exercises.plank import plank
from exercises.lateral_raise import side_lateral_raise
from exercises.triceps_kickback import triceps_kickback_side
from exercises.push_ups import push_ups

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for all routes
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', ping_timeout=60, ping_interval=25)

# Setup for async processing - limiting max workers to prevent resource exhaustion
executor = ThreadPoolExecutor(max_workers=4)

# Dummy sound class to avoid file path issues
class DummySound:
    def __init__(self):
        self.is_playing = False
    
    def play(self):
        self.is_playing = True
        print("Dummy sound play")
    
    def stop(self):
        self.is_playing = False
        print("Dummy sound stop")

# Use dummy sound instead of loading from a specific path
sound = DummySound()

# Ensure audio directory exists
os.makedirs("audio", exist_ok=True)

# Dictionary to store active sessions
active_sessions = {}

# Dictionary to store exercise functions
exercise_map = {
    'hummer': hummer,
    'front_raise': dumbbell_front_raise,
    'squat': squat,
    'triceps': triceps_extension,
    'lunges': lunges,
    'shoulder_press': shoulder_press,
    'plank': plank,
    'side_lateral_raise': side_lateral_raise,
    'triceps_kickback_side': triceps_kickback_side,
    'push_ups': push_ups
}

def get_valid_exercises():
    """Return a list of valid exercise IDs"""
    return list(exercise_map.keys())

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/exercise/<exercise>')
def exercise_page(exercise):
    """
    Unified endpoint for all exercise viewing modes
    """
    valid_exercises = get_valid_exercises()
    
    if exercise not in valid_exercises:
        app.logger.error(f"Invalid exercise requested: {exercise}")
        return "Exercise not found", 404
        
    return render_template('websocket_exercise.html', exercise_id=exercise)

@app.route('/api/exercises', methods=['GET'])
def get_exercises():
    """
    Return a list of available exercises
    """
    try:
        exercises = [
            {"id": "hummer", "name": "Bicep Curl (Hammer)"},
            {"id": "front_raise", "name": "Dumbbell Front Raise"},
            {"id": "squat", "name": "Squat"},
            {"id": "triceps", "name": "Triceps Extension"},
            {"id": "lunges", "name": "Lunges"},
            {"id": "shoulder_press", "name": "Shoulder Press"},
            {"id": "plank", "name": "Plank"},
            {"id": "side_lateral_raise", "name": "Side Lateral Raise"},
            {"id": "triceps_kickback_side", "name": "Triceps Kickback (Side View)"},
            {"id": "push_ups", "name": "Push Ups"}
        ]
        return jsonify(exercises)
    except Exception as e:
        app.logger.error(f"Error in get_exercises: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/status')
def api_status():
    """
    Simple endpoint to check API health
    """
    return jsonify({
        "status": "online",
        "timestamp": time.time(),
        "exercise_count": len(exercise_map),
        "active_sessions": len(active_sessions)
    })

@app.route('/camera_test')
def camera_test():
    """
    Simple page to test camera access
    """
    return render_template('camera_test.html')

@app.route('/video_feed/<exercise>')
def video_feed(exercise):
    """
    MJPEG stream endpoint for direct video access (fallback for WebSocket)
    """
    try:
        if exercise in exercise_map:
            # Create a mock video feed when in cloud environment where camera isn't available
            def generate_mock_feed():
                """Generate a mock video feed with instructions and feedback"""
                while True:
                    # Create a black frame
                    frame = np.zeros((480, 640, 3), np.uint8)
                    
                    # Add exercise name and instructions
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    cv2.putText(frame, f"Exercise: {exercise}", (50, 50), font, 1, (255, 255, 255), 2, cv2.LINE_AA)
                    cv2.putText(frame, "Cloud Mode - No Camera Available", (50, 100), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
                    
                    # Add exercise-specific instructions
                    y_pos = 150
                    instructions = get_exercise_instructions(exercise)
                    for line in instructions:
                        cv2.putText(frame, line, (50, y_pos), font, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
                        y_pos += 30
                    
                    # Add a progress bar
                    cv2.rectangle(frame, (50, 350), (590, 380), (0, 255, 0), 2)
                    
                    # Convert to JPEG
                    ret, buffer = cv2.imencode('.jpg', frame)
                    frame_bytes = buffer.tobytes()
                    
                    # Yield frame
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    
                    # Control frame rate
                    time.sleep(0.1)
                    
            # Try to use actual exercise function, fallback to mock if camera error
            try:
                return Response(
                    exercise_map[exercise](sound), 
                    mimetype='multipart/x-mixed-replace; boundary=frame',
                    headers={
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0'
                    }
                )
            except Exception as camera_error:
                app.logger.warning(f"Camera access error, using mock feed: {str(camera_error)}")
                return Response(
                    generate_mock_feed(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame',
                    headers={
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0'
                    }
                )
        else:
            return "Invalid exercise", 400
    except Exception as e:
        app.logger.error(f"Error in video_feed: {str(e)}")
        app.logger.error(traceback.format_exc())
        return "Error processing video", 500

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
        ]
    }
    
    # Return specific instructions or default ones
    return instructions.get(exercise_id, ["See documentation for proper form"])

# ====================== WebSocket Event Handlers ======================

@socketio.on('connect')
def handle_connect():
    """
    Handle WebSocket connection
    """
    print(f"Client connected: {request.sid}")
    emit('connection_status', {'status': 'connected', 'session_id': request.sid})

@socketio.on('disconnect')
def handle_disconnect():
    """
    Handle WebSocket disconnection and cleanup resources
    """
    print(f"Client disconnected: {request.sid}")
    # Clean up any active session on disconnect
    if request.sid in active_sessions:
        session_data = active_sessions[request.sid]
        if 'stop_event' in session_data:
            session_data['stop_event'].set()
        if 'cap' in session_data and session_data['cap'] is not None:
            session_data['cap'].release()
        del active_sessions[request.sid]

@socketio.on('start_exercise')
def handle_start_exercise(data):
    """
    Start exercise tracking via WebSocket
    """
    try:
        exercise_id = data.get('exercise_id')
        print(f"Starting exercise: {exercise_id} for session {request.sid}")
        
        if not exercise_id or exercise_id not in exercise_map:
            emit('error', {'message': f'Invalid exercise: {exercise_id}'})
            return
        
        # Stop any currently active session
        if request.sid in active_sessions:
            session_data = active_sessions[request.sid]
            if 'stop_event' in session_data:
                session_data['stop_event'].set()
            if 'cap' in session_data and session_data['cap'] is not None:
                session_data['cap'].release()
        
        # Create a stop event to allow safe termination
        stop_event = threading.Event()
        
        # Store session data
        active_sessions[request.sid] = {
            'exercise_id': exercise_id,
            'stop_event': stop_event,
            'cap': None,
            'left_counter': 0,
            'right_counter': 0,
            'start_time': time.time(),
            'last_active': time.time(),
            'frame_count': 0,
            'fps': 0
        }
        
        # Start a thread to process the exercise
        exercise_thread = threading.Thread(
            target=process_exercise_frames,
            args=(request.sid, exercise_id, stop_event)
        )
        exercise_thread.daemon = True
        exercise_thread.start()
        
        emit('exercise_started', {'exercise_id': exercise_id})
        
    except Exception as e:
        print(f"Error starting exercise: {str(e)}")
        traceback.print_exc()
        emit('error', {'message': f'Error starting exercise: {str(e)}'})

@socketio.on('stop_exercise')
def handle_stop_exercise():
    """
    Stop exercise tracking via WebSocket
    """
    try:
        print(f"Stopping exercise for session {request.sid}")
        
        if request.sid in active_sessions:
            session_data = active_sessions[request.sid]
            if 'stop_event' in session_data:
                session_data['stop_event'].set()
            if 'cap' in session_data and session_data['cap'] is not None:
                session_data['cap'].release()
            
        emit('exercise_stopped')
        
    except Exception as e:
        print(f"Error stopping exercise: {str(e)}")
        emit('error', {'message': f'Error stopping exercise: {str(e)}'})

@socketio.on('ping')
def handle_ping():
    """
    Handle ping messages to keep connection alive
    """
    if request.sid in active_sessions:
        active_sessions[request.sid]['last_active'] = time.time()
    emit('pong')

def process_exercise_frames(session_id, exercise_id, stop_event):
    """
    Process exercise frames and send them via WebSocket
    
    Args:
        session_id: WebSocket session ID
        exercise_id: ID of the exercise to track
        stop_event: Event to signal when to stop processing
    """
    try:
        print(f"Processing exercise frames for {exercise_id}, session {session_id}")
        
        # Initialize video capture
        try:
            cap = cv2.VideoCapture(0)
            
            # Configure camera for better performance
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
            
            if not cap.isOpened():
                raise Exception("Failed to open camera")
                
            # Update session data
            active_sessions[session_id]['cap'] = cap
            
        except Exception as camera_error:
            print(f"Camera error: {str(camera_error)}. Using mock video.")
            socketio.emit('error', 
                        {'message': 'Camera not available. Using simulation mode.'}, 
                        room=session_id)
            
            # Use mock video processing instead
            process_mock_exercise(session_id, exercise_id, stop_event)
            return
        
        # Initial variables
        left_counter = 0
        right_counter = 0
        left_state = None
        right_state = None
        frame_count = 0
        fps_counter = 0
        last_fps_time = time.time()
        last_frame_time = time.time()
        
        while not stop_event.is_set():
            # Check if we've been inactive too long
            now = time.time()
            if now - active_sessions.get(session_id, {}).get('last_active', 0) > 30:
                print(f"Session {session_id} timed out due to inactivity")
                break
                
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture frame")
                socketio.emit('error', {'message': 'Camera frame capture failed'}, room=session_id)
                # Try to reconnect camera
                cap.release()
                time.sleep(1)
                cap = cv2.VideoCapture(0)
                continue
            
            # Process only every 2nd frame for better performance
            frame_count += 1
            if frame_count % 2 != 0:
                continue
                
            # Calculate FPS
            current_time = time.time()
            fps_counter += 1
            
            if current_time - last_fps_time >= 1.0:
                fps = fps_counter / (current_time - last_fps_time)
                fps_counter = 0
                last_fps_time = current_time
                if session_id in active_sessions:
                    active_sessions[session_id]['fps'] = int(fps)
            
            # Flip the frame horizontally
            frame = cv2.flip(frame, 1)
            
            # Check if we're processing too quickly - aim for 15 fps max for WebSocket
            elapsed = current_time - last_frame_time
            if elapsed < 1.0/15.0:
                continue
                
            last_frame_time = current_time
            
            # Convert to RGB for mediapipe
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
            # Exercise variables
            form_feedback = ""
            
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                
                # Draw the pose landmarks
                mp_drawing.draw_landmarks(
                    image, 
                    results.pose_landmarks, 
                    mp_pose.POSE_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=4),
                    mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2)
                )
                
                # Define arm landmarks for exercise tracking
                arm_sides = {
                    'left': {
                        'shoulder': mp_pose.PoseLandmark.LEFT_SHOULDER,
                        'elbow': mp_pose.PoseLandmark.LEFT_ELBOW,
                        'wrist': mp_pose.PoseLandmark.LEFT_WRIST,
                        'hip': mp_pose.PoseLandmark.LEFT_HIP
                    },
                    'right': {
                        'shoulder': mp_pose.PoseLandmark.RIGHT_SHOULDER,
                        'elbow': mp_pose.PoseLandmark.RIGHT_ELBOW,
                        'wrist': mp_pose.PoseLandmark.RIGHT_WRIST,
                        'hip': mp_pose.PoseLandmark.RIGHT_HIP
                    }
                }
                
                # Track angles and exercise state
                for side, joints in arm_sides.items():
                    shoulder = [
                        landmarks[joints['shoulder'].value].x,
                        landmarks[joints['shoulder'].value].y,
                    ]
                    elbow = [
                        landmarks[joints['elbow'].value].x,
                        landmarks[joints['elbow'].value].y,
                    ]
                    wrist = [
                        landmarks[joints['wrist'].value].x,
                        landmarks[joints['wrist'].value].y,
                    ]
                    
                    # Calculate elbow angle
                    elbow_angle = calculate_angle(shoulder, elbow, wrist)
                    
                    # Display angle on frame
                    cv2.putText(
                        image,
                        f'{int(elbow_angle)}',
                        tuple(np.multiply(elbow, [image.shape[1], image.shape[0]]).astype(int)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        2,
                        cv2.LINE_AA
                    )
                    
                    # Exercise specific logic - using hammer curl as an example
                    if exercise_id == 'hummer':
                        if side == 'left':
                            if elbow_angle > 160:
                                left_state = 'down'
                            if elbow_angle < 30 and left_state == 'down':
                                left_state = 'up'
                                left_counter += 1
                                form_feedback = "جيد! استمر"
                        
                        if side == 'right':
                            if elbow_angle > 160:
                                right_state = 'down'
                            if elbow_angle < 30 and right_state == 'down':
                                right_state = 'up'
                                right_counter += 1
                                form_feedback = "ممتاز! استمر"
                
                # Display counters on frame
                cv2.putText(image, f'Left: {left_counter}', (10, 50), 
                         cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
                cv2.putText(image, f'Right: {right_counter}', (10, 100), 
                         cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
                
                # Update session counters
                if session_id in active_sessions:
                    active_sessions[session_id]['left_counter'] = left_counter
                    active_sessions[session_id]['right_counter'] = right_counter
            
            # Convert frame to base64 for WebSocket transmission
            # Use JPEG quality reduction for faster transmission
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            ret, buffer = cv2.imencode('.jpg', image, encode_param)
            frame_data = base64.b64encode(buffer).decode('utf-8')
            
            # Update session last activity time
            if session_id in active_sessions:
                active_sessions[session_id]['last_active'] = time.time()
            
            # Send frame and data
            socketio.emit('exercise_frame', {
                'frame': frame_data,
                'left_counter': left_counter,
                'right_counter': right_counter,
                'feedback': form_feedback,
                'fps': active_sessions.get(session_id, {}).get('fps', 0)
            }, room=session_id)
            
            # Add delay to control frame rate and CPU usage
            time.sleep(0.05)  # Max ~20fps
        
        # Clean up camera when done
        if cap and cap.isOpened():
            cap.release()
        
        print(f"Exercise processing stopped for session {session_id}")
        
    except Exception as e:
        print(f"Error in process_exercise_frames: {str(e)}")
        traceback.print_exc()
        socketio.emit('error', {'message': f'Error processing exercise: {str(e)}'}, room=session_id)
        
        # Cleanup
        if session_id in active_sessions:
            session_data = active_sessions[session_id]
            if 'cap' in session_data and session_data['cap'] is not None:
                session_data['cap'].release()

def process_mock_exercise(session_id, exercise_id, stop_event):
    """
    Process mock exercise when camera is not available
    
    Args:
        session_id: WebSocket session ID
        exercise_id: ID of the exercise to track
        stop_event: Event to signal when to stop processing
    """
    try:
        print(f"Processing mock exercise frames for {exercise_id}, session {session_id}")
        
        # Initial variables
        left_counter = 0
        right_counter = 0
        frame_count = 0
        last_update = time.time()
        
        # Instructions for this exercise
        instructions = get_exercise_instructions(exercise_id)
        
        while not stop_event.is_set():
            # Check if we've been inactive too long
            now = time.time()
            if now - active_sessions.get(session_id, {}).get('last_active', 0) > 30:
                print(f"Session {session_id} timed out due to inactivity")
                break
                
            # Don't send frames too quickly
            if now - last_update < 0.1:  # Max 10 FPS for mock
                time.sleep(0.05)
                continue
                
            last_update = now
            
            # Create a black frame
            frame = np.zeros((480, 640, 3), np.uint8)
            
            # Add exercise name and instructions
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(frame, f"Exercise: {exercise_id}", (50, 50), font, 1, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, "Simulation Mode", (50, 100), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            
            # Add exercise-specific instructions
            y_pos = 150
            for i, line in enumerate(instructions):
                cv2.putText(frame, line, (50, y_pos), font, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
                y_pos += 30
            
            # Display counters
            cv2.putText(frame, f'Left: {left_counter}', (10, 250), 
                       font, 1, (255, 0, 0), 2, cv2.LINE_AA)
            cv2.putText(frame, f'Right: {right_counter}', (10, 300), 
                       font, 1, (255, 0, 0), 2, cv2.LINE_AA)
            
            # Occasionally increment counters to simulate exercise
            frame_count += 1
            if frame_count % 30 == 0:  # Every ~3 seconds
                if np.random.random() > 0.5:
                    left_counter += 1
                else:
                    right_counter += 1
                    
                # Update session counters
                if session_id in active_sessions:
                    active_sessions[session_id]['left_counter'] = left_counter
                    active_sessions[session_id]['right_counter'] = right_counter
            
            # Add a progress simulation
            completion = min(1.0, frame_count / 300)  # Full "workout" after 300 frames
            bar_width = int(540 * completion)
            cv2.rectangle(frame, (50, 350), (50 + bar_width, 380), (0, 255, 0), -1)
            cv2.rectangle(frame, (50, 350), (590, 380), (255, 255, 255), 2)
            
            # Convert to JPEG and send
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            ret, buffer = cv2.imencode('.jpg', frame, encode_param)
            frame_data = base64.b64encode(buffer).decode('utf-8')
            
            # Update session last activity time
            if session_id in active_sessions:
                active_sessions[session_id]['last_active'] = time.time()
            
            # Get a random feedback message
            feedback_messages = [
                "جيد! استمر", "حافظ على الوضعية", "ممتاز!", "تنفس بعمق",
                "حافظ على ثبات الجسم", "ابطئ قليلًا", "ركز على العضلة"
            ]
            feedback = ""
            if frame_count % 20 == 0:  # Show feedback message occasionally
                feedback = np.random.choice(feedback_messages)
            
            # Send frame and data
            socketio.emit('exercise_frame', {
                'frame': frame_data,
                'left_counter': left_counter,
                'right_counter': right_counter,
                'feedback': feedback,
                'fps': 10  # Mock always runs at 10 FPS
            }, room=session_id)
            
            # Sleep to control CPU usage
            time.sleep(0.1)
        
        print(f"Mock exercise processing stopped for session {session_id}")
        
    except Exception as e:
        print(f"Error in process_mock_exercise: {str(e)}")
        traceback.print_exc()
        socketio.emit('error', {'message': f'Error processing exercise: {str(e)}'}, room=session_id)

def cleanup_inactive_sessions():
    """
    Periodically clean up inactive sessions
    """
    while True:
        try:
            current_time = time.time()
            sessions_to_remove = []
            
            for session_id, session_data in active_sessions.items():
                # Check if session has been inactive for too long (60 seconds)
                if current_time - session_data.get('last_active', 0) > 60:
                    sessions_to_remove.append(session_id)
                    if 'stop_event' in session_data:
                        session_data['stop_event'].set()
                    if 'cap' in session_data and session_data['cap'] is not None:
                        session_data['cap'].release()
            
            # Remove inactive sessions
            for session_id in sessions_to_remove:
                del active_sessions[session_id]
                print(f"Cleaned up inactive session: {session_id}")
                
        except Exception as e:
            print(f"Error in cleanup task: {str(e)}")
            
        # Sleep for 10 seconds before next cleanup
        time.sleep(10)

# ====================== Mobile-Optimized Routes ======================

@app.route('/mobile/<exercise>')
def mobile_exercise(exercise):
    """
    Mobile-optimized endpoint for exercise viewing
    """
    valid_exercises = get_valid_exercises()
    
    if exercise not in valid_exercises:
        app.logger.error(f"Invalid exercise requested: {exercise}")
        return "Exercise not found", 404
        
    return render_template('direct_video_fast.html', exercise_id=exercise)

# ====================== Debug Routes ======================

@app.route('/debug/<exercise>')
def debug_exercise(exercise):
    """
    Debug endpoint for exercise viewing
    """
    valid_exercises = get_valid_exercises()
    
    if exercise not in valid_exercises:
        app.logger.error(f"Invalid exercise requested: {exercise}")
        return "Exercise not found", 404
        
    return render_template('direct_video_debug.html', exercise_id=exercise)

# ====================== Health Monitoring ======================

@app.route('/health')
def health_check():
    """
    Health check endpoint for monitoring
    """
    # Get basic application health metrics
    try:
        memory_usage = os.popen('ps -o rss= -p %d' % os.getpid()).read()
        if memory_usage:
            memory_usage = int(memory_usage.strip()) / 1024  # Convert to MB
        else:
            memory_usage = "Unknown"
    except:
        memory_usage = "Unknown"
    
    # Count active sessions
    active_count = len(active_sessions)
    
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "uptime": time.time() - app.config.get('START_TIME', time.time()),
        "active_sessions": active_count,
        "memory_usage_mb": memory_usage,
        "eventlet_version": eventlet.__version__
    })

if __name__ == '__main__':
    # Initialize mediapipe if possible
    try:
        import mediapipe as mp
        print(f"Mediapipe loaded successfully")
        
        mp_drawing = mp.solutions.drawing_utils
        mp_pose = mp.solutions.pose
        print("Pose model initialized successfully")
    except Exception as e:
        print(f"Error initializing libraries: {e}")
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_inactive_sessions)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    # Set start time for uptime tracking
    app.config['START_TIME'] = time.time()
    
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 8080))
    
    # Print startup information
    print(f"Starting AI Fitness Trainer on port {port}")
    print(f"Available exercises: {', '.join(get_valid_exercises())}")
    print(f"WebSocket mode: {socketio.async_mode}")
    
    # Run the application
if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 8080))
    
    # Check if running in cloud environment
    is_cloud = os.environ.get('K_SERVICE') is not None
    
    if is_cloud:
        # For Cloud Run, use simpler server setup
        from waitress import serve
        serve(app, host='0.0.0.0', port=port)
    else:
        # For local development, use socketio
        socketio.run(app, host='0.0.0.0', port=port)