import streamlit as st
from datetime import date
import uuid
import sqlite3
import hashlib

# ---------------------- Database Setup ----------------------
def get_connection():
    return sqlite3.connect("child_health.db", check_same_thread=False)

def create_tables():
    conn = get_connection()
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
            FOREIGN KEY(app_number) REFERENCES child_details(app_number)
        )
    """)
    conn.commit()

create_tables()

# ---------------------- Session State ----------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "app_number" not in st.session_state:
    st.session_state.app_number = ""

# ---------------------- Password Helper ----------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT password, role FROM users WHERE username=?", (username,))
    row = c.fetchone()
    if row and row[0] == hash_password(password):
        return True, row[1]
    return False, None

# ---------------------- Logout ----------------------
def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.app_number = ""
    st.experimental_rerun()

# ---------------------- App ----------------------
st.title("Child Health Tracker")

# ---------- Login / Register ----------
if not st.session_state.logged_in:
    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        st.subheader("Login")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        role = st.selectbox("Role", ["Doctor", "Patient"])
        if st.button("Login"):
            success, db_role = verify_login(username, password)
            if success and db_role == role:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = db_role
                st.success(f"Logged in as {db_role}: {username}")
                st.experimental_rerun()
            else:
                st.error("Invalid credentials or role mismatch")

    with register_tab:
        st.subheader("Register")
        reg_username = st.text_input("Username", key="reg_user")
        reg_password = st.text_input("Password", type="password", key="reg_pass")
        reg_role = st.selectbox("Role", ["Doctor", "Patient"], key="reg_role")
        if st.button("Register"):
            if reg_username and reg_password:
                conn = get_connection()
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)",
                              (reg_username, hash_password(reg_password), reg_role))
                    conn.commit()
                    st.success(f"{reg_role} registered successfully!")
                except sqlite3.IntegrityError:
                    st.error("Username already exists")

# ---------- Main Panel ----------
else:
    st.info(f"Logged in as {st.session_state.role}: {st.session_state.username}")
    if st.button("Logout"):
        logout()

    conn = get_connection()
    c = conn.cursor()

    # ---------------------- Doctor Panel ----------------------
    if st.session_state.role == "Doctor":
        st.subheader("Doctor Panel")
        app_number_input = st.text_input("Enter Application Number", value=st.session_state.app_number)
        new_app_btn = st.button("New Application Number")

        # Generate new application number
        if new_app_btn:
            app_number_input = str(uuid.uuid4())[:8]
            st.session_state.app_number = app_number_input
            st.success(f"New Application Number: {app_number_input}")

        if app_number_input:
            st.session_state.app_number = app_number_input

            # Fetch child details
            c.execute("SELECT * FROM child_details WHERE app_number=?", (app_number_input,))
            child = c.fetchone()

            if child:
                st.subheader("Child Details (Editable)")
                col1, col2 = st.columns(2)
                with col1:
                    child_name = st.text_input("Child Name", value=child[1])
                    birth_place = st.text_input("Birth Place", value=child[2])
                with col2:
                    birth_date = st.date_input("DOB", value=date.fromisoformat(child[3]))
                    last_tracked = st.date_input("Last Tracked", value=date.fromisoformat(child[7]))
                col3, col4 = st.columns(2)
                with col3:
                    weight = st.number_input("Weight (kg)", value=child[4])
                with col4:
                    height = st.number_input("Height (cm)", value=child[5])
                    pulse = st.number_input("Pulse", value=child[6])

                if st.button("Save Child Details"):
                    c.execute("""
                        INSERT OR REPLACE INTO child_details (app_number, name, birth_place, birth_date, weight, height, pulse, last_tracked)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, (app_number_input, child_name, birth_place, str(birth_date), weight, height, pulse, str(last_tracked)))
                    conn.commit()
                    st.success("Child details updated successfully!")

                if st.button("Delete Patient Record"):
                    confirm = st.checkbox("Confirm deletion? This will remove ALL data.", key="confirm_delete")
                    if confirm:
                        c.execute("DELETE FROM medical_history WHERE app_number=?", (app_number_input,))
                        c.execute("DELETE FROM vaccinations WHERE app_number=?", (app_number_input,))
                        c.execute("DELETE FROM child_details WHERE app_number=?", (app_number_input,))
                        conn.commit()
                        st.success(f"Patient {app_number_input} deleted!")
                        st.session_state.app_number = str(uuid.uuid4())[:8]
                        st.experimental_rerun()

            else:
                st.info("No record found. Enter new child details below.")
                col1, col2 = st.columns(2)
                with col1:
                    child_name = st.text_input("Child Name", key="new_child_name")
                    birth_place = st.text_input("Birth Place", key="new_birth_place")
                with col2:
                    birth_date = st.date_input("DOB", min_value=date(2018,1,1), max_value=date.today(), key="new_birth_date")
                    last_tracked = st.date_input("Last Tracked", value=date.today(), key="new_last_tracked")
                col3, col4 = st.columns(2)
                with col3:
                    weight = st.number_input("Weight (kg)", min_value=0.0, max_value=50.0, step=0.1, key="new_weight")
                with col4:
                    height = st.number_input("Height (cm)", min_value=30, max_value=150, step=1, key="new_height")
                    pulse = st.number_input("Pulse", min_value=50, max_value=200, step=1, key="new_pulse")

                if st.button("Save New Child"):
                    c.execute("""
                        INSERT INTO child_details (app_number, name, birth_place, birth_date, weight, height, pulse, last_tracked)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, (app_number_input, child_name, birth_place, str(birth_date), weight, height, pulse, str(last_tracked)))
                    conn.commit()
                    st.success("New child record created successfully!")

    # ---------------------- Patient Panel ----------------------
    elif st.session_state.role == "Patient":
        st.subheader("Patient Panel")
        st.write("You can view your child details here (Read-only).")
        c.execute("SELECT * FROM child_details")
        children = c.fetchall()
        for child in children:
            st.markdown(f"**Application Number:** {child[0]}")
            st.write(f"Name: {child[1]}")
            st.write(f"Birth Place: {child[2]}")
            st.write(f"DOB: {child[3]}")
            st.write(f"Weight: {child[4]} kg, Height: {child[5]} cm, Pulse: {child[6]}, Last Tracked: {child[7]}")
