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
import gc
from contextlib import closing
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def secure_temp_path(test_case, suffix):
    """Create a non-racy temporary path and register best-effort cleanup."""
    descriptor, path = tempfile.mkstemp(suffix=suffix)
    os.close(descriptor)

    def cleanup():
        gc.collect()
        try:
            os.remove(path)
        except (FileNotFoundError, PermissionError):
            pass

    test_case.addCleanup(cleanup)
    return path


class TestSecureCredentials(unittest.TestCase):
    """Test secure credential management"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cred_file = os.path.join(self.temp_dir, 'credentials.enc')
    
    def tearDown(self):
        import shutil
        gc.collect()
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


class TestBackupManager(unittest.TestCase):
    """Test local backup safety behavior."""

    def setUp(self):
        import shutil

        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.temp_dir, 'data')
        self.backup_dir = os.path.join(self.temp_dir, 'backups')
        os.makedirs(self.data_dir)
        self._shutil = shutil

    def tearDown(self):
        gc.collect()
        self._shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_backup_excludes_credentials_and_tokens(self):
        """Backups include data but skip credential/token-like files."""
        import zipfile
        from utils.backup_manager import BackupManager

        with open(os.path.join(self.data_dir, 'volunteers.db'), 'w') as f:
            f.write('ledger data')
        with open(os.path.join(self.data_dir, 'google_token.json'), 'w') as f:
            f.write('token')
        with open(os.path.join(self.data_dir, 'credentials.enc'), 'w') as f:
            f.write('encrypted credentials')

        manager = BackupManager(self.data_dir, self.backup_dir)
        backup_path = manager.create_backup('safe_backup')

        metadata = manager.read_backup_metadata(backup_path)
        self.assertIn('volunteers.db', metadata['included_files'])
        self.assertIn('google_token.json', metadata['excluded_files'])
        self.assertIn('credentials.enc', metadata['excluded_files'])

        with zipfile.ZipFile(backup_path, 'r') as backup_zip:
            names = backup_zip.namelist()
        self.assertIn('data/volunteers.db', names)
        self.assertNotIn('data/google_token.json', names)
        self.assertNotIn('data/credentials.enc', names)

    def test_create_backup_sanitizes_backup_name(self):
        """Unsafe backup names are normalized to safe filesystem filenames."""
        from utils.backup_manager import BackupManager

        with open(os.path.join(self.data_dir, 'volunteers.db'), 'w') as f:
            f.write('ledger data')

        manager = BackupManager(self.data_dir, self.backup_dir)
        backup_path = manager.create_backup("../../../../unsafe//name")

        self.assertTrue(os.path.isfile(backup_path))
        backup_file = os.path.basename(backup_path)
        self.assertNotIn("..", backup_file)
        self.assertNotIn("/", backup_file)
        self.assertTrue(backup_file.endswith(".zip"))

    def test_restore_rejects_path_traversal_before_deleting_data(self):
        """Unsafe backup members are rejected before current data is removed."""
        import zipfile
        from utils.backup_manager import BackupManager

        existing_path = os.path.join(self.data_dir, 'volunteers.db')
        with open(existing_path, 'w') as f:
            f.write('existing data')

        backup_path = os.path.join(self.backup_dir, 'unsafe.zip')
        os.makedirs(self.backup_dir, exist_ok=True)
        with zipfile.ZipFile(backup_path, 'w') as backup_zip:
            backup_zip.writestr('../escape.txt', 'unsafe')
            backup_zip.writestr('backup_metadata.json', json.dumps({'backup_date': datetime.now().isoformat()}))

        manager = BackupManager(self.data_dir, self.backup_dir)
        self.assertFalse(manager.restore_backup(backup_path))
        self.assertTrue(os.path.exists(existing_path))

    def test_backup_completion_records_audit_event(self):
        """Completed backup tasks are recorded in the operating audit log."""
        from database.database_manager import DatabaseManager
        from main import EnhancedNLvoorelkaarApp
        from utils.backup_manager import BackupManager

        db_path = os.path.join(self.temp_dir, 'audit.db')
        db = DatabaseManager(db_path)
        manager = BackupManager(self.data_dir, self.backup_dir)
        with open(os.path.join(self.data_dir, 'volunteers.db'), 'w') as f:
            f.write('ledger data')
        backup_path = manager.create_backup('audited_backup')

        app = EnhancedNLvoorelkaarApp.__new__(EnhancedNLvoorelkaarApp)
        app.backup_manager = manager
        app.database_manager = db
        app.ui = None

        class Status:
            value = 'completed'

        class Task:
            result = backup_path
            status = Status()

        EnhancedNLvoorelkaarApp._on_backup_completed(app, Task())

        audit_events = db.get_audit_events(entity_type='backup')
        self.assertEqual(len(audit_events), 1)
        self.assertEqual(audit_events[0]['action'], 'backup_completed')

    def test_restore_failure_audit_records_error_type_only(self):
        """Restore failures are auditable without raw exception text."""
        from database.database_manager import DatabaseManager
        from main import EnhancedNLvoorelkaarApp

        db_path = os.path.join(self.temp_dir, 'restore-audit.db')
        db = DatabaseManager(db_path)

        app = EnhancedNLvoorelkaarApp.__new__(EnhancedNLvoorelkaarApp)
        app.database_manager = db
        app.backup_manager = Mock()
        app.backup_manager.read_backup_metadata.side_effect = RuntimeError('SECRET_RESTORE_TOKEN')

        restored = EnhancedNLvoorelkaarApp.restore_backup(app, 'failed-backup.zip')

        self.assertFalse(restored)
        audit_payload = json.dumps(db.get_audit_events(entity_type='backup'), ensure_ascii=False)
        self.assertIn('RuntimeError', audit_payload)
        self.assertNotIn('SECRET_RESTORE_TOKEN', audit_payload)

    def test_export_data_writes_real_volunteer_export(self):
        """BackupManager export uses the real schema-aware volunteer exporter."""
        from database.database_manager import DatabaseManager
        from utils.backup_manager import BackupManager

        db_path = os.path.join(self.data_dir, 'nlvoorelkaar.db')
        db = DatabaseManager(db_path)
        db.add_volunteer({
            'volunteer_id': 'vol_export',
            'name': 'Export Volunteer',
            'location': 'Amsterdam'
        })

        export_path = os.path.join(self.temp_dir, 'volunteers_export.json')
        manager = BackupManager(self.data_dir, self.backup_dir)

        self.assertTrue(manager.export_data(export_path, 'json'))
        self.assertTrue(os.path.exists(export_path))
        with open(export_path, 'r', encoding='utf-8') as f:
            exported = json.load(f)
        self.assertEqual(exported[0]['volunteer_id'], 'vol_export')

    def test_export_data_fails_closed_without_database(self):
        """BackupManager export must not report success when no database exists."""
        from utils.backup_manager import BackupManager

        export_path = os.path.join(self.temp_dir, 'missing_export.json')
        manager = BackupManager(self.data_dir, self.backup_dir)

        self.assertFalse(manager.export_data(export_path, 'json'))
        self.assertFalse(os.path.exists(export_path))



class TestCredentialAuditLogging(unittest.TestCase):
    """Test non-secret credential/session audit events on login."""

    def setUp(self):
        self.temp_db = secure_temp_path(self, '.db')
        from database.database_manager import DatabaseManager

        self.db = DatabaseManager(self.temp_db)

    def tearDown(self):
        gc.collect()
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)

    def _build_app(self, credential_manager, scraper):
        from main import EnhancedNLvoorelkaarApp

        app = EnhancedNLvoorelkaarApp.__new__(EnhancedNLvoorelkaarApp)
        app.credential_manager = credential_manager
        app.database_manager = self.db
        app.scraper = None
        app.ui = None
        app.logged_in = False
        self.scraper = scraper
        return app

    def _audit_payload(self):
        events = self.db.get_audit_events(entity_type='credentials', limit=20)
        return json.dumps(events, sort_keys=True)

    @patch('main.EnhancedScraper')
    def test_stored_credential_login_success_is_audited_without_secrets(self, scraper_cls):
        """Stored credential load and login success are audited without username/password."""
        credential_manager = Mock()
        credential_manager.credentials_exist.return_value = True
        credential_manager.load_credentials.return_value = {
            'username': 'robert@example.test',
            'password': 'test-password-value'
        }
        scraper = Mock()
        scraper.login.return_value = True
        scraper_cls.return_value = scraper
        app = self._build_app(credential_manager, scraper)

        self.assertTrue(app.login('ignored@example.test', 'ignored-password', 'master-password'))

        scraper.login.assert_called_once_with('robert@example.test', 'test-password-value')
        actions = [event['action'] for event in self.db.get_audit_events(entity_type='credentials', limit=20)]
        self.assertIn('credentials_load_requested', actions)
        self.assertIn('credentials_loaded', actions)
        self.assertIn('login_success', actions)

        payload = self._audit_payload()
        self.assertNotIn('robert@example.test', payload)
        self.assertNotIn('test-password-value', payload)
        self.assertNotIn('master-password', payload)

    @patch('main.EnhancedScraper')
    def test_new_credential_login_failure_is_audited_without_secrets(self, scraper_cls):
        """Failed new credentials are audited but never persisted."""
        credential_manager = Mock()
        credential_manager.credentials_exist.return_value = False
        credential_manager.save_credentials.return_value = True
        scraper = Mock()
        scraper.login.return_value = False
        scraper_cls.return_value = scraper
        app = self._build_app(credential_manager, scraper)

        self.assertFalse(app.login('new@example.test', 'new-password-value', 'new-master-password'))

        credential_manager.save_credentials.assert_not_called()
        actions = [event['action'] for event in self.db.get_audit_events(entity_type='credentials', limit=20)]
        self.assertNotIn('credentials_stored', actions)
        self.assertIn('login_failed', actions)

        payload = self._audit_payload()
        self.assertNotIn('new@example.test', payload)
        self.assertNotIn('new-password-value', payload)
        self.assertNotIn('new-master-password', payload)

    @patch('main.EnhancedScraper')
    def test_login_exception_audit_records_error_type_only(self, scraper_cls):
        """Unexpected login errors are auditable without raw exception text."""
        credential_manager = Mock()
        credential_manager.credentials_exist.return_value = False
        credential_manager.save_credentials.return_value = True
        scraper = Mock()
        scraper.login.side_effect = RuntimeError('password was bad-password-value')
        scraper_cls.return_value = scraper
        app = self._build_app(credential_manager, scraper)

        self.assertFalse(app.login('error@example.test', 'bad-password-value', 'master-password-value'))

        events = self.db.get_audit_events(entity_type='credentials', limit=20)
        login_error = next(event for event in events if event['action'] == 'login_error')
        self.assertIn('RuntimeError', login_error['after_state'])
        self.assertNotIn('bad-password-value', login_error['after_state'])
        self.assertNotIn('error@example.test', self._audit_payload())


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
        import requests
        from models.enhanced_session_manager import EnhancedSessionManager
        
        # First two calls fail, third succeeds
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'success'
        mock_response.history = []
        mock_response.url = 'http://test.com'
        
        mock_get.side_effect = [
            requests.exceptions.ConnectionError("Network error"),
            requests.exceptions.ConnectionError("Network error"),
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
        self.temp_db = secure_temp_path(self, '.db')
    
    def tearDown(self):
        gc.collect()
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
        self.assertIsInstance(msg_id, str)
        self.assertTrue(msg_id)
    
    def test_get_pending_messages(self):
        """Test getting pending messages"""
        from services.message_queue import MessageQueue
        
        queue = MessageQueue(self.temp_db)
        
        # Queue multiple messages
        queue.enqueue(recipient_id='vol_1', recipient_name='User 1', subject='Subject 1', body='Body 1')
        queue.enqueue(recipient_id='vol_2', recipient_name='User 2', subject='Subject 2', body='Body 2')
        
        pending = queue.get_pending(limit=10)
        
        self.assertEqual(len(pending), 2)
    
    def test_mark_sent_refuses_without_ledger_evidence(self):
        """MessageQueue cannot mark sent without ledger evidence."""
        from services.message_queue import MessageQueue
        
        queue = MessageQueue(self.temp_db)
        
        msg_id = queue.enqueue(recipient_id='vol_1', recipient_name='User', subject='Subject', body='Body')
        with self.assertRaisesRegex(RuntimeError, 'ledger|evidence'):
            queue.mark_sent(msg_id)
        
        pending = queue.get_pending()
        self.assertEqual(len(pending), 1)


class TestMessageSafety(unittest.TestCase):
    """Direct-send paths must not bypass the operating ledger."""

    def test_message_queue_refuses_send_callbacks_and_processing(self):
        from services.message_queue import MessageQueue, MessageStatus

        queue = MessageQueue(secure_temp_path(self, '.db'))
        msg_id = queue.enqueue(recipient_id='vol_1', recipient_name='User', subject='Subject', body='Body')
        with self.assertRaisesRegex(RuntimeError, 'approval|approved|ledger'):
            queue.set_send_callback(Mock())
        with self.assertRaisesRegex(RuntimeError, 'approval|approved|ledger'):
            queue.start_processing()
        with self.assertRaisesRegex(RuntimeError, 'ledger|evidence'):
            queue.update_status(msg_id, MessageStatus.SENT)
        with self.assertRaisesRegex(RuntimeError, 'approval|approved|ledger'):
            queue._send_message(queue.get_message(msg_id))

    def test_enhanced_messaging_scheduler_refuses_direct_delivery(self):
        from services.enhanced_messaging_service import EnhancedMessagingService, MessageScheduler

        with self.assertRaisesRegex(RuntimeError, 'approval|approved|ledger'):
            EnhancedMessagingService(secure_temp_path(self, '.db'), Mock())

        scheduler = MessageScheduler(secure_temp_path(self, '.db'))
        message_id = scheduler.schedule_message(
            recipient_id='vol_1',
            recipient_name='User',
            subject='Subject',
            body='Body',
            scheduled_time=datetime.now()
        )
        with self.assertRaisesRegex(RuntimeError, 'approval|approved|ledger'):
            scheduler.set_send_callback(Mock())
        with self.assertRaisesRegex(RuntimeError, 'approval|approved|ledger'):
            scheduler.start_scheduler()
        with self.assertRaisesRegex(RuntimeError, 'ledger|evidence'):
            scheduler.update_status(message_id, 'sent')

    def test_legacy_messaging_service_refuses_direct_send(self):
        from services.messagingservice import MessagingService

        service = MessagingService.__new__(MessagingService)
        with self.assertRaisesRegex(RuntimeError, 'approval|approved'):
            service.send_messages(
                notifier=Mock(),
                username='user',
                password='password',
                message='Hallo',
                phoneNumber='',
                recipients=['vol_1']
            )

    def test_async_task_direct_send_wrapper_refuses_without_ledger(self):
        from services.async_task_manager import TaskWrappers

        with self.assertRaisesRegex(RuntimeError, 'approved'):
            TaskWrappers.send_messages(
                scraper=Mock(),
                message_data={
                    'volunteers': [{'volunteer_id': 'vol_1', 'name': 'Jan'}],
                    'message_template': 'Hallo {name}'
                }
            )

    def test_performance_manager_refuses_batch_send_placeholders(self):
        from performance import PerformanceManager

        manager = PerformanceManager.__new__(PerformanceManager)
        with self.assertRaisesRegex(RuntimeError, 'approval|approved|ledger'):
            manager.send_messages_batch([{'volunteer_id': 'vol_1', 'body': 'Hallo'}])
        with self.assertRaisesRegex(RuntimeError, 'approval|approved|ledger'):
            manager._send_message({'volunteer_id': 'vol_1', 'body': 'Hallo'})

    def test_service_manager_refuses_direct_send_synchronously(self):
        from services.servicemanager import ServiceManager

        manager = ServiceManager.__new__(ServiceManager)
        with self.assertRaisesRegex(RuntimeError, 'approval|approved'):
            manager.send_messages(
                username='user',
                password='password',
                message='Hallo',
                phoneNumber='',
                recipients=['vol_1']
            )
        with self.assertRaisesRegex(RuntimeError, 'approval|approved'):
            manager._ServiceManager__send_message_in_thread(
                username='user',
                password='password',
                message='Hallo',
                phoneNumber='',
                recipients=['vol_1']
            )

    def test_legacy_reminder_paths_refuse_direct_send(self):
        from services.reminderservice import ReminderService
        from services.servicemanager import ServiceManager

        reminder = ReminderService.__new__(ReminderService)
        with self.assertRaisesRegex(RuntimeError, 'follow-up|approval|auditable'):
            reminder.run_reminder_service()
        with self.assertRaisesRegex(RuntimeError, 'follow-up|approval|auditable'):
            reminder.send_reminder('https://www.nlvoorelkaar.nl/mijn-pagina/berichten/1', 'Hallo')
        with self.assertRaisesRegex(RuntimeError, 'follow-up|approval|auditable'):
            reminder.csv_handler(['https://www.nlvoorelkaar.nl/mijn-pagina/berichten/1'], 3, 'Hallo')

        manager = ServiceManager.__new__(ServiceManager)
        with self.assertRaisesRegex(RuntimeError, 'follow-up|approval|auditable'):
            manager.start_reminder_service(3, 'Hallo')

    def test_legacy_home_view_direct_send_failure_is_user_visible(self):
        from view.homeview import HomeView

        view = HomeView.__new__(HomeView)
        view.root_window = Mock(username='user', password='password')
        view.service_manager = Mock()
        view.service_manager.send_messages.side_effect = RuntimeError('approval required')
        view.message = Mock()
        view.message.get.return_value = 'Hallo'
        view.phone = Mock()
        view.phone.get.return_value = ''
        view.percent_var = Mock()
        view.clean_loading_frame = Mock()
        view.show_loading_screen = Mock()

        with patch('view.homeview.messagebox.showwarning') as warning:
            HomeView.send_message(view, [{'volunteer_id': 'vol_1'}])

        view.percent_var.set.assert_called_with(
            'Direct sending is disabled. Use the message review and approval workflow.'
        )
        warning.assert_called_once()

    def test_legacy_home_view_reminder_failure_is_user_visible(self):
        from view.homeview import HomeView

        view = HomeView.__new__(HomeView)
        view.service_manager = Mock()
        view.service_manager.start_reminder_service.side_effect = RuntimeError('approval required')

        with patch('view.homeview.messagebox.showwarning') as warning:
            HomeView.start_reminder_service(view, 3, 'Hallo')

        warning.assert_called_once()

    def test_legacy_home_view_log_reader_handles_missing_and_combined_logs(self):
        from view.homeview import HomeView
        import shutil

        temp_dir = tempfile.mkdtemp()
        current_dir = os.getcwd()
        view = HomeView.__new__(HomeView)
        try:
            os.chdir(temp_dir)
            error_lines, info_lines = HomeView._collect_log_lines(view)
            self.assertEqual(error_lines, ["No error log file found yet."])
            self.assertEqual(info_lines, ["No info log file found yet."])

            os.makedirs('logs', exist_ok=True)
            with open(os.path.join('logs', 'nlvoorelkaar.log'), 'w', encoding='utf-8') as log_file:
                log_file.write('2026-06-29 - app - INFO - Started\n')
                log_file.write('2026-06-29 - app - ERROR - Failed safely\n')

            error_lines, info_lines = HomeView._collect_log_lines(view)
            self.assertEqual(error_lines, ['2026-06-29 - app - ERROR - Failed safely'])
            self.assertEqual(info_lines, ['2026-06-29 - app - INFO - Started'])
        finally:
            os.chdir(current_dir)
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_campaign_manager_platform_send_placeholders_refuse_success(self):
        import asyncio
        from services.campaign_manager import CampaignManager

        manager = CampaignManager.__new__(CampaignManager)
        with self.assertRaisesRegex(RuntimeError, 'approval|ledger'):
            asyncio.run(manager._send_platform_message({'volunteer_id': 'vol_1'}, {'content': 'Hallo'}))
        with self.assertRaisesRegex(RuntimeError, 'ledger'):
            asyncio.run(manager._post_platform_request({'title': 'Vrijwilligershulp gezocht'}))

    def test_volunteer_data_service_refuses_hidden_request_posting(self):
        from services.volunteer_data_service import VolunteerDataService

        service = VolunteerDataService.__new__(VolunteerDataService)
        service.logger = Mock()
        self.assertEqual(service._trigger_hidden_volunteer_responses(), [])
        service.logger.warning.assert_called_once()
        with self.assertRaisesRegex(RuntimeError, 'approval|ledger'):
            service._post_strategic_request({'title': 'Vrijwilligershulp gezocht'})

    def test_enhanced_scraper_refuses_direct_message_send_without_ledger_token(self):
        from services.enhanced_scraper import EnhancedScraper

        scraper = EnhancedScraper.__new__(EnhancedScraper)
        with self.assertRaisesRegex(RuntimeError, 'approval|ledger'):
            scraper.send_message('vol_1', 'Hallo')

    def test_volunteer_data_statistics_labels_request_posting_disabled(self):
        from services.volunteer_data_service import VolunteerDataService

        service = VolunteerDataService.__new__(VolunteerDataService)
        service.db_manager = Mock()
        service.db_manager.get_volunteer_statistics.return_value = {}
        service.logger = Mock()

        stats = service.get_statistics()

        self.assertTrue(
            any('disabled' in method for method in stats.get('access_methods', []))
        )
        self.assertFalse(
            any(method == 'Strategic request posting (trigger responses)' for method in stats.get('access_methods', []))
        )


class TestEnhancedVolunteerService(unittest.TestCase):
    """Test enhanced volunteer service"""
    
    def setUp(self):
        self.temp_db = secure_temp_path(self, '.db')
        self._init_db()
    
    def tearDown(self):
        gc.collect()
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
    
    def _init_db(self):
        """Initialize test database"""
        with closing(sqlite3.connect(self.temp_db)) as conn:
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
        with closing(sqlite3.connect(self.temp_db)) as conn:
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
        with closing(sqlite3.connect(self.temp_db)) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM volunteers')
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)


class TestEnhancedMessagingService(unittest.TestCase):
    """Test enhanced messaging service"""
    
    def setUp(self):
        self.temp_db = secure_temp_path(self, '.db')
    
    def tearDown(self):
        gc.collect()
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
    
    def test_template_rendering(self):
        """Test message template rendering"""
        from services.enhanced_messaging_service import EnhancedMessagingService
        
        service = EnhancedMessagingService(self.temp_db)
        
        template = "Beste {naam}, welkom in {locatie}!"
        variables = {'naam': 'Jan', 'locatie': 'Amsterdam'}
        
        result = service.render_template(template, variables)
        
        self.assertEqual(result, "Beste Jan, welkom in Amsterdam!")
    
    def test_template_validation(self):
        """Test template validation"""
        from services.enhanced_messaging_service import EnhancedMessagingService
        
        service = EnhancedMessagingService(self.temp_db)
        
        # Valid template
        valid = service.validate_template("Hallo {naam}!")
        self.assertTrue(valid['is_valid'])
        
        # Invalid template (unclosed brace)
        invalid = service.validate_template("Hallo {naam!")
        self.assertFalse(invalid['is_valid'])


class TestOutreachLedger(unittest.TestCase):
    """Test volunteer outreach operating ledger behavior."""

    def setUp(self):
        self.temp_db = secure_temp_path(self, '.db')
        from database.database_manager import DatabaseManager
        from services.outreach_ledger import OutreachLedger

        self.db = DatabaseManager(self.temp_db)
        self.ledger = OutreachLedger(self.db)
        self.db.add_volunteer({
            'volunteer_id': 'vol_1',
            'name': 'Jan Jansen',
            'location': 'Amsterdam',
            'categories': 'maatje',
            'skills': 'luisteren',
            'profile_url': 'https://example.test/vol_1'
        })
        self.campaign_id = self.db.add_campaign({
            'name': 'Maatje gezocht',
            'description': 'Zoeken naar passend vrijwillig contact',
            'target_categories': 'maatje',
            'target_location': 'Amsterdam',
            'message_template': 'Beste {name}, ik zag uw profiel in {location}. Heeft u interesse? Met vriendelijke groet'
        })

    def tearDown(self):
        gc.collect()
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)

    def test_outreach_outcome_records_final_campaign_state(self):
        """Outreach outcomes close the loop from response/follow-up work to result tracking."""
        response_id = self.ledger.record_response(
            volunteer_id='vol_1',
            campaign_id=self.campaign_id,
            raw_content='Ja, ik heb interesse.'
        )
        outcome_id = self.ledger.record_outreach_outcome(
            volunteer_id='vol_1',
            campaign_id=self.campaign_id,
            outcome_type='interested',
            notes='Volunteer wants a call.',
            response_id=response_id,
            actor='tester'
        )

        outcomes = self.ledger.get_outreach_outcomes(campaign_id=self.campaign_id)
        self.assertEqual(outcomes[0]['id'], outcome_id)
        self.assertEqual(outcomes[0]['outcome_type'], 'interested')
        self.assertEqual(outcomes[0]['actor'], 'tester')

        summary = self.ledger.get_campaign_operating_summary(self.campaign_id)
        self.assertEqual(summary['counts']['outcomes']['interested'], 1)
        self.assertEqual(summary['outcomes'][0]['notes'], 'Volunteer wants a call.')
        self.assertIn('Campaign has recorded outreach outcomes', summary['next_actions'][0])

        profile = self.ledger.get_volunteer_operating_profile('vol_1')
        self.assertEqual(profile['outcomes'][0]['outcome_type'], 'interested')

        stats = self.db.get_operating_statistics()
        self.assertEqual(stats['outcomes_recorded'], 1)

        audit_actions = {event['action'] for event in self.ledger.get_audit_log()}
        self.assertIn('outcome_recorded', audit_actions)

    def test_campaign_readiness_and_draft_creation(self):
        """Campaign readiness identifies eligible volunteers and draft creation persists."""
        readiness = self.ledger.check_campaign_readiness(self.campaign_id)
        self.assertTrue(readiness['ready'])
        self.assertEqual(readiness['eligible_volunteers'], 1)

        draft_ids = self.ledger.create_message_drafts(self.campaign_id)
        self.assertEqual(len(draft_ids), 1)

        draft = self.db.get_message_draft(draft_ids[0])
        self.assertEqual(draft['status'], 'draft')
        self.assertIn('Jan Jansen', draft['body'])

    def test_campaign_exclusion_reasons_are_persisted_and_visible(self):
        """Readiness explains which volunteers were excluded and why."""
        self.db.add_volunteer({
            'volunteer_id': 'vol_wrong_category',
            'name': 'Wrong Category',
            'location': 'Amsterdam',
            'categories': 'tuin',
            'skills': 'snoeien'
        })
        self.db.add_volunteer({
            'volunteer_id': 'vol_wrong_location',
            'name': 'Wrong Location',
            'location': 'Utrecht',
            'categories': 'maatje',
            'skills': 'luisteren'
        })
        self.db.add_volunteer({
            'volunteer_id': 'vol_blacklisted',
            'name': 'Blacklisted Volunteer',
            'location': 'Amsterdam',
            'categories': 'maatje',
            'skills': 'luisteren'
        })
        self.db.add_to_blacklist('vol_blacklisted', 'Operator opted out')
        self.db.add_volunteer({
            'volunteer_id': 'vol_contacted',
            'name': 'Already Contacted',
            'location': 'Amsterdam',
            'categories': 'maatje',
            'skills': 'luisteren'
        })
        self.db.add_contact({
            'volunteer_id': 'vol_contacted',
            'campaign_id': self.campaign_id,
            'message_sent': 'Previous approved message',
            'status': 'sent'
        })
        self.db.add_volunteer({
            'volunteer_id': 'vol_declined',
            'name': 'Declined Volunteer',
            'location': 'Amsterdam',
            'categories': 'maatje',
            'skills': 'luisteren'
        })
        self.ledger.record_outreach_outcome(
            volunteer_id='vol_declined',
            campaign_id=self.campaign_id,
            outcome_type='declined',
            notes='Not suitable for this campaign'
        )

        readiness = self.ledger.check_campaign_readiness(self.campaign_id)

        self.assertTrue(readiness['ready'])
        self.assertEqual(readiness['eligible_volunteers'], 1)
        self.assertEqual(readiness['excluded_volunteers'], 5)
        self.assertEqual(readiness['exclusion_counts']['category_mismatch'], 1)
        self.assertEqual(readiness['exclusion_counts']['location_mismatch'], 1)
        self.assertEqual(readiness['exclusion_counts']['blacklisted'], 1)
        self.assertEqual(readiness['exclusion_counts']['already_contacted'], 1)
        self.assertEqual(readiness['exclusion_counts']['unsuitable_outcome'], 1)

        exclusions = self.ledger.get_campaign_exclusions(self.campaign_id)
        reason_by_volunteer = {
            (item['volunteer_id'], item['reason_code']) for item in exclusions
        }
        self.assertIn(('vol_wrong_category', 'category_mismatch'), reason_by_volunteer)
        self.assertIn(('vol_wrong_location', 'location_mismatch'), reason_by_volunteer)
        self.assertIn(('vol_blacklisted', 'blacklisted'), reason_by_volunteer)
        self.assertIn(('vol_contacted', 'already_contacted'), reason_by_volunteer)
        self.assertIn(('vol_declined', 'unsuitable_outcome'), reason_by_volunteer)

        summary = self.ledger.get_campaign_operating_summary(self.campaign_id)
        self.assertEqual(summary['counts']['excluded_volunteers'], 5)
        self.assertEqual(summary['counts']['exclusions']['blacklisted'], 1)
        self.assertTrue(summary['exclusions'])

        draft_ids = self.ledger.create_message_drafts(self.campaign_id)
        self.assertEqual(len(draft_ids), 1)
        draft = self.db.get_message_draft(draft_ids[0])
        self.assertEqual(draft['volunteer_id'], 'vol_1')

    def test_unchanged_campaign_exclusion_snapshot_does_not_spam_audit_log(self):
        """Repeated readiness refreshes do not create duplicate exclusion audit events."""
        self.db.add_volunteer({
            'volunteer_id': 'vol_wrong_location',
            'name': 'Wrong Location',
            'location': 'Utrecht',
            'categories': 'maatje',
            'skills': 'luisteren'
        })

        self.ledger.check_campaign_readiness(self.campaign_id)
        self.ledger.check_campaign_readiness(self.campaign_id)

        audit_events = [
            event for event in self.ledger.get_audit_log(limit=20)
            if event['action'] == 'campaign_exclusions_refreshed'
        ]
        self.assertEqual(len(audit_events), 1)

    def test_approval_required_before_send_attempt(self):
        """Send attempts cannot be recorded before explicit approval."""
        draft_id = self.ledger.create_message_drafts(self.campaign_id)[0]

        with self.assertRaises(ValueError):
            self.db.record_send_attempt(draft_id, status='started')

        approval_id = self.ledger.approve_message(draft_id, 'Looks correct')
        self.assertIsInstance(approval_id, int)

        draft = self.db.get_message_draft(draft_id)
        self.assertEqual(draft['status'], 'approved')

        attempts_before = self.db.get_send_attempts(draft_id)
        self.assertEqual(attempts_before, [])

    def test_edit_before_approval_updates_approval_snapshot(self):
        """Operator edits are saved before approval snapshots are captured."""
        draft_id = self.ledger.create_message_drafts(self.campaign_id)[0]

        updated = self.ledger.edit_message_draft(
            draft_id,
            subject='Aangepaste onderwerpregel',
            body='Beste Jan Jansen, aangepaste tekst voor review.'
        )
        self.assertTrue(updated)

        approval_id = self.ledger.approve_message(draft_id, 'Edited and approved')
        self.assertIsInstance(approval_id, int)

        with closing(self.db.get_connection()) as conn:
            row = conn.execute('''
                SELECT approved_subject_snapshot, approved_body_snapshot
                FROM message_approvals
                WHERE id = ?
            ''', (approval_id,)).fetchone()

        self.assertEqual(row['approved_subject_snapshot'], 'Aangepaste onderwerpregel')
        self.assertEqual(row['approved_body_snapshot'], 'Beste Jan Jansen, aangepaste tekst voor review.')

    def test_approved_send_records_attempt_and_contact(self):
        """Approved sending records send attempt evidence and contact history."""
        draft_id = self.ledger.create_message_drafts(self.campaign_id)[0]
        self.ledger.approve_message(draft_id, 'Approved for test')

        fake_scraper = Mock()
        fake_scraper.send_message.return_value = True

        result = self.ledger.send_approved_drafts(fake_scraper, [draft_id])

        self.assertEqual(result['sent_count'], 1)
        attempts = self.db.get_send_attempts(draft_id)
        self.assertEqual(attempts[0]['status'], 'sent')
        self.assertIn('scraper_send_message_returned_true', attempts[0]['delivery_evidence'])
        self.assertEqual(len(self.db.get_contacts(self.campaign_id)), 1)

    def test_approved_send_supplies_ledger_token_to_scraper(self):
        """The ledger supplies the scraper token that direct callers do not have."""
        draft_id = self.ledger.create_message_drafts(self.campaign_id)[0]
        self.ledger.approve_message(draft_id, 'Approved for token test')

        class TokenCheckingScraper:
            def __init__(self):
                self.received_token = None

            def send_message(self, volunteer_id, body, approval_token=None):
                self.received_token = approval_token
                return approval_token == "outreach_ledger_approved_send"

        scraper = TokenCheckingScraper()
        result = self.ledger.send_approved_drafts(scraper, [draft_id])

        self.assertEqual(result['sent_count'], 1)
        self.assertEqual(scraper.received_token, "outreach_ledger_approved_send")

    def test_send_progress_avoids_volunteer_personal_data(self):
        """Progress messages use operational identifiers instead of volunteer names."""
        draft_id = self.ledger.create_message_drafts(self.campaign_id)[0]
        self.ledger.approve_message(draft_id, 'Approved for progress test')
        fake_scraper = Mock()
        fake_scraper.send_message.return_value = True
        progress_messages = []

        self.ledger.send_approved_drafts(
            fake_scraper,
            [draft_id],
            progress_callback=lambda current, total, message: progress_messages.append(message)
        )

        self.assertTrue(progress_messages)
        self.assertIn(f"approved draft {draft_id}", progress_messages[0])
        self.assertNotIn('Jan Jansen', ' '.join(progress_messages))

    def test_failed_send_is_visible(self):
        """Failed approved sends are persisted with a reason."""
        draft_id = self.ledger.create_message_drafts(self.campaign_id)[0]
        self.ledger.approve_message(draft_id, 'Approved for test')

        fake_scraper = Mock()
        fake_scraper.send_message.return_value = False

        result = self.ledger.send_approved_drafts(fake_scraper, [draft_id])

        self.assertEqual(result['failed_count'], 1)
        attempts = self.db.get_send_attempts(draft_id)
        self.assertEqual(attempts[0]['status'], 'failed')
        self.assertIn('confirmation', attempts[0]['error_message'])

    def test_approved_send_exception_records_error_type_only(self):
        """Approved send exceptions do not persist raw scraper exception text."""
        draft_id = self.ledger.create_message_drafts(self.campaign_id)[0]
        self.ledger.approve_message(draft_id, 'Approved for exception test')

        fake_scraper = Mock()
        fake_scraper.send_message.side_effect = RuntimeError('SECRET_SEND_TOKEN')

        result = self.ledger.send_approved_drafts(fake_scraper, [draft_id])

        self.assertEqual(result['failed_count'], 1)
        attempts = self.db.get_send_attempts(draft_id)
        payload = json.dumps(attempts, ensure_ascii=False)
        self.assertEqual(attempts[0]['error_message'], 'RuntimeError')
        self.assertNotIn('SECRET_SEND_TOKEN', payload)

    def test_response_and_follow_up_recording(self):
        """Manual response recording classifies and can create follow-up work."""
        response_id = self.ledger.record_response(
            volunteer_id='vol_1',
            campaign_id=self.campaign_id,
            raw_content='Kunt u meer informatie sturen?'
        )

        self.assertIsInstance(response_id, int)
        stats = self.db.get_operating_statistics()
        self.assertEqual(stats['responses_received'], 1)

    def test_controller_records_manual_response(self):
        """The app controller exposes manual response recording for the UI."""
        from main import EnhancedNLvoorelkaarApp

        controller = EnhancedNLvoorelkaarApp.__new__(EnhancedNLvoorelkaarApp)
        controller.outreach_ledger = self.ledger
        controller.ui = None

        response_id = controller.record_volunteer_response(
            volunteer_id='vol_1',
            campaign_id=self.campaign_id,
            raw_content='Ik heb interesse en wil graag meer weten.',
            source='manual_ui'
        )

        responses = self.ledger.get_response_inbox(campaign_id=self.campaign_id)
        self.assertEqual(responses[0]['id'], response_id)
        self.assertEqual(responses[0]['source'], 'manual_ui')
        self.assertEqual(responses[0]['classification'], 'interested')

    def test_controller_records_outreach_outcome_from_response(self):
        """The app controller exposes response outcome closure for the UI."""
        from main import EnhancedNLvoorelkaarApp

        controller = EnhancedNLvoorelkaarApp.__new__(EnhancedNLvoorelkaarApp)
        controller.outreach_ledger = self.ledger
        controller.ui = None
        response_id = self.ledger.record_response(
            volunteer_id='vol_1',
            campaign_id=self.campaign_id,
            raw_content='Ik kan helaas niet helpen.'
        )

        outcome_id = controller.record_outreach_outcome(
            volunteer_id='vol_1',
            campaign_id=self.campaign_id,
            outcome_type='declined',
            notes='Closed from response inbox action.',
            response_id=response_id
        )

        outcomes = self.ledger.get_outreach_outcomes(campaign_id=self.campaign_id)
        self.assertEqual(outcomes[0]['id'], outcome_id)
        self.assertEqual(outcomes[0]['response_id'], response_id)
        self.assertEqual(outcomes[0]['outcome_type'], 'declined')
        self.assertEqual(outcomes[0]['actor'], 'user')

    def test_response_follow_up_and_audit_queues(self):
        """Operational queues expose responses, follow-ups, and audit events."""
        self.ledger.record_response(
            volunteer_id='vol_1',
            campaign_id=self.campaign_id,
            raw_content='Kunt u meer informatie sturen?'
        )

        inbox = self.ledger.get_response_inbox()
        self.assertEqual(len(inbox), 1)
        self.assertEqual(inbox[0]['classification'], 'more_info')
        self.assertEqual(inbox[0]['volunteer_name'], 'Jan Jansen')

        follow_ups = self.ledger.get_follow_up_queue(status='due', include_future=True)
        self.assertEqual(len(follow_ups), 1)
        self.assertEqual(follow_ups[0]['volunteer_id'], 'vol_1')

        self.assertTrue(self.ledger.complete_follow_up(follow_ups[0]['id']))
        self.assertEqual(self.ledger.get_follow_up_queue(status='due', include_future=True), [])

        audit_actions = {event['action'] for event in self.ledger.get_audit_log()}
        self.assertIn('response_recorded', audit_actions)
        self.assertIn('follow_up_created', audit_actions)
        self.assertIn('follow_up_status_updated', audit_actions)

    def test_controller_records_outreach_outcome_from_follow_up(self):
        """The app controller can close an outcome against a follow-up record."""
        from main import EnhancedNLvoorelkaarApp

        controller = EnhancedNLvoorelkaarApp.__new__(EnhancedNLvoorelkaarApp)
        controller.outreach_ledger = self.ledger
        controller.ui = None
        follow_up_id = self.ledger.create_follow_up(
            volunteer_id='vol_1',
            campaign_id=self.campaign_id,
            previous_message_id=None,
            days_until_due=0,
            suggested_message='Beste Jan, wilt u nog reageren?'
        )

        outcome_id = controller.record_outreach_outcome(
            volunteer_id='vol_1',
            campaign_id=self.campaign_id,
            outcome_type='unavailable',
            notes='Closed from follow-up queue action.',
            follow_up_id=follow_up_id
        )

        outcomes = self.ledger.get_outreach_outcomes(campaign_id=self.campaign_id)
        self.assertEqual(outcomes[0]['id'], outcome_id)
        self.assertEqual(outcomes[0]['follow_up_id'], follow_up_id)
        self.assertEqual(outcomes[0]['outcome_type'], 'unavailable')
        self.assertEqual(outcomes[0]['actor'], 'user')

    def test_follow_up_requires_approval_before_send_confirmation(self):
        """Follow-up sends are approval-gated and visible in send history."""
        follow_up_id = self.ledger.create_follow_up(
            volunteer_id='vol_1',
            campaign_id=self.campaign_id,
            previous_message_id=None,
            days_until_due=0,
            suggested_message='Beste Jan, wilt u nog reageren?'
        )

        with self.assertRaises(ValueError):
            self.ledger.confirm_follow_up_sent(follow_up_id, 'Sent manually')

        self.assertTrue(self.ledger.approve_follow_up(follow_up_id))
        attempt_id = self.ledger.confirm_follow_up_sent(follow_up_id, 'Sent manually')
        self.assertIsInstance(attempt_id, int)

        follow_ups = self.ledger.get_follow_up_queue(status='sent', include_future=True)
        self.assertEqual(len(follow_ups), 1)
        self.assertEqual(follow_ups[0]['approved_message_snapshot'], 'Beste Jan, wilt u nog reageren?')
        self.assertIn('Sent manually', follow_ups[0]['delivery_evidence'])

        history = self.ledger.get_send_attempt_history()
        follow_up_history = [attempt for attempt in history if attempt.get('attempt_type') == 'follow_up']
        self.assertEqual(len(follow_up_history), 1)
        self.assertEqual(follow_up_history[0]['follow_up_id'], follow_up_id)
        self.assertEqual(len(self.db.get_contacts(self.campaign_id)), 1)

    def test_follow_up_send_confirmation_respects_do_not_contact_changes(self):
        """Approved follow-ups are rechecked against current do-not-contact state."""
        follow_up_id = self.ledger.create_follow_up(
            volunteer_id='vol_1',
            campaign_id=self.campaign_id,
            previous_message_id=None,
            days_until_due=0,
            suggested_message='Beste Jan, wilt u nog reageren?'
        )
        self.assertTrue(self.ledger.approve_follow_up(follow_up_id))
        self.db.add_to_blacklist('vol_1', 'Operator opted out after follow-up approval')

        with self.assertRaisesRegex(ValueError, 'blacklisted'):
            self.ledger.confirm_follow_up_sent(follow_up_id, 'Sent manually')

    def test_follow_up_send_confirmation_respects_closed_outcomes(self):
        """Approved follow-ups cannot be confirmed after a declined/do-not-contact outcome."""
        follow_up_id = self.ledger.create_follow_up(
            volunteer_id='vol_1',
            campaign_id=self.campaign_id,
            previous_message_id=None,
            days_until_due=0,
            suggested_message='Beste Jan, wilt u nog reageren?'
        )
        self.assertTrue(self.ledger.approve_follow_up(follow_up_id))
        self.ledger.record_outreach_outcome(
            volunteer_id='vol_1',
            campaign_id=self.campaign_id,
            outcome_type='do_not_contact',
            notes='Volunteer asked not to be contacted'
        )

        with self.assertRaisesRegex(ValueError, 'closed outreach outcome'):
            self.ledger.confirm_follow_up_sent(follow_up_id, 'Sent manually')

    def test_audit_events_summarize_message_and_evidence_text(self):
        """Audit events do not duplicate full message bodies or delivery evidence."""
        draft_id = self.ledger.create_message_drafts(self.campaign_id)[0]
        self.ledger.edit_message_draft(
            draft_id,
            body='UNIQUE_AUDIT_BODY_SHOULD_NOT_BE_IN_AUDIT'
        )
        self.ledger.approve_message(draft_id, 'UNIQUE_REJECTION_OR_APPROVAL_REASON')
        self.ledger.confirm_manual_send(draft_id, 'UNIQUE_MANUAL_EVIDENCE')
        follow_up_id = self.ledger.create_follow_up(
            volunteer_id='vol_1',
            campaign_id=self.campaign_id,
            previous_message_id=None,
            days_until_due=0,
            suggested_message='UNIQUE_FOLLOWUP_MESSAGE_SHOULD_NOT_BE_IN_AUDIT'
        )
        self.assertTrue(self.ledger.approve_follow_up(follow_up_id))

        audit_blob = json.dumps(self.ledger.get_audit_log(limit=50), ensure_ascii=False)

        self.assertNotIn('UNIQUE_AUDIT_BODY_SHOULD_NOT_BE_IN_AUDIT', audit_blob)
        self.assertNotIn('UNIQUE_MANUAL_EVIDENCE', audit_blob)
        self.assertNotIn('UNIQUE_FOLLOWUP_MESSAGE_SHOULD_NOT_BE_IN_AUDIT', audit_blob)
        self.assertIn('length', audit_blob)

    def test_campaign_match_assessments_are_persisted(self):
        """Campaign match scoring records explainable volunteer fit."""
        assessments = self.ledger.assess_campaign_matches(self.campaign_id)

        self.assertEqual(len(assessments), 1)
        self.assertEqual(assessments[0]['volunteer_id'], 'vol_1')
        self.assertEqual(assessments[0]['status'], 'strong')
        self.assertGreaterEqual(assessments[0]['score'], 70)
        self.assertIn('Category matches', assessments[0]['reasons_json'])

        readiness = self.ledger.check_campaign_readiness(self.campaign_id)
        self.assertEqual(readiness['match_counts']['strong'], 1)

    def test_campaign_operating_summary_aggregates_ledger_state(self):
        """Campaign detail data aggregates readiness, sends, responses, follow-ups, and audit."""
        assessments = self.ledger.assess_campaign_matches(self.campaign_id)
        draft_id = self.ledger.create_message_drafts(self.campaign_id)[0]
        self.ledger.approve_message(draft_id, 'Approved for campaign summary')
        self.ledger.confirm_manual_send(draft_id, 'Sent manually from campaign summary test')
        self.ledger.record_response(
            volunteer_id='vol_1',
            campaign_id=self.campaign_id,
            raw_content='Kunt u meer informatie sturen?'
        )

        summary = self.ledger.get_campaign_operating_summary(self.campaign_id)

        self.assertEqual(summary['campaign']['id'], self.campaign_id)
        self.assertFalse(summary['readiness']['ready'])
        self.assertEqual(summary['counts']['eligible_volunteers'], 0)
        self.assertEqual(summary['counts']['matches']['strong'], len(assessments))
        self.assertEqual(summary['counts']['message_drafts']['sent'], 1)
        self.assertEqual(summary['counts']['send_attempts']['sent'], 1)
        self.assertEqual(summary['counts']['responses']['more_info'], 1)
        self.assertEqual(summary['counts']['follow_ups']['due'], 1)
        self.assertEqual(summary['counts']['contacts'], 1)

        self.assertEqual(summary['send_attempts'][0]['status'], 'sent')
        self.assertEqual(summary['responses'][0]['classification'], 'more_info')
        self.assertEqual(summary['follow_ups'][0]['status'], 'due')
        self.assertIn('Approve or cancel due follow-ups.', summary['next_actions'])

        audit_actions = {event['action'] for event in summary['audit_events']}
        self.assertIn('campaign_matches_assessed', audit_actions)
        self.assertIn('message_approved', audit_actions)
        self.assertIn('manual_send_confirmed', audit_actions)
        self.assertIn('response_recorded', audit_actions)

    def test_task_runs_and_send_history_are_durable(self):
        """Task runs and send attempts are visible as ledger history."""
        draft_id = self.ledger.create_message_drafts(self.campaign_id)[0]
        self.ledger.approve_message(draft_id, 'Approved for durable history test')

        fake_scraper = Mock()
        fake_scraper.send_message.return_value = True
        self.ledger.send_approved_drafts(fake_scraper, [draft_id])

        send_history = self.ledger.get_send_attempt_history()
        self.assertEqual(len(send_history), 1)
        self.assertEqual(send_history[0]['status'], 'sent')

        self.ledger.record_task_run({
            'task_id': 'task-1',
            'name': 'Search Volunteers',
            'description': 'Amsterdam search',
            'status': 'completed',
            'progress': {'current': 1, 'total': 1, 'percentage': 100},
            'result': {'found': 1}
        })

        task_runs = self.ledger.get_task_runs()
        self.assertEqual(len(task_runs), 1)
        self.assertEqual(task_runs[0]['task_id'], 'task-1')
        self.assertEqual(task_runs[0]['status'], 'completed')

    def test_task_run_error_message_records_error_type_only(self):
        """Task history records failure class without raw exception details."""
        from main import EnhancedNLvoorelkaarApp

        controller = EnhancedNLvoorelkaarApp.__new__(EnhancedNLvoorelkaarApp)
        controller.outreach_ledger = self.ledger

        class Status:
            value = 'failed'

        class Progress:
            current = 1
            total = 1
            percentage = 100
            message = 'failed'

        class Task:
            id = 'task-error-sanitized'
            name = 'Search Volunteers'
            description = 'Sanitization regression'
            status = Status()
            progress = Progress()
            result = None
            error = RuntimeError('SECRET_TASK_TOKEN')
            started_at = datetime.now()
            completed_at = datetime.now()

        EnhancedNLvoorelkaarApp._record_task_state(controller, Task())

        task_runs = self.ledger.get_task_runs(status='failed')
        payload = json.dumps(task_runs, ensure_ascii=False)
        self.assertEqual(task_runs[0]['error_message'], 'RuntimeError')
        self.assertNotIn('SECRET_TASK_TOKEN', payload)

    def test_database_sanitizes_raw_task_error_strings(self):
        """The database boundary rejects raw task error strings from callers."""
        self.ledger.record_task_run({
            'task_id': 'task-raw-error',
            'name': 'Backup Data',
            'status': 'failed',
            'error_message': 'ValueError: SECRET_DATABASE_ERROR'
        })

        task_runs = self.ledger.get_task_runs(status='failed')
        payload = json.dumps(task_runs, ensure_ascii=False)
        self.assertEqual(task_runs[0]['error_message'], 'ValueError')
        self.assertNotIn('SECRET_DATABASE_ERROR', payload)

    def test_scheduler_task_history_sanitizes_raw_error_strings(self):
        """Scheduler task history stores error labels rather than raw messages."""
        from services.scheduler_service import SchedulerService

        scheduler = SchedulerService.__new__(SchedulerService)
        scheduler.task_history = []

        class Scheduled:
            name = 'Daily Backup'

        scheduler.scheduled_tasks = {'sched-1': Scheduled()}

        SchedulerService._record_task_execution(
            scheduler,
            'sched-1',
            False,
            'RuntimeError: SECRET_SCHEDULER_TOKEN'
        )

        payload = json.dumps(scheduler.task_history, ensure_ascii=False)
        self.assertEqual(scheduler.task_history[0]['error_message'], 'RuntimeError')
        self.assertNotIn('SECRET_SCHEDULER_TOKEN', payload)

    def test_search_session_results_are_durable_and_visible(self):
        """Search sessions store which volunteers were found, not only counts."""
        self.db.add_volunteer({
            'volunteer_id': 'vol_2',
            'name': 'Sara Search',
            'location': 'Amsterdam',
            'categories': 'maatje',
            'skills': 'wandelen',
            'profile_url': 'https://example.test/vol_2'
        })
        search_session_id = self.db.record_search_session(
            {'location': 'Amsterdam', 'categories': 'maatje'},
            task_id='search-task-1',
            status='started'
        )

        recorded = self.db.record_search_session_results('search-task-1', [
            {'volunteer_id': 'vol_1', 'name': 'Jan Jansen', 'location': 'Amsterdam'},
            {'volunteer_id': 'vol_2', 'name': 'Sara Search', 'location': 'Amsterdam'}
        ])

        self.assertEqual(recorded, 2)
        sessions = self.ledger.get_search_sessions()
        self.assertEqual(sessions[0]['id'], search_session_id)
        self.assertEqual(sessions[0]['linked_result_count'], 2)
        self.assertIn('vol_1', sessions[0]['volunteer_ids'])
        self.assertIn('vol_2', sessions[0]['volunteer_ids'])

        results = self.ledger.get_search_session_results(task_id='search-task-1')
        self.assertEqual([row['volunteer_id'] for row in results], ['vol_1', 'vol_2'])
        self.assertEqual(results[1]['volunteer_name'], 'Sara Search')

        stats = self.db.get_operating_statistics()
        self.assertEqual(stats['search_sessions_completed'], 1)
        self.assertEqual(stats['search_results_linked'], 2)

        audit_actions = [event['action'] for event in self.ledger.get_audit_log(limit=20)]
        self.assertIn('search_session_results_recorded', audit_actions)

    def test_search_completion_callback_records_result_membership(self):
        """The app search callback saves volunteers and links them to the search task."""
        from main import EnhancedNLvoorelkaarApp

        controller = EnhancedNLvoorelkaarApp.__new__(EnhancedNLvoorelkaarApp)
        controller.database_manager = self.db
        controller.ui = Mock()
        self.db.record_search_session(
            {'location': 'Amsterdam'},
            task_id='search-task-callback',
            status='started'
        )

        class Status:
            value = 'completed'

        class Task:
            id = 'search-task-callback'
            status = Status()
            result = [{
                'id': 'vol_callback',
                'name': 'Callback Volunteer',
                'location': 'Amsterdam',
                'categories': 'maatje',
                'skills': 'luisteren',
                'profile_url': 'https://example.test/vol_callback'
            }]

        EnhancedNLvoorelkaarApp._on_volunteers_found(controller, Task())

        saved = self.db.get_volunteers({'location': 'Amsterdam'})
        self.assertTrue(any(volunteer['volunteer_id'] == 'vol_callback' for volunteer in saved))

        results = self.ledger.get_search_session_results(task_id='search-task-callback')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['volunteer_id'], 'vol_callback')
        controller.ui.refresh_volunteers.assert_called_once()
        controller.ui.show_success.assert_called_once()

    def test_manual_send_confirmation_records_evidence_and_contact(self):
        """Manual confirmation requires approval and records deterministic evidence."""
        draft_id = self.ledger.create_message_drafts(self.campaign_id)[0]

        with self.assertRaises(ValueError):
            self.ledger.confirm_manual_send(draft_id, 'Sent manually in browser')

        self.ledger.approve_message(draft_id, 'Approved for manual send')
        attempt_id = self.ledger.confirm_manual_send(draft_id, 'Sent manually in browser')
        self.assertIsInstance(attempt_id, int)

        attempts = self.db.get_send_attempts(draft_id)
        self.assertEqual(attempts[0]['status'], 'sent')
        self.assertIn('manual_confirmation', attempts[0]['delivery_evidence'])
        self.assertEqual(len(self.db.get_contacts(self.campaign_id)), 1)

    def test_privacy_retention_candidates_exclude_recent_contacts(self):
        """Retention review finds stale volunteers and excludes recent activity."""
        old_date = (datetime.now() - timedelta(days=800)).strftime('%Y-%m-%d %H:%M:%S')
        with closing(self.db.get_connection()) as conn:
            conn.execute(
                "UPDATE volunteers SET updated_at = ? WHERE volunteer_id = ?",
                (old_date, 'vol_1')
            )
            conn.commit()

        candidates = self.ledger.get_privacy_retention_candidates(days=365)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]['volunteer_id'], 'vol_1')

        self.db.add_contact({
            'volunteer_id': 'vol_1',
            'campaign_id': self.campaign_id,
            'message_sent': 'recent approved message',
            'status': 'sent'
        })

        candidates_after_contact = self.ledger.get_privacy_retention_candidates(days=365)
        self.assertEqual(candidates_after_contact, [])

    def test_retention_proposals_do_not_delete_without_confirmation(self):
        """Retention review records proposals without deleting volunteer data."""
        old_date = (datetime.now() - timedelta(days=800)).strftime('%Y-%m-%d %H:%M:%S')
        with closing(self.db.get_connection()) as conn:
            conn.execute(
                "UPDATE volunteers SET updated_at = ? WHERE volunteer_id = ?",
                (old_date, 'vol_1')
            )
            conn.commit()

        result = self.ledger.propose_retention_actions(days=365)
        self.assertFalse(result)

        retention_records = self.ledger.get_privacy_retention_records(status='proposed')
        self.assertEqual(len(retention_records), 1)
        self.assertEqual(retention_records[0]['volunteer_id'], 'vol_1')

        volunteers = self.db.get_volunteers()
        self.assertEqual(len(volunteers), 1)
        self.assertEqual(volunteers[0]['volunteer_id'], 'vol_1')

    def test_retention_archive_marks_volunteer_and_records_action(self):
        """Retention archive is explicit, non-destructive, and audited."""
        old_date = (datetime.now() - timedelta(days=800)).strftime('%Y-%m-%d %H:%M:%S')
        with closing(self.db.get_connection()) as conn:
            conn.execute(
                "UPDATE volunteers SET updated_at = ? WHERE volunteer_id = ?",
                (old_date, 'vol_1')
            )
            conn.commit()

        archived = self.ledger.archive_volunteer_for_retention(
            'vol_1',
            'No recent outreach need',
            actor='tester'
        )
        self.assertTrue(archived)

        profile = self.ledger.get_volunteer_operating_profile('vol_1')
        self.assertEqual(profile['volunteer']['retention_status'], 'archived')
        self.assertIsNotNone(profile['volunteer']['archived_at'])

        records = self.ledger.get_privacy_retention_records(status='completed')
        self.assertEqual(records[0]['action'], 'archive_volunteer')
        self.assertEqual(records[0]['volunteer_id'], 'vol_1')

        audit_actions = [event['action'] for event in self.ledger.get_audit_log()]
        self.assertIn('volunteer_archived_for_retention', audit_actions)
        self.assertEqual(self.ledger.get_privacy_retention_candidates(days=365), [])

    def test_retention_redaction_minimizes_personal_data_and_blocks_rehydration(self):
        """Redaction preserves the row but removes personal profile fields."""
        redacted = self.ledger.redact_volunteer_personal_data(
            'vol_1',
            'Data minimization request',
            actor='tester'
        )
        self.assertTrue(redacted)

        profile = self.ledger.get_volunteer_operating_profile('vol_1')
        volunteer = profile['volunteer']
        self.assertEqual(volunteer['retention_status'], 'redacted')
        self.assertEqual(volunteer['name'], 'Redacted volunteer')
        self.assertIsNone(volunteer['description'])
        self.assertIsNone(volunteer['location'])
        self.assertIsNone(volunteer['skills'])
        self.assertIsNone(volunteer['categories'])
        self.assertIsNone(volunteer['availability'])
        self.assertIsNone(volunteer['contact_info'])
        self.assertIsNone(volunteer['profile_url'])

        self.db.add_volunteer({
            'volunteer_id': 'vol_1',
            'name': 'Restored Name',
            'description': 'Should not be restored',
            'location': 'Rotterdam',
            'skills': 'Private skill',
            'categories': 'Private category',
            'availability': 'Weekends',
            'contact_info': 'private@example.com',
            'profile_url': 'https://example.test/restored'
        })

        profile_after_rescrape = self.ledger.get_volunteer_operating_profile('vol_1')
        volunteer_after_rescrape = profile_after_rescrape['volunteer']
        self.assertEqual(volunteer_after_rescrape['name'], 'Redacted volunteer')
        self.assertIsNone(volunteer_after_rescrape['profile_url'])
        self.assertIsNone(volunteer_after_rescrape['contact_info'])

        records = self.ledger.get_privacy_retention_records(status='completed')
        self.assertEqual(records[0]['action'], 'redact_volunteer_personal_data')
        audit_actions = [event['action'] for event in self.ledger.get_audit_log()]
        self.assertIn('volunteer_personal_data_redacted', audit_actions)

    def test_ledger_export_volunteer_data_excludes_redacted_and_audits(self):
        """The operating ledger exposes a controlled audited volunteer export."""
        self.db.add_volunteer({
            'volunteer_id': 'vol_2',
            'name': 'Private Volunteer',
            'location': 'Utrecht',
            'description': 'Should stay out of default exports',
            'contact_info': 'private@example.com',
            'profile_url': 'https://example.test/private'
        })
        self.ledger.redact_volunteer_personal_data(
            'vol_2',
            'Data minimization before export',
            actor='tester'
        )

        output_path = secure_temp_path(self, '.json')
        try:
            result = self.ledger.export_volunteer_data(
                output_path,
                export_format='json',
                actor='tester'
            )

            self.assertEqual(result['record_count'], 1)
            self.assertEqual(result['path'], output_path)

            with open(output_path, 'r') as f:
                exported = json.load(f)

            self.assertEqual(exported[0]['volunteer_id'], 'vol_1')
            self.assertNotIn('vol_2', json.dumps(exported))

            audit_events = self.db.get_audit_events(entity_type='volunteers')
            export_events = [
                event for event in audit_events
                if event['action'] == 'volunteers_data_exported'
            ]
            self.assertEqual(len(export_events), 1)
            self.assertEqual(export_events[0]['actor'], 'tester')
            self.assertEqual(export_events[0]['risk_level'], 'high')
        finally:
            gc.collect()
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_duplicate_detection_scaffold(self):
        """Likely duplicates are exposed for review."""
        self.db.add_volunteer({
            'volunteer_id': 'vol_2',
            'name': 'Jan Jansen',
            'location': 'Amsterdam'
        })

        duplicates = self.db.find_duplicate_volunteers()
        self.assertEqual(len(duplicates), 1)
        self.assertIn('vol_1', duplicates[0]['volunteer_ids'])
        self.assertIn('vol_2', duplicates[0]['volunteer_ids'])

    def test_duplicate_identity_proposal_and_confirmation(self):
        """Duplicate groups can be persisted and confirmed without deleting rows."""
        self.db.add_volunteer({
            'volunteer_id': 'vol_2',
            'name': 'Jan Jansen',
            'location': 'Amsterdam'
        })

        identity_ids = self.ledger.propose_duplicate_identities()
        self.assertEqual(len(identity_ids), 1)

        proposals = self.ledger.get_duplicate_identity_proposals(status='proposed')
        self.assertEqual(len(proposals), 1)
        self.assertIn('vol_1', proposals[0]['volunteer_ids'])
        self.assertIn('vol_2', proposals[0]['volunteer_ids'])

        confirmed = self.ledger.confirm_duplicate_identity(
            proposals[0]['id'],
            proposals[0]['canonical_volunteer_id']
        )
        self.assertTrue(confirmed)

        confirmed_groups = self.ledger.get_duplicate_identity_proposals(status='confirmed')
        self.assertEqual(len(confirmed_groups), 1)
        self.assertEqual(len(self.db.get_volunteers()), 2)

    def test_confirmed_duplicate_identity_suppresses_noncanonical_outreach(self):
        """Confirmed duplicate members are excluded from campaign drafts."""
        self.db.add_volunteer({
            'volunteer_id': 'vol_2',
            'name': 'Jan Jansen',
            'location': 'Amsterdam',
            'categories': 'Techniek',
            'skills': 'Python'
        })

        identity_ids = self.ledger.propose_duplicate_identities()
        self.assertEqual(len(identity_ids), 1)

        proposals = self.ledger.get_duplicate_identity_proposals(status='proposed')
        self.assertEqual(len(proposals), 1)
        canonical_id = proposals[0]['canonical_volunteer_id']
        duplicate_id = next(
            volunteer_id
            for volunteer_id in proposals[0]['volunteer_ids'].split(',')
            if volunteer_id != canonical_id
        )

        confirmed = self.ledger.confirm_duplicate_identity(proposals[0]['id'], canonical_id)
        self.assertTrue(confirmed)

        readiness = self.ledger.check_campaign_readiness(self.campaign_id)
        self.assertEqual(readiness['eligible_volunteers'], 1)
        self.assertEqual(readiness['excluded_volunteers'], 1)
        self.assertEqual(readiness['exclusion_counts']['duplicate_identity'], 1)

        exclusions = self.ledger.get_campaign_exclusions(
            campaign_id=self.campaign_id,
            reason_code='duplicate_identity'
        )
        self.assertEqual(len(exclusions), 1)
        self.assertEqual(exclusions[0]['volunteer_id'], duplicate_id)

        draft_ids = self.ledger.create_message_drafts(self.campaign_id)
        self.assertEqual(len(draft_ids), 1)
        drafts = self.db.get_message_drafts(campaign_id=self.campaign_id)
        self.assertEqual(drafts[0]['volunteer_id'], canonical_id)

    def test_volunteer_operating_profile_aggregates_ledger_context(self):
        """Volunteer detail profile includes contacts, responses, matches, follow-ups, and duplicates."""
        self.ledger.assess_campaign_matches(self.campaign_id)
        draft_id = self.ledger.create_message_drafts(self.campaign_id)[0]
        self.ledger.approve_message(draft_id, 'Approved for profile aggregation')
        self.ledger.confirm_manual_send(draft_id, 'Sent manually for profile aggregation')
        self.ledger.record_response(
            volunteer_id='vol_1',
            campaign_id=self.campaign_id,
            raw_content='Kunt u meer informatie sturen?'
        )
        self.db.add_volunteer({
            'volunteer_id': 'vol_2',
            'name': 'Jan Jansen',
            'location': 'Amsterdam'
        })
        self.ledger.propose_duplicate_identities()

        profile = self.ledger.get_volunteer_operating_profile('vol_1')

        self.assertEqual(profile['volunteer']['name'], 'Jan Jansen')
        self.assertEqual(len(profile['contacts']), 1)
        self.assertEqual(len(profile['responses']), 1)
        self.assertGreaterEqual(len(profile['follow_ups']), 1)
        self.assertEqual(len(profile['match_assessments']), 1)
        self.assertEqual(len(profile['duplicate_identities']), 1)


class TestDataExporter(unittest.TestCase):
    """Test data export functionality"""
    
    def setUp(self):
        self.temp_db = secure_temp_path(self, '.db')
        self.temp_dir = tempfile.mkdtemp()
        self._init_db()
    
    def tearDown(self):
        import shutil
        gc.collect()
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _init_db(self):
        """Initialize test database with sample data"""
        with closing(sqlite3.connect(self.temp_db)) as conn:
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

    def test_export_current_schema_excludes_redacted_and_records_audit(self):
        """Current ledger exports skip redacted volunteers and create audit events."""
        from database.database_manager import DatabaseManager
        from services.data_management import DataExporter, ExportConfig, ExportFormat

        current_db = secure_temp_path(self, '.db')
        try:
            db = DatabaseManager(current_db)
            db.add_volunteer({
                'volunteer_id': 'active_1',
                'name': 'Active Volunteer',
                'location': 'Amsterdam',
                'description': 'Can help',
                'profile_url': 'https://example.test/active'
            })
            db.add_volunteer({
                'volunteer_id': 'redacted_1',
                'name': 'Private Volunteer',
                'location': 'Utrecht',
                'description': 'Should not export',
                'contact_info': 'private@example.com',
                'profile_url': 'https://example.test/private'
            })
            db.redact_volunteer_personal_data(
                'redacted_1',
                'Data minimization test',
                actor='tester'
            )

            exporter = DataExporter(current_db)
            output_path = os.path.join(self.temp_dir, 'current_volunteers.json')
            count = exporter.export_volunteers(
                output_path,
                ExportConfig(format=ExportFormat.JSON)
            )

            self.assertEqual(count, 1)
            with open(output_path, 'r') as f:
                data = json.load(f)
            self.assertEqual(data[0]['volunteer_id'], 'active_1')
            self.assertNotIn('redacted_1', json.dumps(data))

            audit_events = db.get_audit_events(entity_type='volunteers')
            self.assertTrue(
                any(event['action'] == 'volunteers_data_exported' for event in audit_events)
            )
        finally:
            gc.collect()
            if os.path.exists(current_db):
                os.remove(current_db)


class TestReportGenerator(unittest.TestCase):
    """Test report generation"""
    
    def setUp(self):
        self.temp_db = secure_temp_path(self, '.db')
        self._init_db()
    
    def tearDown(self):
        gc.collect()
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
    
    def _init_db(self):
        """Initialize test database"""
        with closing(sqlite3.connect(self.temp_db)) as conn:
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


class TestSchedulerService(unittest.TestCase):
    """Test scheduler task registration and updates."""

    class _FakeJob:
        def __init__(self, callback, args):
            self.callback = callback
            self.args = args
            self.tags = set()

        def tag(self, *tags):
            self.tags.update(tags)
            return self

    class _FakeSchedule:
        def __init__(self):
            self.jobs = []
            self.clear_calls = []
            self.run_pending_calls = 0

        def every(self):
            return self

        @property
        def day(self):
            return self

        def at(self, _time):
            return self

        def do(self, callback, *args):
            job = TestSchedulerService._FakeJob(callback, args)
            self.jobs.append(job)
            return job

        def clear(self, tag=None):
            self.clear_calls.append(tag)
            if tag is None:
                self.jobs.clear()
                return
            self.jobs = [job for job in self.jobs if tag not in job.tags]

        def run_pending(self):
            self.run_pending_calls += 1

    def test_task_schedule_update_uses_task_tag(self):
        """Updating a task should clear and retag the same task id."""
        fake_schedule = self._FakeSchedule()
        import services.scheduler_service as scheduler_service
        from services.scheduler_service import SchedulerService

        # Build service with fake schedule injected for setup.
        original_schedule = scheduler_service.schedule
        scheduler_service.schedule = fake_schedule
        try:
            service = SchedulerService(Mock())
            self.assertNotIn("daily_sync", service.scheduled_tasks)
            self.assertEqual(service.update_task_schedule("daily_backup", "04:00"), True)
        finally:
            scheduler_service.schedule = original_schedule

        self.assertTrue(any("daily_backup" in job.tags for job in fake_schedule.jobs))

        self.assertIn("daily_backup", fake_schedule.clear_calls)
        matching_jobs = [job for job in fake_schedule.jobs if "daily_backup" in job.tags]
        self.assertEqual(len(matching_jobs), 1)

    def test_retry_tasks_keep_retry_tag(self):
        """Retry scheduling should add retry-specific tags."""
        fake_schedule = self._FakeSchedule()
        import services.scheduler_service as scheduler_service
        from services.scheduler_service import SchedulerService

        original_schedule = scheduler_service.schedule
        scheduler_service.schedule = fake_schedule
        try:
            service = SchedulerService(Mock())
            service._schedule_retry("daily_backup")
        finally:
            scheduler_service.schedule = original_schedule

        retry_tags = {
            tag
            for job in fake_schedule.jobs
            for tag in job.tags
        }
        self.assertIn("retry_daily_backup", retry_tags)

    def test_retired_provider_sync_fails_closed(self):
        """The compatibility entry point must never perform autonomous sync."""
        import asyncio
        from services.scheduler_service import SchedulerService

        service = SchedulerService(Mock())
        with self.assertRaisesRegex(RuntimeError, "retired"):
            asyncio.run(service._run_daily_sync())


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
        gc.collect()
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


class TestLegacyCsvUtilities(unittest.TestCase):
    """Test legacy CSV send guards without leaking volunteer identifiers."""

    class FakeDriveManager:
        def __init__(self, files):
            self.files = files

        def find_file_id_by_name(self, name):
            return name

        def download_file_content(self, file_id):
            return self.files.get(file_id, "").encode("utf-8")

        def upload_file_content(self, content, name):
            self.files[name] = content.decode("utf-8")

    def test_pre_send_check_blocks_recent_contact(self):
        from utils.csv_util.csv_util import pre_send_message_check

        drive = self.FakeDriveManager({
            "contacts_date.csv": f"vol_1,{date.today().isoformat()}\n",
            "chats_no_response.csv": ""
        })

        self.assertFalse(pre_send_message_check("vol_1", drive))

    def test_pre_send_check_blocks_active_no_response_ban(self):
        from utils.csv_util.csv_util import pre_send_message_check

        old_contact = (date.today() - timedelta(days=220)).isoformat()
        recent_ban = (date.today() - timedelta(days=30)).isoformat()
        drive = self.FakeDriveManager({
            "contacts_date.csv": f"vol_1,{old_contact}\n",
            "chats_no_response.csv": f"https://example.test/chat/vol_1,{recent_ban},5\n"
        })

        self.assertFalse(pre_send_message_check("vol_1", drive))

    def test_pre_send_check_allows_expired_no_response_ban(self):
        from utils.csv_util.csv_util import pre_send_message_check

        old_contact = (date.today() - timedelta(days=220)).isoformat()
        expired_ban = (date.today() - timedelta(days=400)).isoformat()
        drive = self.FakeDriveManager({
            "contacts_date.csv": f"vol_1,{old_contact}\n",
            "chats_no_response.csv": f"https://example.test/chat/vol_1,{expired_ban},5\n"
        })

        self.assertTrue(pre_send_message_check("vol_1", drive))


class TestBlacklistService(unittest.TestCase):
    """Test blacklist service"""
    
    def setUp(self):
        self.temp_db = secure_temp_path(self, '.db')
        self._init_db()
    
    def tearDown(self):
        gc.collect()
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
    
    def _init_db(self):
        """Initialize test database"""
        with closing(sqlite3.connect(self.temp_db)) as conn:
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
        with closing(sqlite3.connect(self.temp_db)) as conn:
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
