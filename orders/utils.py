from twilio.rest import Client
import os

def send_whatsapp_message(to_number, message):
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")

    if not (account_sid and auth_token and from_whatsapp_number):
        print("❌ Twilio credentials missing in environment variables")
        return False

    client = Client(account_sid, auth_token)

    try:
        client.messages.create(
            from_=from_whatsapp_number,
            body=message,
            to=f"whatsapp:+91{to_number}"  # CRM का नंबर
        )
        print(f"✅ WhatsApp message sent to {to_number}")
        return True
    except Exception as e:
        print(f"❌ Failed to send WhatsApp: {e}")
        return False
