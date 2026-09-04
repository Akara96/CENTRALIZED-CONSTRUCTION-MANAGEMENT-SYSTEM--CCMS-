import os
from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import strip_tags

try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False


def send_notification_email(recipient_email, subject, html_message):
    """Kirim notifikasi via email"""
    plain_message = strip_tags(html_message)
    from_email = settings.DEFAULT_FROM_EMAIL
    try:
        send_mail(
            subject,
            plain_message,
            from_email,
            [recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def send_notification_whatsapp(recipient_phone, message):
    """Kirim notifikasi via WhatsApp (menggunakan Twilio)"""
    if not TWILIO_AVAILABLE or not settings.TWILIO_ACCOUNT_SID:
        print("Twilio tidak dikonfigurasi, lewati pengiriman WhatsApp")
        return False
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            from_=f"whatsapp:{settings.TWILIO_PHONE_NUMBER}",
            body=message,
            to=f"whatsapp:{recipient_phone}"
        )
        return True
    except Exception as e:
        print(f"Error sending WhatsApp: {e}")
        return False


def create_and_send_notification(recipient_user, title, message, notification_type='INFO', send_email=False, send_whatsapp=False):
    """Buat notifikasi di database dan kirim via email/WhatsApp jika diaktifkan"""
    from .models import Notification
    
    # Buat notifikasi di database
    notification = Notification.objects.create(
        recipient=recipient_user,
        title=title,
        message=message,
        notification_type=notification_type,
        status='UNREAD'
    )
    
    # Kirim email jika diaktifkan
    if send_email and recipient_user.email:
        html_content = f"""
        <html>
            <body>
                <h2>{title}</h2>
                <p>{message}</p>
                <br>
                <p>Terima kasih,</p>
                <p><i>CCMS - Centralized Construction Management System</i></p>
            </body>
        </html>
        """
        send_notification_email(recipient_user.email, title, html_content)
    
    # Kirim WhatsApp jika diaktifkan dan user punya nomor telepon
    if send_whatsapp:
        from .models import UserProfile
        try:
            profile = UserProfile.objects.get(user=recipient_user)
            if profile.phone:
                whatsapp_message = f"[CCMS] {title}\n{message}"
                send_notification_whatsapp(profile.phone, whatsapp_message)
        except UserProfile.DoesNotExist:
            pass
    
    return notification
