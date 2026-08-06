import os
import requests

def send_whatsapp_template(to_number, template_name, template_language, parameters=[]):
    """
    WhatsApp template message भेजने के लिए
    :param to_number: receiver number (without +91)
    :param template_name: Meta console में बनाया गया template का नाम
    :param template_language: template language code, जैसे 'en_US'
    :param parameters: template में dynamic variables की list
                       example: ["Party Name", "Order ID", "₹1000"]
    """
    token = os.getenv("META_WHATSAPP_TOKEN")
    
    if not token:
        print("❌ Spur WhatsApp token (META_WHATSAPP_TOKEN) missing in environment variables")
        return False

    url = "https://api.spurnow.com/send-message"

    # template parameters
    components = []
    if parameters:
        components = [{
            "type": "body",
            "parameters": [{"type": "text", "text": str(p)} for p in parameters]
        }]

    payload = {
        "channel": "whatsapp",
        "to": f"91{to_number}",
        "content": {
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": template_language},
                "components": components
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            print(f"✅ WhatsApp template sent to {to_number}")
            return True
        else:
            print(f"❌ Failed to send WhatsApp template: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception while sending WhatsApp template: {e}")
        return False