import os
import requests

def send_whatsapp_message(to_number, message):
    token = os.getenv("META_WHATSAPP_TOKEN")
    phone_number_id = os.getenv("META_PHONE_NUMBER_ID")
    version = os.getenv("META_WHATSAPP_VERSION", "v20.0")

    if not (token and phone_number_id):
        print("❌ Meta WhatsApp credentials missing in environment variables")
        return False

    url = f"https://graph.facebook.com/{version}/{phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": f"91{to_number}",   # ✅ सिर्फ नंबर, बिना '+' और बिना 'whatsapp:'
        "type": "text",
        "text": {
            "body": message
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"✅ WhatsApp message sent to {to_number}")
            return True
        else:
            print(f"❌ Failed to send WhatsApp: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception while sending WhatsApp: {e}")
        return False
