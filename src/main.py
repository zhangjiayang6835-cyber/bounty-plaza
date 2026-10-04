<content>
from email_service import EmailService

def send_notification_email(user_email, subject, message_body):
    """
    Send a notification email to the user
    
    Args:
        user_email (str): User's email address
        subject (str): Email subject
        message_body (str): Email body content
    
    Returns:
        bool: True if email was sent successfully
    """
    # Initialize email service with SMTP configuration
    # In a real application, these would come from environment variables or config
    smtp_config = {
        "smtp_server": "smtp.example.com",
        "smtp_port": 587,
        "username": "your-email@example.com",
        "password": "your-password"
    }
    
    email_service = EmailService(**smtp_config)
    
    # Send email using the secure method
    return email_service.send_email(user_email, subject, message_body)

# Example of how this would be used in the application:
# if send_notification_email(user.email, "Your Account Update", "Your account has been updated."):
#     print("Email sent successfully")
# else:
#     print("Failed to send email")
</content>