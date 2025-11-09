import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv


SOURCE = "000.mp4"  


ZONE_POLYGON = np.array([
    [0, 0],
    [1, 0],
    [1, 1],
    [0, 1]
])

def main():
  
    cap = cv2.VideoCapture("000.mp4")

    
    ret, frame = cap.read()
    if not ret:
        print(f"Error: Cannot read from source: {"000.mp4"}")
        return
    
    frame_height, frame_width = frame.shape[:2]
    
    model = YOLO("yolov8n.pt")

    
    box_annotator = sv.BoxAnnotator(thickness=2)
    label_annotator = sv.LabelAnnotator(text_thickness=2, text_scale=1)

   
    zone_polygon = (ZONE_POLYGON * np.array([frame_width, frame_height])).astype(int)
    zone = sv.PolygonZone(polygon=zone_polygon)
    zone_annotator = sv.PolygonZoneAnnotator(
        zone=zone,
        color=sv.Color.RED,
        thickness=2,
        text_thickness=4,
        text_scale=2
    )

    while True:
        ret, frame = cap.read()
        if not ret:
            break

    
        result = model(frame)[0]
        detections = sv.Detections.from_ultralytics(result)
        
        zone.trigger(detections=detections)

        labels = [
            f"{model.names[class_id]} {confidence:0.2f}"
            for class_id, confidence
            in zip(detections.class_id, detections.confidence)
        ]

        frame = box_annotator.annotate(scene=frame, detections=detections)
        frame = label_annotator.annotate(scene=frame, detections=detections, labels=labels)
        frame = zone_annotator.annotate(scene=frame)

        cv2.imshow('yolov8', frame)

        if cv2.waitKey(1) == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()