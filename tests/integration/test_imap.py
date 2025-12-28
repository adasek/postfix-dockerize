import pytest
from imapclient import IMAPClient
import ssl

class TestIMAP:

    def test_imap_connection(self, imap_connection):
        """Test IMAP SSL connection"""
        client = IMAPClient('localhost', port=993, ssl=True,
                            ssl_context=ssl._create_unverified_context())
        client.logout()

    def test_imap_authentication(self, imap_connection, test_user):
        """Test IMAP authentication"""
        imap_connection.login(test_user['email'], test_user['password'])
        # If we get here without exception, auth succeeded

    def test_imap_authentication_failure(self, imap_connection, test_user):
        """Test IMAP authentication with wrong password"""
        client = IMAPClient('localhost', port=993, ssl=True,
                            ssl_context=ssl._create_unverified_context())

        with pytest.raises(Exception):
            client.login(test_user['email'], 'wrongpassword')

        try:
            client.logout()
        except:
            pass

    def test_imap_list_folders(self, imap_connection, test_user):
        """Test listing IMAP folders"""
        imap_connection.login(test_user['email'], test_user['password'])
        folders = imap_connection.list_folders()

        assert len(folders) > 0, "Should have at least INBOX"
        folder_names = [str(folder) for folder in folders]
        assert any('INBOX' in name for name in folder_names)
