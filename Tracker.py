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
            st.rerun()
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
        # TODO: Display patient-specific records

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
                # Load existing child details
                c.execute("SELECT * FROM child_details WHERE app_number=?", (app_number_input,))
                child = c.fetchone()

                if child:
                    st.subheader("Child Details")
                    st.write(f"Name: {child[1]}")
                    st.write(f"Birth Place: {child[2]}")
                    st.write(f"DOB: {child[3]}")
                    st.write(f"Weight: {child[4]} kg, Height: {child[5]} cm, Pulse: {child[6]} bpm, Last Tracked: {child[7]}")
                else:
                    st.info("No record found. Enter new details below.")
                    # New child details input
                    col1, col2 = st.columns(2)
                    with col1:
                        child_name = st.text_input("Child Name", key="new_child_name")
                        birth_place = st.text_input("Birth Place", key="new_birth_place")
                    with col2:
                        birth_date = st.date_input("Date of Birth", min_value=date(2018,1,1), max_value=date.today(), key="new_birth_date")
                        last_tracked = st.date_input("Last Tracked On", value=date.today(), key="new_last_tracked")
                    col3, col4 = st.columns(2)
                    with col3:
                        weight = st.number_input("Weight (kg)", min_value=0.0, max_value=50.0, step=0.1, key="new_weight")
                    with col4:
                        height = st.number_input("Height (cm)", min_value=30, max_value=150, step=1, key="new_height")
                        pulse = st.number_input("Pulse (bpm)", min_value=50, max_value=200, step=1, key="new_pulse")

                    if st.button("Save Child Details"):
                        c.execute("""
                            INSERT INTO child_details (app_number, name, birth_place, birth_date, weight, height, pulse, last_tracked)
                            VALUES (?,?,?,?,?,?,?,?)
                        """, (app_number_input, child_name, birth_place, str(birth_date),
                              weight, height, pulse, str(last_tracked)))
                        conn.commit()
                        st.success("Child details saved successfully!")

            # --- Medical History Section ---
            st.subheader("Medical History")
            with st.form(key=f"history_form_{app_number_input}"):
                visit_date = st.date_input("Visit Date", value=date.today())
                hospital = st.text_input("Hospital Name")
                specialization = st.text_input("Doctor Specialization")
                reason = st.text_area("Reason for Visit")
                meds = st.text_area("Medications Prescribed")
                submitted = st.form_submit_button("Add to History")

                if submitted:
                    if visit_date and hospital and specialization and reason:
                        with get_connection() as conn:
                            c = conn.cursor()
                            c.execute("""
                                INSERT INTO medical_history (app_number, visit_date, hospital, doctor, specialization, reason, medications)
                                VALUES (?,?,?,?,?,?,?)
                            """, (app_number_input, str(visit_date), hospital, st.session_state.username,
                                  specialization, reason, meds))
                            conn.commit()
                            st.success("Medical history added!")

            # Display medical history
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT id, visit_date, hospital, doctor, specialization, reason, medications, wrong_record
                    FROM medical_history WHERE app_number=? ORDER BY visit_date
                """, (app_number_input,))
                histories = c.fetchall()
                for h in histories:
                    if h[7]:
                        st.warning(f"Record {h[0]} marked as WRONG")
                        continue
                    st.write({
                        "Visit Date": h[1],
                        "Hospital": h[2],
                        "Doctor": h[3],
                        "Specialization": h[4],
                        "Reason": h[5],
                        "Medications": h[6]
                    })

            # --- Vaccinations Section ---
            st.subheader("Vaccination Schedule")
            vaccines_by_year = {
                "At Birth": ["BCG", "Hepatitis B"],
                "6 Weeks": ["Polio 1", "DPT 1", "Hepatitis B 2"],
                "10 Weeks": ["Polio 2", "DPT 2", "Hepatitis B 3"],
                "14 Weeks": ["Polio 3", "DPT 3"],
                "9 Months": ["Measles 1"],
                "15 Months": ["MMR 1", "Varicella 1"],
                "18 Months": ["DPT Booster", "Polio Booster"],
                "4-5 Years": ["MMR 2", "Varicella 2"]
            }

            for year, vaccines in vaccines_by_year.items():
                st.markdown(f"**{year}**")
                for v in vaccines:
                    with get_connection() as conn:
                        c = conn.cursor()
                        c.execute("SELECT id FROM vaccinations WHERE app_number=? AND vaccine_name=?",
                                  (app_number_input, v))
                        completed = c.fetchone() is not None
                    done = st.checkbox(f"{v}", value=completed, key=f"{v}_{app_number_input}")
                    if done and not completed:
                        barcode = str(uuid.uuid4())[:8]
                        with get_connection() as conn:
                            c = conn.cursor()
                            c.execute("""
                                INSERT OR IGNORE INTO vaccinations (app_number, vaccine_name, date, barcode)
                                VALUES (?,?,?,?)
                            """, (app_number_input, v, str(date.today()), barcode))
                            conn.commit()
            # Display completed vaccinations
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT vaccine_name, date, barcode FROM vaccinations WHERE app_number=?",
                          (app_number_input,))
                vac_rows = c.fetchall()
                if vac_rows:
                    st.subheader("Completed Vaccinations")
                    st.table(vac_rows)

