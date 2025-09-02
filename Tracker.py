import streamlit as st
from datetime import date
import uuid
import sqlite3
import hashlib

# --- Session State Initialization ---
if "app_number" not in st.session_state:
    st.session_state.app_number = ""
if "doctor_logged_in" not in st.session_state:
    st.session_state.doctor_logged_in = False
if "doctor_username" not in st.session_state:
    st.session_state.doctor_username = ""

# --- Database helper function ---
def get_connection():
    return sqlite3.connect("child_health.db")

# --- Create Tables ---
def create_tables():
    with get_connection() as conn:
        c = conn.cursor()
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
        # Doctor login table (optional)
        c.execute("""
            CREATE TABLE IF NOT EXISTS doctors (
                username TEXT PRIMARY KEY,
                password TEXT
            )
        """)
        conn.commit()

create_tables()

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["Child Details", "Medical History", "Vaccinations"])

# ------------------- TAB 1: Child Details -------------------
with tab1:
    st.header("Child Details")
    col1, col2 = st.columns(2)
    with col1:
        child_name = st.text_input("Child Name")
        birth_place = st.text_input("Birth Place")
    with col2:
        birth_date = st.date_input("Date of Birth", min_value=date(2018,1,1), max_value=date.today())

    st.header("Growth Metrics")
    col1, col2 = st.columns(2)
    with col1:
        weight = st.number_input("Weight (kg)", min_value=0.0, max_value=50.0, step=0.1)
        height = st.number_input("Height (cm)", min_value=30, max_value=150, step=1)
    with col2:
        pulse = st.number_input("Pulse (bpm)", min_value=50, max_value=200, step=1)
        last_tracked = st.date_input("Last Tracked On", value=date.today())

    if st.button("Save Child Details"):
        if not st.session_state.app_number:
            st.session_state.app_number = str(uuid.uuid4())[:8]
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO child_details
                (app_number, name, birth_place, birth_date, weight, height, pulse, last_tracked)
                VALUES (?,?,?,?,?,?,?,?)
            """, (st.session_state.app_number, child_name, birth_place, str(birth_date),
                  weight, height, pulse, str(last_tracked)))
            conn.commit()
            st.success(f"Child details saved successfully! Application Number: {st.session_state.app_number}")

# ------------------- TAB 2: Medical History -------------------
with tab2:
    st.header("Medical History")
    with st.form(key="history_form"):
        visit_date = st.date_input("Visit Date", value=date.today())
        hospital = st.text_input("Hospital Name")
        doctor = st.text_input("Doctor Name")
        specialization = st.text_input("Doctor Specialization")
        reason = st.text_area("Reason for Visit")
        meds = st.text_area("Medications Prescribed")
        submitted = st.form_submit_button("Add to History")

        if submitted:
            if not st.session_state.app_number:
                st.error("Please save child details first!")
            else:
                with get_connection() as conn:
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO medical_history
                        (app_number, visit_date, hospital, doctor, specialization, reason, medications)
                        VALUES (?,?,?,?,?,?,?)
                    """, (st.session_state.app_number, str(visit_date), hospital, doctor,
                          specialization, reason, meds))
                    conn.commit()
                    st.success("Medical history added!")

    # Display history table
    if st.session_state.app_number:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT visit_date, hospital, doctor, specialization, reason, medications 
                FROM medical_history WHERE app_number=?
            """, (st.session_state.app_number,))
            rows = c.fetchall()
            if rows:
                st.subheader("Medical History Table")
                st.table(rows)

# ------------------- TAB 3: Vaccinations -------------------
with tab3:
    st.header("Vaccination Schedule (0-5 Years)")
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

    if st.session_state.app_number:
        with get_connection() as conn:
            c = conn.cursor()
            for year, vaccines in vaccines_by_year.items():
                st.subheader(year)
                for v in vaccines:
                    c.execute("SELECT id FROM vaccinations WHERE app_number=? AND vaccine_name=?",
                              (st.session_state.app_number, v))
                    completed = c.fetchone() is not None
                    done = st.checkbox(f"{v}", value=completed, key=f"{v}_done")
                    if done and not completed:
                        barcode = str(uuid.uuid4())[:8]
                        c.execute("""
                            INSERT OR IGNORE INTO vaccinations
                            (app_number, vaccine_name, date, barcode)
                            VALUES (?,?,?,?)
                        """, (st.session_state.app_number, v, str(date.today()), barcode))
            conn.commit()

        # Display completed vaccines
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT vaccine_name, date, barcode FROM vaccinations WHERE app_number=?",
                      (st.session_state.app_number,))
            vac_rows = c.fetchall()
            if vac_rows:
                st.subheader("Completed Vaccinations")
                st.table(vac_rows)

# ------------------- Doctor Panel -------------------
st.sidebar.header("Doctor Panel")
if st.sidebar.checkbox("Doctor Login"):
    st.session_state.doctor_logged_in = True
    st.session_state.doctor_username = st.sidebar.text_input("Doctor Username")

if st.session_state.doctor_logged_in:
    st.subheader("Doctor Controls")
    app_number_input = st.text_input("Enter Application Number")
    new_record_button = st.button("New Application Number")

    if new_record_button:
        app_number_input = str(uuid.uuid4())[:8]
        st.success(f"New Application Number generated: {app_number_input}")

    if app_number_input:
        with get_connection() as conn:
            c = conn.cursor()
            # Load child details
            c.execute("SELECT * FROM child_details WHERE app_number=?", (app_number_input,))
            child = c.fetchone()
            if child:
                st.write(f"Child Name: {child[1]}, DOB: {child[3]}")
            else:
                st.info("No record found. Enter new details below.")
