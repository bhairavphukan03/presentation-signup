import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# Page config
st.set_page_config(page_title="Presentation Sign-Up", layout="centered")

# Custom CSS
st.markdown("""
    <style>
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

# Load slot tracker
@st.cache_data(ttl=5)
def load_slot_tracker():
    response = supabase.table('slot_tracker').select('*').execute()
    return {row['date']: row['slots_used'] for row in response.data}

slot_tracker = load_slot_tracker()

# Header
st.markdown('<div class="main-header">Student Presentation Sign-Up</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Reserve your presentation slot for December 2nd or 4th</div>', unsafe_allow_html=True)

# Availability section
st.markdown('<div class="section-header">Slot Availability</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    dec2_used = slot_tracker.get('December 2', 0)
    dec2_remaining = MAX_SLOTS_PER_DATE - dec2_used
    if dec2_remaining > 0:
        st.markdown(f"""
            <div class="availability-box available">
                <strong>December 2</strong><br>
                {dec2_remaining} of {MAX_SLOTS_PER_DATE} slots available
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="availability-box full">
                <strong>December 2</strong><br>
                FULL - No slots remaining
            </div>
        """, unsafe_allow_html=True)

with col2:
    dec4_used = slot_tracker.get('December 4', 0)
    dec4_remaining = MAX_SLOTS_PER_DATE - dec4_used
    if dec4_remaining > 0:
        st.markdown(f"""
            <div class="availability-box available">
                <strong>December 4</strong><br>
                {dec4_remaining} of {MAX_SLOTS_PER_DATE} slots available
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="availability-box full">
                <strong>December 4</strong><br>
                FULL - No slots remaining
            </div>
        """, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# Check if both dates are full
both_full = dec2_remaining <= 0 and dec4_remaining <= 0

if both_full:
    st.error("All presentation slots have been filled. Please contact your instructor if you need assistance.")
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
            date = st.selectbox(
                "Presentation Date",
                available_dates,
                help="Select the date you'd like to present"
            )
            
            group_size = st.radio(
                "Number of Presenters",
                [1, 2, 3],
                format_func=lambda x: f"{x} presenter{'s' if x > 1 else ''} ({x * 3} minutes)",
                help="Select how many people are in your presentation group"
            )
            
            student_ids = st.text_input(
                "Student ID(s)",
                placeholder="e.g., 12345678 or 12345678, 87654321, 11223344",
                help="Enter student IDs separated by commas for group presentations"
            )
            
            st.markdown('<p class="info-text">One person per group should submit this form</p>', unsafe_allow_html=True)
            
            submitted = st.form_submit_button("Reserve Slot")
            
            if submitted:
                if not student_ids.strip():
                    st.error("Please enter at least one student ID")
                else:
                    # Call the atomic booking function
                    try:
                        result = supabase.rpc('book_slot', {
                            'p_date': date,
                            'p_group_size': group_size,
                            'p_student_ids': student_ids.strip()
                        }).execute()
                        
                        response = result.data
                        
                        if response['success']:
                            st.success(f"""
                            **Booking Confirmed**
                            
                            Date: {date}  
                            Time slots: {response['start_slot']}-{response['end_slot']}  
                            Duration: {group_size * 3} minutes  
                            Student(s): {student_ids}
                            """)
                            # Clear cache to refresh availability
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(f"{response['message']}. Only {response['slots_remaining']} slots remaining.")
                    except Exception as e:
                        st.error(f"Booking failed: {str(e)}")

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
            with st.expander(f"{date} ({len(date_bookings)} booking{'s' if len(date_bookings) > 1 else ''})"):
                display_df = date_bookings[['student_ids', 'group_size', 'start_slot', 'end_slot', 'created_at']].copy()
                display_df.columns = ['Student ID(s)', 'Group Size', 'Start Slot', 'End Slot', 'Booked At']
                st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    csv = bookings_df.to_csv(index=False)
    st.download_button(
        label="Download All Bookings (CSV)",
        data=csv,
        file_name=f"presentation_bookings_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True
    )
else:
    st.info("No bookings yet. Be the first to sign up!")
