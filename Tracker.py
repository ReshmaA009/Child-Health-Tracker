import streamlit as st
from datetime import date
import uuid
import sqlite3
import hashlib

# ------------------- Styling -------------------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #ffcccc, #ffe6cc, #ffffcc, #e6ffcc, #ccffff, #e6ccff);
}
.stContainer, .css-1d391kg, .css-1v3fvcr, .stFrame {
    background-color: #ffe6f0 !important;
    padding: 1rem;
    border-radius: 10px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}
h1, h2, h3, h4, h5, h6 {
    color: #8B0000 !important;
}
label, .stTextInput > div > input, .stTextArea > div > textarea, .stSelectbox > div, 
.stNumberInput > div > input, td, th, .stCheckbox > div > label, .stCheckbox > div > label span {
    color: #8B0000 !important;
    font-weight: bold;
}
table {
    background-color: #ffe6f0 !important;
    color: #8B0000 !important;
    border-radius: 10px;
}
button, .stButton > button {
    color: #8B0000 !important;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ------------------- Database Setup -------------------
def get_connection():
    return sqlite3.connect("child_health.db", check_same_thread=False)

def create_tables():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS child_details (
                app_number TEXT PRIMARY KEY, name TEXT, birth_place TEXT, birth_date TEXT,
                weight REAL, height REAL, pulse INTEGER, last_tracked TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS medical_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, app_number TEXT, visit_date TEXT,
                hospital TEXT, doctor TEXT, specialization TEXT, diagnosis TEXT, reason TEXT,
                medications TEXT, allergic TEXT, FOREIGN KEY(app_number) REFERENCES child_details(app_number))""")
    c.execute("""CREATE TABLE IF NOT EXISTS vaccinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, app_number TEXT, vaccine_name TEXT,
                date TEXT, barcode TEXT, UNIQUE(app_number, vaccine_name),
                FOREIGN KEY(app_number) REFERENCES child_details(app_number))""")
    conn.commit()
create_tables()

# ------------------- Session State -------------------
for key in ["logged_in", "username", "role", "app_number"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key != "logged_in" else False

# ------------------- Password Helper -------------------
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

def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.app_number = ""
    st.rerun()

# ------------------- App -------------------
st.title("Child Health Tracker")

# ------------------- Tabs -------------------
tab1, tab2, tab3 = st.tabs(["Child Details", "Medical History", "Vaccinations"])

# ------------------- Login / Register -------------------
if not st.session_state.logged_in:
    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        st.subheader("Login")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        role = st.selectbox("Role", ["Doctor", "Patient"])
        app_number_input = st.text_input("Application Number", key="login_app_number") if role=="Patient" else ""

        if st.button("Login"):
            success, db_role = verify_login(username, password)
            if success and db_role == role:
                if role == "Patient":
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("SELECT * FROM child_details WHERE app_number=? AND name=?", (app_number_input, username))
                    child = c.fetchone()
                    if child:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.role = "Patient"
                        st.session_state.app_number = app_number_input
                        st.success(f"Logged in as Patient: {username}")
                        st.rerun()
                    else:
                        st.error("Invalid Application Number for this patient.")
                else:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.role = "Doctor"
                    st.success(f"Logged in as Doctor: {username}")
                    st.rerun()
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

# ------------------- Main Panel -------------------
else:
    st.info(f"Logged in as {st.session_state.role}: {st.session_state.username}")
    if st.button("Logout"):
        logout()

    conn = get_connection()
    c = conn.cursor()

    # ------------------- Doctor Panel -------------------
    if st.session_state.role == "Doctor":
        st.subheader("Doctor Panel")
        app_number_input = st.text_input("Enter Application Number", value=st.session_state.app_number)
        new_app_btn = st.button("New Application Number")
        if new_app_btn:
            app_number_input = str(uuid.uuid4())[:8]
            st.session_state.app_number = app_number_input
            st.success(f"New Application Number: {app_number_input}")
        if app_number_input:
            st.session_state.app_number = app_number_input

            # --- Child Details Tab ---
            with tab1:
                st.header("Child Details")
                c.execute("SELECT * FROM child_details WHERE app_number=?", (app_number_input,))
                child = c.fetchone()
                col1, col2 = st.columns(2)
                with col1:
                    child_name = st.text_input("Child Name", value=child[1] if child else "", key="child_name")
                    birth_place = st.text_input("Birth Place", value=child[2] if child else "", key="birth_place")
                with col2:
                    birth_date = st.date_input("DOB", value=date.fromisoformat(child[3]) if child else date.today(), key="birth_date")
                    last_tracked = st.date_input("Last Tracked", value=date.fromisoformat(child[7]) if child else date.today(), key="last_tracked")
                col3, col4 = st.columns(2)
                with col3:
                    weight = st.number_input("Weight (kg)", value=child[4] if child else 0.0, key="weight")
                with col4:
                    height = st.number_input("Height (cm)", value=child[5] if child else 0.0, key="height")
                    pulse = st.number_input("Pulse", value=child[6] if child else 60, key="pulse")
                if st.button("Save Child Details"):
                    c.execute("""INSERT OR REPLACE INTO child_details
                                 (app_number, name, birth_place, birth_date, weight, height, pulse, last_tracked)
                                 VALUES (?,?,?,?,?,?,?,?)""",
                              (app_number_input, child_name, birth_place, str(birth_date), weight, height, pulse, str(last_tracked)))
                    conn.commit()
                    st.success("Child details saved successfully!")

            # --- Medical History Tab ---
            with tab2:
                st.header("Medical History")
                with st.form(key=f"history_form_{app_number_input}"):
                    visit_date = st.date_input("Visit Date", value=date.today())
                    hospital = st.text_input("Hospital Name")
                    specialization = st.text_input("Doctor Specialization")
                    diagnosis = st.text_area("Diagnosis")
                    reason = st.text_area("Reason for Visit")
                    meds = st.text_area("Medications Prescribed")
                    allergic = st.text_area("Allergic to Medicine")
                    submitted = st.form_submit_button("Add Medical History")
                    if submitted:
                        if visit_date and hospital and specialization and reason:
                            c.execute("""INSERT INTO medical_history 
                                         (app_number, visit_date, hospital, doctor, specialization, diagnosis, reason, medications, allergic)
                                         VALUES (?,?,?,?,?,?,?,?,?)""",
                                      (app_number_input, str(visit_date), hospital, st.session_state.username,
                                       specialization, diagnosis, reason, meds, allergic))
                            conn.commit()
                            st.success("Medical history added!")
                # Display Medical History
                c.execute("""SELECT visit_date, hospital, doctor, specialization, diagnosis, reason, medications, allergic 
                             FROM medical_history WHERE app_number=?""", (app_number_input,))
                rows = c.fetchall()
                if rows:
                    st.subheader("Medical History Records")
                    st.table(rows)

            # --- Vaccinations Tab ---
            with tab3:
                st.header("Vaccination Schedule")
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
                        c.execute("SELECT id FROM vaccinations WHERE app_number=? AND vaccine_name=?", 
                                  (app_number_input, v))
                        completed = c.fetchone() is not None
                        done = st.checkbox(f"{v}", value=completed, key=f"{v}_done")
                        if done and not completed:
                            barcode = str(uuid.uuid4())[:8]
                            c.execute("INSERT INTO vaccinations (app_number, vaccine_name, date, barcode) VALUES (?,?,?,?)",
                                      (app_number_input, v, str(date.today()), barcode))
                            conn.commit()
                        elif not done and completed:
                            c.execute("DELETE FROM vaccinations WHERE app_number=? AND vaccine_name=?",
                                      (app_number_input, v))
                            conn.commit()
                # Display completed vaccines
                c.execute("SELECT vaccine_name, date, barcode FROM vaccinations WHERE app_number=?", 
                          (app_number_input,))
                vac_rows = c.fetchall()
                if vac_rows:
                    st.subheader("Completed Vaccinations")
                    st.table(vac_rows)

    # ------------------- Patient Panel -------------------
    elif st.session_state.role == "Patient":
        st.subheader("Patient Panel (Read-only)")
        app_number_input = st.session_state.app_number
        c.execute("SELECT * FROM child_details WHERE app_number=?", (app_number_input,))
        child = c.fetchone()
        if child:
            st.markdown(f"**Application Number:** {child[0]}")
            st.write(f"Name: {child[1]}")
            st.write(f"Birth Place: {child[2]}")
            st.write(f"DOB: {child[3]}")
            st.write(f"Weight: {child[4]} kg, Height: {child[5]} cm, Pulse: {child[6]}, Last Tracked: {child[7]}")
            # Medical History
            c.execute("""SELECT visit_date, hospital, doctor, specialization, diagnosis, reason, medications, allergic
                         FROM medical_history WHERE app_number=?""", (app_number_input,))
            rows = c.fetchall()
            if rows:
                st.subheader("Medical History / Prescription / Allergic Info")
                st.table(rows)
            else:
                st.info("No medical history recorded yet.")
            # Vaccinations
            c.execute("SELECT vaccine_name, date, barcode FROM vaccinations WHERE app_number=?", (app_number_input,))
            vac_rows = c.fetchall()
            if vac_rows:
                st.subheader("Vaccinations (with Barcode)")
                st.table(vac_rows)
            else:
                st.info("No vaccinations recorded yet.")
