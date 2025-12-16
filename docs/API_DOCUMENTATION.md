# NLvoorElkaar Tool - API Documentation

## Overview

This document provides comprehensive documentation for all services and components in the NLvoorElkaar Outreach Tool.

---

## Table of Contents

1. [Core Services](#core-services)
2. [Security Components](#security-components)
3. [Data Management](#data-management)
4. [UI Components](#ui-components)
5. [Utilities](#utilities)
6. [Configuration](#configuration)

---

## Core Services

### EnhancedVolunteerService

**Location:** `services/enhanced_volunteer_service.py`

Handles volunteer data scraping, storage, and management with rate limiting and progress persistence.

#### Methods

##### `__init__(db_path: str, session_manager: EnhancedSessionManager)`
Initialize the volunteer service.

**Parameters:**
- `db_path`: Path to SQLite database
- `session_manager`: Session manager instance for HTTP requests

##### `scrape_volunteers(start_page: int = 1, max_pages: int = None, on_progress: Callable = None) -> Dict`
Scrape volunteers from NLvoorElkaar platform.

**Parameters:**
- `start_page`: Starting page number (default: 1)
- `max_pages`: Maximum pages to scrape (default: None = all)
- `on_progress`: Progress callback function `(current, total, message)`

**Returns:**
```python
{
    'total_found': int,
    'new_volunteers': int,
    'updated_volunteers': int,
    'pages_scraped': int,
    'errors': List[str]
}
```

**Example:**
```python
from services.enhanced_volunteer_service import EnhancedVolunteerService
from models.enhanced_session_manager import EnhancedSessionManager

session = EnhancedSessionManager()
service = EnhancedVolunteerService('data/volunteers.db', session)

def progress_callback(current, total, message):
    print(f"Progress: {current}/{total} - {message}")

result = service.scrape_volunteers(
    start_page=1,
    max_pages=10,
    on_progress=progress_callback
)
print(f"Found {result['total_found']} volunteers")
```

##### `save_volunteer(volunteer: Dict) -> bool`
Save or update a volunteer record.

**Parameters:**
- `volunteer`: Dictionary with volunteer data

**Required Keys:**
- `profile_id`: Unique profile identifier
- `name`: Volunteer name

**Optional Keys:**
- `location`: Location/city
- `description`: Profile description
- `skills`: Skills offered
- `availability`: Availability information
- `contact_info`: Contact details
- `profile_url`: Profile URL

##### `get_volunteer(profile_id: str) -> Optional[Dict]`
Get volunteer by profile ID.

##### `search_volunteers(query: str, filters: Dict = None) -> List[Dict]`
Search volunteers with optional filters.

**Filters:**
- `location`: Filter by location
- `skills`: Filter by skills
- `active_only`: Only active volunteers (default: True)

---

### EnhancedMessagingService

**Location:** `services/enhanced_messaging_service.py`

Handles message composition, templating, scheduling, and delivery.

#### Methods

##### `create_template(name: str, subject: str, body: str, variables: List[str] = None) -> int`
Create a message template.

**Parameters:**
- `name`: Template name
- `subject`: Message subject with placeholders
- `body`: Message body with placeholders
- `variables`: List of variable names used

**Placeholders:** Use `{variable_name}` syntax

**Example:**
```python
template_id = service.create_template(
    name='Welkomstbericht',
    subject='Welkom bij ons project, {naam}!',
    body='''
Beste {naam},

Bedankt voor je aanmelding als vrijwilliger in {locatie}.
We nemen binnenkort contact met je op.

Met vriendelijke groet,
Het Team
''',
    variables=['naam', 'locatie']
)
```

##### `render_template(template: str, variables: Dict) -> str`
Render a template with variables.

##### `validate_template(template: str) -> Dict`
Validate template syntax.

**Returns:**
```python
{
    'is_valid': bool,
    'variables': List[str],
    'errors': List[str]
}
```

##### `schedule_message(recipient_id: str, template_id: int, variables: Dict, scheduled_time: datetime = None) -> int`
Schedule a message for delivery.

##### `send_message(message_id: int) -> bool`
Send a scheduled message immediately.

##### `get_message_preview(template_id: int, variables: Dict) -> Dict`
Get preview of rendered message.

---

### EnhancedReminderService

**Location:** `services/enhanced_reminder_blacklist.py`

Manages follow-up reminders with smart scheduling.

#### Methods

##### `create_reminder(volunteer_id: str, reminder_type: str, scheduled_date: datetime, notes: str = None) -> int`
Create a new reminder.

**Reminder Types:**
- `follow_up`: General follow-up
- `no_response`: No response received
- `interested`: Volunteer showed interest
- `callback`: Callback requested

##### `get_due_reminders(limit: int = 50) -> List[Dict]`
Get reminders that are due.

##### `mark_completed(reminder_id: int, outcome: str, notes: str = None)`
Mark reminder as completed.

**Outcomes:**
- `responded`: Volunteer responded
- `no_answer`: No answer
- `not_interested`: Not interested
- `rescheduled`: Rescheduled for later

##### `reschedule(reminder_id: int, new_date: datetime, reason: str = None)`
Reschedule a reminder.

---

### EnhancedBlacklistService

**Location:** `services/enhanced_reminder_blacklist.py`

Manages volunteer blacklist with categories and expiration.

#### Methods

##### `add_to_blacklist(profile_id: str, name: str, reason: str, notes: str = None, duration_days: int = None) -> int`
Add volunteer to blacklist.

**Reasons:**
- `no_response`: No response after multiple attempts
- `not_interested`: Explicitly not interested
- `inappropriate`: Inappropriate behavior
- `duplicate`: Duplicate profile
- `inactive`: Inactive account
- `other`: Other reason

**Parameters:**
- `duration_days`: Days until expiration (None = permanent)

##### `is_blacklisted(profile_id: str) -> bool`
Check if volunteer is blacklisted.

##### `remove_from_blacklist(profile_id: str) -> bool`
Remove from blacklist.

##### `get_blacklist(include_expired: bool = False) -> List[Dict]`
Get all blacklisted profiles.

---

## Security Components

### SecureCredentialManager

**Location:** `utils/secure_credentials.py`

Handles secure storage of credentials with AES-256 encryption.

#### Methods

##### `__init__(credential_file: str)`
Initialize credential manager.

##### `set_master_password(password: str)`
Set the master password for encryption.

**Important:** Must be called before any other operations.

##### `store_credential(service: str, key: str, value: str)`
Store an encrypted credential.

**Example:**
```python
manager = SecureCredentialManager('credentials.enc')
manager.set_master_password('my_secure_password')

manager.store_credential('nlvoorelkaar', 'email', 'user@example.com')
manager.store_credential('nlvoorelkaar', 'password', 'secret123')
```

##### `get_credential(service: str, key: str) -> Optional[str]`
Retrieve a credential.

##### `delete_credential(service: str, key: str) -> bool`
Delete a credential.

##### `rotate_master_password(old_password: str, new_password: str) -> bool`
Rotate the master password.

---

### EnhancedSessionManager

**Location:** `models/enhanced_session_manager.py`

Manages HTTP sessions with retry logic, rate limiting, and connection pooling.

#### Methods

##### `__init__()`
Initialize session manager with default settings.

##### `get_session() -> requests.Session`
Get a configured session.

##### `get_with_retry(url: str, max_retries: int = 3, **kwargs) -> Response`
Make GET request with automatic retry.

##### `post_with_retry(url: str, data: Dict = None, max_retries: int = 3, **kwargs) -> Response`
Make POST request with automatic retry.

#### Configuration

```python
manager = EnhancedSessionManager()
manager.max_retries = 5
manager.retry_delay = 2.0  # seconds
manager.min_request_interval = 1.0  # rate limiting
manager.timeout = 30  # request timeout
```

---

## Data Management

### DataExporter

**Location:** `services/data_management.py`

Export data to various formats.

#### Methods

##### `export_volunteers(output_path: str, config: ExportConfig = None, filters: Dict = None) -> int`
Export volunteers to file.

**Supported Formats:**
- CSV
- JSON
- Excel (XLSX)

**Example:**
```python
from services.data_management import DataExporter, ExportConfig, ExportFormat

exporter = DataExporter('data/volunteers.db')

# Export to CSV
config = ExportConfig(format=ExportFormat.CSV)
count = exporter.export_volunteers('export/volunteers.csv', config)

# Export with filters
filters = {
    'location': 'Amsterdam',
    'active_only': True,
    'since': '2024-01-01'
}
count = exporter.export_volunteers('export/amsterdam.json', 
    ExportConfig(format=ExportFormat.JSON), filters)
```

##### `export_messages(output_path: str, config: ExportConfig = None, status: str = None) -> int`
Export messages.

##### `export_blacklist(output_path: str, config: ExportConfig = None) -> int`
Export blacklist.

---

### DataImporter

**Location:** `services/data_management.py`

Import data from external files.

#### Methods

##### `import_volunteers(file_path: str, on_progress: Callable = None) -> Dict`
Import volunteers from CSV/JSON.

**Returns:**
```python
{
    'imported': int,
    'updated': int,
    'skipped': int,
    'errors': int
}
```

##### `import_blacklist(file_path: str, default_reason: str = 'other') -> Dict`
Import blacklist entries.

---

### ReportGenerator

**Location:** `services/data_management.py`

Generate activity and performance reports.

#### Methods

##### `generate_activity_report(period: str = 'this_week', output_path: str = None) -> Dict`
Generate activity report.

**Periods:**
- `today`
- `yesterday`
- `this_week`
- `last_week`
- `this_month`
- `last_month`

**Output Formats:**
- JSON (`.json`)
- Markdown (`.md`)
- HTML (`.html`)

**Example:**
```python
generator = ReportGenerator('data/volunteers.db')

# Generate report
report = generator.generate_activity_report('this_week')

# Save to file
report = generator.generate_activity_report(
    'this_month',
    output_path='reports/monthly_report.html'
)
```

---

## UI Components

### Dashboard

**Location:** `views/dashboard.py`

Main dashboard view with statistics and quick actions.

#### Usage

```python
import tkinter as tk
from views.dashboard import Dashboard

root = tk.Tk()
dashboard = Dashboard(root, 'data/volunteers.db')
dashboard.pack(fill='both', expand=True)
root.mainloop()
```

### ProgressIndicator

**Location:** `views/enhanced_ui_components.py`

Progress indicator widget.

#### Usage

```python
from views.enhanced_ui_components import ProgressIndicator, ProgressDialog

# Inline progress
progress = ProgressIndicator(parent, title="Laden...")
progress.update_progress(50, 100, "Bezig met laden...")
progress.set_complete("Voltooid!")

# Modal dialog
dialog = ProgressDialog(parent, title="Verwerken", task_name="Vrijwilligers laden")
dialog.update_progress(25, 100, "Pagina 1 van 4")
dialog.complete("Alle vrijwilligers geladen!")
```

### Toast Notifications

**Location:** `views/enhanced_ui_components.py`

Toast notification popups.

#### Usage

```python
from views.enhanced_ui_components import show_toast, ToastType

# Info toast
show_toast(parent, "Bestand opgeslagen", ToastType.INFO)

# Success toast
show_toast(parent, "Bericht verzonden!", ToastType.SUCCESS)

# Error toast
show_toast(parent, "Fout bij verzenden", ToastType.ERROR, duration=5000)
```

---

## Utilities

### ErrorHandler

**Location:** `utils/error_handler.py`

Global error handling with categorization.

#### Usage

```python
from utils.error_handler import ErrorHandler, ErrorCategory

handler = ErrorHandler()

try:
    # Some operation
    pass
except Exception as e:
    category = handler.categorize_error(e)
    user_message = handler.get_user_message(category)
    handler.log_error(e, context={'operation': 'scrape'})
```

### EnhancedLogging

**Location:** `utils/enhanced_logging.py`

Configurable logging with rotation.

#### Usage

```python
from utils.enhanced_logging import setup_logging
import logging

logger = setup_logging(
    log_file='logs/app.log',
    level=logging.INFO,
    max_bytes=10*1024*1024,  # 10MB
    backup_count=5
)

logger.info("Application started")
logger.error("Error occurred", exc_info=True)
```

---

## Configuration

### Application Settings

**Location:** `config/enhanced_settings.py`

#### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NLVOORELKAAR_EMAIL` | Login email | None |
| `NLVOORELKAAR_PASSWORD` | Login password | None |
| `DATABASE_PATH` | Database file path | `data/volunteers.db` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FILE` | Log file path | `logs/app.log` |
| `RATE_LIMIT_DELAY` | Request delay (seconds) | `1.0` |
| `MAX_RETRIES` | Maximum retry attempts | `3` |

#### Configuration File

Create `config/settings.json`:

```json
{
    "database": {
        "path": "data/volunteers.db",
        "backup_dir": "backups/"
    },
    "scraping": {
        "rate_limit": 1.0,
        "max_retries": 3,
        "timeout": 30
    },
    "messaging": {
        "batch_size": 50,
        "delay_between_messages": 5
    },
    "ui": {
        "theme": "dark",
        "language": "nl"
    }
}
```

---

## Error Codes

| Code | Category | Description |
|------|----------|-------------|
| E001 | Network | Connection failed |
| E002 | Network | Timeout |
| E003 | Auth | Invalid credentials |
| E004 | Auth | Session expired |
| E005 | Parse | Invalid HTML structure |
| E006 | Parse | Missing data |
| E007 | Database | Connection failed |
| E008 | Database | Query error |
| E009 | Config | Invalid configuration |
| E010 | Config | Missing required setting |

---

## Best Practices

### Rate Limiting

Always respect rate limits to avoid being blocked:

```python
# Good
service = EnhancedVolunteerService(db_path, session)
service.rate_limit_delay = 2.0  # 2 seconds between requests

# Bad - too fast
service.rate_limit_delay = 0.1
```

### Error Handling

Always wrap operations in try-except:

```python
try:
    result = service.scrape_volunteers()
except NetworkError as e:
    logger.error(f"Network error: {e}")
    show_toast(parent, "Netwerkfout", ToastType.ERROR)
except AuthenticationError as e:
    logger.error(f"Auth error: {e}")
    # Prompt for re-login
```

### Database Backups

Regularly backup the database:

```python
from utils.backup_manager import BackupManager

backup = BackupManager('data/volunteers.db', 'backups/')
backup.create_backup()
backup.cleanup_old_backups(keep_days=30)
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 3.0.0 | 2024-12 | Added sync service, validation, reporting |
| 2.0.0 | 2024-12 | Enhanced security, UI improvements |
| 1.0.0 | 2024-11 | Initial release |
