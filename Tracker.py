import streamlit as st
from datetime import date
import uuid
import sqlite3
import hashlib

# --- Session State Initialization ---
if "app_number" not in st.session_state:
    st.session_state.app_number = str(uuid.uuid4())[:8]
if "doctor_logged_in" not in st.session_state:
    st.session_state.doctor_logged_in = False
if "doctor_username" not in st.session_state:
    st.session_state.doctor_username = ""

# --- Database helper function ---
def get_connection():
    return sqlite3.connect("child_health.db")

def create_tables():
    with get_connection() as conn:
        c = conn.cursor()
        # Child Details table
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
        # Medical History table
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
        # Optional: Doctor login table
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

# --- TAB 1: Child Details & Growth Metrics ---
with tab1:
    st.header("Child Details")
    col1, col2 = st.columns(2)
    with col1:
        child_name = st.text_input("Child Name")
        birth_place = st.text_input("Birth Place")
    with col2:
        birth_date = st.date_input("Date of Birth", min_value=date(2018,1,1), max_value=date.today())

    st.write(f"**Application Number:** {st.session_state.app_number}")

    st.header("Growth Metrics")
    col1, col2 = st.columns(2)
    with col1:
        weight = st.number_input("Weight (kg)", min_value=0.0, max_value=50.0, step=0.1)
        height = st.number_input("Height (cm)", min_value=30, max_value=150, step=1)
    with col2:
        pulse = st.number_input("Pulse (bpm)", min_value=50, max_value=200, step=1)
        last_tracked = st.date_input("Last Tracked On", value=date.today())

    if st.button("Save Child Details"):
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO child_details 
                (app_number, name, birth_place, birth_date, weight, height, pulse, last_tracked)
                VALUES (?,?,?,?,?,?,?,?)
            """, (st.session_state.app_number, child_name, birth_place, str(birth_date),
                  weight, height, pulse, str(last_tracked)))
            conn.commit()
            st.success("Child details saved successfully!")

# --- TAB 2: Medical History ---
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
            if visit_date and hospital and doctor and reason:
                with get_connection() as conn:
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO medical_history
                        (app_number, visit_date, hospital, doctor, specialization, reason, medications)
                        VALUES (?,?,?,?,?,?,?)
                    """, (st.session_state.app_number, str(visit_date), hospital,
                          doctor, specialization, reason, meds))
                    conn.commit()
                    st.success("Medical history added!")

    # Display history from DB
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

# --- TAB 3: Vaccinations ---
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

    for year, vaccines in vaccines_by_year.items():
        st.subheader(year)
        for v in vaccines:
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT id FROM vaccinations WHERE app_number=? AND vaccine_name=?",
                          (st.session_state.app_number, v))
                completed = c.fetchone() is not None
            done = st.checkbox(f"{v}", value=completed, key=f"{v}_done")
            if done and not completed:
                barcode = str(uuid.uuid4())[:8]
                with get_connection() as conn:
                    c = conn.cursor()
                    c.execute("""
                        INSERT OR IGNORE INTO vaccinations (app_number, vaccine_name, date, barcode)
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

# --- Doctor Panel ---
if st.session_state.doctor_logged_in:
    st.header("Doctor Panel")
    app_number_input = st.text_input("Enter Application Number")
    new_record_button = st.button("New Application Number")
    
    if new_record_button:
        app_number_input = str(uuid.uuid4())[:8]
        st.success(f"New Application Number generated: {app_number_input}")

    if app_number_input:
        with get_connection() as conn:
            c = conn.cursor()
            # Load child details
            c.execute("""
                SELECT name, birth_place, birth_date, weight, height, pulse, last_tracked
                FROM child_details WHERE app_number=?
            """, (app_number_input,))
            child = c.fetchone()
            if child:
                st.subheader("Child Details")
                st.write(f"Name: {child[0]}")
                st.write(f"Birth Place: {child[1]}")
                st.write(f"DOB: {child[2]}")
                st.write(f"Weight: {child[4]} cm, Height: {child[5]} kg, Pulse: {child[6]} bpm, Last Tracked: {child[6]}")
            else:
                st.info("No existing record found. You can add new child details below.")
                child_name = st.text_input("Child Name", key="new_child_name")
                birth_place = st.text_input("Birth Place", key="new_birth_place")
                birth_date = st.date_input("Date of Birth", min_value=date(2018,1,1), max_value=date.today(), key="new_birth_date")
                weight = st.number_input("Weight (kg)", min_value=0.0, max_value=50.0, step=0.1, key="new_weight")
                height = st.number_input("Height (cm)", min_value=30, max_value=150, step=1, key="new_height")
                pulse = st.number_input("Pulse (bpm)", min_value=50, max_value=200, step=1, key="new_pulse")
                last_tracked = st.date_input("Last Tracked On", value=date.today(), key="new_last_tracked")
                if st.button("Save Child Details for Doctor"):
                    c.execute("""
                        INSERT INTO child_details (app_number, name, birth_place, birth_date, weight, height, pulse, last_tracked)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, (app_number_input, child_name, birth_place, str(birth_date), weight, height, pulse, str(last_tracked)))
                    conn.commit()
                    st.success("Child details saved successfully!")

        # Medical history editor for Doctor
        c.execute("""
            SELECT id, visit_date, hospital, doctor, specialization, reason, medications, wrong_record
            FROM medical_history WHERE app_number=? ORDER BY visit_date
        """, (app_number_input,))
        histories = c.fetchall()
        if histories:
            st.subheader("Medical History")
            for h in histories:
                if h[7]:
                    st.write(f"⚠️ Record {h[0]} is marked WRONG")
                    continue
                st.write({
                    "Visit Date": h[1],
                    "Hospital": h[2],
                    "Doctor": h[3],
                    "Specialization": h[4],
                    "Reason": h[5],
                    "Medications": h[6]
                })
                with st.form(f"edit_history_{h[0]}"):
                    new_visit = st.date_input("Visit Date", value=date.fromisoformat(h[1]), key=f"visit_{h[0]}")
                    new_hospital = st.text_input("Hospital Name", value=h[2], key=f"hospital_{h[0]}")
                    new_specialization = st.text_input("Doctor Specialization", value=h[4], key=f"spec_{h[0]}")
                    new_reason = st.text_area("Reason for Visit", value=h[5], key=f"reason_{h[0]}")
                    new_meds = st.text_area("Medications Prescribed", value=h[6], key=f"meds
