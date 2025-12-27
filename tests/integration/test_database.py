import pytest

class TestDatabase:

    def test_database_connection(self, db_connection):
        """Test PostgreSQL database connectivity"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        assert result[0] == 1

    def test_postfixadmin_schema(self, db_connection):
        """Verify PostfixAdmin schema exists"""
        cursor = db_connection.cursor()
        cursor.execute("""
                       SELECT table_name
                       FROM information_schema.tables
                       WHERE table_schema = 'public'
                         AND table_name IN ('domain', 'mailbox', 'alias')
                       """)

        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()

        assert 'domain' in tables
        assert 'mailbox' in tables
        assert 'alias' in tables

    def test_virtual_domain_query(self, db_connection, setup_test_domain_and_user, test_user):
        """Test virtual domain lookup"""
        cursor = db_connection.cursor()
        cursor.execute(
            "SELECT domain FROM domain WHERE domain = %s AND active = true",
            (test_user['domain'],)
        )
        result = cursor.fetchone()
        cursor.close()
        assert result is not None, f"Domain {test_user['domain']} should exist"
        assert result[0] == test_user['domain']
