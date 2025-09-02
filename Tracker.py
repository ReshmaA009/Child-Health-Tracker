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
        c.execute("""...""")  # child_details table
        c.execute("""...""")  # medical_history table
        c.execute("""...""")  # vaccinations table
        # add doctor table if needed
        conn.commit()

create_tables()

# --- Your Tab 1, Tab 2, Tab 3 code goes here ---

# --- Doctor Panel with Edit & Mark Wrong ---
if st.session_state.doctor_logged_in:
    st.header("Doctor Panel")
    with get_connection() as conn:
        c = conn.cursor()
        # rest of doctor panel code

        c.execute("SELECT app_number, name, birth_date FROM child_details")
        children = c.fetchall()
        st.subheader("All Children")

        for child in children:
            app_num, name, dob = child
            st.write(f"**Application Number:** {app_num} | **Name:** {name} | **DOB:** {dob}")

            # Load medical history that is NOT marked wrong
            c.execute("""
                SELECT id, visit_date, hospital, doctor, specialization, reason, medications, wrong_record
                FROM medical_history WHERE app_number=? ORDER BY visit_date
            """, (app_num,))
            histories = c.fetchall()

            for h in histories:
                if h[7]:  # wrong_record column
                    st.write(f"⚠️ This record is marked wrong and cannot be edited. (ID: {h[0]})")
                    continue

                st.write({
                    "Visit Date": h[1],
                    "Hospital": h[2],
                    "Doctor": h[3],
                    "Specialization": h[4],
                    "Reason": h[5],
                    "Medications": h[6]
                })

                # Edit form
                with st.form(f"edit_history_{h[0]}"):
                    new_visit = st.date_input("Visit Date", value=date.fromisoformat(h[1]), key=f"visit_{h[0]}")
                    new_hospital = st.text_input("Hospital Name", value=h[2], key=f"hospital_{h[0]}")
                    new_specialization = st.text_input("Doctor Specialization", value=h[4], key=f"spec_{h[0]}")
                    new_reason = st.text_area("Reason for Visit", value=h[5], key=f"reason_{h[0]}")
                    new_meds = st.text_area("Medications Prescribed", value=h[6], key=f"meds_{h[0]}")
                    mark_wrong = st.checkbox("Mark this record as WRONG", key=f"wrong_{h[0]}")
                    submitted_edit = st.form_submit_button("Save Changes")

                    if submitted_edit:
                        with get_connection() as conn2:
                            c2 = conn2.cursor()
                            if mark_wrong:
                                # Mark as wrong
                                c2.execute("UPDATE medical_history SET wrong_record=1 WHERE id=?", (h[0],))
                                conn2.commit()
                                st.warning("Record marked as WRONG. You can now create a new record.")
                            else:
                                # Update the record
                                c2.execute("""
                                    UPDATE medical_history
                                    SET visit_date=?, hospital=?, doctor=?, specialization=?, reason=?, medications=?
                                    WHERE id=?
                                """, (str(new_visit), new_hospital, st.session_state.doctor_username,
                                      new_specialization, new_reason, new_meds, h[0]))
                                conn2.commit()
                                st.success("Record updated successfully!")

            # Add new record
            with st.form(f"add_history_{app_num}"):
                st.subheader("Add New Medical History")
                visit_date = st.date_input("Visit Date", value=date.today(), key=f"new_visit_{app_num}")
                hospital = st.text_input("Hospital Name", key=f"new_hospital_{app_num}")
                specialization = st.text_input("Doctor Specialization", key=f"new_spec_{app_num}")
                reason = st.text_area("Reason for Visit", key=f"new_reason_{app_num}")
                meds = st.text_area("Medications Prescribed", key=f"new_meds_{app_num}")
                submitted_new = st.form_submit_button("Add History")
                if submitted_new:
                    with get_connection() as conn2:
                        c2 = conn2.cursor()
                        c2.execute("""
                            INSERT INTO medical_history (app_number, visit_date, hospital, doctor, specialization, reason, medications, wrong_record)
                            VALUES (?,?,?,?,?,?,?,0)
                        """, (app_num, str(visit_date), hospital, st.session_state.doctor_username,
                              specialization, reason, meds))
                        conn2.commit()
                        st.success("New record added successfully!")
import streamlit as st
from datetime import date
import uuid
import sqlite3

# --- Session State Initialization ---
if "app_number" not in st.session_state:
    st.session_state.app_number = str(uuid.uuid4())[:8]

# --- Database helper function ---
def get_connection():
    return sqlite3.connect("child_health.db")

def create_tables():
    with get_connection() as conn:
        c = conn.cursor()
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
            """, (st.session_state.app_number, child_name, birth_place, str(birth_date), weight, height, pulse, str(last_tracked)))
            conn.commit()
            st.success("Child details saved successfully!")

    # Load saved child details
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT name, birth_place, birth_date, weight, height, pulse, last_tracked FROM child_details WHERE app_number=?", (st.session_state.app_number,))
        child = c.fetchone()
        if child:
            st.subheader("Saved Child Details")
            st.write(f"Name: {child[0]}")
            st.write(f"Birth Place: {child[1]}")
            st.write(f"DOB: {child[2]}")
            st.write(f"Weight: {child[3]} kg, Height: {child[4]} cm, Pulse: {child[5]} bpm (Last tracked: {child[6]})")

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
                    """, (st.session_state.app_number, str(visit_date), hospital, doctor, specialization, reason, meds))
                    conn.commit()
                    st.success("Medical history added!")

    # Display history from DB
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT visit_date, hospital, doctor, specialization, reason, medications FROM medical_history WHERE app_number=?", (st.session_state.app_number,))
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
            # Check DB if vaccine completed
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT id FROM vaccinations WHERE app_number=? AND vaccine_name=?", (st.session_state.app_number, v))
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
        c.execute("SELECT vaccine_name, date, barcode FROM vaccinations WHERE app_number=?", (st.session_state.app_number,))
        vac_rows = c.fetchall()
        if vac_rows:
            st.subheader("Completed Vaccinations")
            st.table(vac_rows)

# --- Optional: Reset App ---
if st.button("Reset App"):
    st.session_state.clear()
    st.experimental_rerun()


