<content>
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

class EmailService:
    def __init__(self, smtp_server, smtp_port, username=None, password=None):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
    
    def send_email(self, to_email, subject, body, from_email=None):
        """
        Send an email using SMTP instead of shell commands
        
        Args:
            to_email (str): Recipient email address
            subject (str): Email subject (will be sanitized)
            body (str): Email body
            from_email (str, optional): Sender email address
        
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Sanitize subject to prevent command injection
            sanitized_subject = self._sanitize_subject(subject)
            
            # Create message
            message = MIMEMultipart()
            message["From"] = from_email or "noreply@example.com"
            message["To"] = to_email
            message["Subject"] = sanitized_subject
            
            # Add body to email
            message.attach(MIMEText(body, "plain"))
            
            # Connect to SMTP server and send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.username and self.password:
                    server.starttls()
                    server.login(self.username, self.password)
                
                server.send_message(message)
            
            return True
        
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def _sanitize_subject(self, subject):
        """
        Sanitize email subject to prevent command injection
        
        Args:
            subject (str): Original subject line
        
        Returns:
            str: Sanitized subject line
        """
        # Remove or escape shell metacharacters
        if not subject:
            return "No Subject"
        
        # Replace potentially dangerous characters
        sanitized = re.sub(r'[;&|`$><()]', '', subject)
        
        # Limit subject length (common email limit)
        if len(sanitized) > 78:
            sanitized = sanitized[:75] + "..."
        
        return sanitized.strip()

# Example usage:
# email_service = EmailService("smtp.example.com", 587, "username", "password")
# email_service.send_email("recipient@example.com", "Test Subject", "Test Body")
</content>