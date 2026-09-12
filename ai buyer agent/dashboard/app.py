import streamlit as st
import json
import pandas as pd
from datetime import datetime
import os

# Page config
st.set_page_config(
    page_title="Merchant Dashboard - AI Buyer Agent",
    page_icon="📊",
    layout="wide"
)

# Title
st.title("📊 Merchant Dashboard - AI Buyer Agent")
st.markdown("---")

# Audit log file path
AUDIT_LOG = "../backend/audit_log.jsonl"

# Function to load audit log
@st.cache_data(ttl=5)
def load_audit_log():
    if not os.path.exists(AUDIT_LOG):
        return []
    
    logs = []
    with open(AUDIT_LOG, "r") as f:
        for line in f:
            if line.strip():
                logs.append(json.loads(line))
    return logs

# Load data
logs = load_audit_log()

# Sidebar filters
st.sidebar.header("🔍 Filters")

# Date filter
if logs:
    dates = [log.get("timestamp", "")[:10] for log in logs]
    unique_dates = sorted(list(set(dates)))
    selected_date = st.sidebar.selectbox("Select Date", ["All"] + unique_dates)
    
    # Status filter
    status_options = ["All", "success", "failed", "rejected"]
    selected_status = st.sidebar.selectbox("Status", status_options)
    
    # Action type filter
    action_types = ["All", "checkout_created", "payment_captured", "payment_failed", "user_rejected"]
    selected_action = st.sidebar.selectbox("Action Type", action_types)
else:
    selected_date = "All"
    selected_status = "All"
    selected_action = "All"

# Filter logs
filtered_logs = logs
if selected_date != "All":
    filtered_logs = [log for log in filtered_logs if log.get("timestamp", "")[:10] == selected_date]
if selected_status != "All":
    filtered_logs = [log for log in filtered_logs if log.get("outcome") == selected_status]
if selected_action != "All":
    filtered_logs = [log for log in filtered_logs if log.get("action") == selected_action]

# Summary Metrics
st.subheader("📈 Summary Metrics")
col1, col2, col3, col4 = st.columns(4)

total_checkouts = len([log for log in logs if log.get("action") == "checkout_created"])
successful_payments = len([log for log in logs if log.get("action") == "payment_captured"])
failed_payments = len([log for log in logs if log.get("action") == "payment_failed"])
total_revenue = sum([log.get("amount", 0) for log in logs if log.get("action") == "payment_captured"]) / 100  # Convert to INR

col1.metric("Total Checkouts", total_checkouts)
col2.metric("Successful Payments", successful_payments)
col3.metric("Failed Payments", failed_payments)
col4.metric("Total Revenue (₹)", f"₹{total_revenue:,.2f}")

st.markdown("---")

# Recent Transactions Table
st.subheader("💳 Recent Transactions")

if filtered_logs:
    # Create DataFrame
    df_data = []
    for log in filtered_logs:
        row = {
            "Timestamp": log.get("timestamp", "")[:19].replace("T", " "),
            "Action": log.get("action", ""),
            "Order ID": log.get("order_id", "N/A"),
            "Payment ID": log.get("payment_id", "N/A"),
            "Amount (₹)": f"₹{log.get('amount', 0) / 100:,.2f}" if log.get("amount") else "N/A",
            "Status": log.get("outcome", ""),
            "Products": ", ".join([p.get("name", "") for p in log.get("products", [])]) if log.get("products") else "N/A",
            "Customer": log.get("customer_info", {}).get("customer_name", "N/A") if log.get("customer_info") else "N/A",
            "Reason": log.get("reason", log.get("error", "")) if log.get("outcome") == "failed" else "-"
        }
        df_data.append(row)
    
    df = pd.DataFrame(df_data)
    
    # Display table
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Timestamp": st.column_config.TextColumn("Timestamp", width="medium"),
            "Action": st.column_config.TextColumn("Action", width="medium"),
            "Order ID": st.column_config.TextColumn("Order ID", width="small"),
            "Payment ID": st.column_config.TextColumn("Payment ID", width="small"),
            "Amount (₹)": st.column_config.TextColumn("Amount", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Products": st.column_config.TextColumn("Products", width="large"),
            "Customer": st.column_config.TextColumn("Customer", width="medium"),
            "Reason": st.column_config.TextColumn("Reason", width="medium")
        }
    )
else:
    st.info("No transactions found with current filters.")

st.markdown("---")

# Product Insights
st.subheader("🛍️ Product Insights")

if logs:
    # Extract all products
    all_products = []
    for log in logs:
        if log.get("products"):
            for product in log.get("products", []):
                all_products.append(product.get("name", "Unknown"))
    
    if all_products:
        from collections import Counter
        product_counts = Counter(all_products)
        
        # Display as table
        product_df = pd.DataFrame([
            {"Product Name": name, "Times Ordered": count}
            for name, count in product_counts.items()
        ]).sort_values("Times Ordered", ascending=False)
        
        st.dataframe(
            product_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No product data available.")
else:
    st.info("No data available.")

st.markdown("---")

# Raw Audit Log (for debugging)
with st.expander("📄 View Raw Audit Log"):
    if logs:
        st.json(logs)
    else:
        st.info("No audit log entries.")

# Footer
st.markdown("---")
st.caption(" AI Growth & Agentic Commerce ")