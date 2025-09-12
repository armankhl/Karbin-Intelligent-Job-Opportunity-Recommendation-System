import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

# --- Configuration ---
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = os.getenv('BREVO_API_KEY')
api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

SENDER_EMAIL = os.getenv('BREVO_SENDER_EMAIL')
SENDER_NAME = os.getenv('BREVO_SENDER_NAME')

def send_verification_email(recipient_email: str, verification_code: str) -> bool:
    """
    Sends a verification email using the Brevo API, now with a Persian template.

    Returns:
        bool: True if the email was sent successfully, False otherwise.
    """
    # --- REVISED: Persian Subject Line ---
    subject = f"کاربین | کد تایید ایمیل شما"
    
    # --- REVISED: Persian HTML Content with RTL support ---
    # We add `dir="rtl"` and font styling for a professional look.
    html_content = f"""
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
    </head>
    <body style="font-family: 'Vazirmatn', sans-serif; text-align: right; color: #333;">
        <h1>به کاربین خوش آمدید!</h1>
        <p>از ثبت‌نام شما سپاسگزاریم. لطفاً برای تایید آدرس ایمیل خود از کد زیر استفاده کنید:</p>
        
        <div style="background-color: #f2f2f2; border-radius: 8px; padding: 10px 20px; margin: 20px 0;">
            <h2 style="font-size: 28px; letter-spacing: 4px; text-align: center; color: #000; margin: 0;">
                {verification_code}
            </h2>
        </div>
        
        <p>این کد تا ۱۵ دقیقه دیگر معتبر است.</p>
        <p>اگر شما در کاربین ثبت‌نام نکرده‌اید، می‌توانید این ایمیل را نادیده بگیرید.</p>
        <br>
        <p>با احترام،<br>تیم کاربین</p>
    </body>
    </html>
    """
    
    sender = {"name": SENDER_NAME, "email": SENDER_EMAIL}
    to = [{"email": recipient_email}]
    
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        html_content=html_content
    )

    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        print(f"Brevo API response: {api_response}")
        return True
    except ApiException as e:
        print(f"Exception when calling Brevo API: {e}\n")
        return False