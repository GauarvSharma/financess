
import streamlit as st
import pandas as pd
import os
import socket

st.set_page_config(page_title="Loan Portfolio", layout="centered")
st.title("Loan Portfolio ")

# Path to save processed file
OUTPUT_PATH = os.path.join(os.getcwd(), "Loan_Portfolio.xlsx")

# Detect current device
current_device = socket.gethostname().lower()
OWNER_DEVICE = "RJHO5568LP".lower()  # Set your actual PC name here

# Track if file was processed
if "just_processed" not in st.session_state:
    st.session_state.just_processed = os.path.exists(OUTPUT_PATH)

# --- OWNER UPLOAD SECTION ---
if current_device == OWNER_DEVICE:
    st.markdown("### 📂 Upload & Process Files")
    loan_file = st.file_uploader("Loan Portfolio File", type=["xlsx", "xls"])
    arc_file  = st.file_uploader("ARC Finance File", type=["xlsx", "xls"])
    lms_file  = st.file_uploader("LMS053 Voucher MIS File", type=["xlsx", "xls"])

    if loan_file and arc_file and lms_file and st.button("Process & Save"):
        try:
            # Load & filter Loan Portfolio
            loan_df = pd.read_excel(loan_file)
            loan_df = loan_df[loan_df['accounting_writeoff'].fillna('').str.lower() != 'yes']
            loan_df = loan_df[loan_df['loan_status'].fillna('').str.lower() == 'active']

            # Keep only required columns
            keep_cols = [
                "loan_account_number","customer_name","cibil","product_code","product_name",
                "interest_rate","original_tenure","ltv","login_date","sourcing_channel",
                "dsa_name","dealer_code","dealer_name","collateral_type","model",
                "model_year","registration_number","chasis_no","engine_no","sanction_date",
                "sanctioned_amount","interest_start_date","repayment_start_date","maturity_date",
                "installment_amount","disbursal_date","disbursal_amount","pending_amount",
                "disbursal_status","principal_outstanding","total_excess_money","dpd","dpd_wise",
                "asset_classification","credit_manager_id","credit_manager_name","sourcing_rm_id",
                "sourcing_rm_name","branch_id","branch_code","branch_name","state","repayment_mode",
                "nach_status","loan_status"
            ]
            loan_df = loan_df[[c for c in keep_cols if c in loan_df.columns]]

            # ARC Lookup
            arc_df = pd.read_excel(arc_file)
            arc_df.columns = arc_df.columns.str.strip()
            arc_col = next((c for c in arc_df.columns if 'loan_account_number' in c.lower()), None)
            if not arc_col:
                st.error("ARC Finance file needs a 'loan_account_number' column.")
                st.stop()
            loan_df['ARC Lookup'] = loan_df['loan_account_number'].apply(
                lambda v: v if v in arc_df[arc_col].values else None
            )
            loan_df = loan_df[loan_df['ARC Lookup'].isna()].drop(columns=['ARC Lookup'])

            # LMS053 Accrual
            lms_df = pd.read_excel(lms_file)
            lms_df.columns = lms_df.columns.str.strip()
            if 'Gl Desc' not in lms_df.columns:
                st.error("LMS053 file needs 'Gl Desc' column.")
                st.stop()
            lms_df = lms_df[lms_df['Gl Desc'].str.upper() == 'ACCRUAL INCOME']
            if not all(c in lms_df.columns for c in ['Loan Account Number','Debit Amount']):
                st.error("LMS053 file must have 'Loan Account Number' and 'Debit Amount'.")
                st.stop()
            accrual = (
                lms_df[['Loan Account Number','Debit Amount']]
                .groupby('Loan Account Number')['Debit Amount']
                .sum().reset_index()
                .rename(columns={'Loan Account Number':'loan_account_number','Debit Amount':'Accrul_Amount'})
            )
            loan_df = loan_df.merge(accrual, on='loan_account_number', how='left')
            loan_df['Accrul_Amount'] = loan_df['Accrul_Amount'].fillna(0)

            # AUM Calculation
            cols = loan_df.columns.tolist()
            try:
                AB, AD, AE, AT = cols[27], cols[29], cols[30], cols[45]
            except IndexError:
                st.error("Not enough columns to calculate AUM.")
                st.stop()
            loan_df['AUM'] = loan_df.apply(
                lambda r: max(r[AD] - (r[AB] + r[AE]), 0) + r[AT], axis=1
            )

            # Save file
            loan_df.to_excel(OUTPUT_PATH, index=False, sheet_name="Loan Portfolio")
            st.success("✅ File processed and saved.")
            st.session_state.just_processed = True

        except Exception as e:
            st.error(f"❌ Error: {e}")

# --- DOWNLOAD SECTION FOR EVERYONE ---
if st.session_state.just_processed and os.path.exists(OUTPUT_PATH):
    st.markdown("---")
    st.markdown("### 📥 Download Loan Portfolio")
    with open(OUTPUT_PATH, "rb") as f:
        data = f.read()
    st.download_button(
        label="Download Excel File",
        data=data,
        file_name="Loan_Portfolio.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
