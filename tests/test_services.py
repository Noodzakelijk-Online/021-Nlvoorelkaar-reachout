"""
Comprehensive Test Suite for NLvoorElkaar Tool
Addresses TODO items #16: Technical Debt - Unit Tests
"""

import unittest
import os
import sys
import tempfile
import sqlite3
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSecureCredentials(unittest.TestCase):
    """Test secure credential management"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cred_file = os.path.join(self.temp_dir, 'credentials.enc')
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_credential_encryption(self):
        """Test that credentials are encrypted"""
        from utils.secure_credentials import SecureCredentialManager
        
        manager = SecureCredentialManager(self.cred_file)
        manager.set_master_password('test_password_123')
        
        # Store credentials
        manager.store_credential('test_service', 'username', 'secret_value')
        
        # Read raw file - should be encrypted
        with open(self.cred_file, 'rb') as f:
            content = f.read()
        
        self.assertNotIn(b'secret_value', content)
        self.assertNotIn(b'username', content)
    
    def test_credential_retrieval(self):
        """Test credential retrieval"""
        from utils.secure_credentials import SecureCredentialManager
        
        manager = SecureCredentialManager(self.cred_file)
        manager.set_master_password('test_password_123')
        
        # Store and retrieve
        manager.store_credential('test_service', 'username', 'my_secret')
        retrieved = manager.get_credential('test_service', 'username')
        
        self.assertEqual(retrieved, 'my_secret')
    
    def test_wrong_password_fails(self):
        """Test that wrong password fails"""
        from utils.secure_credentials import SecureCredentialManager
        
        manager1 = SecureCredentialManager(self.cred_file)
        manager1.set_master_password('correct_password')
        manager1.store_credential('test', 'key', 'value')
        
        # Try with wrong password
        manager2 = SecureCredentialManager(self.cred_file)
        manager2.set_master_password('wrong_password')
        
        with self.assertRaises(Exception):
            manager2.get_credential('test', 'key')


class TestEnhancedSessionManager(unittest.TestCase):
    """Test enhanced session manager"""
    
    def test_session_creation(self):
        """Test session creation"""
        from models.enhanced_session_manager import EnhancedSessionManager
        
        manager = EnhancedSessionManager()
        session = manager.get_session()
        
        self.assertIsNotNone(session)
        self.assertIn('User-Agent', session.headers)
    
    def test_rate_limiting(self):
        """Test rate limiting"""
        from models.enhanced_session_manager import EnhancedSessionManager
        
        manager = EnhancedSessionManager()
        manager.min_request_interval = 0.1  # 100ms for testing
        
        import time
        start = time.time()
        
        # Make multiple requests
        for _ in range(3):
            manager._apply_rate_limit()
        
        elapsed = time.time() - start
        self.assertGreaterEqual(elapsed, 0.2)  # At least 200ms for 3 requests
    
    @patch('requests.Session.get')
    def test_retry_logic(self, mock_get):
        """Test retry logic on failure"""
        from models.enhanced_session_manager import EnhancedSessionManager
        
        # First two calls fail, third succeeds
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'success'
        
        mock_get.side_effect = [
            Exception("Network error"),
            Exception("Network error"),
            mock_response
        ]
        
        manager = EnhancedSessionManager()
        manager.max_retries = 3
        manager.retry_delay = 0.01  # Fast retry for testing
        
        result = manager.get_with_retry('http://test.com')
        
        self.assertEqual(result.text, 'success')
        self.assertEqual(mock_get.call_count, 3)


class TestMessageQueue(unittest.TestCase):
    """Test message queue system"""
    
    def setUp(self):
        self.temp_db = tempfile.mktemp(suffix='.db')
    
    def tearDown(self):
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
    
    def test_queue_message(self):
        """Test queuing a message"""
        from services.message_queue import MessageQueue
        
        queue = MessageQueue(self.temp_db)
        
        msg_id = queue.enqueue(
            recipient_id='vol_123',
            recipient_name='Test User',
            subject='Test Subject',
            body='Test Body'
        )
        
        self.assertIsNotNone(msg_id)
        self.assertGreater(msg_id, 0)
    
    def test_get_pending_messages(self):
        """Test getting pending messages"""
        from services.message_queue import MessageQueue
        
        queue = MessageQueue(self.temp_db)
        
        # Queue multiple messages
        queue.enqueue('vol_1', 'User 1', 'Subject 1', 'Body 1')
        queue.enqueue('vol_2', 'User 2', 'Subject 2', 'Body 2')
        
        pending = queue.get_pending(limit=10)
        
        self.assertEqual(len(pending), 2)
    
    def test_mark_sent(self):
        """Test marking message as sent"""
        from services.message_queue import MessageQueue
        
        queue = MessageQueue(self.temp_db)
        
        msg_id = queue.enqueue('vol_1', 'User', 'Subject', 'Body')
        queue.mark_sent(msg_id)
        
        pending = queue.get_pending()
        self.assertEqual(len(pending), 0)


class TestEnhancedVolunteerService(unittest.TestCase):
    """Test enhanced volunteer service"""
    
    def setUp(self):
        self.temp_db = tempfile.mktemp(suffix='.db')
        self._init_db()
    
    def tearDown(self):
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
    
    def _init_db(self):
        """Initialize test database"""
        with sqlite3.connect(self.temp_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS volunteers (
                    id INTEGER PRIMARY KEY,
                    profile_id TEXT UNIQUE,
                    name TEXT,
                    location TEXT,
                    description TEXT,
                    profile_url TEXT,
                    first_seen TEXT,
                    last_seen TEXT,
                    last_updated TEXT,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS scrape_sessions (
                    id INTEGER PRIMARY KEY,
                    status TEXT,
                    last_updated TEXT,
                    current_page INTEGER,
                    total_pages INTEGER,
                    volunteers_found INTEGER
                )
            ''')
            conn.commit()
    
    def test_save_volunteer(self):
        """Test saving volunteer"""
        from services.enhanced_volunteer_service import EnhancedVolunteerService
        
        service = EnhancedVolunteerService(self.temp_db, Mock())
        
        volunteer = {
            'profile_id': 'vol_123',
            'name': 'Test Volunteer',
            'location': 'Amsterdam',
            'description': 'Test description'
        }
        
        service.save_volunteer(volunteer)
        
        # Verify saved
        with sqlite3.connect(self.temp_db) as conn:
            cursor = conn.execute(
                'SELECT name FROM volunteers WHERE profile_id = ?',
                ('vol_123',)
            )
            row = cursor.fetchone()
            self.assertEqual(row[0], 'Test Volunteer')
    
    def test_deduplication(self):
        """Test volunteer deduplication"""
        from services.enhanced_volunteer_service import EnhancedVolunteerService
        
        service = EnhancedVolunteerService(self.temp_db, Mock())
        
        # Save same volunteer twice
        volunteer = {
            'profile_id': 'vol_123',
            'name': 'Test Volunteer',
            'location': 'Amsterdam'
        }
        
        service.save_volunteer(volunteer)
        service.save_volunteer(volunteer)
        
        # Should only have one record
        with sqlite3.connect(self.temp_db) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM volunteers')
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)


class TestEnhancedMessagingService(unittest.TestCase):
    """Test enhanced messaging service"""
    
    def setUp(self):
        self.temp_db = tempfile.mktemp(suffix='.db')
    
    def tearDown(self):
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
    
    def test_template_rendering(self):
        """Test message template rendering"""
        from services.enhanced_messaging_service import EnhancedMessagingService
        
        service = EnhancedMessagingService(self.temp_db, Mock())
        
        template = "Beste {naam}, welkom in {locatie}!"
        variables = {'naam': 'Jan', 'locatie': 'Amsterdam'}
        
        result = service.render_template(template, variables)
        
        self.assertEqual(result, "Beste Jan, welkom in Amsterdam!")
    
    def test_template_validation(self):
        """Test template validation"""
        from services.enhanced_messaging_service import EnhancedMessagingService
        
        service = EnhancedMessagingService(self.temp_db, Mock())
        
        # Valid template
        valid = service.validate_template("Hallo {naam}!")
        self.assertTrue(valid['is_valid'])
        
        # Invalid template (unclosed brace)
        invalid = service.validate_template("Hallo {naam!")
        self.assertFalse(invalid['is_valid'])


class TestDataExporter(unittest.TestCase):
    """Test data export functionality"""
    
    def setUp(self):
        self.temp_db = tempfile.mktemp(suffix='.db')
        self.temp_dir = tempfile.mkdtemp()
        self._init_db()
    
    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _init_db(self):
        """Initialize test database with sample data"""
        with sqlite3.connect(self.temp_db) as conn:
            conn.execute('''
                CREATE TABLE volunteers (
                    id INTEGER PRIMARY KEY,
                    profile_id TEXT,
                    name TEXT,
                    location TEXT,
                    description TEXT,
                    skills TEXT,
                    availability TEXT,
                    contact_info TEXT,
                    profile_url TEXT,
                    first_seen TEXT,
                    last_seen TEXT,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            
            # Insert test data
            conn.execute('''
                INSERT INTO volunteers 
                (profile_id, name, location, description, first_seen, last_seen, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ('vol_1', 'Jan Jansen', 'Amsterdam', 'Test', 
                  datetime.now().isoformat(), datetime.now().isoformat(), 1))
            
            conn.commit()
    
    def test_export_csv(self):
        """Test CSV export"""
        from services.data_management import DataExporter, ExportConfig, ExportFormat
        
        exporter = DataExporter(self.temp_db)
        output_path = os.path.join(self.temp_dir, 'volunteers.csv')
        
        config = ExportConfig(format=ExportFormat.CSV)
        count = exporter.export_volunteers(output_path, config)
        
        self.assertEqual(count, 1)
        self.assertTrue(os.path.exists(output_path))
        
        # Verify content
        with open(output_path, 'r') as f:
            content = f.read()
            self.assertIn('Jan Jansen', content)
    
    def test_export_json(self):
        """Test JSON export"""
        from services.data_management import DataExporter, ExportConfig, ExportFormat
        
        exporter = DataExporter(self.temp_db)
        output_path = os.path.join(self.temp_dir, 'volunteers.json')
        
        config = ExportConfig(format=ExportFormat.JSON)
        count = exporter.export_volunteers(output_path, config)
        
        self.assertEqual(count, 1)
        
        # Verify JSON structure
        with open(output_path, 'r') as f:
            data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['name'], 'Jan Jansen')


class TestReportGenerator(unittest.TestCase):
    """Test report generation"""
    
    def setUp(self):
        self.temp_db = tempfile.mktemp(suffix='.db')
        self._init_db()
    
    def tearDown(self):
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
    
    def _init_db(self):
        """Initialize test database"""
        with sqlite3.connect(self.temp_db) as conn:
            conn.executescript('''
                CREATE TABLE volunteers (
                    id INTEGER PRIMARY KEY,
                    profile_id TEXT,
                    name TEXT,
                    first_seen TEXT,
                    last_seen TEXT,
                    is_active INTEGER DEFAULT 1
                );
                
                CREATE TABLE scheduled_messages (
                    id INTEGER PRIMARY KEY,
                    status TEXT,
                    created_at TEXT,
                    sent_at TEXT
                );
                
                CREATE TABLE reminders (
                    id INTEGER PRIMARY KEY,
                    status TEXT,
                    created_at TEXT
                );
            ''')
            conn.commit()
    
    def test_generate_activity_report(self):
        """Test activity report generation"""
        from services.data_management import ReportGenerator
        
        generator = ReportGenerator(self.temp_db)
        report = generator.generate_activity_report('this_week')
        
        self.assertIn('title', report)
        self.assertIn('sections', report)
        self.assertIn('volunteers', report['sections'])
        self.assertIn('messages', report['sections'])


class TestErrorHandler(unittest.TestCase):
    """Test error handling"""
    
    def test_error_categorization(self):
        """Test error categorization"""
        from utils.error_handler import ErrorHandler, ErrorCategory
        
        handler = ErrorHandler()
        
        # Network error
        category = handler.categorize_error(ConnectionError("Network failed"))
        self.assertEqual(category, ErrorCategory.NETWORK)
        
        # Auth error
        category = handler.categorize_error(PermissionError("Access denied"))
        self.assertEqual(category, ErrorCategory.AUTHENTICATION)
    
    def test_user_friendly_message(self):
        """Test user-friendly error messages"""
        from utils.error_handler import ErrorHandler, ErrorCategory
        
        handler = ErrorHandler()
        
        message = handler.get_user_message(ErrorCategory.NETWORK)
        
        # Should be in Dutch
        self.assertIn('verbinding', message.lower())


class TestEnhancedLogging(unittest.TestCase):
    """Test enhanced logging"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_log_file_creation(self):
        """Test log file creation"""
        from utils.enhanced_logging import setup_logging
        
        log_file = os.path.join(self.temp_dir, 'test.log')
        logger = setup_logging(log_file=log_file)
        
        logger.info("Test message")
        
        self.assertTrue(os.path.exists(log_file))
    
    def test_log_levels(self):
        """Test different log levels"""
        from utils.enhanced_logging import setup_logging
        import logging
        
        log_file = os.path.join(self.temp_dir, 'test.log')
        logger = setup_logging(log_file=log_file, level=logging.DEBUG)
        
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        with open(log_file, 'r') as f:
            content = f.read()
            self.assertIn("Debug message", content)
            self.assertIn("Error message", content)


class TestBlacklistService(unittest.TestCase):
    """Test blacklist service"""
    
    def setUp(self):
        self.temp_db = tempfile.mktemp(suffix='.db')
        self._init_db()
    
    def tearDown(self):
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
    
    def _init_db(self):
        """Initialize test database"""
        with sqlite3.connect(self.temp_db) as conn:
            conn.execute('''
                CREATE TABLE blacklist (
                    id INTEGER PRIMARY KEY,
                    profile_id TEXT UNIQUE,
                    name TEXT,
                    reason TEXT,
                    notes TEXT,
                    added_at TEXT,
                    expires_at TEXT,
                    is_permanent INTEGER DEFAULT 0
                )
            ''')
            conn.commit()
    
    def test_add_to_blacklist(self):
        """Test adding to blacklist"""
        from services.enhanced_reminder_blacklist import EnhancedBlacklistService
        
        service = EnhancedBlacklistService(self.temp_db)
        
        service.add_to_blacklist(
            profile_id='vol_123',
            name='Test User',
            reason='no_response'
        )
        
        self.assertTrue(service.is_blacklisted('vol_123'))
    
    def test_temporary_blacklist(self):
        """Test temporary blacklist expiration"""
        from services.enhanced_reminder_blacklist import EnhancedBlacklistService
        
        service = EnhancedBlacklistService(self.temp_db)
        
        # Add with expiration in the past
        with sqlite3.connect(self.temp_db) as conn:
            conn.execute('''
                INSERT INTO blacklist (profile_id, name, reason, added_at, expires_at, is_permanent)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                'vol_expired',
                'Expired User',
                'test',
                (datetime.now() - timedelta(days=31)).isoformat(),
                (datetime.now() - timedelta(days=1)).isoformat(),
                0
            ))
            conn.commit()
        
        # Should not be blacklisted (expired)
        self.assertFalse(service.is_blacklisted('vol_expired'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
