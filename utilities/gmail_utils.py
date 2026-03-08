"""
Gmail Utilities for Digital Empire Network
Handles email sending via Gmail SMTP with Google Cloud Secret Manager
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from google.cloud import secretmanager
from os import environ, path
from dotenv import load_dotenv
from typing import List, Optional, Dict

# Configure logging
logger = logging.getLogger('DigitalEmpire.Gmail')

# Define the project ID and secret IDs
PROJECT_ID = 'digital-empire-461123'  # Your project ID
GMAIL_USERNAME_SECRET_ID = 'gmail-username'  # Change from KUMORI_GMAIL_USERNAME
GMAIL_APP_PASSWORD_SECRET_ID = 'gmail-app-password'  # Change from KUMORI_GMAIL_APP_PASSWORD

def load_env_file() -> bool:
    """Load environment variables from .env file if it exists"""
    base_dir = path.abspath(path.join(path.dirname(__file__), '..'))
    dotenv_path = path.join(base_dir, '.env')
    if path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        logger.info("Loaded .env file")
        return True
    return False

def get_secret_version(project_id: str, secret_id: str, version_id: str = "latest") -> str:
    """Retrieve a secret from Google Cloud Secret Manager"""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode('UTF-8')
    except Exception as e:
        logger.error(f"Error accessing secret {secret_id}: {e}")
        raise

def get_gmail_credentials() -> Dict[str, str]:
    """
    Get Gmail credentials from environment variables or Secret Manager
    
    Returns:
        dict: Contains 'user' and 'password' keys
    """
    # First try environment variables (for local development)
    if load_env_file():
        gmail_user = environ.get('GMAIL_USER')
        gmail_password = environ.get('GMAIL_APP_PASSWORD')
        
        if gmail_user and gmail_password:
            logger.info("Using Gmail credentials from environment variables")
            return {
                'user': gmail_user,
                'password': gmail_password
            }
    
    # Fall back to Google Cloud Secret Manager (for production)
    logger.info("Loading Gmail credentials from Google Cloud Secret Manager")
    try:
        return {
            'user': get_secret_version(PROJECT_ID, GMAIL_USERNAME_SECRET_ID),
            'password': get_secret_version(PROJECT_ID, GMAIL_APP_PASSWORD_SECRET_ID),
        }
    except Exception as e:
        logger.error(f"Failed to load Gmail credentials: {e}")
        raise

# Cache credentials on module load
_gmail_credentials = None

def _get_cached_credentials() -> Dict[str, str]:
    """Get cached credentials or load them"""
    global _gmail_credentials
    if _gmail_credentials is None:
        _gmail_credentials = get_gmail_credentials()
    return _gmail_credentials

def send_email(
    subject: str,
    body: str,
    to_emails: List[str],
    attachment_paths: Optional[List[str]] = None,
    is_html: bool = False,
    from_name: str = "Digital Empire Network"
) -> bool:
    """
    Send an email using Gmail SMTP
    
    Args:
        subject: Email subject
        body: Email body content
        to_emails: List of recipient email addresses
        attachment_paths: Optional list of file paths to attach
        is_html: Whether the body is HTML content
        from_name: Display name for sender
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        credentials = _get_cached_credentials()
        gmail_user = credentials['user']
        gmail_password = credentials['password']
        
        # Create message
        message = MIMEMultipart()
        message['From'] = f'{from_name} <{gmail_user}>'
        message['To'] = ', '.join(to_emails)
        message['Subject'] = subject
        
        # Attach body
        if is_html:
            message.attach(MIMEText(body, 'html'))
        else:
            message.attach(MIMEText(body, 'plain'))
        
        # Add attachments if provided
        if attachment_paths:
            for attachment_path in attachment_paths:
                if not path.exists(attachment_path):
                    logger.warning(f"Attachment not found: {attachment_path}")
                    continue
                    
                part = MIMEBase('application', 'octet-stream')
                with open(attachment_path, 'rb') as file:
                    part.set_payload(file.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=path.basename(attachment_path)
                )
                message.attach(part)
        
        # Send email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_user, gmail_password)
            server.send_message(message)
            logger.info(f"Email sent successfully to {', '.join(to_emails)}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

def send_partnership_inquiry_notification(
    company_name: str,
    contact_email: str,
    message: str,
    admin_emails: Optional[List[str]] = None
) -> bool:
    """
    Send notification about new partnership inquiry
    
    Args:
        company_name: Name of the company inquiring
        contact_email: Contact email of the inquirer
        message: Inquiry message
        admin_emails: List of admin emails to notify
        
    Returns:
        bool: Success status
    """
    if admin_emails is None:
        admin_emails = ['kumoridotai@gmail.com']  # Using the Kumori email as default
    
    subject = f"New Partnership Inquiry from {company_name}"
    
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>New Partnership Inquiry</h2>
            <p><strong>Company:</strong> {company_name}</p>
            <p><strong>Contact Email:</strong> {contact_email}</p>
            <p><strong>Message:</strong></p>
            <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px;">
                {message}
            </div>
            <hr>
            <p style="color: #666; font-size: 12px;">
                This notification was sent from the Digital Empire Network website.
            </p>
        </body>
    </html>
    """
    
    return send_email(
        subject=subject,
        body=body,
        to_emails=admin_emails,
        is_html=True
    )

def send_media_kit_download_notification(
    email: str,
    company_name: Optional[str] = None
) -> bool:
    """
    Send notification when someone downloads the media kit
    
    Args:
        email: Email of the person downloading
        company_name: Optional company name
        
    Returns:
        bool: Success status
    """
    admin_emails = ['kumoridotai@gmail.com']  # Using the Kumori email
    
    subject = "Media Kit Download"
    
    company_info = f" from {company_name}" if company_name else ""
    
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h3>Media Kit Downloaded</h3>
            <p>The media kit was downloaded by:</p>
            <ul>
                <li><strong>Email:</strong> {email}</li>
                {"<li><strong>Company:</strong> " + company_name + "</li>" if company_name else ""}
                <li><strong>Time:</strong> {environ.get('TZ', 'UTC')} time</li>
            </ul>
        </body>
    </html>
    """
    
    return send_email(
        subject=subject,
        body=body,
        to_emails=admin_emails,
        is_html=True
    )

# Sample usage (for testing)
if __name__ == '__main__':
    # Test configuration
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)
    
    print("Gmail utilities loaded. Ready for use.")
    print(f"Project ID: {PROJECT_ID}")
    print(f"Gmail username secret: {GMAIL_USERNAME_SECRET_ID}")
    print(f"Gmail password secret: {GMAIL_APP_PASSWORD_SECRET_ID}")
    
    # Uncomment to test email sending
    # success = send_email(
    #     subject="Test Email from Digital Empire",
    #     body="This is a test email from the Digital Empire Network platform.",
    #     to_emails=["kumoridotai@gmail.com"]  # Send test to yourself
    # )
    # print(f"Email sent: {success}")