import io
import logging
import time
import socketserver
import os
import json
from threading import Condition
from http import server
from datetime import datetime
import urllib.parse
import pickle
import paho.mqtt.client as mqtt
import face_recognition
import cv2
import numpy as np
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
import firebase_admin
from firebase_admin import credentials, messaging, db
from imutils import paths

# Firebase initialization
cred = credentials.Certificate("smartdoorbell-14d0d-firebase-adminsdk-56098-8c3498ce73.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://smartdoorbell-14d0d-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

def get_password():
    try:
        ref = db.reference("password")
        
        password = ref.get()
        
        return password
        
    except Exception as e:
        print(f"Error retrieving password: {str(e)}")
        return None

# MQTT Settings
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_MOTION = "doorbell/motion" #when motion is detected, from esp32
#MQTT_TOPIC_RECOGNITION = "doorbell/recognition" 
MQTT_TOPIC_UNLOCK = "doorbell/unlock" #unlock the door relay, to esp32
MQTT_TOPIC_LOCK = "doorbell/lock" #lock the door relay, to esp32
MQTT_TOPIC_PASSWORD = "doorbell/password" #check password, from esp32
MQTT_TOPIC_RING = "doorbell/ring" #ring the doorbell, from esp32

# Store FCM tokens
fcm_tokens = set()

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

class FaceRecognitionSystem:
    def __init__(self):
        print("[INFO] Loading facial recognition encodings...")
        self.data = pickle.loads(open("encodings.pickle", "rb").read())
        self.known_face_encodings = self.data["encodings"]
        self.known_face_names = self.data["names"]
        
    def process_frame(self, frame):
        nparr = np.frombuffer(frame, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        rgb_frame = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        
        recognized_names = []
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
            name = "Unknown"
            
            if True in matches:
                matched_idxs = [i for i, b in enumerate(matches) if b]
                counts = {}
                
                for i in matched_idxs:
                    name = self.known_face_names[i]
                    counts[name] = counts.get(name, 0) + 1
                
                name = max(counts, key=counts.get)
            
            recognized_names.append(name)
            
        return recognized_names

def send_fcm_notification(title, body, data=None):
    if not fcm_tokens:
        print("No FCM tokens registered")
        return

    # Send to each token individually instead of using multicast
    for token in fcm_tokens:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data if data else {},
            token=token,  # Single token instead of token list
            android=messaging.AndroidConfig(
                priority='high'
            )
        )

        try:
            # Send to individual token
            response = messaging.send(message)
            print(f'Successfully sent message to {token[:20]}...: {response}')
        except messaging.ApiCallError as e:
            print(f"Error sending to token {token[:20]}...: {e.code} - {e.message}")
            # Remove invalid tokens
            if e.code in ['registration-token-not-registered', 'invalid-argument']:
                fcm_tokens.discard(token)
        except Exception as e:
            print(f"Unexpected error sending to token {token[:20]}...: {str(e)}")

class StreamingHandler(server.BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.face_recognizer = FaceRecognitionSystem()
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        if self.path == '/token':
            try:
                data = json.loads(post_data.decode('utf-8'))
                token = data.get('token')
                if token:
                    print(f"Registering new FCM token: {token[:20]}...")
                    fcm_tokens.add(token)              
                    print("Start")
                    time.sleep(7)  # Delay for 5 seconds
                    print("End")
                    # Test notification
                    try:
                        test_message = messaging.Message(
                            notification=messaging.Notification(
                                title="Smart Doorbell Connected",
                                body="Your device is now registered for notifications"
                            ),
                            token=token,
                            android=messaging.AndroidConfig(
                                priority='high'
                            )
                        )
                        response = messaging.send(test_message)
                        print(f"Test notification sent successfully: {response}")
                    except Exception as e:
                        print(f"Error sending test notification: {e}")
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = json.dumps({"message": "Token registered successfully"})
                    self.wfile.write(response.encode())
                else:
                    self.send_error(400, "Token not provided")
            except Exception as e:
                self.send_error(500, f"Error registering token: {str(e)}")

        elif self.path == '/capture':
            try:
                json_data = json.loads(post_data.decode('utf-8'))
                name = json_data.get('name', 'unknown')
                name = ''.join(char for char in name.lower() if char.isalnum())
                
                dataset_folder = "dataset"
                if not os.path.exists(dataset_folder):
                    os.makedirs(dataset_folder)
                
                person_folder = os.path.join(dataset_folder, name)
                if not os.path.exists(person_folder):
                    os.makedirs(person_folder)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{name}_{timestamp}.jpg"
                filepath = os.path.join(person_folder, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(output.frame)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = json.dumps({"message": "Image saved", "filename": filename})
                self.wfile.write(response.encode())
            
            except Exception as e:
                self.send_error(500, f"Error capturing image: {str(e)}")

        elif self.path == '/unlock':
            try:
                mqtt_client.publish(MQTT_TOPIC_UNLOCK, "unlock")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = json.dumps({"message": "Unlock command sent"})
                self.wfile.write(response.encode())
            
            except Exception as e:
                self.send_error(500, f"Error sending unlock command: {str(e)}")

        elif self.path == '/lock':
            try:
                mqtt_client.publish(MQTT_TOPIC_LOCK, "lock")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = json.dumps({"message": "Lock command sent"})
                self.wfile.write(response.encode())
            
            except Exception as e:
                self.send_error(500, f"Error sending lock command: {str(e)}")

        elif self.path == '/train':
            try:
                dataset_folder = "dataset"
                if not os.path.exists(dataset_folder):
                    self.send_error(400, "No dataset folder found")
                    return

                imagePaths = list(paths.list_images(dataset_folder))
                knownEncodings = []
                knownNames = []

                print("HERE")

                for imagePath in imagePaths:
                    name = imagePath.split(os.path.sep)[-2]
                    image = cv2.imread(imagePath)
                    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    
                    boxes = face_recognition.face_locations(rgb, model="hog")
                    encodings = face_recognition.face_encodings(rgb, boxes)
                    
                    for encoding in encodings:
                        knownEncodings.append(encoding)
                        knownNames.append(name)

                data = {"encodings": knownEncodings, "names": knownNames}
                with open("encodings.pickle", "wb") as f:
                    f.write(pickle.dumps(data))

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = json.dumps({
                    "message": "Training complete",
                    "total_faces": len(knownEncodings),
                    "unique_persons": len(set(knownNames))
                })
                self.wfile.write(response.encode())

            except Exception as e:
                self.send_error(500, f"Training failed: {str(e)}")

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

def on_mqtt_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    client.subscribe(MQTT_TOPIC_MOTION)
    client.subscribe(MQTT_TOPIC_PASSWORD)
    client.subscribe(MQTT_TOPIC_RING)

def on_mqtt_message(client, userdata, msg):
    if msg.topic == MQTT_TOPIC_MOTION:
        print("Motion detected! Processing face recognition...")
        with output.condition:
            frame = output.frame
            if frame is not None:
                face_recognizer = FaceRecognitionSystem()
                recognized_names = face_recognizer.process_frame(frame)
                
                if recognized_names:
                    known_people = [name for name in recognized_names if name != "Unknown"]
                    if known_people:
                        result = {"status": "known", "names": known_people}
                        # Send FCM notification for known person
                        mqtt_client.publish(MQTT_TOPIC_UNLOCK, json.dumps(result))
                        send_fcm_notification(
                            "Known Person Detected",
                            f"Welcome {', '.join(known_people)}!",
                            {
                                "type": "known_person",
                                "names": json.dumps(known_people),
                                "timestamp": str(datetime.now())
                            }
                        )
                    else:
                        result = {"status": "unknown"}
                        # Send FCM notification for unknown person
                        send_fcm_notification(
                            "Unknown Person Detected",
                            "Someone is at your door",
                            {
                                "type": "unknown_person",
                                "timestamp": str(datetime.now())
                            }
                        )
                else:
                    result = {"status": "no_face_detected"}
                
                #mqtt_client.publish(MQTT_TOPIC_RECOGNITION, json.dumps(result))
    elif msg.topic == MQTT_TOPIC_PASSWORD:
        print("Password detected! Processing password recognition...")
        password = msg.payload.decode("utf-8")
        #get password from firebase realtime database and store it in cloudPass
        cloudPass = get_password()
        if password == cloudPass:
            print("Password is correct! Unlocking door...")
            mqtt_client.publish(MQTT_TOPIC_UNLOCK, "unlock")
            send_fcm_notification(
                "Door Unlocked",
                "Door has been unlocked with password",
                {
                    "type": "password_unlock",
                    "timestamp": str(datetime.now())
                }
            )
        else:
            print("Password is incorrect! Please try again...")
    elif msg.topic == MQTT_TOPIC_RING:
        print("Doorbell ring detected! Sending notification...")
        send_fcm_notification(
            "Doorbell Ring",
            "Someone is at your door",
            {
                "type": "doorbell_ring",
                "timestamp": str(datetime.now())
            }
        )

# Initialize MQTT client
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message

# Connect to MQTT broker
try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
except Exception as e:
    print(f"Failed to connect to MQTT broker: {e}")

# Initialize the camera
picam2 = Picamera2()
video_config = picam2.create_video_configuration(main={"size": (640, 480)})
picam2.configure(video_config)
output = StreamingOutput()
encoder = JpegEncoder(q=70)
file_output = FileOutput(output)

# Start the camera
picam2.start_recording(encoder, file_output)


try:
    address = ('', 8000)
    server = StreamingServer(address, StreamingHandler)
    print("Server running on http://localhost:8000")
    server.serve_forever()
finally:
    picam2.stop_recording()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()