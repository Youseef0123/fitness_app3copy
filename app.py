from flask import Flask, Response, render_template, request, jsonify, send_from_directory
import cv2
import os
import json
import pygame
import time
from gtts import gTTS
from flask_cors import CORS
import asyncio
import traceback
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

# Initialize pygame mixer
pygame.mixer.init()

# Define a dummy sound class that doesn't use actual file paths
class DummySound:
    def play(self):
        pass
        
    def stop(self):
        pass

# Use dummy sound instead of loading from a specific path
sound = DummySound()

# Create audio directory if it doesn't exist
os.makedirs("audio", exist_ok=True)

# Serve static files
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# Legacy video feed route (still kept for backward compatibility)
@app.route('/video_feed/<exercise>')
def video_feed(exercise):
    try:
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
    except Exception as e:
        app.logger.error(f"Error in video_feed: {str(e)}")
        app.logger.error(traceback.format_exc())
        return "Error processing video", 500

# WebRTC signaling endpoint
@app.route('/api/rtc_offer', methods=['POST'])
def rtc_offer():
    try:
        data = request.json
        app.logger.info(f"Received WebRTC offer for exercise: {data.get('exercise', 'unknown')}")
        
        # Process the offer asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(process_offer(data))
        loop.close()
        
        return jsonify(response)
    except Exception as e:
        app.logger.error(f"Error in rtc_offer: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/exercises', methods=['GET'])
def get_exercises():
    """Return the list of available exercises"""
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

@app.route('/api/pose_data')
def pose_data():
    # Get the pose data and return it as a JSON response
    # This is a placeholder - actual implementation would return real pose data
    try:
        data = {
            "status": "ok",
            "timestamp": time.time(),
            "message": "Pose data API is working"
        }
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Error in pose_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/camera_test')
def camera_test():
    return render_template('camera_test.html')


# أضف هذا المسار الجديد في ملف app.py

@app.route('/exercise/<exercise>')
def direct_exercise(exercise):
    """
    مسار لفتح صفحة تمرين محدد مباشرة
    
    Args:
        exercise: معرف التمرين
    
    Returns:
        صفحة HTML للتمرين
    """
    print(f"تم طلب صفحة تمرين مباشر: {exercise}")
    
    # التحقق من وجود التمرين
    valid_exercises = [
        "hummer", "front_raise", "squat", "triceps", "lunges", 
        "shoulder_press", "plank", "side_lateral_raise", 
        "triceps_kickback_side", "push_ups"
    ]
    
    if exercise not in valid_exercises:
        app.logger.error(f"تم طلب تمرين غير صالح: {exercise}")
        return "Exercise not found", 404
        
    # قم بتمرير معرف التمرين إلى قالب HTML
    return render_template('direct_exercise.html', exercise_id=exercise)





if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Enable debugging for development
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    # Start the server
    app.run(host='0.0.0.0', port=port, debug=debug_mode)