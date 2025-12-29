import pytest
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class TestSMTP:

    def test_smtp_connection_port_587(self):
        """Test SMTP connection on submission port with STARTTLS"""
        server = smtplib.SMTP('localhost', 587, timeout=10)
        code, msg = server.ehlo()
        assert code == 250, f"EHLO failed with code {code}"

        code, msg = server.starttls()
        assert code == 220, f"STARTTLS failed with code {code}"
        server.quit()

    def test_smtp_authentication(self, smtp_connection, test_user):
        """Test SMTP authentication with valid credentials"""
        smtp_connection.starttls()
        smtp_connection.login(test_user['email'], test_user['password'])
        # If we get here without exception, auth succeeded

    def test_smtp_authentication_failure(self, smtp_connection, test_user):
        """Test SMTP authentication with invalid credentials"""
        smtp_connection.starttls()
        with pytest.raises(smtplib.SMTPAuthenticationError):
            smtp_connection.login(test_user['email'], 'wrongpassword')

    def test_send_email(self, authenticated_smtp, test_user):
        """Test sending an email through the mail server"""
        msg = MIMEMultipart()
        msg['From'] = 'sender@example.com'
        msg['To'] = test_user['email']
        msg['Subject'] = 'Test Email'
        msg.attach(MIMEText('This is a test email body', 'plain'))

        authenticated_smtp.send_message(msg)

    @pytest.mark.slow
    def test_message_within_size_limit(self, authenticated_smtp, test_user):
        """Test that messages within the size limit are sent"""
        large_body = 'X' * (19 * 1024 * 1024)  # ~19MB

        msg = MIMEMultipart()
        msg['From'] = test_user['email']
        msg['To'] = test_user['email']
        msg['Subject'] = 'Large Test Email'
        msg.attach(MIMEText(large_body, 'plain'))

        authenticated_smtp.send_message(msg)

    @pytest.mark.slow
    def test_message_size_over_limit(self, authenticated_smtp, test_user):
        """Test that messages exceeding size limit are rejected"""
        large_body = 'X' * (21 * 1024 * 1024)  # 21MB

        msg = MIMEMultipart()
        msg['From'] = 'sender@example.com'
        msg['To'] = test_user['email']
        msg['Subject'] = 'Large Test Email'
        msg.attach(MIMEText(large_body, 'plain'))

        with pytest.raises(smtplib.SMTPSenderRefused):
            authenticated_smtp.send_message(msg)
