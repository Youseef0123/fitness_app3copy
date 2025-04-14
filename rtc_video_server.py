import json
import cv2
import asyncio
import threading
import numpy as np
import mediapipe as mp
from utils import calculate_angle, mp_pose, pose

# Dictionary to store active video processors
video_processors = {}

# Function to process WebRTC offer and setup connection
async def process_offer(offer_data):
    sdp = offer_data.get('sdp')
    video_type = offer_data.get('exercise', 'default')
    
    # Create a proper WebRTC answer
    # Note: In a real WebRTC implementation, we would process the offer SDP
    # and create a real answer. This is a simplified version.
    response = {
        'sdp': {
            'type': 'answer',
            'sdp': sdp.get('sdp')  # Properly extract SDP from the offer
        },
        'ice_candidates': [
            # Example ICE candidates - in real implementation these would be dynamic
            {'candidate': 'candidate:1 1 UDP 2130706431 192.168.1.1 8888 typ host', 'sdpMLineIndex': 0}
        ]
    }
    
    # Start a new video processing thread for this connection
    if video_type not in video_processors:
        # Start appropriate video processor based on exercise type
        start_video_processor(video_type)
    
    return response

def start_video_processor(exercise_type):
    """
    Start a new thread to process video for the given exercise type
    
    Args:
        exercise_type: Type of exercise to track
    """
    processor_thread = threading.Thread(target=video_processor_worker, args=(exercise_type,))
    processor_thread.daemon = True
    processor_thread.start()
    video_processors[exercise_type] = processor_thread
    print(f"Started video processor for {exercise_type}")

def video_processor_worker(exercise_type):
    """
    Worker function that runs in a separate thread to process video
    
    Args:
        exercise_type: Type of exercise to track
    """
    # Initialize video capture
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print(f"Error: Could not open camera for {exercise_type}")
            return
    except Exception as e:
        print(f"Error opening camera: {str(e)}")
        return
    
    # Set up dummy pygame sound for the exercise functions
    # We won't actually play sounds in the cloud version
    class DummySound:
        def play(self):
            pass
            
        def stop(self):
            pass
    
    dummy_sound = DummySound()
    
    # Import exercise modules locally to avoid circular imports
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
    
    # Use a generator to process frames
    exercise_generator = None
    
    # Select the appropriate exercise generator
    try:
        if exercise_type == 'hummer':
            exercise_generator = hummer(dummy_sound)
        elif exercise_type == 'front_raise':
            exercise_generator = dumbbell_front_raise(dummy_sound)
        elif exercise_type == 'squat':
            exercise_generator = squat(dummy_sound)
        elif exercise_type == 'triceps':
            exercise_generator = triceps_extension(dummy_sound)
        elif exercise_type == 'lunges':
            exercise_generator = lunges(dummy_sound)
        elif exercise_type == 'shoulder_press':
            exercise_generator = shoulder_press(dummy_sound)
        elif exercise_type == 'plank':
            exercise_generator = plank(dummy_sound)
        elif exercise_type == 'side_lateral_raise':
            exercise_generator = side_lateral_raise(dummy_sound)
        elif exercise_type == 'triceps_kickback_side':
            exercise_generator = triceps_kickback_side(dummy_sound)
        elif exercise_type == 'push_ups':
            exercise_generator = push_ups(dummy_sound)
        else:
            print(f"Unknown exercise type: {exercise_type}")
            return
        
        print(f"Exercise generator for {exercise_type} created successfully")
    except Exception as e:
        print(f"Error creating exercise generator: {str(e)}")
        if cap.isOpened():
            cap.release()
        return
    
    try:
        # Process frames from the generator
        for frame_data in exercise_generator:
            # In a real implementation, we would send this frame over WebRTC
            # For now, we'll just print that we processed a frame
            print(f"Processed frame for {exercise_type}")
            
            # Add a small delay to avoid consuming too much CPU
            cv2.waitKey(30)
    except Exception as e:
        print(f"Error in video processor: {str(e)}")
    finally:
        # Clean up resources
        if cap.isOpened():
            cap.release()
        
        # Remove this processor from the active list
        if exercise_type in video_processors:
            del video_processors[exercise_type]
            
        print(f"Video processor for {exercise_type} stopped")

def get_frame_from_exercise(exercise_type):
    """
    Get the latest processed frame for a specific exercise
    
    Args:
        exercise_type: Type of exercise
        
    Returns:
        Latest processed frame or None if not available
    """
    # In a real implementation, this would retrieve the latest frame
    # For now it just returns None
    return None