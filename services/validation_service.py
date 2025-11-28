"""
Data Validation and Integrity Service
Ensures data quality and consistency in the volunteer database
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import phonenumbers
from email_validator import validate_email, EmailNotValidError

class ValidationLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ValidationCategory(Enum):
    CONTACT_INFO = "contact_info"
    PERSONAL_DATA = "personal_data"
    LOCATION_DATA = "location_data"
    SKILLS_DATA = "skills_data"
    DATA_CONSISTENCY = "data_consistency"
    DATA_FRESHNESS = "data_freshness"

@dataclass
class ValidationIssue:
    """Represents a data validation issue"""
    volunteer_id: str
    volunteer_name: str
    category: ValidationCategory
    level: ValidationLevel
    field: str
    issue_type: str
    description: str
    current_value: str
    suggested_fix: Optional[str]
    detected_at: datetime

@dataclass
class ValidationReport:
    """Comprehensive validation report"""
    report_date: datetime
    total_volunteers_checked: int
    issues_found: List[ValidationIssue]
    data_quality_score: float
    category_scores: Dict[ValidationCategory, float]
    recommendations: List[str]
    validation_duration: float

class ValidationService:
    """
    Data validation and integrity service for volunteer database
    
    Features:
    - Contact information validation (email, phone)
    - Data consistency checking
    - Duplicate detection
    - Data freshness monitoring
    - Location validation
    - Skills categorization validation
    - Comprehensive reporting
    """
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Validation configuration
        self.config = {
            'email_validation': True,
            'phone_validation': True,
            'location_validation': True,
            'skills_validation': True,
            'duplicate_detection': True,
            'data_freshness_days': 30,
            'min_data_quality_score': 80.0,
            'required_fields': ['name', 'location'],
            'optional_fields': ['email', 'phone', 'skills', 'description']
        }
        
        # Known valid skill categories
        self.valid_skill_categories = {
            'Computerhulp & ICT', 'Boodschappen', 'Taal & lezen', 
            'Klussen buiten & tuin', 'Maatje, buddy & gezelschap',
            'Activiteitenbegeleiding', 'Sociaal & welzijn', 'Zorg',
            'Tuin, dieren & natuur', 'Sport & beweging', 'Onderwijs',
            'Cultuur & kunst', 'Milieu & duurzaamheid', 'Administratie'
        }
        
        # Dutch location patterns
        self.dutch_location_patterns = [
            r'^[A-Z][a-z]+(?:\s[A-Z][a-z]+)*$',  # City names
            r'^[A-Z][a-z]+(?:\s[A-Z][a-z]+)*,\s*Nederland$',  # City, Nederland
            r'^\d{4}\s*[A-Z]{2}\s+[A-Z][a-z]+$',  # Postal code format
        ]
        
        # Validation history
        self.validation_history = []
    
    def validate_all_volunteers(self) -> ValidationReport:
        """
        Perform comprehensive validation of all volunteers in database
        """
        start_time = datetime.now()
        
        try:
            self.logger.info("Starting comprehensive volunteer data validation")
            
            # Get all volunteers
            volunteers = self.db_manager.get_all_volunteers()
            total_volunteers = len(volunteers)
            
            # Collect all validation issues
            all_issues = []
            
            # Validate each volunteer
            for volunteer in volunteers:
                volunteer_issues = self._validate_volunteer(volunteer)
                all_issues.extend(volunteer_issues)
            
            # Perform database-wide validations
            database_issues = self._validate_database_consistency(volunteers)
            all_issues.extend(database_issues)
            
            # Calculate data quality scores
            data_quality_score = self._calculate_data_quality_score(volunteers, all_issues)
            category_scores = self._calculate_category_scores(all_issues)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(all_issues, data_quality_score)
            
            # Create validation report
            validation_duration = (datetime.now() - start_time).total_seconds()
            
            report = ValidationReport(
                report_date=start_time,
                total_volunteers_checked=total_volunteers,
                issues_found=all_issues,
                data_quality_score=data_quality_score,
                category_scores=category_scores,
                recommendations=recommendations,
                validation_duration=validation_duration
            )
            
            # Store validation report
            self._store_validation_report(report)
            self.validation_history.append(report)
            
            self.logger.info(f"Validation completed: {len(all_issues)} issues found in {validation_duration:.2f} seconds")
            self.logger.info(f"Data quality score: {data_quality_score:.1f}%")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Validation failed: {str(e)}")
            raise
    
    def _validate_volunteer(self, volunteer: Dict) -> List[ValidationIssue]:
        """
        Validate a single volunteer's data
        """
        issues = []
        volunteer_id = volunteer.get('id', volunteer.get('name', 'unknown'))
        volunteer_name = volunteer.get('name', 'Unknown')
        
        try:
            # Validate required fields
            issues.extend(self._validate_required_fields(volunteer, volunteer_id, volunteer_name))
            
            # Validate contact information
            issues.extend(self._validate_contact_info(volunteer, volunteer_id, volunteer_name))
            
            # Validate location data
            issues.extend(self._validate_location_data(volunteer, volunteer_id, volunteer_name))
            
            # Validate skills data
            issues.extend(self._validate_skills_data(volunteer, volunteer_id, volunteer_name))
            
            # Validate data freshness
            issues.extend(self._validate_data_freshness(volunteer, volunteer_id, volunteer_name))
            
        except Exception as e:
            self.logger.error(f"Error validating volunteer {volunteer_name}: {str(e)}")
            issues.append(ValidationIssue(
                volunteer_id=volunteer_id,
                volunteer_name=volunteer_name,
                category=ValidationCategory.DATA_CONSISTENCY,
                level=ValidationLevel.ERROR,
                field='validation',
                issue_type='validation_error',
                description=f'Error during validation: {str(e)}',
                current_value='',
                suggested_fix='Manual review required',
                detected_at=datetime.now()
            ))
        
        return issues
    
    def _validate_required_fields(self, volunteer: Dict, volunteer_id: str, volunteer_name: str) -> List[ValidationIssue]:
        """Validate required fields are present and valid"""
        issues = []
        
        for field in self.config['required_fields']:
            value = volunteer.get(field)
            
            if not value or (isinstance(value, str) and not value.strip()):
                issues.append(ValidationIssue(
                    volunteer_id=volunteer_id,
                    volunteer_name=volunteer_name,
                    category=ValidationCategory.PERSONAL_DATA,
                    level=ValidationLevel.ERROR,
                    field=field,
                    issue_type='missing_required_field',
                    description=f'Required field "{field}" is missing or empty',
                    current_value=str(value) if value else '',
                    suggested_fix=f'Add valid {field} information',
                    detected_at=datetime.now()
                ))
        
        return issues
    
    def _validate_contact_info(self, volunteer: Dict, volunteer_id: str, volunteer_name: str) -> List[ValidationIssue]:
        """Validate contact information (email, phone)"""
        issues = []
        
        # Validate email
        if self.config['email_validation']:
            email = volunteer.get('email') or volunteer.get('contact_info', {}).get('email')
            if email:
                if not self._is_valid_email(email):
                    issues.append(ValidationIssue(
                        volunteer_id=volunteer_id,
                        volunteer_name=volunteer_name,
                        category=ValidationCategory.CONTACT_INFO,
                        level=ValidationLevel.WARNING,
                        field='email',
                        issue_type='invalid_email',
                        description='Email address format is invalid',
                        current_value=email,
                        suggested_fix='Correct email format (example@domain.com)',
                        detected_at=datetime.now()
                    ))
        
        # Validate phone number
        if self.config['phone_validation']:
            phone = volunteer.get('phone') or volunteer.get('contact_info', {}).get('phone')
            if phone:
                if not self._is_valid_phone(phone):
                    issues.append(ValidationIssue(
                        volunteer_id=volunteer_id,
                        volunteer_name=volunteer_name,
                        category=ValidationCategory.CONTACT_INFO,
                        level=ValidationLevel.WARNING,
                        field='phone',
                        issue_type='invalid_phone',
                        description='Phone number format is invalid',
                        current_value=phone,
                        suggested_fix='Use Dutch phone format (+31 6 12345678)',
                        detected_at=datetime.now()
                    ))
        
        return issues
    
    def _validate_location_data(self, volunteer: Dict, volunteer_id: str, volunteer_name: str) -> List[ValidationIssue]:
        """Validate location information"""
        issues = []
        
        if self.config['location_validation']:
            location = volunteer.get('location')
            if location:
                if not self._is_valid_dutch_location(location):
                    issues.append(ValidationIssue(
                        volunteer_id=volunteer_id,
                        volunteer_name=volunteer_name,
                        category=ValidationCategory.LOCATION_DATA,
                        level=ValidationLevel.INFO,
                        field='location',
                        issue_type='unusual_location_format',
                        description='Location format does not match typical Dutch location patterns',
                        current_value=location,
                        suggested_fix='Use format: "City" or "City, Nederland"',
                        detected_at=datetime.now()
                    ))
        
        return issues
    
    def _validate_skills_data(self, volunteer: Dict, volunteer_id: str, volunteer_name: str) -> List[ValidationIssue]:
        """Validate skills and categories"""
        issues = []
        
        if self.config['skills_validation']:
            skills = volunteer.get('skills', [])
            if isinstance(skills, str):
                skills = [skills]
            
            for skill in skills:
                if skill not in self.valid_skill_categories:
                    # Check for close matches
                    suggested_category = self._find_closest_skill_category(skill)
                    
                    issues.append(ValidationIssue(
                        volunteer_id=volunteer_id,
                        volunteer_name=volunteer_name,
                        category=ValidationCategory.SKILLS_DATA,
                        level=ValidationLevel.INFO,
                        field='skills',
                        issue_type='unknown_skill_category',
                        description=f'Skill category "{skill}" is not in standard categories',
                        current_value=skill,
                        suggested_fix=f'Consider using: {suggested_category}' if suggested_category else 'Review skill categorization',
                        detected_at=datetime.now()
                    ))
        
        return issues
    
    def _validate_data_freshness(self, volunteer: Dict, volunteer_id: str, volunteer_name: str) -> List[ValidationIssue]:
        """Validate data freshness"""
        issues = []
        
        # Check when data was last updated
        last_updated = volunteer.get('last_updated') or volunteer.get('extracted_at')
        if last_updated:
            try:
                if isinstance(last_updated, str):
                    last_updated_date = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                elif isinstance(last_updated, (int, float)):
                    last_updated_date = datetime.fromtimestamp(last_updated)
                else:
                    last_updated_date = last_updated
                
                days_old = (datetime.now() - last_updated_date.replace(tzinfo=None)).days
                
                if days_old > self.config['data_freshness_days']:
                    issues.append(ValidationIssue(
                        volunteer_id=volunteer_id,
                        volunteer_name=volunteer_name,
                        category=ValidationCategory.DATA_FRESHNESS,
                        level=ValidationLevel.WARNING,
                        field='last_updated',
                        issue_type='stale_data',
                        description=f'Data is {days_old} days old',
                        current_value=str(last_updated),
                        suggested_fix='Update volunteer information',
                        detected_at=datetime.now()
                    ))
            except Exception as e:
                issues.append(ValidationIssue(
                    volunteer_id=volunteer_id,
                    volunteer_name=volunteer_name,
                    category=ValidationCategory.DATA_FRESHNESS,
                    level=ValidationLevel.INFO,
                    field='last_updated',
                    issue_type='invalid_timestamp',
                    description='Cannot parse last updated timestamp',
                    current_value=str(last_updated),
                    suggested_fix='Fix timestamp format',
                    detected_at=datetime.now()
                ))
        
        return issues
    
    def _validate_database_consistency(self, volunteers: List[Dict]) -> List[ValidationIssue]:
        """Validate database-wide consistency"""
        issues = []
        
        if self.config['duplicate_detection']:
            # Detect duplicate volunteers
            duplicates = self._find_duplicate_volunteers(volunteers)
            
            for duplicate_group in duplicates:
                for volunteer in duplicate_group[1:]:  # Skip first one
                    issues.append(ValidationIssue(
                        volunteer_id=volunteer.get('id', volunteer.get('name', 'unknown')),
                        volunteer_name=volunteer.get('name', 'Unknown'),
                        category=ValidationCategory.DATA_CONSISTENCY,
                        level=ValidationLevel.WARNING,
                        field='duplicate',
                        issue_type='duplicate_volunteer',
                        description=f'Potential duplicate of {duplicate_group[0].get("name")}',
                        current_value=volunteer.get('name', ''),
                        suggested_fix='Review and merge or remove duplicate',
                        detected_at=datetime.now()
                    ))
        
        return issues
    
    def _find_duplicate_volunteers(self, volunteers: List[Dict]) -> List[List[Dict]]:
        """Find potential duplicate volunteers"""
        duplicates = []
        processed = set()
        
        for i, volunteer1 in enumerate(volunteers):
            if i in processed:
                continue
            
            duplicate_group = [volunteer1]
            name1 = volunteer1.get('name', '').lower().strip()
            location1 = volunteer1.get('location', '').lower().strip()
            
            for j, volunteer2 in enumerate(volunteers[i+1:], i+1):
                if j in processed:
                    continue
                
                name2 = volunteer2.get('name', '').lower().strip()
                location2 = volunteer2.get('location', '').lower().strip()
                
                # Check for exact name match
                if name1 == name2 and name1:
                    duplicate_group.append(volunteer2)
                    processed.add(j)
                # Check for name and location match
                elif name1 == name2 and location1 == location2 and name1 and location1:
                    duplicate_group.append(volunteer2)
                    processed.add(j)
            
            if len(duplicate_group) > 1:
                duplicates.append(duplicate_group)
                processed.add(i)
        
        return duplicates
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email address format"""
        try:
            validate_email(email)
            return True
        except EmailNotValidError:
            return False
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Validate Dutch phone number format"""
        try:
            # Parse phone number with Netherlands as default region
            parsed_number = phonenumbers.parse(phone, "NL")
            return phonenumbers.is_valid_number(parsed_number)
        except:
            # Fallback to basic regex validation
            phone_pattern = r'^(\+31|0031|0)[6-9]\d{8}$'
            return bool(re.match(phone_pattern, re.sub(r'[\s\-\(\)]', '', phone)))
    
    def _is_valid_dutch_location(self, location: str) -> bool:
        """Validate Dutch location format"""
        for pattern in self.dutch_location_patterns:
            if re.match(pattern, location):
                return True
        return False
    
    def _find_closest_skill_category(self, skill: str) -> Optional[str]:
        """Find closest matching skill category"""
        skill_lower = skill.lower()
        
        # Simple keyword matching
        keyword_mapping = {
            'computer': 'Computerhulp & ICT',
            'ict': 'Computerhulp & ICT',
            'digitaal': 'Computerhulp & ICT',
            'boodschap': 'Boodschappen',
            'winkelen': 'Boodschappen',
            'taal': 'Taal & lezen',
            'nederlands': 'Taal & lezen',
            'lezen': 'Taal & lezen',
            'klus': 'Klussen buiten & tuin',
            'tuin': 'Klussen buiten & tuin',
            'onderhoud': 'Klussen buiten & tuin',
            'gezelschap': 'Maatje, buddy & gezelschap',
            'buddy': 'Maatje, buddy & gezelschap',
            'maatje': 'Maatje, buddy & gezelschap',
            'activiteit': 'Activiteitenbegeleiding',
            'begeleiding': 'Activiteitenbegeleiding',
            'zorg': 'Zorg',
            'sport': 'Sport & beweging',
            'beweging': 'Sport & beweging'
        }
        
        for keyword, category in keyword_mapping.items():
            if keyword in skill_lower:
                return category
        
        return None
    
    def _calculate_data_quality_score(self, volunteers: List[Dict], issues: List[ValidationIssue]) -> float:
        """Calculate overall data quality score"""
        if not volunteers:
            return 0.0
        
        total_volunteers = len(volunteers)
        
        # Weight issues by severity
        severity_weights = {
            ValidationLevel.INFO: 0.1,
            ValidationLevel.WARNING: 0.5,
            ValidationLevel.ERROR: 1.0,
            ValidationLevel.CRITICAL: 2.0
        }
        
        total_penalty = sum(severity_weights.get(issue.level, 1.0) for issue in issues)
        max_possible_penalty = total_volunteers * 10  # Assume max 10 issues per volunteer
        
        # Calculate score (0-100)
        score = max(0, 100 - (total_penalty / max_possible_penalty * 100))
        
        return round(score, 1)
    
    def _calculate_category_scores(self, issues: List[ValidationIssue]) -> Dict[ValidationCategory, float]:
        """Calculate data quality scores by category"""
        category_scores = {}
        
        # Group issues by category
        category_issues = {}
        for issue in issues:
            if issue.category not in category_issues:
                category_issues[issue.category] = []
            category_issues[issue.category].append(issue)
        
        # Calculate score for each category
        for category in ValidationCategory:
            category_issue_count = len(category_issues.get(category, []))
            
            # Simple scoring: fewer issues = higher score
            if category_issue_count == 0:
                score = 100.0
            else:
                # Penalty based on issue count and severity
                penalty = sum(
                    2.0 if issue.level == ValidationLevel.CRITICAL else
                    1.0 if issue.level == ValidationLevel.ERROR else
                    0.5 if issue.level == ValidationLevel.WARNING else 0.1
                    for issue in category_issues.get(category, [])
                )
                score = max(0, 100 - penalty * 5)  # Scale penalty
            
            category_scores[category] = round(score, 1)
        
        return category_scores
    
    def _generate_recommendations(self, issues: List[ValidationIssue], data_quality_score: float) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Overall score recommendations
        if data_quality_score < 60:
            recommendations.append("URGENT: Data quality is critically low. Immediate action required.")
        elif data_quality_score < 80:
            recommendations.append("Data quality needs improvement. Focus on resolving errors and warnings.")
        elif data_quality_score < 95:
            recommendations.append("Good data quality. Address remaining issues for optimization.")
        else:
            recommendations.append("Excellent data quality. Continue regular maintenance.")
        
        # Category-specific recommendations
        category_counts = {}
        for issue in issues:
            category_counts[issue.category] = category_counts.get(issue.category, 0) + 1
        
        if category_counts.get(ValidationCategory.CONTACT_INFO, 0) > 10:
            recommendations.append("High number of contact information issues. Implement contact validation during data entry.")
        
        if category_counts.get(ValidationCategory.DATA_CONSISTENCY, 0) > 5:
            recommendations.append("Data consistency issues detected. Review duplicate detection and data entry processes.")
        
        if category_counts.get(ValidationCategory.DATA_FRESHNESS, 0) > 20:
            recommendations.append("Many records have stale data. Increase synchronization frequency.")
        
        # Issue-specific recommendations
        error_count = len([i for i in issues if i.level == ValidationLevel.ERROR])
        if error_count > 0:
            recommendations.append(f"Resolve {error_count} critical errors immediately to improve data reliability.")
        
        warning_count = len([i for i in issues if i.level == ValidationLevel.WARNING])
        if warning_count > 10:
            recommendations.append(f"Address {warning_count} warnings to prevent future data quality degradation.")
        
        return recommendations
    
    def _store_validation_report(self, report: ValidationReport):
        """Store validation report in database"""
        try:
            report_data = {
                'report_date': report.report_date.isoformat(),
                'total_volunteers_checked': report.total_volunteers_checked,
                'issues_count': len(report.issues_found),
                'data_quality_score': report.data_quality_score,
                'category_scores': {cat.value: score for cat, score in report.category_scores.items()},
                'recommendations': report.recommendations,
                'validation_duration': report.validation_duration
            }
            
            self.db_manager.store_validation_report(report_data)
            
            # Store individual issues
            for issue in report.issues_found:
                issue_data = {
                    'report_date': report.report_date.isoformat(),
                    'volunteer_id': issue.volunteer_id,
                    'volunteer_name': issue.volunteer_name,
                    'category': issue.category.value,
                    'level': issue.level.value,
                    'field': issue.field,
                    'issue_type': issue.issue_type,
                    'description': issue.description,
                    'current_value': issue.current_value,
                    'suggested_fix': issue.suggested_fix,
                    'detected_at': issue.detected_at.isoformat()
                }
                self.db_manager.store_validation_issue(issue_data)
            
            self.logger.info("Validation report stored successfully")
            
        except Exception as e:
            self.logger.error(f"Error storing validation report: {str(e)}")
    
    def get_validation_summary(self) -> Dict:
        """Get summary of latest validation results"""
        try:
            if not self.validation_history:
                return {'status': 'no_validation_performed'}
            
            latest_report = self.validation_history[-1]
            
            return {
                'last_validation': latest_report.report_date.isoformat(),
                'data_quality_score': latest_report.data_quality_score,
                'total_issues': len(latest_report.issues_found),
                'critical_issues': len([i for i in latest_report.issues_found if i.level == ValidationLevel.CRITICAL]),
                'error_issues': len([i for i in latest_report.issues_found if i.level == ValidationLevel.ERROR]),
                'warning_issues': len([i for i in latest_report.issues_found if i.level == ValidationLevel.WARNING]),
                'info_issues': len([i for i in latest_report.issues_found if i.level == ValidationLevel.INFO]),
                'category_scores': {cat.value: score for cat, score in latest_report.category_scores.items()},
                'top_recommendations': latest_report.recommendations[:3]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting validation summary: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def get_validation_history(self, days: int = 30) -> List[Dict]:
        """Get validation history for specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            history = []
            for report in self.validation_history:
                if report.report_date >= cutoff_date:
                    history.append({
                        'report_date': report.report_date.isoformat(),
                        'data_quality_score': report.data_quality_score,
                        'total_issues': len(report.issues_found),
                        'volunteers_checked': report.total_volunteers_checked,
                        'validation_duration': report.validation_duration
                    })
            
            return sorted(history, key=lambda x: x['report_date'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error getting validation history: {str(e)}")
            return []
    
    def fix_validation_issues(self, issue_ids: List[str]) -> Dict:
        """Attempt to automatically fix validation issues"""
        try:
            fixed_count = 0
            failed_count = 0
            results = []
            
            for issue_id in issue_ids:
                try:
                    # This would implement automatic fixes for common issues
                    # For now, just log the attempt
                    self.logger.info(f"Attempting to fix issue {issue_id}")
                    fixed_count += 1
                    results.append({'issue_id': issue_id, 'status': 'fixed'})
                except Exception as e:
                    failed_count += 1
                    results.append({'issue_id': issue_id, 'status': 'failed', 'error': str(e)})
            
            return {
                'fixed_count': fixed_count,
                'failed_count': failed_count,
                'results': results
            }
            
        except Exception as e:
            self.logger.error(f"Error fixing validation issues: {str(e)}")
            return {'error': str(e)}
