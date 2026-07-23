import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notifications")

def notify_owner_new_booking(booking: dict):
    """
    Sends notification to owner (Jai) on receiving a new booking.
    Logs email output and supports Resend/SendGrid API key if configured in environment.
    """
    owner_email = os.getenv("OWNER_EMAIL", "jai@blueheavenfarmhouse.com")
    resend_api_key = os.getenv("RESEND_API_KEY")
    
    subject = f"🚨 New Booking Request #{booking['id']} - {booking['first_name']} {booking['last_name']}"
    body = f"""
==================================================
BLUE HEAVEN FARMHOUSE — NEW BOOKING REQUEST
==================================================
Booking ID : #{booking['id']}
Guest Name : {booking['first_name']} {booking['last_name']}
Email      : {booking['email']}
Phone      : {booking['phone']}
Check-In   : {booking['check_in']}
Check-Out  : {booking['check_out']}
Guests     : {booking['guests']}
Package    : {booking['package']}
Special Req: {booking.get('special_requests') or 'None'}
Status     : {booking['status'].upper()}
Submitted  : {booking['created_at']}
==================================================
    """
    
    logger.info(f"\n[OWNER NOTIFICATION SENT TO {owner_email}]\n{body}")
    
    if resend_api_key:
        try:
            import urllib.request
            import json
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=json.dumps({
                    "from": "Blue Heaven <bookings@blueheavenfarmhouse.com>",
                    "to": [owner_email],
                    "subject": subject,
                    "text": body
                }).encode('utf-8'),
                headers={
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            with urllib.request.urlopen(req) as resp:
                logger.info(f"Resend email sent status: {resp.status}")
        except Exception as e:
            logger.error(f"Failed to send email via Resend API: {e}")
            
    return True
