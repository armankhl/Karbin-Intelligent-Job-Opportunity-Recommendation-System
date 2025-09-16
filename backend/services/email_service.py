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

# ... (keep the existing send_verification_email function) ...

def send_recommendations_email(recipient_email: str, user_name: str, jobs: list[dict]) -> bool:
    """
    Sends a curated list of job recommendations to a user.
    """
    subject = f"{user_name} این فرصتهای شغلی مناسب شما هستند."

    # --- Build the HTML for the list of jobs ---
    jobs_html = ""
    for job in jobs:
        reason_data = job.get('reason', {})
        matched_skills = reason_data.get('matched_skills', [])
        
        reason_parts = []
        if matched_skills:
            reason_parts.append(f"متناسب با مهارت‌های شما در: {', '.join(matched_skills)}")
        else:
            reason_parts.append("شباهت بالا با رزومه شما")

        reason_text = " | ".join(reason_parts)

        jobs_html += f"""
        <div style="...">
            <h3 style="...">_build_job_texts_for_reranking</h3>
            <p style="...">🏢 {job['company_name']}</p>
            <p style="...">📍 {job.get('city', 'N/A')}</p>
            <p style="margin: 0 0 15px 0; color: #007bff; font-size: 14px;">✨ {reason_text}</p>
            <a href="{job['source_link']}" ...>مشاهده جزئیات</a>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head><meta charset="UTF-8"></head>
    <body style="font-family: 'Vazirmatn', sans-serif; text-align: right; color: #333; background-color: #f9f9f9; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background-color: #fff; border-radius: 12px; padding: 30px;">
            <h1>سلام {user_name}</h1>
            <p>بر اساس پروفایل و مهارت‌های شما، این فرصت‌های شغلی جدید را برایتان پیدا کرده‌ایم:</p>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
            {jobs_html}
            <p style="text-align: center; margin-top: 30px;">
                <a href="http://localhost:3000/recommendations" target="_blank" style="font-size: 16px;">
                    مشاهده همه پیشنهادات
                </a>
            </p>
        </div>
    </body>
    </html>
    """
    
    sender = {"name": SENDER_NAME, "email": SENDER_EMAIL}
    to = [{"email": recipient_email}]
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(to=to, sender=sender, subject=subject, html_content=html_content)

    try:
        api_instance.send_transac_email(send_smtp_email)
        print(f"Recommendations email sent successfully to {recipient_email}.")
        return True
    except ApiException as e:
        print(f"Exception when calling Brevo API: {e}\n")
        return False