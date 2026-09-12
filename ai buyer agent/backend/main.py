from dotenv import load_dotenv
load_dotenv() 
from fastapi import FastAPI, HTTPException, Request, Header
from pydantic import BaseModel
from typing import List, Optional
import razorpay
import hmac
import hashlib
import json
import os
from datetime import datetime


app = FastAPI(title="Merchant Backend")


# Razorpay configuration
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_xxxxx")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "your_test_secret")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "your_webhook_secret")


client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


# Hardcoded product catalog (you can move to DB later)
PRODUCTS = [
    {
        "id": "prod_001",
        "name": "Wireless Charger",
        "price": 1499,
        "currency": "INR",
        "available": True,
        "description": "15W fast wireless charger"
    },
    {
        "id": "prod_002",
        "name": "USB-C Cable",
        "price": 299,
        "currency": "INR",
        "available": True,
        "description": "1m braided USB-C cable"
    },
    {
        "id": "prod_003",
        "name": "Power Bank 10000mAh",
        "price": 1999,
        "currency": "INR",
        "available": True,
        "description": "Fast charging power bank"
    }
]


# Pydantic models
class CartItem(BaseModel):
    product_id: str
    qty: int = 1


class CheckoutRequest(BaseModel):
    items: List[CartItem]
    shipping: str = "standard"
    customer_info: Optional[dict] = None  # ADDED: For customer name


class CheckoutResponse(BaseModel):
    order_id: str
    payment_link: str
    amount: int
    currency: str


class AuditLogRequest(BaseModel):
    action: str
    order_id: str
    amount: int
    outcome: str


# ==================== ENDPOINTS ====================


@app.get("/products")
async def get_products():
    """
    Returns the merchant's product catalog.
    """
    return PRODUCTS


@app.get("/products/{product_id}")
async def get_product(product_id: str):
    """
    Returns a single product by ID.
    """
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(request: CheckoutRequest):
    """
    Creates a Razorpay order and returns payment link.
    Logs checkout with product and customer info to audit trail.
    """
    # Calculate total amount
    total_amount = 0
    selected_products = []  # Track products for audit log
    
    for item in request.items:
        product = next((p for p in PRODUCTS if p["id"] == item.product_id), None)
        if not product or not product["available"]:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} not available")
        total_amount += product["price"] * item.qty
        selected_products.append({  # ADD THIS
            "name": product["name"],
            "price": product["price"],
            "quantity": item.qty
        })
    
    # Add shipping cost
    shipping_costs = {"standard": 50, "express": 150}
    total_amount += shipping_costs.get(request.shipping, 50)
    
    # Convert to paise (Razorpay expects amount in paise)
    amount_paise = total_amount * 100
    
    # Create Razorpay order
    order_data = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": f"order_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "payment_capture": 1
    }
    
    try:
        order = client.order.create(data=order_data)
        order_id = order["id"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")
    
    # Create Razorpay payment link
    try:
        payment_link_data = {
            "amount": amount_paise,
            "currency": "INR",
            "expire_by": int(datetime.now().timestamp()) + 3600,
            "reference_id": order_id,
            "description": f"Order {order_id}",
            "customer": {
                "name": "AI Buyer",
                "email": "buyer@example.com"
            },
            "notify": {
                "sms": False,
                "email": False
            }
        }
        payment_link = client.payment_link.create(data=payment_link_data)
        payment_link_url = payment_link["short_url"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create payment link: {str(e)}")
    
    # ============ ADD THIS SECTION - Log checkout with product info ============
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": "checkout_created",
        "order_id": order_id,
        "amount": amount_paise,
        "currency": "INR",
        "products": selected_products,
        "customer_info": request.customer_info or {},
        "outcome": "success"
    }
    
    with open("audit_log.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    # ===========================================================================
    
    return CheckoutResponse(
        order_id=order_id,
        payment_link=payment_link_url,
        amount=amount_paise,
        currency="INR"
    )

@app.post("/webhooks/order-events")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(
        None,
        alias="X-Razorpay-Signature"
    )
):
    """
    Receives Razorpay webhook events.
    Logs payment success/failure events.
    Uses 'receipt' from order.entity to link to our checkout order.
    """

    # Get raw body
    body = await request.body()

    try:
        # Parse webhook JSON
        event = json.loads(body)

        event_type = event.get("event", "unknown")
        payload = event.get("payload", {})

        # Print complete webhook information for debugging
        print(f"[WEBHOOK] Event: {event_type}")
        print(
            f"[WEBHOOK] Payload: "
            f"{json.dumps(payload, indent=2)}"
        )

        # ==========================================
        # PAYMENT FAILED
        # ==========================================
        if event_type == "payment.failed":

            payment = payload.get("payment", {}).get("entity", {})
            order = payload.get("order", {}).get("entity", {})

            payment_id = payment.get("id")
            
            # ============ CHANGE THIS ============
            # Get receipt from order.entity (not payment.entity)
            order_id = order.get("receipt") or payment.get("order_id")
            # =====================================
            
            amount = payment.get("amount")
            reason = payment.get("error_description")

            print(f"Payment ID: {payment_id}")
            print(f"Order ID (from order.receipt): {order_id}")
            print(f"Amount: {amount}")
            print(f"Reason: {reason}")

            print(
                f"❌ Payment failed: "
                f"{payment_id} - Reason: {reason}"
            )

            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": "payment_failed",
                "payment_id": payment_id,
                "order_id": order_id,  # Now matches our checkout order_id!
                "amount": amount,
                "outcome": "failed",
                "reason": reason
            }

            with open("audit_log.jsonl", "a") as f:
                f.write(json.dumps(log_entry) + "\n")

        # ==========================================
        # PAYMENT CAPTURED
        # ==========================================
        elif event_type == "payment.captured":

            payment = payload.get("payment", {}).get("entity", {})
            order = payload.get("order", {}).get("entity", {})

            payment_id = payment.get("id")
            
            # ============ CHANGE THIS ============
            # Get receipt from order.entity (not payment.entity)
            order_id = order.get("receipt") or payment.get("order_id")
            # =====================================
            
            amount = payment.get("amount")

            print(
                f"✅ Payment captured: "
                f"{payment_id} - Amount: {amount} - Order (receipt): {order_id}"
            )

            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": "payment_captured",
                "payment_id": payment_id,
                "order_id": order_id,  # Now matches our checkout order_id!
                "amount": amount,
                "outcome": "success"
            }

            with open("audit_log.jsonl", "a") as f:
                f.write(json.dumps(log_entry) + "\n")

        # ==========================================
        # ORDER PAID
        # ==========================================
        elif event_type == "order.paid":

            order = payload.get("order", {}).get("entity", {})

            order_id = order.get("id")

            print(f"✅ Order paid: {order_id}")

        # ==========================================
        # OTHER EVENTS
        # ==========================================
        else:
            print(f"[WEBHOOK] Event ignored: {event_type}")

        return {
            "status": "success",
            "event": event_type
        }

    except Exception as e:

        print(f"[WEBHOOK ERROR] {str(e)}")

        raise HTTPException(
            status_code=400,
            detail=f"Invalid webhook payload: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/debug-keys")
async def debug_keys():
    return {
        "key_id": RAZORPAY_KEY_ID,
        "key_secret_set": bool(RAZORPAY_KEY_SECRET),
        "webhook_secret_set": bool(RAZORPAY_WEBHOOK_SECRET)
    }


@app.post("/audit-log")
async def create_audit_log(request: AuditLogRequest):
    """
    Logs audit entry to file.
    """
    import json
    from datetime import datetime
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": request.action,
        "order_id": request.order_id,
        "amount": request.amount,
        "outcome": request.outcome
    }
    
    # Append to log file
    with open("audit_log.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    return {"status": "logged", "log_entry": log_entry}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)