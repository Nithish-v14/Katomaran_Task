# app.py
import streamlit as st
import cv2
import face_recognition
import numpy as np
import sqlite3
import datetime
from PIL import Image
from io import BytesIO
import os
import subprocess

# Ensure the database folder exists
os.makedirs('database', exist_ok=True)

# DB setup
conn = sqlite3.connect('database/faces.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS faces
                  (name TEXT, encoding BLOB, timestamp TEXT)''')
conn.commit()

def save_face_to_db(name, encoding):
    timestamp = datetime.datetime.now().isoformat()
    encoding_blob = encoding.tobytes()
    cursor.execute("INSERT INTO faces (name, encoding, timestamp) VALUES (?, ?, ?)",
                   (name, encoding_blob, timestamp))
    conn.commit()

def load_known_faces():
    cursor.execute("SELECT name, encoding FROM faces")
    records = cursor.fetchall()
    known_names = []
    known_encodings = []
    for name, encoding_blob in records:
        encoding = np.frombuffer(encoding_blob, dtype=np.float64)
        known_names.append(name)
        known_encodings.append(encoding)
    return known_names, known_encodings

def capture_face(name):
    cap = cv2.VideoCapture(0)
    stframe = st.empty()
    captured = False

    while not captured:
        ret, frame = cap.read()
        if not ret:
            break
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)

        for top, right, bottom, left in face_locations:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

        stframe.image(frame, channels="BGR")

        if face_locations:
            face_encoding = face_recognition.face_encodings(rgb_frame, face_locations)[0]
            save_face_to_db(name, face_encoding)
            st.success(f"Face registered for {name}")
            captured = True

    cap.release()

def recognize_faces():
    known_names, known_encodings = load_known_faces()
    cap = cv2.VideoCapture(0)
    stframe = st.empty()
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            matches = face_recognition.compare_faces(known_encodings, face_encoding)
            name = "Unknown"
            if True in matches:
                match_index = matches.index(True)
                name = known_names[match_index]
            cv2.rectangle(frame, (left, top), (right, bottom), (255, 0, 0), 2)
            cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

        stframe.image(frame, channels="BGR")

    cap.release()

def verify_and_launch_chatbot():
    known_names, known_encodings = load_known_faces()
    cap = cv2.VideoCapture(0)
    stframe = st.empty()
    verified_user = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            matches = face_recognition.compare_faces(known_encodings, face_encoding)
            name = "Unknown"
            if True in matches:
                match_index = matches.index(True)
                name = known_names[match_index]
                verified_user = name
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(frame, f"Verified: {name}", (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
                stframe.image(frame, channels="BGR")
                break

        stframe.image(frame, channels="BGR")
        if verified_user:
            st.success(f"✅ Verified as {verified_user}")
            cap.release()
            # Launch chatbot
            subprocess.Popen(["streamlit", "run", "qa.py"])
            break

    if not verified_user:
        st.warning("No known face detected.")

# ---------------- Streamlit App ---------------- #
st.title("👤 Face Recognition Platform")
tab1, tab2, tab3, tab4 = st.tabs(["Register Face", "Live Recognition", "View Registered Faces", "Access Chatbot"])

with tab1:
    st.subheader("Face Registration")
    name_input = st.text_input("Enter Name to Register")
    if st.button("Register Face") and name_input:
        capture_face(name_input)

with tab2:
    st.subheader("Live Face Recognition")
    if st.button("Start Recognition"):
        recognize_faces()

with tab3:
    st.subheader("👥 Registered Users in Database")
    cursor.execute("SELECT name, timestamp FROM faces")
    rows = cursor.fetchall()
    if rows:
        for i, (name, ts) in enumerate(rows, start=1):
            st.write(f"{i}. **{name}** registered at *{ts}*")
    else:
        st.info("No faces registered yet.")

with tab4:
    st.subheader("🔐 Verify Face to Access Chatbot")
    if st.button("Verify and Access Chatbot"):
        verify_and_launch_chatbot()
