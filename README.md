# Enhanced NLvoorelkaar Outreach Tool

A modern, secure, and feature-rich tool for automating volunteer outreach on NLvoorelkaar platform with enhanced reliability, security, and user experience.

## 🚀 Key Features

### Security & Reliability
- **Encrypted Credential Storage**: Local encryption of login credentials using industry-standard cryptography
- **Automatic Data Backup**: Daily automated backups with manual backup options
- **Enhanced Web Scraping**: Intelligent rate limiting, retry logic, and error handling
- **Data Recovery**: Complete backup and restore functionality

### Modern User Interface
- **Dark Theme**: Clean, modern dark theme interface
- **Real-time Progress Tracking**: Live progress indicators for all operations
- **Asynchronous Operations**: Non-blocking background tasks
- **Responsive Design**: Optimized for different screen sizes

### Advanced Functionality
- **SQLite Database**: Fast, reliable local data storage
- **Campaign Management**: Create and manage multiple outreach campaigns
- **Smart Filtering**: Advanced volunteer search and filtering
- **Message Personalization**: Template-based message customization
- **Analytics Dashboard**: Comprehensive statistics and metrics

## 📋 Requirements

### System Requirements
- **Operating System**: Windows 10/11, macOS 10.14+, or Linux
- **Python**: 3.8 or higher
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 500MB free space for application and data

### Python Dependencies
All dependencies are listed in `requirements.txt` and will be installed automatically.

## 🛠️ Installation

### Option 1: Quick Setup (Recommended)

1. **Download and Extract**
   ```bash
   # Extract the tool to your desired location
   cd /path/to/nlvoorelkaar_enhanced
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Application**
   ```bash
   python main.py
   ```

### Option 2: Virtual Environment Setup

1. **Create Virtual Environment**
   ```bash
   python -m venv nlvoorelkaar_env
   
   # Windows
   nlvoorelkaar_env\\Scripts\\activate
   
   # macOS/Linux
   source nlvoorelkaar_env/bin/activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Application**
   ```bash
   python main.py
   ```

## 🔧 First-Time Setup

### 1. Initial Configuration
When you first run the application, you'll be prompted to:

1. **Enter NLvoorelkaar Credentials**
   - Your NLvoorelkaar username/email
   - Your NLvoorelkaar password

2. **Set Master Password**
   - Choose a strong master password for encrypting your credentials
   - This password will be required each time you start the application

### 2. Verify Connection
The application will test your credentials and establish a connection to NLvoorelkaar.

## 📖 Usage Guide

### Dashboard
- **Metrics Overview**: View total volunteers, contacts, response rates, and active campaigns
- **Recent Activity**: Monitor recent actions and system status
- **Quick Actions**: Access frequently used features

### Campaign Management

#### Creating a Campaign
1. Navigate to **Campaigns** → **New Campaign**
2. Fill in campaign details:
   - **Name**: Descriptive campaign name
   - **Description**: Campaign purpose and goals
   - **Target Categories**: Volunteer categories to target
   - **Location**: Geographic targeting
   - **Message Template**: Personalized message template

#### Message Templates
Use placeholders for personalization:
- `{name}` - Volunteer's name
- `{location}` - Volunteer's location
- `{skills}` - Volunteer's skills
- `{categories}` - Volunteer's categories

Example:
```
Hello {name},

I hope this message finds you well. I noticed your interest in {categories} and thought you might be interested in an opportunity in {location}.

Your skills in {skills} would be valuable for our cause.

Best regards
```

### Volunteer Search
1. **Set Search Criteria**
   - Categories of interest
   - Location preferences
   - Distance radius
   - Skill requirements

2. **Start Search**
   - Click "Search Volunteers"
   - Monitor progress in real-time
   - Results are automatically saved to database

### Sending Messages
1. **Select Campaign**: Choose an existing campaign
2. **Filter Volunteers**: Apply filters to target specific volunteers
3. **Review Recipients**: Verify the list of volunteers to contact
4. **Send Messages**: Start the messaging process with progress tracking

### Data Management

#### Backup & Recovery
- **Automatic Backups**: Daily backups are created automatically
- **Manual Backup**: Create backups anytime via Settings → Backup Data
- **Restore Data**: Restore from any backup file

#### Database Maintenance
- **View Statistics**: Monitor database size and performance
- **Clean Old Data**: Remove outdated records (configurable retention period)
- **Export Data**: Export data in JSON or CSV format

## ⚙️ Configuration

### Application Settings
Settings are stored in `data/settings.db` and can be modified through the UI:

- **Scraping Delays**: Adjust delays between requests (1-5 seconds recommended)
- **Retry Attempts**: Number of retry attempts for failed requests (3-5 recommended)
- **Backup Retention**: Number of backup files to keep (30 days default)
- **Auto-backup Schedule**: Frequency of automatic backups

### Advanced Configuration
For advanced users, you can modify `config/app_config.py`:

```python
# Scraping configuration
SCRAPING_CONFIG = {
    'min_delay': 1.0,
    'max_delay': 3.0,
    'max_retries': 3,
    'timeout': 30
}

# Database configuration
DATABASE_CONFIG = {
    'backup_retention_days': 30,
    'auto_cleanup_enabled': True
}
```

## 🔒 Security Features

### Credential Protection
- **Local Encryption**: Credentials are encrypted using AES-256
- **Master Password**: Additional layer of protection
- **Secure Storage**: Encrypted files with restricted permissions

### Data Privacy
- **Local Storage**: All data remains on your computer
- **No Cloud Sync**: No data is transmitted to external servers
- **Secure Deletion**: Secure overwriting when deleting sensitive data

### Best Practices
1. **Use Strong Master Password**: Minimum 12 characters with mixed case, numbers, and symbols
2. **Regular Backups**: Keep multiple backup copies in secure locations
3. **Update Regularly**: Keep the application updated for security patches
4. **Monitor Logs**: Review application logs for any unusual activity

## 🚨 Troubleshooting

### Common Issues

#### Login Problems
- **Invalid Credentials**: Verify your NLvoorelkaar username and password
- **Connection Timeout**: Check your internet connection
- **Rate Limiting**: Wait a few minutes and try again

#### Scraping Issues
- **No Results Found**: Adjust search criteria or check if website structure changed
- **Slow Performance**: Increase delays between requests in settings
- **Blocked Requests**: The tool may be temporarily rate-limited

#### Database Issues
- **Corruption**: Restore from a recent backup
- **Performance**: Run database cleanup to remove old data
- **Storage Full**: Free up disk space or change data location

### Log Files
Check log files for detailed error information:
- **Application Log**: `nlvoorelkaar.log`
- **Error Log**: `error.log`
- **Debug Log**: `debug.log` (if debug mode enabled)

### Getting Help
1. **Check Logs**: Review log files for error details
2. **Restart Application**: Close and restart the application
3. **Restore Backup**: If data is corrupted, restore from backup
4. **Reset Configuration**: Delete `data/settings.db` to reset settings

## 📊 Performance Optimization

### System Optimization
- **Close Unnecessary Programs**: Free up system resources
- **SSD Storage**: Use SSD for better database performance
- **Adequate RAM**: Ensure sufficient memory for smooth operation

### Application Optimization
- **Adjust Delays**: Balance speed vs. respectful scraping
- **Limit Concurrent Tasks**: Reduce concurrent operations if system is slow
- **Regular Cleanup**: Remove old data to maintain performance

## 🔄 Updates and Maintenance

### Updating the Application
1. **Backup Data**: Create a backup before updating
2. **Download New Version**: Get the latest version
3. **Replace Files**: Replace application files (keep data folder)
4. **Test Functionality**: Verify everything works correctly

### Regular Maintenance
- **Weekly**: Review logs and performance
- **Monthly**: Clean old data and verify backups
- **Quarterly**: Update dependencies and security review

## 📝 Legal and Ethical Considerations

### Responsible Usage
- **Respect Rate Limits**: Don't overwhelm the NLvoorelkaar servers
- **Personal Use Only**: Tool is for personal volunteer coordination
- **Data Privacy**: Respect volunteer privacy and data protection laws
- **Terms of Service**: Comply with NLvoorelkaar's terms of service

### GDPR Compliance
- **Data Minimization**: Only collect necessary volunteer information
- **Retention Limits**: Regularly clean old data
- **Consent**: Ensure you have permission to contact volunteers
- **Right to Deletion**: Provide mechanism to remove volunteer data

## 🤝 Support and Contributing

### Support
For technical support or questions:
1. Check this documentation
2. Review troubleshooting section
3. Check log files for errors
4. Contact the development team

### Contributing
Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This tool is provided for educational and personal use. Please ensure compliance with:
- NLvoorelkaar's terms of service
- Local data protection laws
- Ethical web scraping practices

## 🔖 Version History

### Version 2.0.0 (Current)
- ✅ Enhanced security with encrypted credential storage
- ✅ Modern dark theme UI with improved UX
- ✅ SQLite database integration for better performance
- ✅ Asynchronous operations with progress tracking
- ✅ Automatic backup and recovery system
- ✅ Advanced campaign management
- ✅ Intelligent web scraping with retry logic
- ✅ Comprehensive error handling and logging

### Version 1.0.0 (Original)
- Basic volunteer scraping functionality
- Simple CSV data storage
- Basic UI with limited features

---

**Enhanced NLvoorelkaar Outreach Tool v2.0.0**  
*Secure • Reliable • Modern*

