import pytest
import docker
import time
import smtplib
from imapclient import IMAPClient
import psycopg2
import logging
import subprocess
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to docker-compose file
TEST_DIR = Path(__file__).parent
COMPOSE_FILE = TEST_DIR / "docker-compose.test.yml"

@pytest.fixture(scope="session")
def docker_client():
    """Docker client for container management"""
    return docker.from_env()

@pytest.fixture(scope="session", autouse=True)
def docker_compose_services():
    """Start docker-compose services for the test session"""
    # Check if services are already running
    result = subprocess.run(
        ["docker-compose", "-f", str(COMPOSE_FILE), "ps", "-q"],
        capture_output=True,
        text=True
    )

    services_running = bool(result.stdout.strip())

    if not services_running:
        logger.info("Starting docker-compose services...")
        subprocess.run(
            ["docker-compose", "-f", str(COMPOSE_FILE), "up", "-d"],
            check=True
        )
        logger.info("Services started")
    else:
        logger.info("Services already running")

    yield

    # Note: We don't stop services here - let bin/test handle cleanup
    # This allows for --keep flag to work properly

def wait_for_port(host, port, timeout=60):
    """Wait for a port to be available"""
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except:
            pass
        time.sleep(1)
    return False

@pytest.fixture(scope="session")
def wait_for_services(docker_client, docker_compose_services):
    """Wait for all services to be healthy"""
    timeout = 120
    start = time.time()

    required_services = ['postfix_test_mail', 'postfix_test_postgres', 'postfix_test_admin']
    required_ports = {
        'postgres': 5432,
        'postfixadmin': 8181,
        'smtp': 587,
        'imap': 993
    }

    logger.info("Waiting for services to become healthy...")

    # First wait for containers to be running
    while time.time() - start < timeout:
        try:
            all_running = True
            for service_name in required_services:
                try:
                    container = docker_client.containers.get(service_name)
                    if container.status != 'running':
                        all_running = False
                        logger.debug(f"{service_name} is {container.status}")
                        break
                except docker.errors.NotFound:
                    all_running = False
                    logger.debug(f"{service_name} not found")
                    break

            if all_running:
                logger.info("All containers are running")
                break
        except Exception as e:
            logger.debug(f"Error checking containers: {e}")

        time.sleep(2)
    else:
        raise TimeoutError("Containers did not start in time")

    # Now wait for ports to be available
    logger.info("Waiting for service ports...")
    for service, port in required_ports.items():
        logger.info(f"Waiting for {service} on port {port}...")
        if not wait_for_port('localhost', port, timeout=60):
            raise TimeoutError(f"Port {port} ({service}) did not become available")

    # Additional wait for services to fully initialize
    logger.info("Services are up, waiting for full initialization (15s)...")
    time.sleep(15)

    return True

@pytest.fixture
def test_user():
    """Test user credentials"""
    return {
        'email': 'test@example.com',
        'password': 'testpassword123',
        'domain': 'example.com',
        'username': 'test'
    }

@pytest.fixture(scope="session")
def db_connection():
    """PostgreSQL connection for direct database verification"""
    max_retries = 10
    retry_delay = 3

    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='postfix',
                user='postfix',
                password='postfix_password',
                connect_timeout=10
            )
            logger.info("Successfully connected to PostgreSQL")
            yield conn
            conn.close()
            return
        except psycopg2.OperationalError as e:
            if attempt < max_retries - 1:
                logger.warning(f"Failed to connect to PostgreSQL (attempt {attempt + 1}/{max_retries}), retrying...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to PostgreSQL after {max_retries} attempts")
                raise

@pytest.fixture
def smtp_connection(wait_for_services):
    """Create SMTP connection for testing"""
    server = smtplib.SMTP('localhost', 587, timeout=10)
    server.set_debuglevel(0)
    yield server
    try:
        server.quit()
    except:
        pass

@pytest.fixture
def authenticated_smtp(smtp_connection, test_user):
    """SMTP connection with authentication"""
    smtp_connection.starttls()
    smtp_connection.login(test_user['email'], test_user['password'])
    return smtp_connection

@pytest.fixture
def setup_test_domain_and_user(db_connection, test_user):
    """Create test domain and user in the database"""
    cursor = db_connection.cursor()

    # Check if domain exists, if not create it
    cursor.execute("SELECT domain FROM domain WHERE domain = %s", (test_user['domain'],))
    if not cursor.fetchone():
        logger.info(f"Creating test domain: {test_user['domain']}")
        cursor.execute("""
                       INSERT INTO domain (domain, description, aliases, mailboxes, maxquota, quota, transport, backupmx, active)
                       VALUES (%s, 'Test domain', 10, 10, 0, 0, 'virtual', false, true)
                       """, (test_user['domain'],))
        db_connection.commit()

    # Check if mailbox exists, if not create it
    cursor.execute("SELECT username FROM mailbox WHERE username = %s", (test_user['email'],))
    if not cursor.fetchone():
        logger.info(f"Creating test user: {test_user['email']}")
        # Note: This is a hashed version of 'testpassword123' using MD5-CRYPT
        # In production, use proper password hashing via PostfixAdmin
        password_hash = '$1$12345678$CyVBb0dOWJsY3vUpgRQst0'
        cursor.execute("""
                       INSERT INTO mailbox (username, password, name, maildir, quota, local_part, domain, active, created, modified)
                       VALUES (%s, %s, 'Test User', %s, 512000000, %s, %s, true, NOW(), NOW())
                       """, (
                           test_user['email'],
                           password_hash,
                           f"{test_user['domain']}/{test_user['username']}/",
                           test_user['username'],
                           test_user['domain']
                       ))
        db_connection.commit()

    cursor.close()
    logger.info("✓ Test domain and user are ready")

    yield

    # Cleanup is optional - we destroy the whole database container anyway



@pytest.fixture
def imap_connection(wait_for_services, setup_test_domain_and_user):
    """Create IMAP connection for testing"""
    from imapclient import IMAPClient
    import ssl

    client = IMAPClient(
        'localhost',
        port=993,
        ssl=True,
        ssl_context=ssl._create_unverified_context()
    )

    yield client

    try:
        client.logout()
    except:
        pass
