"""
Email Service Utility for handling email sending with retry logic and async support.
"""

import os
import smtplib
import ssl
import threading
import logging
from typing import Optional, Callable
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from queue import Queue
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service with support for async sending, retry logic, and timeout handling.
    """

    def __init__(self):
        self.sender_email = os.environ.get('SENDER_EMAIL')
        self.sender_password = os.environ.get('SENDER_EMAIL_PASSWORD')
        print(f"Sender email: {self.sender_email}")
        print(f"Sender password: {self.sender_password}")
        self.smtp_host = "smtpout.secureserver.net"
        self.smtp_port = 465
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self.timeout = 10  # seconds for SMTP connection
        self.email_queue = Queue()
        self._start_email_worker()

    def _start_email_worker(self):
        """Start background worker thread for async email sending."""
        worker_thread = threading.Thread(target=self._email_worker, daemon=True)
        worker_thread.start()

    def _email_worker(self):
        """Background worker that processes emails from the queue."""
        while True:
            try:
                email_task = self.email_queue.get()
                if email_task is None:  # Shutdown signal
                    break
                
                receiver_email, subject, body, callback = email_task
                self._send_email_with_retry(receiver_email, subject, body, callback)
                self.email_queue.task_done()
            except Exception as e:
                logger.error(f"Error in email worker: {e}")

    def _send_email_with_retry(
        self,
        receiver_email: str,
        subject: str,
        body: str,
        callback: Optional[Callable] = None
    ) -> bool:
        """
        Send email with retry logic.

        Args:
            receiver_email: Recipient email address
            subject: Email subject
            body: Email body
            callback: Optional callback function(success: bool, error: str) after sending

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        for attempt in range(self.max_retries):
            try:
                # Create message
                msg = MIMEMultipart()
                msg['From'] = self.sender_email
                msg['To'] = receiver_email
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))

                # Create SSL context
                context = ssl.create_default_context()

                # Send email with timeout
                with smtplib.SMTP_SSL(
                    self.smtp_host,
                    self.smtp_port,
                    context=context,
                    timeout=self.timeout
                ) as server:
                    server.login(self.sender_email, self.sender_password)
                    server.sendmail(self.sender_email, receiver_email, msg.as_string())

                logger.info(f"Email sent successfully to {receiver_email}")
                if callback:
                    callback(True, None)
                return True

            except smtplib.SMTPException as smtp_err:
                logger.warning(
                    f"SMTP error on attempt {attempt + 1}/{self.max_retries}: {smtp_err}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    error_msg = f"Failed after {self.max_retries} attempts: {smtp_err}"
                    logger.error(error_msg)
                    if callback:
                        callback(False, error_msg)
                    return False

            except TimeoutError as timeout_err:
                logger.warning(
                    f"Timeout on attempt {attempt + 1}/{self.max_retries}: {timeout_err}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    error_msg = f"Timeout after {self.max_retries} attempts"
                    logger.error(error_msg)
                    if callback:
                        callback(False, error_msg)
                    return False

            except Exception as err:
                logger.error(f"Unexpected error on attempt {attempt + 1}/{self.max_retries}: {err}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    error_msg = f"Unexpected error after {self.max_retries} attempts: {err}"
                    logger.error(error_msg)
                    if callback:
                        callback(False, error_msg)
                    return False

        return False

    def send_email_async(
        self,
        receiver_email: str,
        subject: str,
        body: str,
        callback: Optional[Callable] = None
    ):
        """
        Send email asynchronously using background worker thread.

        Args:
            receiver_email: Recipient email address
            subject: Email subject
            body: Email body
            callback: Optional callback function(success: bool, error: str) after sending
        """
        self.email_queue.put((receiver_email, subject, body, callback))

    def send_email_sync(
        self,
        receiver_email: str,
        subject: str,
        body: str
    ) -> bool:
        """
        Send email synchronously (blocking call).

        Args:
            receiver_email: Recipient email address
            subject: Email subject
            body: Email body

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        return self._send_email_with_retry(receiver_email, subject, body)


# Create a singleton instance
_email_service = None


def get_email_service() -> EmailService:
    """Get or create the email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
