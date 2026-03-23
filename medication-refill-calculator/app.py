import streamlit as st
from core_logic import calculate_refill_metrics

# --- Page Configuration ---
st.set_page_config(page_title="Medication Refill Calculator", page_icon="💊", layout="centered")

st.title("Medication Refill Calculator")
st.write("A fast, privacy-focused calculator that determines exact medication refill dates and tracks your remaining pill supply. No data is saved or shared.")

# --- Input Form ---
with st.form("refill_form"):
    st.subheader("Prescription Details")
    
    last_filled = st.text_input(
        "Date Last Filled (Required)", 
        placeholder="e.g., Nov 15, today, 11/15/2024",
        help="Type any date format or relative term."
    )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        day_supply = st.number_input("Day Supply", min_value=1, max_value=365, value=30)
    with col2:
        quantity = st.number_input("Total Pills Dispensed", min_value=0, value=0, help="Leave 0 if unknown.")
    with col3:
        taken_per_day = st.number_input("Pills Taken Per Day", min_value=0.0, value=0.0, step=0.5, help="Leave 0 if unknown.")

    submitted = st.form_submit_button("Calculate")

# --- Output Logic ---
if submitted:
    if not last_filled:
        st.error("Please enter the date your prescription was last filled.")
    else:
        try:
            # Format inputs for logic engine
            qty_val = int(quantity) if quantity > 0 else None
            taken_val = float(taken_per_day) if taken_per_day > 0 else None
            
            # Run calculations
            metrics = calculate_refill_metrics(
                last_filled=last_filled,
                day_supply=int(day_supply),
                quantity=qty_val,
                taken_per_day=taken_val
            )
            
            st.divider()
            
            # Display Core Refill Dates
            st.subheader("Refill Timeline")
            
            if metrics['days_until_refill'] == 0:
                st.error(f"⚠️ Refill is due today or overdue. (Target date was {metrics['refill_date'].strftime('%b %d, %Y')})")
            elif metrics['days_until_refill'] <= 3:
                st.warning(f"⏳ Refill due soon: **{metrics['days_until_refill']} days** (Target: {metrics['refill_date'].strftime('%b %d, %Y')})")
            else:
                st.success(f"✅ Refill due in **{metrics['days_until_refill']} days**. (Target: {metrics['refill_date'].strftime('%b %d, %Y')})")

            st.write(f"**Current Cycle Day:** Day {metrics['current_day_num']} of {metrics['day_supply']}")

            # Display Quantity Metrics if provided
            if metrics['has_quantity_metrics']:
                st.subheader("Supply Status")
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Pills Taken", f"{metrics['should_have_taken']:g}")
                col_b.metric("Pills Remaining", f"{metrics['should_have_left']:g}")
                col_c.metric("Days of Supply Left", f"{metrics['days_remaining']:g}")
                
        except ValueError as e:
            st.error(f"Error parsing date: {e}. Please try a standard format like 'MM/DD/YYYY' or 'Month DD'.")
