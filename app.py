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
from concurrent.futures import ThreadPoolExecutor

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

# Setup for async processing
executor = ThreadPoolExecutor()

# Dummy sound class to avoid file path issues
class DummySound:
    def play(self):
        pass
    def stop(self):
        pass

# Use dummy sound instead of loading from a specific path
sound = DummySound()

# Ensure audio directory exists
os.makedirs("audio", exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/video_feed/<exercise>')
def video_feed(exercise):
    try:
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
        
        if exercise in exercise_map:
            return Response(exercise_map[exercise](sound), 
                            mimetype='multipart/x-mixed-replace; boundary=frame')
        else:
            return "Invalid exercise", 400
    except Exception as e:
        app.logger.error(f"Error in video_feed: {str(e)}")
        app.logger.error(traceback.format_exc())
        return "Error processing video", 500

@app.route('/api/rtc_offer', methods=['POST'])
def rtc_offer():
    try:
        data = request.json
        app.logger.info(f"Received WebRTC offer for exercise: {data.get('exercise', 'unknown')}")
        
        # Use ThreadPoolExecutor to handle async processing
        future = executor.submit(asyncio.run, process_offer(data))
        response = future.result()
        
        return jsonify(response)
    except Exception as e:
        app.logger.error(f"Error in rtc_offer: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/exercises', methods=['GET'])
def get_exercises():
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

@app.route('/exercise/<exercise>')
def direct_exercise(exercise):
    valid_exercises = [
        "hummer", "front_raise", "squat", "triceps", "lunges", 
        "shoulder_press", "plank", "side_lateral_raise", 
        "triceps_kickback_side", "push_ups"
    ]
    
    if exercise not in valid_exercises:
        app.logger.error(f"Invalid exercise requested: {exercise}")
        return "Exercise not found", 404
        
    return render_template('direct_exercise.html', exercise_id=exercise)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)