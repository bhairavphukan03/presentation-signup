import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import json

# Page config
st.set_page_config(page_title="Presentation Sign-Up", layout="centered")

# Custom CSS
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: #1f1f1f;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .availability-box {
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        font-weight: 500;
    }
    .available {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
    }
    .full {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        margin-top: 2rem;
        margin-bottom: 1rem;
        color: #2c3e50;
    }
    .stButton>button {
        width: 100%;
        background-color: #007bff;
        color: white;
        font-weight: 600;
        padding: 0.75rem;
        border-radius: 6px;
    }
    .stButton>button:hover {
        background-color: #0056b3;
    }
    .info-text {
        font-size: 0.9rem;
        color: #666;
        font-style: italic;
    }
    hr {
        margin: 2rem 0;
        border: none;
        border-top: 2px solid #e0e0e0;
    }
    /* Add spacing between radio buttons */
    div[role="radiogroup"] label {
        margin-right: 2rem !important;
    }
    .success-banner {
        background-color: #d4edda;
        border: 2px solid #28a745;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        margin: 2rem 0;
    }
    .success-banner h1 {
        color: #28a745;
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    .success-banner p {
        font-size: 1.2rem;
        color: #155724;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize Supabase client
@st.cache_resource
def init_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase: Client = init_supabase()

# Configuration
MAX_SLOTS_PER_DATE = 22
DATES = ['December 2', 'December 4']
DATE_DISPLAY = {
    'December 2': '2 Dec',
    'December 4': '4 Dec'
}

# Initialize session state for booking completion
if 'booking_completed' not in st.session_state:
    st.session_state.booking_completed = False
if 'booking_details' not in st.session_state:
    st.session_state.booking_details = None

# Load slot tracker
@st.cache_data(ttl=5)
def load_slot_tracker():
    response = supabase.table('slot_tracker').select('*').execute()
    return {row['date']: row['slots_used'] for row in response.data}

# Check if student already booked
def check_existing_booking(student_id):
    try:
        response = supabase.table('bookings').select('*').ilike('student_ids', f'%{student_id}%').execute()
        return len(response.data) > 0
    except:
        return False

slot_tracker = load_slot_tracker()

# Header
st.markdown('<div class="main-header">Student Presentation Sign-Up</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Reserve your presentation slot for 2 Dec or 4 Dec</div>', unsafe_allow_html=True)

# If booking completed, show success banner and stop
if st.session_state.booking_completed:
    details = st.session_state.booking_details
    st.markdown(f"""
        <div class="success-banner">
            <h1>Booking Complete</h1>
            <p><strong>Date:</strong> {details['date']}</p>
            <p><strong>Time Slots:</strong> {details['start_slot']}-{details['end_slot']}</p>
            <p><strong>Duration:</strong> {details['duration']} minutes</p>
            <p><strong>Student(s):</strong> {details['student_ids']}</p>
            <br>
            <p style="font-size: 1rem; color: #666;">You can close this page now.</p>
        </div>
    """, unsafe_allow_html=True)
    st.stop()

# Availability section
st.markdown('<div class="section-header">Slot Availability</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    dec2_used = slot_tracker.get('December 2', 0)
    dec2_remaining = MAX_SLOTS_PER_DATE - dec2_used
    if dec2_remaining > 0:
        st.markdown(f"""
            <div class="availability-box available">
                <strong>2 Dec</strong><br>
                {dec2_remaining} of {MAX_SLOTS_PER_DATE} slots available
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="availability-box full">
                <strong>2 Dec</strong><br>
                FULL - No slots remaining
            </div>
        """, unsafe_allow_html=True)

with col2:
    dec4_used = slot_tracker.get('December 4', 0)
    dec4_remaining = MAX_SLOTS_PER_DATE - dec4_used
    if dec4_remaining > 0:
        st.markdown(f"""
            <div class="availability-box available">
                <strong>4 Dec</strong><br>
                {dec4_remaining} of {MAX_SLOTS_PER_DATE} slots available
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="availability-box full">
                <strong>4 Dec</strong><br>
                FULL - No slots remaining
            </div>
        """, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# Check if both dates are full
both_full = dec2_remaining <= 0 and dec4_remaining <= 0

if both_full:
    st.error("All presentation slots have been filled. Please contact TA if you need assistance.")
else:
    # Booking form
    st.markdown('<div class="section-header">Book Your Slot</div>', unsafe_allow_html=True)
    
    with st.form("booking_form", clear_on_submit=True):
        # Filter available dates
        available_dates = []
        if dec2_remaining > 0:
            available_dates.append('December 2')
        if dec4_remaining > 0:
            available_dates.append('December 4')
        
        if not available_dates:
            st.error("No dates currently available.")
        else:
            # Try pills (Streamlit 1.34+), fallback to radio if not available
            try:
                date = st.pills(
                    "Presentation Date",
                    available_dates,
                    format_func=lambda x: DATE_DISPLAY[x],
                    default=available_dates[0],
                    selection_mode="single",
                    help="Select the date you'd like to present"
                )
            except (AttributeError, TypeError):
                # Fallback to horizontal radio buttons
                date = st.radio(
                    "Presentation Date",
                    available_dates,
                    format_func=lambda x: DATE_DISPLAY[x],
                    help="Select the date you'd like to present",
                    horizontal=True
                )
            
            group_size = st.radio(
                "Number of Members",
                [1, 2, 3],
                format_func=lambda x: f"{x} member{'s' if x > 1 else ''} ({x * 3} minutes)",
                help="Select how many people are in your presentation group"
            )
            
            student_ids = st.text_input(
                "Student uni",
                help="Enter student IDs separated by commas for group presentations"
            )
            
            st.markdown('<p class="info-text">One person per group should submit this form</p>', unsafe_allow_html=True)
            
            submitted = st.form_submit_button("Reserve Slot")
            
            if submitted:
                if not student_ids.strip():
                    st.error("Please enter at least one student ID")
                else:
                    # Check if student already booked
                    first_student_id = student_ids.strip().split(',')[0].strip()
                    if check_existing_booking(first_student_id):
                        st.error("You have already booked a slot. Each student can only book once.")
                    else:
                        # Call the atomic booking function
                        try:
                            result = supabase.rpc('book_slot', {
                                'p_date': date,
                                'p_group_size': group_size,
                                'p_student_ids': student_ids.strip()
                            }).execute()
                            
                            # Handle response (it might be in .data or need parsing)
                            response = result.data
                            
                            # If response is a string, try to parse it
                            if isinstance(response, str):
                                try:
                                    response = json.loads(response)
                                except:
                                    st.error("Unable to process booking. Please try again or contact TA.")
                                    st.stop()
                            
                            if response and response.get('success'):
                                # Set booking completion flag
                                st.session_state.booking_completed = True
                                st.session_state.booking_details = {
                                    'date': DATE_DISPLAY[date],
                                    'start_slot': response['start_slot'],
                                    'end_slot': response['end_slot'],
                                    'duration': group_size * 3,
                                    'student_ids': student_ids
                                }
                                st.rerun()
                            else:
                                # Simple error message
                                remaining = response.get('slots_remaining', 0) if response else 0
                                if remaining > 0:
                                    st.error(f"Not enough slots available for {DATE_DISPLAY[date]}. Only {remaining} slot(s) remaining. Please try the other date.")
                                else:
                                    st.error(f"No slots available for {DATE_DISPLAY[date]}. Please try the other date.")
                                    
                        except Exception as e:
                            # Try to extract useful error info
                            error_str = str(e)
                            if 'not enough slots' in error_str.lower():
                                st.error("Not enough slots available for your selected date. Please try the other date.")
                            elif 'details' in error_str and 'slots_remaining' in error_str:
                                # Try to parse from error details
                                try:
                                    import re
                                    match = re.search(r'slots_remaining["\s:]+(\d+)', error_str)
                                    if match:
                                        remaining = match.group(1)
                                        st.error(f"Not enough slots available. Only {remaining} slot(s) remaining on this date.")
                                    else:
                                        st.error("Unable to complete booking. Please try the other date or contact TA.")
                                except:
                                    st.error("Unable to complete booking. Please try the other date or contact TA.")
                            else:
                                st.error("Booking failed. Please try again or contact TA if the problem persists.")

# Bookings overview
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown('<div class="section-header">Current Bookings</div>', unsafe_allow_html=True)



@st.cache_data(ttl=5)
def load_bookings():
    response = supabase.table('bookings').select('*').order('created_at').execute()
    return pd.DataFrame(response.data)

bookings_df = load_bookings()

if not bookings_df.empty:
    for date in DATES:
        date_bookings = bookings_df[bookings_df['date'] == date]
        if not date_bookings.empty:
            with st.expander(f"{DATE_DISPLAY[date]} ({len(date_bookings)} booking{'s' if len(date_bookings) > 1 else ''})"):
                display_df = date_bookings[['student_ids', 'group_size', 'start_slot', 'end_slot', 'created_at']].copy()
                display_df.columns = ['Student ID(s)', 'Group Size', 'Start Slot', 'End Slot', 'Booked At']
                st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    csv = bookings_df.to_csv(index=False)

else:
    st.info("No bookings yet. Be the first to sign up.")
