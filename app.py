import cv2
import gradio as gr
import numpy as np
from ultralytics import YOLO
import tempfile
import os

# Load YOLOv8 face and plate detection models
face_model = YOLO("models/yolov8n-face.pt")
plate_model = YOLO("models/license_plate_detector.pt")

def pixelate(image, boxes, factor=10):
    for box in boxes:
        x1, y1, x2, y2 = map(int, box[:4])
        region = image[y1:y2, x1:x2]
        h, w = region.shape[:2]
        if h == 0 or w == 0:
            continue
        temp = cv2.resize(region, (factor, factor), interpolation=cv2.INTER_LINEAR)
        pixelated = cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)
        image[y1:y2, x1:x2] = pixelated
    return image

def detect_and_redact(img, redact_faces, redact_plates):
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    if redact_faces:
        face_results = face_model.predict(img, conf=0.3, verbose=False)
        face_boxes = face_results[0].boxes.xyxy.cpu().numpy() if face_results else []
        img = pixelate(img, face_boxes)

    if redact_plates:
        plate_results = plate_model.predict(img, conf=0.3, verbose=False)
        plate_boxes = plate_results[0].boxes.xyxy.cpu().numpy() if plate_results else []
        img = pixelate(img, plate_boxes)

    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

def process_image(input_image, mode):
    redact_faces = mode in ["Faces Only", "Both"]
    redact_plates = mode in ["Plates Only", "Both"]
    return detect_and_redact(input_image, redact_faces, redact_plates)

def process_video(video_file, mode):
    redact_faces = mode in ["Faces Only", "Both"]
    redact_plates = mode in ["Plates Only", "Both"]

    cap = cv2.VideoCapture(video_file)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Temporary output file
    temp_video = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    out = cv2.VideoWriter(temp_video.name, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        redacted = detect_and_redact(frame_rgb, redact_faces, redact_plates)
        out.write(cv2.cvtColor(redacted, cv2.COLOR_RGB2BGR))

    cap.release()
    out.release()
    return temp_video.name

# Gradio Interface
with gr.Blocks(title="Visual Privacy Filter") as demo:
    gr.Markdown("## 🔒 Visual Privacy Filter (Faces & License Plates)")
    gr.Markdown("Upload an image or video and choose what to redact.")

    mode = gr.Radio(
        choices=["Faces Only", "Plates Only", "Both"],
        value="Both",
        label="Redaction Mode"
    )

    with gr.Tabs():
        with gr.Tab("📷 Image"):
            img_input = gr.Image(type="numpy", label="Upload Image")
            img_output = gr.Image(type="numpy", label="Redacted Output")
            img_btn = gr.Button("Redact Image")
            img_btn.click(fn=process_image, inputs=[img_input, mode], outputs=img_output)

        with gr.Tab("🎥 Video"):
            vid_input = gr.Video(label="Upload Video")
            vid_output = gr.Video(label="Redacted Video")
            vid_btn = gr.Button("Redact Video")
            vid_btn.click(fn=process_video, inputs=[vid_input, mode], outputs=vid_output)

demo.launch()
