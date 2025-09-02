import streamlit as st
from datetime import date
import uuid
import sqlite3
import hashlib

# --- Database helper functions ---
def get_connection():
    return sqlite3.connect("child_health.db")

def create_tables():
    with get_connection() as conn:
        c = conn.cursor()
        # Users table
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT,
                role TEXT
            )
        """)
        # Child details table
        c.execute("""
            CREATE TABLE IF NOT EXISTS child_details (
                app_number TEXT PRIMARY KEY,
                name TEXT,
                birth_place TEXT,
                birth_date TEXT,
                weight REAL,
                height REAL,
                pulse INTEGER,
                last_tracked TEXT
            )
        """)
        # Medical history table
        c.execute("""
            CREATE TABLE IF NOT EXISTS medical_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_number TEXT,
                visit_date TEXT,
                hospital TEXT,
                doctor TEXT,
                specialization TEXT,
                reason TEXT,
                medications TEXT,
                wrong_record INTEGER DEFAULT 0,
                FOREIGN KEY(app_number) REFERENCES child_details(app_number)
            )
        """)
        # Vaccinations table
        c.execute("""
            CREATE TABLE IF NOT EXISTS vaccinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_number TEXT,
                vaccine_name TEXT,
                date TEXT,
                barcode TEXT,
                UNIQUE(app_number, vaccine_name),
                FOREIGN KEY(app_number) REFERENCES child_details(app_number)
            )
        """)
        conn.commit()

create_tables()

# --- Session State ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = ""
if "username" not in st.session_state:
    st.session_state.username = ""
if "app_number" not in st.session_state:
    st.session_state.app_number = ""

# --- Helper functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(username, password):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT password, role FROM users WHERE username=?", (username,))
        row = c.fetchone()
        if row and row[0] == hash_password(password):
            return True, row[1]
        return False, None

# --- Login/Register Tabs ---
st.title("Child Health Tracker")

tab1, tab2 = st.tabs(["Login", "Register"])

with tab1:
    st.subheader("Login")
    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")
    login_role = st.selectbox("Role", ["Doctor", "Patient"], key="login_role")
    if st.button("Login"):
        success, role = verify_login(username, password)
        if success and role == login_role:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = role
            st.success(f"Logged in as {role}: {username}")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials or role mismatch")

with tab2:
    st.subheader("Register")
    reg_username = st.text_input("Username", key="reg_user")
    reg_password = st.text_input("Password", type="password", key="reg_pass")
    reg_role = st.selectbox("Role", ["Doctor", "Patient"], key="reg_role")
    if st.button("Register"):
        if reg_username and reg_password:
            with get_connection() as conn:
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)",
                              (reg_username, hash_password(reg_password), reg_role))
                    conn.commit()
                    st.success(f"{reg_role} registered successfully!")
                except sqlite3.IntegrityError:
                    st.error("Username already exists")

# --- After login ---
if st.session_state.logged_in:
    st.info(f"Logged in as {st.session_state.role}: {st.session_state.username}")

    if st.session_state.role == "Patient":
        st.subheader("Patient Panel")
        st.write("Your child health records will be displayed here...")
        # Here you can show Patient-specific views (child details, medical history, vaccinations)

    elif st.session_state.role == "Doctor":
        st.subheader("Doctor Panel")
        app_number_input = st.text_input("Enter Application Number")
        new_record_button = st.button("New Application Number")
        if new_record_button:
            app_number_input = str(uuid.uuid4())[:8]
            st.success(f"New Application Number generated: {app_number_input}")

        if app_number_input:
            st.session_state.app_number = app_number_input
            with get_connection() as conn:
                c = conn.cursor()
                # Load child details
                c.execute("SELECT * FROM child_details WHERE app_number=?", (app_number_input,))
                child = c.fetchone()
                if child:
                    st.write(f"Child Name: {child[1]}, DOB: {child[3]}")
                else:
                    st.info("No record found. Enter new details below.")
                    # Here you can add new child details input forms for Doctor

