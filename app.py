import os
import cv2
import numpy as np
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from ultralytics import YOLO
import supervision as sv
import threading
import time
from collections import Counter

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

model = YOLO("yolov8n.pt")
ZONE_POLYGON = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
UPLOAD_FOLDER = os.path.abspath('uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

webcam_running = False
webcam_count = 0
webcam_summary = {} 
lock = threading.Lock()
cap = None

def get_detections_summary(detections, model):
    
    detected_classes = []
    for class_id in detections.class_id:
        detected_classes.append(model.names[class_id])
    return dict(Counter(detected_classes))

def process_video_file(filepath):
    video_cap = cv2.VideoCapture(filepath)
    if not video_cap.isOpened(): return 0, {}
    
    h = int(video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    w = int(video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    
    zone_polygon = (ZONE_POLYGON * np.array([w, h])).astype(int)
    zone = sv.PolygonZone(polygon=zone_polygon)
    max_count = 0
    final_summary = Counter() 

    while True:
        ret, frame = video_cap.read()
        if not ret: break
        
        result = model(frame, verbose=False, imgsz=640)[0]
        detections = sv.Detections.from_ultralytics(result)
        zone.trigger(detections=detections)
        
        current_summary = Counter(get_detections_summary(detections, model))
        
        for key, value in current_summary.items():
             final_summary[key] = max(final_summary[key], value)

        max_count = max(max_count, zone.current_count)

    video_cap.release()
    return max_count, dict(final_summary)

def generate_frames():
    global webcam_running, webcam_count, webcam_summary, cap
    while webcam_running:
        if cap is None or not cap.isOpened():
            time.sleep(0.1)
            continue
        success, frame = cap.read()
        if not success:
            time.sleep(0.1)
            continue

        result = model(frame, verbose=False, imgsz=640)[0]
        detections = sv.Detections.from_ultralytics(result)
        h, w = frame.shape[:2]
        zone_polygon = (ZONE_POLYGON * np.array([w, h])).astype(int)
        zone = sv.PolygonZone(polygon=zone_polygon)
        zone.trigger(detections=detections)
        
        current_summary = get_detections_summary(detections, model)

        with lock:
            webcam_count = zone.current_count
            webcam_summary = current_summary

        box_annotator = sv.BoxAnnotator(thickness=2)
        zone_annotator = sv.PolygonZoneAnnotator(zone=zone, color=sv.Color.RED, thickness=2, text_scale=1)
        frame = box_annotator.annotate(scene=frame, detections=detections)
        frame = zone_annotator.annotate(scene=frame)

        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def home():
    return "Backend is Running!"

@app.route('/upload_video', methods=['POST'])
def upload_video():
    try:
        file = request.files['file']
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        count, summary = process_video_file(filepath)
        os.remove(filepath)
        return jsonify({'success': True, 'total_count': count, 'summary': summary})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/webcam_start')
def webcam_start():
    global webcam_running, cap
    if not webcam_running:
        if cap is not None: cap.release()
        cap = cv2.VideoCapture(0)
        time.sleep(1)
        if cap.isOpened():
            webcam_running = True
            return jsonify({'status': 'started'})
        return jsonify({'status': 'error'}), 500
    return jsonify({'status': 'already_running'})

@app.route('/webcam_stop')
def webcam_stop():
    global webcam_running, cap
    webcam_running = False
    if cap: cap.release()
    return jsonify({'status': 'stopped', 'final_count': webcam_count, 'final_summary': webcam_summary})

@app.route('/webcam_feed')
def webcam_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/current_data')
def current_data():
    with lock: return jsonify({'count': webcam_count, 'summary': webcam_summary})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)