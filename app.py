from flask import Flask, Response, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import cv2
import os
import json
import pygame
import time
import base64
from gtts import gTTS
from flask_cors import CORS
import asyncio
import traceback
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import threading

# Import WebRTC processing
from rtc_video_server import process_offer

# Import exercise modules
from utils import calculate_angle
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
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Setup for async processing
executor = ThreadPoolExecutor()

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

# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/static/<path:path>')
# def serve_static(path):
#     return send_from_directory('static', path)

# # Original endpoint for direct exercise
# @app.route('/exercise/<exercise>')
# def direct_exercise(exercise):
#     valid_exercises = list(exercise_map.keys())
    
#     if exercise not in valid_exercises:
#         app.logger.error(f"Invalid exercise requested: {exercise}")
#         return "Exercise not found", 404
        
#     return render_template('websocket_exercise.html', exercise_id=exercise)



@app.route('/test/<exercise>')
def video_feedd(exercise):
    if exercise == 'hummer':
        return Response(hummer(sound), mimetype='multipart/x-mixed-replace; boundary=frame')
    elif exercise == 'front_raise':
        return Response(dumbbell_front_raise(sound), mimetype='multipart/x-mixed-replace; boundary=frame')
    elif exercise == 'squat':
        return Response(squat(sound), mimetype='multipart/x-mixed-replace; boundary=frame')
    elif exercise == 'triceps':
        return Response(triceps_extension(sound), mimetype='multipart/x-mixed-replace; boundary=frame')
    elif exercise == 'lunges':
        return Response(lunges(sound), mimetype='multipart/x-mixed-replace; boundary=frame')
    elif exercise == 'shoulder_press':
        return Response(shoulder_press(sound), mimetype='multipart/x-mixed-replace; boundary=frame')
    elif exercise == 'plank':
        return Response(plank(sound), mimetype='multipart/x-mixed-replace; boundary=frame')
    elif exercise == 'side_lateral_raise':
        return Response(side_lateral_raise(sound), mimetype='multipart/x-mixed-replace; boundary=frame')
    elif exercise == 'triceps_kickback_side':
        return Response(triceps_kickback_side(sound), mimetype='multipart/x-mixed-replace; boundary=frame')
    elif exercise == 'push_ups':
        return Response(push_ups(sound), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return "Invalid exercise", 400


#===========================test=============================================== 


# direct_video_fast.html

# @app.route('/fast_video/<exercise>')
# def fast_video(exercise):
#     valid_exercises = [
#         "hummer", "front_raise", "squat", "triceps", "lunges", 
#         "shoulder_press", "plank", "side_lateral_raise", 
#         "triceps_kickback_side", "push_ups"
#     ]
    
#     if exercise not in valid_exercises:
#         app.logger.error(f"Invalid exercise requested: {exercise}")
#         return "Exercise not found", 404
        
#     return render_template('direct_video_fast.html', exercise_id=exercise)



# direct_video_debug.html

# @app.route('/debug_video/<exercise>')
# def debug_video(exercise):
#     valid_exercises = [
#         "hummer", "front_raise", "squat", "triceps", "lunges", 
#         "shoulder_press", "plank", "side_lateral_raise", 
#         "triceps_kickback_side", "push_ups"
#     ]
    
#     if exercise not in valid_exercises:
#         app.logger.error(f"Invalid exercise requested: {exercise}")
#         return "Exercise not found", 404
        
#     return render_template('direct_video_debug.html', exercise_id=exercise)






import numpy as np

@app.route('/video_feed/<exercise>')
def video_feed(exercise):
    try:
        if exercise in exercise_map:
            # محاولة استخدام الدالة الأصلية
            try:
                print(f"Starting video feed for exercise: {exercise}")
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
                # لوج الخطأ الأصلي
                app.logger.error(f"Error accessing camera: {str(camera_error)}")
                print(f"Error accessing camera: {str(camera_error)}")
                
                # إنشاء استجابة بديلة باستخدام إطارات وهمية
                def mock_video_feed():
                    """
                    توليد إطارات وهمية للعرض عندما تكون الكاميرا غير متاحة
                    """
                    while True:
                        # إنشاء إطار أسود بنص
                        frame = np.zeros((480, 640, 3), np.uint8)
                        
                        # إضافة نص
                        font = cv2.FONT_HERSHEY_SIMPLEX
                        cv2.putText(frame, f"Exercise: {exercise}", (50, 50), font, 1, (255, 255, 255), 2, cv2.LINE_AA)
                        cv2.putText(frame, "Camera not available in cloud environment", (50, 100), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
                        cv2.putText(frame, "Please try running locally", (50, 150), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
                        
                        # إضافة تعليمات للتمرين
                        if exercise == "hummer":
                            instructions = [
                                "Bicep Curl Instructions:",
                                "1. Stand with weights at your sides",
                                "2. Curl the weights up to your shoulders",
                                "3. Lower back down with control"
                            ]
                        elif exercise == "squat":
                            instructions = [
                                "Squat Instructions:",
                                "1. Stand with feet shoulder-width apart",
                                "2. Lower your body as if sitting in a chair",
                                "3. Keep back straight and knees over toes",
                                "4. Return to standing position"
                            ]
                        else:
                            instructions = [
                                f"{exercise.replace('_', ' ').title()} Instructions:",
                                "See documentation for proper form"
                            ]
                        
                        y_pos = 200
                        for line in instructions:
                            cv2.putText(frame, line, (50, y_pos), font, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
                            y_pos += 30
                            
                        # Simulate exercise tracking UI
                        cv2.rectangle(frame, (50, 350), (590, 400), (0, 255, 0), 2)
                        cv2.putText(frame, "Exercise Progress", (250, 380), font, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
                        
                        # تحويل الإطار إلى JPEG للبث
                        ret, buffer = cv2.imencode('.jpg', frame)
                        frame_bytes = buffer.tobytes()
                        
                        # إرسال الإطار
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                        
                        # انتظار قبل الإطار التالي
                        time.sleep(0.1)  # 10 FPS
                
                # إرجاع الاستجابة البديلة
                return Response(
                    mock_video_feed(), 
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

#===========================test=============================================== 














# # New endpoint for WebSocket-based exercise viewing
# @app.route('/websocket_exercise/<exercise>')
# def websocket_exercise(exercise):
#     valid_exercises = list(exercise_map.keys())
    
#     if exercise not in valid_exercises:
#         app.logger.error(f"Invalid exercise requested: {exercise}")
#         return "Exercise not found", 404
        
#     return render_template('websocket_exercise.html', exercise_id=exercise)

# # For backward compatibility
# @app.route('/direct_video/<exercise>')
# def direct_video(exercise):
#     valid_exercises = list(exercise_map.keys())
    
#     if exercise not in valid_exercises:
#         app.logger.error(f"Invalid exercise requested: {exercise}")
#         return "Exercise not found", 404
        
#     return render_template('websocket_exercise.html', exercise_id=exercise)

# @app.route('/api/rtc_offer', methods=['POST'])
# def rtc_offer():
#     try:
#         data = request.json
#         app.logger.info(f"Received WebRTC offer for exercise: {data.get('exercise', 'unknown')}")
        
#         # Use ThreadPoolExecutor to handle async processing
#         future = executor.submit(asyncio.run, process_offer(data))
#         response = future.result()
        
#         return jsonify(response)
#     except Exception as e:
#         app.logger.error(f"Error in rtc_offer: {str(e)}")
#         app.logger.error(traceback.format_exc())
#         return jsonify({"error": str(e)}), 500

# @app.route('/api/exercises', methods=['GET'])
# def get_exercises():
#     try:
#         exercises = [
#             {"id": "hummer", "name": "Bicep Curl (Hammer)"},
#             {"id": "front_raise", "name": "Dumbbell Front Raise"},
#             {"id": "squat", "name": "Squat"},
#             {"id": "triceps", "name": "Triceps Extension"},
#             {"id": "lunges", "name": "Lunges"},
#             {"id": "shoulder_press", "name": "Shoulder Press"},
#             {"id": "plank", "name": "Plank"},
#             {"id": "side_lateral_raise", "name": "Side Lateral Raise"},
#             {"id": "triceps_kickback_side", "name": "Triceps Kickback (Side View)"},
#             {"id": "push_ups", "name": "Push Ups"}
#         ]
#         return jsonify(exercises)
#     except Exception as e:
#         app.logger.error(f"Error in get_exercises: {str(e)}")
#         return jsonify({"error": str(e)}), 500

# @app.route('/api/pose_data')
# def pose_data():
#     try:
#         data = {
#             "status": "ok",
#             "timestamp": time.time(),
#             "message": "Pose data API is working"
#         }
#         return jsonify(data)
#     except Exception as e:
#         app.logger.error(f"Error in pose_data: {str(e)}")
#         return jsonify({"error": str(e)}), 500

# @app.route('/camera_test')
# def camera_test():
#     return render_template('camera_test.html')

# # Original MJPEG streaming endpoint for backwards compatibility
# # @app.route('/video_feed/<exercise>')
# # def video_feed(exercise):
# #     try:
# #         if exercise in exercise_map:
# #             # Add debug logging
# #             print(f"Starting video feed for exercise: {exercise}")
            
# #             # Add cache control headers
# #             return Response(
# #                 exercise_map[exercise](sound), 
# #                 mimetype='multipart/x-mixed-replace; boundary=frame',
# #                 headers={
# #                     'Cache-Control': 'no-cache, no-store, must-revalidate',
# #                     'Pragma': 'no-cache',
# #                     'Expires': '0'
# #                 }
# #             )
# #         else:
# #             return "Invalid exercise", 400
# #     except Exception as e:
# #         app.logger.error(f"Error in video_feed: {str(e)}")
# #         app.logger.error(traceback.format_exc())
# #         return "Error processing video", 500

# # ====================== WebSocket Event Handlers ======================

# @socketio.on('connect')
# def handle_connect():
#     print(f"Client connected: {request.sid}")
#     emit('connection_status', {'status': 'connected', 'session_id': request.sid})

# @socketio.on('disconnect')
# def handle_disconnect():
#     print(f"Client disconnected: {request.sid}")
#     # Clean up any active session on disconnect
#     if request.sid in active_sessions:
#         session_data = active_sessions[request.sid]
#         if 'stop_event' in session_data:
#             session_data['stop_event'].set()
#         if 'cap' in session_data and session_data['cap'] is not None:
#             session_data['cap'].release()
#         del active_sessions[request.sid]

# @socketio.on('start_exercise')
# def handle_start_exercise(data):
#     try:
#         exercise_id = data.get('exercise_id')
#         print(f"Starting exercise: {exercise_id} for session {request.sid}")
        
#         if not exercise_id or exercise_id not in exercise_map:
#             emit('error', {'message': f'Invalid exercise: {exercise_id}'})
#             return
        
#         # Stop any currently active session
#         if request.sid in active_sessions:
#             session_data = active_sessions[request.sid]
#             if 'stop_event' in session_data:
#                 session_data['stop_event'].set()
#             if 'cap' in session_data and session_data['cap'] is not None:
#                 session_data['cap'].release()
        
#         # Create a stop event to allow safe termination
#         stop_event = threading.Event()
        
#         # Store session data
#         active_sessions[request.sid] = {
#             'exercise_id': exercise_id,
#             'stop_event': stop_event,
#             'cap': None,
#             'left_counter': 0,
#             'right_counter': 0
#         }
        
#         # Start a thread to process the exercise
#         exercise_thread = threading.Thread(
#             target=process_exercise_frames,
#             args=(request.sid, exercise_id, stop_event)
#         )
#         exercise_thread.daemon = True
#         exercise_thread.start()
        
#         emit('exercise_started', {'exercise_id': exercise_id})
        
#     except Exception as e:
#         print(f"Error starting exercise: {str(e)}")
#         traceback.print_exc()
#         emit('error', {'message': f'Error starting exercise: {str(e)}'})

# @socketio.on('stop_exercise')
# def handle_stop_exercise():
#     try:
#         print(f"Stopping exercise for session {request.sid}")
        
#         if request.sid in active_sessions:
#             session_data = active_sessions[request.sid]
#             if 'stop_event' in session_data:
#                 session_data['stop_event'].set()
#             if 'cap' in session_data and session_data['cap'] is not None:
#                 session_data['cap'].release()
            
#         emit('exercise_stopped')
        
#     except Exception as e:
#         print(f"Error stopping exercise: {str(e)}")
#         emit('error', {'message': f'Error stopping exercise: {str(e)}'})

# def process_exercise_frames(session_id, exercise_id, stop_event):
#     """
#     Process exercise frames and send them via WebSocket
    
#     Args:
#         session_id: WebSocket session ID
#         exercise_id: ID of the exercise to track
#         stop_event: Event to signal when to stop processing
#     """
#     try:
#         print(f"Processing exercise frames for {exercise_id}, session {session_id}")
        
#         # Initialize video capture
#         cap = cv2.VideoCapture(0)
        
#         if not cap.isOpened():
#             print("Failed to open camera")
#             socketio.emit('error', {'message': 'Failed to open camera'}, room=session_id)
#             return
        
#         # Update session data
#         active_sessions[session_id]['cap'] = cap
        
#         # Initial variables
#         left_counter = 0
#         right_counter = 0
#         left_state = None
#         right_state = None
        
#         while not stop_event.is_set():
#             ret, frame = cap.read()
#             if not ret:
#                 print("Failed to capture frame")
#                 break
            
#             # Flip the frame horizontally
#             frame = cv2.flip(frame, 1)
            
#             # Convert to RGB for mediapipe
#             image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#             results = pose.process(image)
#             image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
#             # Exercise variables
#             form_feedback = ""
            
#             if results.pose_landmarks:
#                 landmarks = results.pose_landmarks.landmark
                
#                 # Draw the pose landmarks
#                 mp_drawing.draw_landmarks(
#                     image, 
#                     results.pose_landmarks, 
#                     mp_pose.POSE_CONNECTIONS,
#                     mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=4),
#                     mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2)
#                 )
                
#                 # Define arm landmarks for exercise tracking
#                 arm_sides = {
#                     'left': {
#                         'shoulder': mp_pose.PoseLandmark.LEFT_SHOULDER,
#                         'elbow': mp_pose.PoseLandmark.LEFT_ELBOW,
#                         'wrist': mp_pose.PoseLandmark.LEFT_WRIST,
#                         'hip': mp_pose.PoseLandmark.LEFT_HIP
#                     },
#                     'right': {
#                         'shoulder': mp_pose.PoseLandmark.RIGHT_SHOULDER,
#                         'elbow': mp_pose.PoseLandmark.RIGHT_ELBOW,
#                         'wrist': mp_pose.PoseLandmark.RIGHT_WRIST,
#                         'hip': mp_pose.PoseLandmark.RIGHT_HIP
#                     }
#                 }
                
#                 # Track angles and exercise state
#                 for side, joints in arm_sides.items():
#                     shoulder = [
#                         landmarks[joints['shoulder'].value].x,
#                         landmarks[joints['shoulder'].value].y,
#                     ]
#                     elbow = [
#                         landmarks[joints['elbow'].value].x,
#                         landmarks[joints['elbow'].value].y,
#                     ]
#                     wrist = [
#                         landmarks[joints['wrist'].value].x,
#                         landmarks[joints['wrist'].value].y,
#                     ]
                    
#                     # Calculate elbow angle
#                     elbow_angle = calculate_angle(shoulder, elbow, wrist)
                    
#                     # Display angle on frame
#                     cv2.putText(
#                         image,
#                         f'{int(elbow_angle)}',
#                         tuple(np.multiply(elbow, [image.shape[1], image.shape[0]]).astype(int)),
#                         cv2.FONT_HERSHEY_SIMPLEX,
#                         0.5,
#                         (255, 255, 255),
#                         2,
#                         cv2.LINE_AA
#                     )
                    
#                     # Exercise specific logic - using hammer curl as an example
#                     if exercise_id == 'hummer':
#                         if side == 'left':
#                             if elbow_angle > 160:
#                                 left_state = 'down'
#                             if elbow_angle < 30 and left_state == 'down':
#                                 left_state = 'up'
#                                 left_counter += 1
#                                 print(f'Left Counter: {left_counter}')
#                                 form_feedback = "جيد! استمر"
                        
#                         if side == 'right':
#                             if elbow_angle > 160:
#                                 right_state = 'down'
#                             if elbow_angle < 30 and right_state == 'down':
#                                 right_state = 'up'
#                                 right_counter += 1
#                                 print(f'Right Counter: {right_counter}')
#                                 form_feedback = "ممتاز! استمر"
                    
#                     # (Add more exercise-specific logic here for other exercises)
                
#                 # Display counters on frame
#                 cv2.putText(image, f'Left: {left_counter}', (10, 50), 
#                          cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
#                 cv2.putText(image, f'Right: {right_counter}', (10, 100), 
#                          cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
                
#                 # Update session counters
#                 active_sessions[session_id]['left_counter'] = left_counter
#                 active_sessions[session_id]['right_counter'] = right_counter
                
#             # Convert frame to base64 for WebSocket transmission
#             ret, buffer = cv2.imencode('.jpg', image)
#             frame_data = base64.b64encode(buffer).decode('utf-8')
            
#             # Send frame and data
#             socketio.emit('exercise_frame', {
#                 'frame': frame_data,
#                 'left_counter': left_counter,
#                 'right_counter': right_counter,
#                 'feedback': form_feedback
#             }, room=session_id)
            
#             # Short delay to reduce CPU usage
#             time.sleep(0.03)  # ~30 fps
        
#         # Clean up camera when done
#         if cap.isOpened():
#             cap.release()
        
#         print(f"Exercise processing stopped for session {session_id}")
        
#     except Exception as e:
#         print(f"Error in process_exercise_frames: {str(e)}")
#         traceback.print_exc()
#         socketio.emit('error', {'message': f'Error processing exercise: {str(e)}'}, room=session_id)
        
#         # Cleanup
#         if session_id in active_sessions:
#             session_data = active_sessions[session_id]
#             if 'cap' in session_data and session_data['cap'] is not None:
#                 session_data['cap'].release()

# if __name__ == '__main__':
#     # Initialize mediapipe
#     try:
#         import mediapipe as mp
#         print(f"Mediapipe loaded successfully")
        
#         # Initialize pose
#         mp_drawing = mp.solutions.drawing_utils
#         mp_pose = mp.solutions.pose
#         pose = mp_pose.Pose(
#             min_detection_confidence=0.5,
#             min_tracking_confidence=0.5,
#             model_complexity=1  # Medium complexity for balance between performance and accuracy
#         )
#         print("Pose model initialized successfully")
#     except Exception as e:
#         print(f"Error initializing libraries: {e}")
    
#     port = int(os.environ.get('PORT', 8080))
#     socketio.run(app, host='0.0.0.0', port=port)






# from flask import Flask, Response, render_template, request, jsonify, send_from_directory
# from flask_socketio import SocketIO, emit
# import cv2
# import os
# import json
# import pygame
# import time
# import base64
# import traceback
# from concurrent.futures import ThreadPoolExecutor
# import numpy as np
# import threading
# from flask_cors import CORS

# # Import exercise modules
# from utils import calculate_angle, mp_pose, pose
# from exercises.bicep_curl import hummer
# from exercises.front_raise import dumbbell_front_raise
# from exercises.squat import squat
# from exercises.triceps_extension import triceps_extension
# from exercises.lunges import lunges
# from exercises.shoulder_press import shoulder_press
# from exercises.plank import plank
# from exercises.lateral_raise import side_lateral_raise
# from exercises.triceps_kickback import triceps_kickback_side
# from exercises.push_ups import push_ups

# app = Flask(__name__, static_folder='static')
# CORS(app)  # Enable CORS for all routes
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# # Setup for async processing
# executor = ThreadPoolExecutor(max_workers=4)

# # Dummy sound class to avoid file path issues
# class DummySound:
#     def __init__(self):
#         self.is_playing = False
    
#     def play(self):
#         self.is_playing = True
#         print("Dummy sound play")
    
#     def stop(self):
#         self.is_playing = False
#         print("Dummy sound stop")

# # Use dummy sound instead of loading from a specific path
# sound = DummySound()

# # Ensure audio directory exists
# os.makedirs("audio", exist_ok=True)

# # Dictionary to store active sessions
# active_sessions = {}

# # Dictionary to store exercise functions
# exercise_map = {
#     'hummer': hummer,
#     'front_raise': dumbbell_front_raise,
#     'squat': squat,
#     'triceps': triceps_extension,
#     'lunges': lunges,
#     'shoulder_press': shoulder_press,
#     'plank': plank,
#     'side_lateral_raise': side_lateral_raise,
#     'triceps_kickback_side': triceps_kickback_side,
#     'push_ups': push_ups
# }

# def get_valid_exercises():
#     """Return a list of valid exercise IDs"""
#     return list(exercise_map.keys())

# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/static/<path:path>')
# def serve_static(path):
#     return send_from_directory('static', path)

# @app.route('/exercise/<exercise>')
# def exercise_page(exercise):
#     """
#     Unified endpoint for all exercise viewing modes
#     """
#     valid_exercises = get_valid_exercises()
    
#     if exercise not in valid_exercises:
#         app.logger.error(f"Invalid exercise requested: {exercise}")
#         return "Exercise not found", 404
        
#     return render_template('websocket_exercise.html', exercise_id=exercise)

# @app.route('/api/exercises', methods=['GET'])
# def get_exercises():
#     """
#     Return a list of available exercises
#     """
#     try:
#         exercises = [
#             {"id": "hummer", "name": "Bicep Curl (Hammer)"},
#             {"id": "front_raise", "name": "Dumbbell Front Raise"},
#             {"id": "squat", "name": "Squat"},
#             {"id": "triceps", "name": "Triceps Extension"},
#             {"id": "lunges", "name": "Lunges"},
#             {"id": "shoulder_press", "name": "Shoulder Press"},
#             {"id": "plank", "name": "Plank"},
#             {"id": "side_lateral_raise", "name": "Side Lateral Raise"},
#             {"id": "triceps_kickback_side", "name": "Triceps Kickback (Side View)"},
#             {"id": "push_ups", "name": "Push Ups"}
#         ]
#         return jsonify(exercises)
#     except Exception as e:
#         app.logger.error(f"Error in get_exercises: {str(e)}")
#         return jsonify({"error": str(e)}), 500

# @app.route('/api/status')
# def api_status():
#     """
#     Simple endpoint to check API health
#     """
#     return jsonify({
#         "status": "online",
#         "timestamp": time.time(),
#         "exercise_count": len(exercise_map)
#     })

# @app.route('/camera_test')
# def camera_test():
#     """
#     Simple page to test camera access
#     """
#     return render_template('camera_test.html')

# @app.route('/video_feed/<exercise>')
# def video_feed(exercise):
#     """
#     MJPEG stream endpoint for direct video access
#     """
#     try:
#         if exercise in exercise_map:
#             # Add cache control headers
#             return Response(
#                 exercise_map[exercise](sound), 
#                 mimetype='multipart/x-mixed-replace; boundary=frame',
#                 headers={
#                     'Cache-Control': 'no-cache, no-store, must-revalidate',
#                     'Pragma': 'no-cache',
#                     'Expires': '0'
#                 }
#             )
#         else:
#             return "Invalid exercise", 400
#     except Exception as e:
#         app.logger.error(f"Error in video_feed: {str(e)}")
#         app.logger.error(traceback.format_exc())
#         return "Error processing video", 500

# # ====================== WebSocket Event Handlers ======================

# @socketio.on('connect')
# def handle_connect():
#     """
#     Handle WebSocket connection
#     """
#     print(f"Client connected: {request.sid}")
#     emit('connection_status', {'status': 'connected', 'session_id': request.sid})

# @socketio.on('disconnect')
# def handle_disconnect():
#     """
#     Handle WebSocket disconnection and cleanup resources
#     """
#     print(f"Client disconnected: {request.sid}")
#     # Clean up any active session on disconnect
#     if request.sid in active_sessions:
#         session_data = active_sessions[request.sid]
#         if 'stop_event' in session_data:
#             session_data['stop_event'].set()
#         if 'cap' in session_data and session_data['cap'] is not None:
#             session_data['cap'].release()
#         del active_sessions[request.sid]

# @socketio.on('start_exercise')
# def handle_start_exercise(data):
#     """
#     Start exercise tracking via WebSocket
#     """
#     try:
#         exercise_id = data.get('exercise_id')
#         print(f"Starting exercise: {exercise_id} for session {request.sid}")
        
#         if not exercise_id or exercise_id not in exercise_map:
#             emit('error', {'message': f'Invalid exercise: {exercise_id}'})
#             return
        
#         # Stop any currently active session
#         if request.sid in active_sessions:
#             session_data = active_sessions[request.sid]
#             if 'stop_event' in session_data:
#                 session_data['stop_event'].set()
#             if 'cap' in session_data and session_data['cap'] is not None:
#                 session_data['cap'].release()
        
#         # Create a stop event to allow safe termination
#         stop_event = threading.Event()
        
#         # Store session data
#         active_sessions[request.sid] = {
#             'exercise_id': exercise_id,
#             'stop_event': stop_event,
#             'cap': None,
#             'left_counter': 0,
#             'right_counter': 0,
#             'start_time': time.time()
#         }
        
#         # Start a thread to process the exercise
#         exercise_thread = threading.Thread(
#             target=process_exercise_frames,
#             args=(request.sid, exercise_id, stop_event)
#         )
#         exercise_thread.daemon = True
#         exercise_thread.start()
        
#         emit('exercise_started', {'exercise_id': exercise_id})
        
#     except Exception as e:
#         print(f"Error starting exercise: {str(e)}")
#         traceback.print_exc()
#         emit('error', {'message': f'Error starting exercise: {str(e)}'})

# @socketio.on('stop_exercise')
# def handle_stop_exercise():
#     """
#     Stop exercise tracking via WebSocket
#     """
#     try:
#         print(f"Stopping exercise for session {request.sid}")
        
#         if request.sid in active_sessions:
#             session_data = active_sessions[request.sid]
#             if 'stop_event' in session_data:
#                 session_data['stop_event'].set()
#             if 'cap' in session_data and session_data['cap'] is not None:
#                 session_data['cap'].release()
            
#         emit('exercise_stopped')
        
#     except Exception as e:
#         print(f"Error stopping exercise: {str(e)}")
#         emit('error', {'message': f'Error stopping exercise: {str(e)}'})

# def process_exercise_frames(session_id, exercise_id, stop_event):
#     """
#     Process exercise frames and send them via WebSocket
    
#     Args:
#         session_id: WebSocket session ID
#         exercise_id: ID of the exercise to track
#         stop_event: Event to signal when to stop processing
#     """
#     try:
#         print(f"Processing exercise frames for {exercise_id}, session {session_id}")
        
#         # Initialize video capture with optimized settings
#         cap = cv2.VideoCapture(0)
        
#         # Configure camera for better performance
#         cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
#         cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
#         cap.set(cv2.CAP_PROP_FPS, 30)
        
#         if not cap.isOpened():
#             print("Failed to open camera")
#             socketio.emit('error', {'message': 'Failed to open camera'}, room=session_id)
#             return
        
#         # Update session data
#         active_sessions[session_id]['cap'] = cap
        
#         # Initial variables
#         left_counter = 0
#         right_counter = 0
#         left_state = None
#         right_state = None
#         frame_count = 0
#         last_frame_time = time.time()
        
#         while not stop_event.is_set():
#             ret, frame = cap.read()
#             if not ret:
#                 print("Failed to capture frame")
#                 socketio.emit('error', {'message': 'Failed to capture camera frame'}, room=session_id)
#                 break
            
#             # Process only every 2nd frame for better performance
#             frame_count += 1
#             if frame_count % 2 != 0:
#                 continue
                
#             # Calculate FPS
#             current_time = time.time()
#             fps = 1 / (current_time - last_frame_time)
#             last_frame_time = current_time
            
#             # Flip the frame horizontally
#             frame = cv2.flip(frame, 1)
            
#             # Convert to RGB for mediapipe
#             image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#             results = pose.process(image)
#             image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
#             # Exercise variables
#             form_feedback = ""
            
#             if results.pose_landmarks:
#                 landmarks = results.pose_landmarks.landmark
                
#                 # Draw the pose landmarks
#                 mp_drawing.draw_landmarks(
#                     image, 
#                     results.pose_landmarks, 
#                     mp_pose.POSE_CONNECTIONS,
#                     mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=4),
#                     mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2)
#                 )
                
#                 # Define arm landmarks for exercise tracking
#                 arm_sides = {
#                     'left': {
#                         'shoulder': mp_pose.PoseLandmark.LEFT_SHOULDER,
#                         'elbow': mp_pose.PoseLandmark.LEFT_ELBOW,
#                         'wrist': mp_pose.PoseLandmark.LEFT_WRIST,
#                         'hip': mp_pose.PoseLandmark.LEFT_HIP
#                     },
#                     'right': {
#                         'shoulder': mp_pose.PoseLandmark.RIGHT_SHOULDER,
#                         'elbow': mp_pose.PoseLandmark.RIGHT_ELBOW,
#                         'wrist': mp_pose.PoseLandmark.RIGHT_WRIST,
#                         'hip': mp_pose.PoseLandmark.RIGHT_HIP
#                     }
#                 }
                
#                 # Track angles and exercise state
#                 for side, joints in arm_sides.items():
#                     shoulder = [
#                         landmarks[joints['shoulder'].value].x,
#                         landmarks[joints['shoulder'].value].y,
#                     ]
#                     elbow = [
#                         landmarks[joints['elbow'].value].x,
#                         landmarks[joints['elbow'].value].y,
#                     ]
#                     wrist = [
#                         landmarks[joints['wrist'].value].x,
#                         landmarks[joints['wrist'].value].y,
#                     ]
                    
#                     # Calculate elbow angle
#                     elbow_angle = calculate_angle(shoulder, elbow, wrist)
                    
#                     # Display angle on frame
#                     cv2.putText(
#                         image,
#                         f'{int(elbow_angle)}',
#                         tuple(np.multiply(elbow, [image.shape[1], image.shape[0]]).astype(int)),
#                         cv2.FONT_HERSHEY_SIMPLEX,
#                         0.5,
#                         (255, 255, 255),
#                         2,
#                         cv2.LINE_AA
#                     )
                    
#                     # Exercise specific logic - using hammer curl as an example
#                     if exercise_id == 'hummer':
#                         if side == 'left':
#                             if elbow_angle > 160:
#                                 left_state = 'down'
#                             if elbow_angle < 30 and left_state == 'down':
#                                 left_state = 'up'
#                                 left_counter += 1
#                                 form_feedback = "جيد! استمر"
                        
#                         if side == 'right':
#                             if elbow_angle > 160:
#                                 right_state = 'down'
#                             if elbow_angle < 30 and right_state == 'down':
#                                 right_state = 'up'
#                                 right_counter += 1
#                                 form_feedback = "ممتاز! استمر"
                    
#                     # Implement exercise-specific logic based on exercise_id
#                     # Would need specific logic for each exercise
                
#                 # Display counters on frame
#                 cv2.putText(image, f'Left: {left_counter}', (10, 50), 
#                          cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
#                 cv2.putText(image, f'Right: {right_counter}', (10, 100), 
#                          cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
                
#                 # Update session counters
#                 active_sessions[session_id]['left_counter'] = left_counter
#                 active_sessions[session_id]['right_counter'] = right_counter
                
#                 # Display FPS on frame
#                 cv2.putText(image, f'FPS: {int(fps)}', (10, image.shape[0] - 20), 
#                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                
#             # Convert frame to base64 for WebSocket transmission
#             # Use lower quality JPEG compression for faster transmission
#             encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
#             ret, buffer = cv2.imencode('.jpg', image, encode_param)
#             frame_data = base64.b64encode(buffer).decode('utf-8')
            
#             # Send frame and data
#             socketio.emit('exercise_frame', {
#                 'frame': frame_data,
#                 'left_counter': left_counter,
#                 'right_counter': right_counter,
#                 'feedback': form_feedback,
#                 'fps': int(fps)
#             }, room=session_id)
            
#             # Short delay to reduce CPU usage
#             time.sleep(0.03)  # ~30 fps
        
#         # Clean up camera when done
#         if cap.isOpened():
#             cap.release()
        
#         print(f"Exercise processing stopped for session {session_id}")
        
#     except Exception as e:
#         print(f"Error in process_exercise_frames: {str(e)}")
#         traceback.print_exc()
#         socketio.emit('error', {'message': f'Error processing exercise: {str(e)}'}, room=session_id)
        
#         # Cleanup
#         if session_id in active_sessions:
#             session_data = active_sessions[session_id]
#             if 'cap' in session_data and session_data['cap'] is not None:
#                 session_data['cap'].release()

# @app.route('/api/exercise/start/<exercise>', methods=['POST'])
# def start_exercise_api(exercise):
#     """
#     REST API endpoint to start an exercise
#     Returns a session ID that can be used to retrieve frames
#     """
#     try:
#         valid_exercises = get_valid_exercises()
        
#         if exercise not in valid_exercises:
#             return jsonify({"error": f"Invalid exercise: {exercise}"}), 400
            
#         # Generate a unique session ID
#         session_id = f"api_{int(time.time())}_{os.urandom(4).hex()}"
        
#         # Create a stop event to allow safe termination
#         stop_event = threading.Event()
        
#         # Store session data
#         active_sessions[session_id] = {
#             'exercise_id': exercise,
#             'stop_event': stop_event,
#             'cap': None,
#             'left_counter': 0,
#             'right_counter': 0,
#             'start_time': time.time(),
#             'last_access': time.time(),
#             'frames': []  # Store last few frames
#         }
        
#         # Start a thread to process the exercise
#         exercise_thread = threading.Thread(
#             target=process_exercise_frames_api,
#             args=(session_id, exercise, stop_event)
#         )
#         exercise_thread.daemon = True
#         exercise_thread.start()
        
#         return jsonify({
#             "status": "success",
#             "session_id": session_id,
#             "message": f"Exercise {exercise} started",
#             "access_url": f"/api/exercise/frames/{session_id}"
#         })
        
#     except Exception as e:
#         app.logger.error(f"Error starting exercise API: {str(e)}")
#         app.logger.error(traceback.format_exc())
#         return jsonify({"error": str(e)}), 500

# @app.route('/api/exercise/frames/<session_id>', methods=['GET'])
# def get_exercise_frames(session_id):
#     """
#     Retrieve the latest frame and data for a session
#     """
#     try:
#         if session_id not in active_sessions:
#             return jsonify({"error": "Invalid or expired session ID"}), 404
            
#         session_data = active_sessions[session_id]
#         session_data['last_access'] = time.time()
        
#         # If no frames available yet
#         if not session_data.get('frames'):
#             return jsonify({
#                 "status": "pending",
#                 "message": "Waiting for frames",
#                 "left_counter": session_data.get('left_counter', 0),
#                 "right_counter": session_data.get('right_counter', 0)
#             })
        
#         # Get the latest frame
#         latest_frame = session_data['frames'][-1]
        
#         return jsonify({
#             "status": "success",
#             "frame": latest_frame.get('frame'),
#             "left_counter": session_data.get('left_counter', 0),
#             "right_counter": session_data.get('right_counter', 0),
#             "feedback": latest_frame.get('feedback', ''),
#             "fps": latest_frame.get('fps', 0),
#             "timestamp": latest_frame.get('timestamp', time.time())
#         })
        
#     except Exception as e:
#         app.logger.error(f"Error getting exercise frames: {str(e)}")
#         return jsonify({"error": str(e)}), 500

# @app.route('/api/exercise/stop/<session_id>', methods=['POST'])
# def stop_exercise_api(session_id):
#     """
#     Stop an exercise session
#     """
#     try:
#         if session_id not in active_sessions:
#             return jsonify({"error": "Invalid or expired session ID"}), 404
            
#         session_data = active_sessions[session_id]
#         if 'stop_event' in session_data:
#             session_data['stop_event'].set()
#         if 'cap' in session_data and session_data['cap'] is not None:
#             session_data['cap'].release()
            
#         # Keep session data for a short time for final frame retrieval
#         # It will be cleaned up by the housekeeping task
        
#         return jsonify({
#             "status": "success",
#             "message": f"Exercise stopped for session {session_id}",
#             "left_counter": session_data.get('left_counter', 0),
#             "right_counter": session_data.get('right_counter', 0)
#         })
        
#     except Exception as e:
#         app.logger.error(f"Error stopping exercise: {str(e)}")
#         return jsonify({"error": str(e)}), 500

# def process_exercise_frames_api(session_id, exercise_id, stop_event):
#     """
#     Process exercise frames for the REST API
    
#     Args:
#         session_id: Session ID for tracking
#         exercise_id: ID of the exercise to track
#         stop_event: Event to signal when to stop processing
#     """
#     try:
#         print(f"Processing API exercise frames for {exercise_id}, session {session_id}")
        
#         # Initialize video capture with optimized settings
#         cap = cv2.VideoCapture(0)
        
#         # Configure camera for better performance
#         cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
#         cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
#         cap.set(cv2.CAP_PROP_FPS, 30)
        
#         if not cap.isOpened():
#             print("Failed to open camera")
#             active_sessions[session_id]['error'] = "Failed to open camera"
#             return
        
#         # Update session data
#         active_sessions[session_id]['cap'] = cap
        
#         # Initial variables
#         left_counter = 0
#         right_counter = 0
#         left_state = None
#         right_state = None
#         frame_count = 0
#         last_frame_time = time.time()
        
#         # Max frames to store
#         MAX_STORED_FRAMES = 5
        
#         while not stop_event.is_set():
#             ret, frame = cap.read()
#             if not ret:
#                 print("Failed to capture frame")
#                 break
            
#             # Process only every 3rd frame for better performance in API mode
#             frame_count += 1
#             if frame_count % 3 != 0:
#                 continue
                
#             # Calculate FPS
#             current_time = time.time()
#             fps = 1 / (current_time - last_frame_time)
#             last_frame_time = current_time
            
#             # Flip the frame horizontally
#             frame = cv2.flip(frame, 1)
            
#             # Resize for faster processing
#             frame = cv2.resize(frame, (640, 480))
            
#             # Convert to RGB for mediapipe
#             image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#             results = pose.process(image)
#             image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
#             # Exercise variables
#             form_feedback = ""
            
#             if results.pose_landmarks:
#                 landmarks = results.pose_landmarks.landmark
                
#                 # Draw the pose landmarks
#                 mp_drawing.draw_landmarks(
#                     image, 
#                     results.pose_landmarks, 
#                     mp_pose.POSE_CONNECTIONS,
#                     mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=4),
#                     mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2)
#                 )
                
#                 # Define arm landmarks for exercise tracking
#                 arm_sides = {
#                     'left': {
#                         'shoulder': mp_pose.PoseLandmark.LEFT_SHOULDER,
#                         'elbow': mp_pose.PoseLandmark.LEFT_ELBOW,
#                         'wrist': mp_pose.PoseLandmark.LEFT_WRIST,
#                         'hip': mp_pose.PoseLandmark.LEFT_HIP
#                     },
#                     'right': {
#                         'shoulder': mp_pose.PoseLandmark.RIGHT_SHOULDER,
#                         'elbow': mp_pose.PoseLandmark.RIGHT_ELBOW,
#                         'wrist': mp_pose.PoseLandmark.RIGHT_WRIST,
#                         'hip': mp_pose.PoseLandmark.RIGHT_HIP
#                     }
#                 }
                
#                 # Simplified exercise logic for API mode
#                 for side, joints in arm_sides.items():
#                     shoulder = [
#                         landmarks[joints['shoulder'].value].x,
#                         landmarks[joints['shoulder'].value].y,
#                     ]
#                     elbow = [
#                         landmarks[joints['elbow'].value].x,
#                         landmarks[joints['elbow'].value].y,
#                     ]
#                     wrist = [
#                         landmarks[joints['wrist'].value].x,
#                         landmarks[joints['wrist'].value].y,
#                     ]
                    
#                     # Calculate elbow angle
#                     elbow_angle = calculate_angle(shoulder, elbow, wrist)
                    
#                     # Display angle on frame
#                     cv2.putText(
#                         image,
#                         f'{int(elbow_angle)}',
#                         tuple(np.multiply(elbow, [image.shape[1], image.shape[0]]).astype(int)),
#                         cv2.FONT_HERSHEY_SIMPLEX,
#                         0.5,
#                         (255, 255, 255),
#                         2,
#                         cv2.LINE_AA
#                     )
                    
#                     # Exercise specific logic - basic version
#                     if exercise_id == 'hummer':
#                         if side == 'left':
#                             if elbow_angle > 160:
#                                 left_state = 'down'
#                             if elbow_angle < 30 and left_state == 'down':
#                                 left_state = 'up'
#                                 left_counter += 1
#                                 form_feedback = "جيد! استمر"
                        
#                         if side == 'right':
#                             if elbow_angle > 160:
#                                 right_state = 'down'
#                             if elbow_angle < 30 and right_state == 'down':
#                                 right_state = 'up'
#                                 right_counter += 1
#                                 form_feedback = "ممتاز! استمر"
                
#                 # Display counters on frame
#                 cv2.putText(image, f'Left: {left_counter}', (10, 50), 
#                          cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
#                 cv2.putText(image, f'Right: {right_counter}', (10, 100), 
#                          cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
                
#                 # Display FPS
#                 cv2.putText(image, f'FPS: {int(fps)}', (10, image.shape[0] - 20), 
#                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                
#                 # Update session counters
#                 active_sessions[session_id]['left_counter'] = left_counter
#                 active_sessions[session_id]['right_counter'] = right_counter
            
#             # Convert frame to base64 for API transmission
#             # Use higher compression for API
#             encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 65]
#             ret, buffer = cv2.imencode('.jpg', image, encode_param)
#             frame_data = base64.b64encode(buffer).decode('utf-8')
            
#             # Store frame data
#             frame_info = {
#                 'frame': frame_data,
#                 'feedback': form_feedback,
#                 'fps': int(fps),
#                 'timestamp': time.time()
#             }
            
#             # Add to frames list, keeping only the last MAX_STORED_FRAMES
#             active_sessions[session_id]['frames'].append(frame_info)
#             if len(active_sessions[session_id]['frames']) > MAX_STORED_FRAMES:
#                 active_sessions[session_id]['frames'] = active_sessions[session_id]['frames'][-MAX_STORED_FRAMES:]
            
#             # Longer delay for API mode to reduce server load
#             time.sleep(0.1)  # ~10 fps
        
#         # Clean up camera when done
#         if cap.isOpened():
#             cap.release()
        
#         print(f"API exercise processing stopped for session {session_id}")
        
#     except Exception as e:
#         print(f"Error in process_exercise_frames_api: {str(e)}")
#         traceback.print_exc()
#         active_sessions[session_id]['error'] = str(e)
        
#         # Cleanup
#         if 'cap' in active_sessions[session_id] and active_sessions[session_id]['cap'] is not None:
#             active_sessions[session_id]['cap'].release()

# def cleanup_sessions():
#     """
#     Periodically clean up inactive sessions
#     """
#     while True:
#         try:
#             current_time = time.time()
#             sessions_to_remove = []
            
#             for session_id, session_data in active_sessions.items():
#                 # Check for API sessions that haven't been accessed in a while
#                 if session_id.startswith('api_') and 'last_access' in session_data:
#                     if current_time - session_data['last_access'] > 60:  # 60 seconds timeout
#                         sessions_to_remove.append(session_id)
#                         if 'stop_event' in session_data:
#                             session_data['stop_event'].set()
#                         if 'cap' in session_data and session_data['cap'] is not None:
#                             session_data['cap'].release()
            
#             # Remove inactive sessions
#             for session_id in sessions_to_remove:
#                 del active_sessions[session_id]
#                 print(f"Cleaned up inactive session: {session_id}")
                
#         except Exception as e:
#             print(f"Error in cleanup task: {str(e)}")
            
#         # Sleep for 10 seconds before next cleanup
#         time.sleep(10)

# # Route for mobile-optimized view
# @app.route('/mobile/<exercise>')
# def mobile_exercise(exercise):
#     """
#     Mobile-optimized endpoint for exercise viewing
#     """
#     valid_exercises = get_valid_exercises()
    
#     if exercise not in valid_exercises:
#         app.logger.error(f"Invalid exercise requested: {exercise}")
#         return "Exercise not found", 404
        
#     return render_template('direct_video_fast.html', exercise_id=exercise)

# # Route for debug view
# @app.route('/debug/<exercise>')
# def debug_exercise(exercise):
#     """
#     Debug endpoint for exercise viewing
#     """
#     valid_exercises = get_valid_exercises()
    
#     if exercise not in valid_exercises:
#         app.logger.error(f"Invalid exercise requested: {exercise}")
#         return "Exercise not found", 404
        
#     return render_template('direct_video_debug.html', exercise_id=exercise)

# # Health monitoring endpoints
# @app.route('/health')
# def health_check():
#     """
#     Health check endpoint for monitoring
#     """
#     # Get basic application health metrics
#     memory_usage = os.popen('ps -o rss= -p %d' % os.getpid()).read()
#     if memory_usage:
#         memory_usage = int(memory_usage.strip()) / 1024  # Convert to MB
#     else:
#         memory_usage = "Unknown"
    
#     # Count active sessions
#     active_count = len(active_sessions)
    
#     return jsonify({
#         "status": "healthy",
#         "timestamp": time.time(),
#         "uptime": time.time() - app.config.get('START_TIME', time.time()),
#         "active_sessions": active_count,
#         "memory_usage_mb": memory_usage
#     })

# # Simplified lightweight endpoint for mobile clients
# @app.route('/api/exercise_simple/<exercise>', methods=['GET'])
# def simple_exercise_stream(exercise):
#     """
#     Returns a simple MJPEG stream with minimal overhead for low-bandwidth clients
#     """
#     try:
#         if exercise in exercise_map:
#             # Use a generator with lower quality frames
#             def generate_low_quality_frames():
#                 cap = cv2.VideoCapture(0)
                
#                 # Configure for lower quality
#                 cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
#                 cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                
#                 if not cap.isOpened():
#                     yield (b'--frame\r\n'
#                            b'Content-Type: text/plain\r\n\r\n'
#                            b'Camera not available\r\n')
#                     return
                
#                 try:
#                     while True:
#                         ret, frame = cap.read()
#                         if not ret:
#                             break
                            
#                         # Skip frames for performance
#                         for _ in range(2):
#                             cap.read()
                            
#                         # Resize to even smaller for bandwidth reduction
#                         frame = cv2.resize(frame, (320, 240))
                        
#                         # Lower quality JPEG
#                         encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 40]
#                         ret, buffer = cv2.imencode('.jpg', frame, encode_param)
#                         frame_data = buffer.tobytes()
                        
#                         yield (b'--frame\r\n'
#                                b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
#                 finally:
#                     cap.release()
            
#             # Return the stream with cache control headers
#             return Response(
#                 generate_low_quality_frames(), 
#                 mimetype='multipart/x-mixed-replace; boundary=frame',
#                 headers={
#                     'Cache-Control': 'no-cache, no-store, must-revalidate',
#                     'Pragma': 'no-cache',
#                     'Expires': '0'
#                 }
#             )
#         else:
#             return "Invalid exercise", 400
#     except Exception as e:
#         app.logger.error(f"Error in simple_exercise_stream: {str(e)}")
#         app.logger.error(traceback.format_exc())
#         return "Error processing video", 500

# if __name__ == '__main__':
#     # Initialize mediapipe
#     try:
#         import mediapipe as mp
#         print(f"Mediapipe loaded successfully")
        
#         # Initialize pose
#         mp_drawing = mp.solutions.drawing_utils
#         mp_pose = mp.solutions.pose
#         pose = mp_pose.Pose(
#             min_detection_confidence=0.5,
#             min_tracking_confidence=0.5,
#             model_complexity=1  # Medium complexity for balance between performance and accuracy
#         )
#         print("Pose model initialized successfully")
#     except Exception as e:
#         print(f"Error initializing libraries: {e}")
    
#     # Start cleanup thread
#     cleanup_thread = threading.Thread(target=cleanup_sessions)
#     cleanup_thread.daemon = True
#     cleanup_thread.start()
    
#     # Set start time for uptime tracking
#     app.config['START_TIME'] = time.time()
    
#     # Get port from environment variable or use default
#     port = int(os.environ.get('PORT', 8080))
    
#     # Print startup information
#     print(f"Starting AI Fitness Trainer on port {port}")
#     print(f"Available exercises: {', '.join(get_valid_exercises())}")
    
#     # Run the application
#     socketio.run(app, host='0.0.0.0', port=port)