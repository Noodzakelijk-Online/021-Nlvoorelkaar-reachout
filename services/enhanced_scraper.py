"""
Enhanced Web Scraper for NLvoorelkaar
Improved reliability, error handling, and adaptive scraping strategies
"""

import requests
import time
import random
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, urlparse
import json
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ScrapingConfig:
    """Configuration for scraping behavior"""
    base_url: str = "https://www.nlvoorelkaar.nl"
    min_delay: float = 1.0
    max_delay: float = 3.0
    max_retries: int = 3
    timeout: int = 30
    user_agents: List[str] = None
    
    def __post_init__(self):
        if self.user_agents is None:
            self.user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            ]

class EnhancedScraper:
    """Enhanced web scraper with improved reliability"""
    
    def __init__(self, config: ScrapingConfig = None):
        self.config = config or ScrapingConfig()
        self.session = requests.Session()
        self.last_request_time = 0
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        self._setup_session()
        
    def _setup_session(self):
        """Setup session with headers and configuration"""
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def _get_random_user_agent(self) -> str:
        """Get random user agent"""
        return random.choice(self.config.user_agents)
        
    def _respect_rate_limit(self):
        """Implement intelligent rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Calculate delay based on recent failures
        base_delay = random.uniform(self.config.min_delay, self.config.max_delay)
        failure_multiplier = 1 + (self.consecutive_failures * 0.5)
        delay = base_delay * failure_multiplier
        
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
        
    def _make_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with retry logic and error handling"""
        self._respect_rate_limit()
        
        for attempt in range(self.config.max_retries):
            try:
                # Rotate user agent
                self.session.headers['User-Agent'] = self._get_random_user_agent()
                
                # Make request
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.config.timeout,
                    **kwargs
                )
                
                # Check response status
                if response.status_code == 200:
                    self.consecutive_failures = 0
                    logger.debug(f"Successfully fetched: {url}")
                    return response
                elif response.status_code == 429:  # Rate limited
                    wait_time = 60 * (attempt + 1)
                    logger.warning(f"Rate limited, waiting {wait_time} seconds")
                    time.sleep(wait_time)
                    continue
                elif response.status_code in [403, 404]:
                    logger.error(f"Client error {response.status_code} for {url}")
                    return None
                else:
                    logger.warning(f"HTTP {response.status_code} for {url}, attempt {attempt + 1}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout for {url}, attempt {attempt + 1}")
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error for {url}, attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Unexpected error for {url}: {e}")
                
            # Exponential backoff
            if attempt < self.config.max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
                
        self.consecutive_failures += 1
        logger.error(f"Failed to fetch {url} after {self.config.max_retries} attempts")
        return None
        
    def login(self, username: str, password: str) -> bool:
        """Login to NLvoorelkaar with enhanced error handling"""
        try:
            # Get login page
            login_url = urljoin(self.config.base_url, "/login")
            response = self._make_request(login_url)
            
            if not response:
                logger.error("Failed to load login page")
                return False
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find login form and extract CSRF token
            login_form = soup.find('form', {'id': 'login-form'}) or soup.find('form')
            if not login_form:
                logger.error("Login form not found")
                return False
                
            # Extract form data
            form_data = {}
            for input_field in login_form.find_all('input'):
                name = input_field.get('name')
                value = input_field.get('value', '')
                if name:
                    form_data[name] = value
                    
            # Update with credentials
            form_data.update({
                'username': username,
                'password': password,
                'email': username  # Some forms use email field
            })
            
            # Submit login form
            action_url = login_form.get('action', '/login')
            if not action_url.startswith('http'):
                action_url = urljoin(self.config.base_url, action_url)
                
            response = self._make_request(
                action_url,
                method='POST',
                data=form_data,
                allow_redirects=True
            )
            
            if not response:
                logger.error("Failed to submit login form")
                return False
                
            # Check if login was successful
            if self._is_logged_in(response):
                logger.info("Login successful")
                return True
            else:
                logger.error("Login failed - invalid credentials or form structure changed")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
            
    def _is_logged_in(self, response: requests.Response) -> bool:
        """Check if user is logged in based on response"""
        # Look for indicators of successful login
        indicators = [
            'dashboard', 'profile', 'logout', 'mijn account',
            'welkom', 'uitloggen'
        ]
        
        text_lower = response.text.lower()
        return any(indicator in text_lower for indicator in indicators)
        
    def search_volunteers(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for volunteers with enhanced error handling"""
        try:
            volunteers = []
            page = 1
            max_pages = 50  # Safety limit
            
            while page <= max_pages:
                logger.info(f"Scraping volunteers page {page}")
                
                # Build search URL
                search_url = self._build_search_url(search_params, page)
                response = self._make_request(search_url)
                
                if not response:
                    logger.error(f"Failed to fetch page {page}")
                    break
                    
                # Parse volunteers from page
                page_volunteers = self._parse_volunteers_page(response.text)
                
                if not page_volunteers:
                    logger.info(f"No more volunteers found on page {page}")
                    break
                    
                volunteers.extend(page_volunteers)
                logger.info(f"Found {len(page_volunteers)} volunteers on page {page}")
                
                # Check for next page
                if not self._has_next_page(response.text):
                    break
                    
                page += 1
                
            logger.info(f"Total volunteers found: {len(volunteers)}")
            return volunteers
            
        except Exception as e:
            logger.error(f"Error searching volunteers: {e}")
            return []
            
    def _build_search_url(self, params: Dict[str, Any], page: int = 1) -> str:
        """Build search URL with parameters"""
        base_search_url = urljoin(self.config.base_url, "/zoeken/vrijwilligers")
        
        # Build query parameters
        query_params = {
            'p': page,
            'submitSearchForm': '1'
        }
        
        # Add search parameters
        if params.get('categories'):
            for i, category in enumerate(params['categories']):
                query_params[f'categories[{i}]'] = category
                
        if params.get('location'):
            query_params['location'] = params['location']
            
        if params.get('distance'):
            query_params['distance'] = params['distance']
            
        # Build URL
        from urllib.parse import urlencode
        query_string = urlencode(query_params, doseq=True)
        return f"{base_search_url}?{query_string}"
        
    def _parse_volunteers_page(self, html: str) -> List[Dict[str, Any]]:
        """Parse volunteers from search results page"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            volunteers = []
            
            # Find volunteer cards - adapt selectors based on actual site structure
            volunteer_cards = soup.find_all(['article', 'div'], class_=lambda x: x and any(
                keyword in x.lower() for keyword in ['card', 'volunteer', 'result', 'offer']
            ))
            
            for card in volunteer_cards:
                volunteer = self._parse_volunteer_card(card)
                if volunteer and volunteer.get('volunteer_id'):
                    volunteers.append(volunteer)
                    
            return volunteers
            
        except Exception as e:
            logger.error(f"Error parsing volunteers page: {e}")
            return []
            
    def _parse_volunteer_card(self, card) -> Optional[Dict[str, Any]]:
        """Parse individual volunteer card"""
        try:
            volunteer = {}
            
            # Extract volunteer ID from link or data attributes
            link = card.find('a')
            if link:
                href = link.get('href', '')
                # Extract ID from URL or use href as ID
                volunteer_id = self._extract_id_from_url(href) or href
                volunteer['volunteer_id'] = volunteer_id
                volunteer['profile_url'] = urljoin(self.config.base_url, href)
            else:
                # Try to find ID in data attributes
                volunteer_id = card.get('data-id') or card.get('id')
                if not volunteer_id:
                    return None
                volunteer['volunteer_id'] = volunteer_id
                
            # Extract name
            name_elem = card.find(['h1', 'h2', 'h3', 'h4'], class_=lambda x: x and 'title' in x.lower()) or \
                       card.find(['h1', 'h2', 'h3', 'h4']) or \
                       card.find(class_=lambda x: x and 'name' in x.lower())
            volunteer['name'] = name_elem.get_text(strip=True) if name_elem else ''
            
            # Extract description
            desc_elem = card.find(['p', 'div'], class_=lambda x: x and any(
                keyword in x.lower() for keyword in ['description', 'summary', 'content']
            ))
            volunteer['description'] = desc_elem.get_text(strip=True) if desc_elem else ''
            
            # Extract location
            location_elem = card.find(class_=lambda x: x and 'location' in x.lower()) or \
                           card.find(string=lambda text: text and any(
                               keyword in text.lower() for keyword in ['locatie', 'plaats', 'location']
                           ))
            if location_elem:
                if hasattr(location_elem, 'get_text'):
                    volunteer['location'] = location_elem.get_text(strip=True)
                else:
                    volunteer['location'] = str(location_elem).strip()
            else:
                volunteer['location'] = ''
                
            # Extract categories/skills
            categories_elem = card.find(class_=lambda x: x and any(
                keyword in x.lower() for keyword in ['category', 'skill', 'tag']
            ))
            volunteer['categories'] = categories_elem.get_text(strip=True) if categories_elem else ''
            
            # Set default values
            volunteer.setdefault('skills', '')
            volunteer.setdefault('availability', '')
            volunteer.setdefault('contact_info', '')
            
            return volunteer
            
        except Exception as e:
            logger.error(f"Error parsing volunteer card: {e}")
            return None
            
    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """Extract volunteer ID from URL"""
        try:
            # Common patterns for extracting IDs from URLs
            import re
            
            # Pattern 1: /volunteer/123 or /vrijwilliger/123
            match = re.search(r'/(?:volunteer|vrijwilliger)/(\d+)', url)
            if match:
                return match.group(1)
                
            # Pattern 2: id=123
            match = re.search(r'id=(\d+)', url)
            if match:
                return match.group(1)
                
            # Pattern 3: Last segment of path
            path_segments = url.strip('/').split('/')
            if path_segments and path_segments[-1].isdigit():
                return path_segments[-1]
                
            return None
            
        except Exception:
            return None
            
    def _has_next_page(self, html: str) -> bool:
        """Check if there's a next page"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for next page indicators
            next_indicators = [
                soup.find('a', {'rel': 'next'}),
                soup.find('a', class_=lambda x: x and 'next' in x.lower()),
                soup.find(string=lambda text: text and any(
                    keyword in text.lower() for keyword in ['volgende', 'next', '→']
                ))
            ]
            
            return any(indicator for indicator in next_indicators)
            
        except Exception:
            return False
            
    def get_volunteer_details(self, volunteer_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed volunteer information"""
        try:
            # Build profile URL
            profile_url = urljoin(self.config.base_url, f"/vrijwilliger/{volunteer_id}")
            response = self._make_request(profile_url)
            
            if not response:
                return None
                
            return self._parse_volunteer_profile(response.text, volunteer_id)
            
        except Exception as e:
            logger.error(f"Error getting volunteer details for {volunteer_id}: {e}")
            return None
            
    def _parse_volunteer_profile(self, html: str, volunteer_id: str) -> Dict[str, Any]:
        """Parse detailed volunteer profile"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            volunteer = {'volunteer_id': volunteer_id}
            
            # Extract detailed information
            # This would need to be adapted based on actual profile page structure
            
            # Name
            name_elem = soup.find('h1') or soup.find(class_=lambda x: x and 'name' in x.lower())
            volunteer['name'] = name_elem.get_text(strip=True) if name_elem else ''
            
            # Description
            desc_elem = soup.find(class_=lambda x: x and 'description' in x.lower())
            volunteer['description'] = desc_elem.get_text(strip=True) if desc_elem else ''
            
            # Skills and other details would be extracted similarly
            
            return volunteer
            
        except Exception as e:
            logger.error(f"Error parsing volunteer profile: {e}")
            return {'volunteer_id': volunteer_id}
            
    def send_message(self, volunteer_id: str, message: str) -> bool:
        """Send message to volunteer with enhanced error handling"""
        try:
            # Build message URL
            message_url = urljoin(self.config.base_url, f"/bericht/versturen/{volunteer_id}")
            
            # Get message form
            response = self._make_request(message_url)
            if not response:
                logger.error(f"Failed to load message form for volunteer {volunteer_id}")
                return False
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find message form
            form = soup.find('form', {'id': 'message-form'}) or soup.find('form')
            if not form:
                logger.error("Message form not found")
                return False
                
            # Extract form data
            form_data = {}
            for input_field in form.find_all('input'):
                name = input_field.get('name')
                value = input_field.get('value', '')
                if name:
                    form_data[name] = value
                    
            # Add message content
            form_data['message'] = message
            form_data['content'] = message  # Alternative field name
            
            # Submit form
            action_url = form.get('action', message_url)
            if not action_url.startswith('http'):
                action_url = urljoin(self.config.base_url, action_url)
                
            response = self._make_request(
                action_url,
                method='POST',
                data=form_data
            )
            
            if response and response.status_code == 200:
                # Check for success indicators
                success_indicators = ['verzonden', 'sent', 'success', 'bedankt']
                if any(indicator in response.text.lower() for indicator in success_indicators):
                    logger.info(f"Message sent successfully to volunteer {volunteer_id}")
                    return True
                    
            logger.error(f"Failed to send message to volunteer {volunteer_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error sending message to volunteer {volunteer_id}: {e}")
            return False
            
    def check_health(self) -> Dict[str, Any]:
        """Check scraper health and connectivity"""
        try:
            start_time = time.time()
            response = self._make_request(self.config.base_url)
            response_time = time.time() - start_time
            
            return {
                'status': 'healthy' if response else 'unhealthy',
                'response_time': response_time,
                'consecutive_failures': self.consecutive_failures,
                'last_check': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'consecutive_failures': self.consecutive_failures,
                'last_check': datetime.now().isoformat()
            }

