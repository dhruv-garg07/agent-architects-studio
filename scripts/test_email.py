
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utlis.email_service import get_email_service
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_email_sending():
    """
    Test the EmailService by sending a test email to a provided address.
    """
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/test_email.py <recipient_email>")
        return

    recipient_email = sys.argv[1]
    
    print(f"Testing email sending to: {recipient_email}")
    print(f"Using Sender: {os.environ.get('SENDER_EMAIL')}")
    
    email_service = get_email_service()
    
    subject = "Test Email from Agent Architects Studio"
    body = "This is a test email to verify the email service configuration.\n\nTime: " + str(os.popen('date').read().strip())
    
    # Try synchronous sending first for immediate feedback
    print("Attempting to send email (SYNC)...")
    success = email_service.send_email_sync(recipient_email, subject + " (SYNC)", body)
    
    if success:
        print("✅ SYNC Email sent successfully!")
    else:
        print("❌ SYNC Failed to send email.")

    # Try async sending
    print("\nAttempting to send email (ASYNC)...")
    import time
    def callback(success, error):
        if success:
            print("✅ ASYNC Email sent successfully!")
        else:
            print(f"❌ ASYNC Failed to send email: {error}")
            
    email_service.send_email_async(recipient_email, subject + " (ASYNC)", body, callback)
    
    print("Waiting for async worker...")
    time.sleep(5)  # Wait for worker to process
    print("Done waiting.")

if __name__ == "__main__":
    test_email_sending()
