# ai-buyer-agent-commerce

## Overview

Agent connects an AI-powered conversational interface with a merchant's commerce backend.

A customer can interact with the system through Telegram, describe what they want to buy, and receive product recommendations based on their intent.

The system can then:

* Understand buyer intent
* Search the merchant catalog
* Recommend suitable products
* Ask the user to accept or reject recommended products
* Build the checkout
* Updates the checkout details in audit log.
* Generate a Razorpay payment link
* Track payment status through webhooks
* Send payment notifications through Telegram
* Maintain an audit log of all commerce events and Summary metrics in merchant dashboard

 # Architecture
Customer → Telegram Bot → n8n AI Buyer Agent → FastAPI Backend(updates checkout details in audit_log.jsonl) → Razorpay → Payment Webhook → Update Audit Log → Payment Notification → Telegram -> Merchant dashboard

n8n AI Buyer Agent: Understand Intent → Search Product Catalog → Recommend Products → User accepts/rejects products → Checkout


##  Key Features

### 1. Conversational Product Discovery

Users can describe their requirements naturally instead of searching using exact product names.

The AI agent interprets the request and searches the merchant catalog.

### 2. Catalog-Based Recommendations

Products are recommended only from the merchant's catalog.

The agent uses product information such as:

* Product ID
* Product name
* Price
* Stock status

### 3. User Product Confirmation

The agent presents suitable products and allows the user to accept or reject the recommendations.

The user's confirmation determines which products proceed to checkout.

### 4. Checkout and Payment

After the customer confirms the products, the system creates the checkout(Updates details in audit log)/payment flow and generates a Razorpay payment link.

### 5. Payment Status Tracking

Razorpay webhook events are processed by the backend.

Supported payment states include:

order.paid
payment.captured
payment.failed

The system can then notify the customer about the payment result.

### 6. Audit Logging

All important commerce events are recorded in an audit log for traceability and debugging.

The audit log is clearly visible to merchants through the dashboard.

The audit log records details such as:

* customer info
* Order details
* Payment status
* Payment/order IDs
* Event timestamps

## Setup

### 1. Clone the repository

### 2. Create a Python virtual environment

### 3. Install dependencies

### 4. Configure environment variables

### 5. Start the FastAPI backend and dashboard
 
### Backend

```bash
cd backend
pip install -r requirements.txt
# Edit .env with your Razorpay credentials
uvicorn main:app --reload
```
### Dashboard

```bash
cd dashboard
pip install -r requirements.txt
python -m streamlit run app.py
```
Open: http://localhost:8501


##  n8n Workflows

The repository contains exported n8n workflows:

### AI Buyer Agent

Responsible for the buyer conversation, product discovery, recommendations, user confirmation, checkout logic, audit logging, and commerce orchestration.

### Payment Notifications

Handles payment events and sends appropriate notifications to the customer.

Import the workflow JSON files into your n8n instance and configure the required credentials.

##  Security
This repository contains configuration templates only.

No API keys or webhook secrets are included. .

##  Demo

A demonstration of the complete buyer-agent flow is available in:
https://drive.google.com/file/d/19Rbe-eLPjlj--NvLEg646EQ0D4hf2Ocm/view?usp=sharing

The demo covers:

1. Customer request
2. AI intent understanding
3. Product recommendation
4. User acceptance/rejection of products
5. Checkout
6. Audit log
7. Razorpay payment
8. Payment notification
9. Merchant dashboard





