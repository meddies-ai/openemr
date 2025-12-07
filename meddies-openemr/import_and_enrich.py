"""
Combined OpenEMR Import Script
Creates patients and adds medical history using web session (form-based) approach.
"""

import requests
import urllib3
import re
import json
from pathlib import Path
from datetime import datetime, timedelta

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
OPENEMR_URL = "http://localhost"
USERNAME = "admin"
PASSWORD = "pass"
# ---------------------


class OpenEMRWebSession:
    """
    Mimics browser-based interaction with OpenEMR web interface.
    Uses session cookies for authentication instead of OAuth2 API tokens.
    Handles patient creation and medical history management.
    """
    
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.csrf_token = None
        
    def login(self):
        """Login via web form and get session cookie + CSRF token"""
        login_page_url = f"{self.base_url}/interface/login/login.php"
        login_url = f"{self.base_url}/interface/main/main_screen.php?auth=login&site=default"
        
        login_data = {
            'new_login_session_management': '1',
            'authProvider': 'Default',
            'authUser': self.username,
            'clearPass': self.password,
            'languageChoice': '1'
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        try:
            # Get login page first
            self.session.get(login_page_url, verify=False)
            
            # Post login
            response = self.session.post(login_url, data=login_data, headers=headers, 
                                         verify=False, allow_redirects=True)
            
            cookies = self.session.cookies.get_dict()
            if 'OpenEMR' in cookies:
                print(f"  ✓ Web login successful")
                return True
            else:
                print(f"  ! Login may have failed. Cookies: {list(cookies.keys())}")
                return True
                
        except Exception as e:
            print(f"  ✗ Login error: {e}")
            return False
    
    def get_csrf_token(self, page_url):
        """Extract CSRF token from a page"""
        try:
            response = self.session.get(page_url, verify=False)
            if response.status_code == 200:
                # Look for csrf_token_form in the page
                match = re.search(r'name=["\']csrf_token_form["\'][^>]*value=["\']([^"\']+)["\']', response.text)
                if match:
                    return match.group(1)
                # Alternative pattern
                match = re.search(r'value=["\']([a-f0-9]{64})["\'][^>]*name=["\']csrf_token_form["\']', response.text)
                if match:
                    return match.group(1)
        except Exception as e:
            print(f"  ! Error getting CSRF token: {e}")
        return None
    
    def set_active_patient(self, pid):
        """Set the active patient in the session"""
        url = f"{self.base_url}/interface/patient_file/summary/demographics.php"
        params = {'set_pid': pid}
        
        try:
            response = self.session.get(url, params=params, verify=False)
            if response.status_code == 200:
                return True
        except Exception as e:
            print(f"  ! Error setting patient: {e}")
        return False

    # ==================== PATIENT CREATION ====================
    
    def create_patient(self, patient_data, debug=False):
        """
        Create a new patient via web interface.
        
        Args:
            patient_data: dict with patient information:
                - fname: First name (required)
                - lname: Last name (required)
                - mname: Middle name
                - DOB: Date of birth (YYYY-MM-DD)
                - sex: Gender (Male/Female)
                - street: Address line
                - city: City
                - postal_code: Postal/ZIP code
                - country_code: Country code (e.g., 'VN')
                - phone_cell: Mobile phone
                - email: Email address
                - language: Preferred language
                - status: Marital status
            debug: If True, save response HTML for debugging
                
        Returns:
            pid (int) if successful, None if failed
        """
        # Get the new patient form page to get CSRF token
        form_url = f"{self.base_url}/interface/new/new_comprehensive.php"
        save_url = f"{self.base_url}/interface/new/new_comprehensive_save.php"
        
        # First, get the form page to extract CSRF token
        try:
            form_response = self.session.get(form_url, verify=False)
            if debug:
                with open('/tmp/new_patient_form.html', 'w') as f:
                    f.write(form_response.text)
                print(f"    [DEBUG] Form saved to /tmp/new_patient_form.html")
        except Exception as e:
            print(f"    ✗ Error fetching patient form: {e}")
            return None
        
        csrf_token = self.get_csrf_token(form_url)
        if not csrf_token:
            print("  ✗ Could not get CSRF token for patient form")
            return None
        
        # Build form data - matching OpenEMR's new_comprehensive.php expected fields
        # All fields use 'form_' prefix
        form_data = {
            'csrf_token_form': csrf_token,
            'form_fname': patient_data.get('fname', ''),
            'form_lname': patient_data.get('lname', ''),
            'form_mname': patient_data.get('mname', ''),
            'form_DOB': patient_data.get('DOB', ''),
            'form_sex': patient_data.get('sex', 'Female'),
            'form_street': patient_data.get('street', ''),
            'form_city': patient_data.get('city', ''),
            'form_postal_code': patient_data.get('postal_code', ''),
            'form_country_code': patient_data.get('country_code', ''),
            'form_phone_cell': patient_data.get('phone_cell', ''),
            'form_email': patient_data.get('email', ''),
            'form_language': patient_data.get('language', ''),
            'form_status': patient_data.get('status', ''),
            'form_ss': patient_data.get('ssn', ''),
            'form_pubpid': patient_data.get('external_id', ''),
            # Additional common fields
            'form_phone_home': '',
            'form_phone_biz': '',
            'form_state': '',
            'form_street_line_2': '',
            'form_title': '',
            'form_birth_fname': '',
            'form_birth_lname': '',
            # Privacy settings
            'form_hipaa_notice': 'YES',
            'form_hipaa_voice': 'YES',
            'form_hipaa_mail': 'YES',
            'form_hipaa_allowsms': 'YES',
            'form_hipaa_allowemail': 'YES',
            # Submit button - this is crucial
            'create': 'Create New Patient',
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': self.base_url,
            'Referer': form_url
        }
        
        try:
            response = self.session.post(save_url, data=form_data, 
                                        headers=headers, verify=False, allow_redirects=True)
            
            if debug:
                with open('/tmp/patient_create_response.html', 'w') as f:
                    f.write(response.text)
                print(f"    [DEBUG] Response saved to /tmp/patient_create_response.html")
                print(f"    [DEBUG] Final URL: {response.url}")
            
            if response.status_code == 200:
                # Check for error messages in response
                response_text = response.text
                if 'ERROR:' in response_text:
                    print(f"    ✗ Server error: {response_text[:200]}")
                    return None
                
                # Try to extract the new patient ID from response or URL
                pid = self._extract_pid_from_response(response)
                
                if pid:
                    print(f"    ✓ Created Patient: {patient_data.get('fname', '')} {patient_data.get('lname', '')} (PID: {pid})")
                    return pid
                else:
                    # Patient might be created, try to find by name
                    pid = self.find_patient_by_name(patient_data.get('fname', ''), patient_data.get('lname', ''))
                    if pid:
                        print(f"    ✓ Created Patient: {patient_data.get('fname', '')} {patient_data.get('lname', '')} (PID: {pid})")
                        return pid
                    print(f"    ? Patient may have been created, but couldn't confirm PID")
                    return None
            else:
                print(f"    ✗ Failed to create patient: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"    ✗ Patient creation error: {e}")
            return None
    
    def _extract_pid_from_response(self, response):
        """Extract patient ID from response URL or content"""
        # Check URL for pid parameter
        if 'pid=' in response.url:
            match = re.search(r'pid=(\d+)', response.url)
            if match:
                return int(match.group(1))
        
        # Check response text for pid
        patterns = [
            r'set_pid\s*=\s*["\']?(\d+)["\']?',
            r'pid["\']?\s*:\s*["\']?(\d+)["\']?',
            r'patient_id["\']?\s*=\s*["\']?(\d+)["\']?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response.text)
            if match:
                return int(match.group(1))
        
        return None
    
    def find_patient_by_name(self, fname, lname):
        """Search for a patient by name and return their PID"""
        search_url = f"{self.base_url}/interface/patient_file/find_interface/find_interface.php"
        
        try:
            # Try to search
            params = {
                'fname': fname,
                'lname': lname,
            }
            response = self.session.get(search_url, params=params, verify=False)
            
            if response.status_code == 200:
                # Look for pid in results
                match = re.search(r'pid["\']?\s*[:=]\s*["\']?(\d+)["\']?', response.text)
                if match:
                    return int(match.group(1))
        except Exception as e:
            pass
        
        return None

    # ==================== MEDICAL HISTORY ====================
    
    def add_medication(self, pid, title, dosage_instructions="", begin_date=None, end_date=None, comments=""):
        """Add a medication to a patient via the web interface."""
        self.set_active_patient(pid)
        
        add_url = f"{self.base_url}/interface/patient_file/summary/add_edit_issue.php"
        params = {'issue': '0', 'thistype': 'medication'}
        
        csrf_token = self.get_csrf_token(f"{add_url}?issue=0&thistype=medication")
        if not csrf_token:
            print("    ! Could not get CSRF token for medication form")
            return False
        
        if begin_date is None:
            begin_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        if end_date is None:
            end_date = ""
        
        form_data = {
            'csrf_token_form': csrf_token,
            'issue': '0',
            'thispid': str(pid),
            'thisenc': '0',
            'form_type': '2',
            'form_active': '1',
            'form_title': title,
            'form_title_id': '',
            'form_begin': begin_date,
            'form_end': end_date,
            'form_reaction': 'unassigned',
            'form_severity_id': 'unassigned',
            'form_medication[usage_category]': 'community',
            'form_medication[request_intent]': 'order',
            'form_medication[drug_dosage_instructions]': dosage_instructions,
            'form_comments': comments,
            'form_diagnosis': '',
            'form_occur': '0',
            'form_outcome': '0',
            'form_subtype': '',
            'form_classification': '0',
            'form_verification': 'unconfirmed',
            'form_referredby': '',
            'form_destination': '',
            'form_return': '',
            'row_reinjury_id': '',
            'form_save': 'Save'
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': self.base_url,
            'Referer': f"{add_url}?issue=0&thistype=medication"
        }
        
        try:
            response = self.session.post(f"{add_url}?issue=0&thistype=medication", 
                                         data=form_data, headers=headers, verify=False)
            if response.status_code == 200:
                print(f"      ✓ Added Medication: {title}")
                return True
            else:
                print(f"      ✗ Failed Medication: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"      ✗ Medication error: {e}")
            return False
    
    def add_problem(self, pid, title, icd10="", begin_date=None, comments=""):
        """Add a medical problem/diagnosis via the web interface."""
        self.set_active_patient(pid)
        
        add_url = f"{self.base_url}/interface/patient_file/summary/add_edit_issue.php"
        csrf_token = self.get_csrf_token(f"{add_url}?issue=0&thistype=medical_problem")
        
        if not csrf_token:
            print("    ! Could not get CSRF token for problem form")
            return False
        
        if begin_date is None:
            begin_date = datetime.now().strftime("%Y-%m-%d")
        
        form_data = {
            'csrf_token_form': csrf_token,
            'issue': '0',
            'thispid': str(pid),
            'thisenc': '0',
            'form_type': '0',
            'form_active': '1',
            'form_title': title,
            'form_title_id': '',
            'form_begin': begin_date,
            'form_end': '',
            'form_diagnosis': icd10,
            'form_occur': '0',
            'form_outcome': '0',
            'form_classification': '0',
            'form_verification': 'unconfirmed',
            'form_comments': comments,
            'form_referredby': '',
            'form_destination': '',
            'form_return': '',
            'form_save': 'Save'
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': self.base_url,
            'Referer': f"{add_url}?issue=0&thistype=medical_problem"
        }
        
        try:
            response = self.session.post(f"{add_url}?issue=0&thistype=medical_problem",
                                         data=form_data, headers=headers, verify=False)
            if response.status_code == 200:
                print(f"      ✓ Added Problem: {title}")
                return True
            else:
                print(f"      ✗ Failed Problem: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"      ✗ Problem error: {e}")
            return False
    
    def add_allergy(self, pid, title, reaction="", severity="", begin_date=None):
        """Add an allergy via the web interface."""
        self.set_active_patient(pid)
        
        add_url = f"{self.base_url}/interface/patient_file/summary/add_edit_issue.php"
        csrf_token = self.get_csrf_token(f"{add_url}?issue=0&thistype=allergy")
        
        if not csrf_token:
            print("    ! Could not get CSRF token for allergy form")
            return False
        
        if begin_date is None:
            begin_date = datetime.now().strftime("%Y-%m-%d")
        
        form_data = {
            'csrf_token_form': csrf_token,
            'issue': '0',
            'thispid': str(pid),
            'thisenc': '0',
            'form_type': '3',
            'form_active': '1',
            'form_title': title,
            'form_title_id': '',
            'form_begin': begin_date,
            'form_end': '',
            'form_reaction': reaction or 'unassigned',
            'form_severity_id': severity or 'unassigned',
            'form_occur': '0',
            'form_outcome': '0',
            'form_verification': 'unconfirmed',
            'form_comments': '',
            'form_save': 'Save'
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': self.base_url,
            'Referer': f"{add_url}?issue=0&thistype=allergy"
        }
        
        try:
            response = self.session.post(f"{add_url}?issue=0&thistype=allergy",
                                         data=form_data, headers=headers, verify=False)
            if response.status_code == 200:
                print(f"      ✓ Added Allergy: {title}")
                return True
            else:
                print(f"      ✗ Failed Allergy: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"      ✗ Allergy error: {e}")
            return False

    # ==================== ENCOUNTERS & VITALS ====================
    
    def create_encounter(self, pid, date, reason="Office Visit", category_id="5", provider_id="1", facility_id="3"):
        """
        Create a new encounter/visit for a patient.
        
        Args:
            pid: Patient ID
            date: Encounter date (YYYY-MM-DD)
            reason: Visit reason/chief complaint
            category_id: Category (5=Office Visit, 9=Established Patient, etc.)
            provider_id: Provider ID
            facility_id: Facility ID
            
        Returns:
            encounter_id if successful, None if failed
        """
        self.set_active_patient(pid)
        
        form_url = f"{self.base_url}/interface/forms/newpatient/new.php?autoloaded=1&calenc="
        save_url = f"{self.base_url}/interface/forms/newpatient/save.php"
        
        csrf_token = self.get_csrf_token(form_url)
        if not csrf_token:
            print("    ! Could not get CSRF token for encounter form")
            return None
        
        form_data = {
            'csrf_token_form': csrf_token,
            'mode': 'new',
            'form_date': date,
            'reason': reason,
            'facility_id': facility_id,
            'pc_catid': category_id,
            'provider_id': provider_id,
            'pos_code': '11',  # Office
            'class_code': 'AMB',  # Ambulatory
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': self.base_url,
            'Referer': form_url
        }
        
        try:
            response = self.session.post(save_url, data=form_data, headers=headers, verify=False)
            if response.status_code == 200:
                # Extract encounter ID from response
                match = re.search(r'EncounterIdArray\[Count\]\s*=\s*(\d+)', response.text)
                if match:
                    enc_id = int(match.group(1))
                    print(f"      ✓ Created Encounter: {date} - {reason} (ID: {enc_id})")
                    return enc_id
            print(f"      ? Encounter may have been created but couldn't confirm ID")
            return None
        except Exception as e:
            print(f"      ✗ Encounter error: {e}")
            return None
    
    def set_active_encounter(self, encounter_id):
        """Set the active encounter in the session"""
        url = f"{self.base_url}/interface/patient_file/encounter/encounter_top.php"
        params = {'set_encounter': encounter_id}
        try:
            self.session.get(url, params=params, verify=False)
            return True
        except:
            return False
    
    def add_vitals(self, pid, encounter_id, vitals_data):
        """
        Add vitals to an encounter.
        
        Args:
            pid: Patient ID
            encounter_id: Encounter ID
            vitals_data: dict with vitals:
                - weight: Weight in lbs or kg
                - height: Height in inches or cm
                - bps: Systolic blood pressure
                - bpd: Diastolic blood pressure
                - pulse: Heart rate
                - respiration: Respiratory rate
                - temperature: Temperature
                - oxygen_saturation: O2 sat percentage
                - note: Additional notes
        """
        self.set_active_patient(pid)
        self.set_active_encounter(encounter_id)
        
        form_url = f"{self.base_url}/interface/forms/vitals/new.php"
        save_url = f"{self.base_url}/interface/forms/vitals/save.php"
        
        # Get the form to extract hidden fields
        try:
            form_response = self.session.get(form_url, verify=False)
        except Exception as e:
            print(f"        ! Error fetching vitals form: {e}")
            return False
        
        csrf_token = None
        csrf_match = re.search(r'name=["\']csrf_token_form["\'][^>]*value=["\']([^"\']+)["\']', form_response.text)
        if csrf_match:
            csrf_token = csrf_match.group(1)
        
        if not csrf_token:
            print("        ! Could not get CSRF token for vitals form")
            return False
        
        # Extract hidden field values
        id_match = re.search(r'name=["\']id["\'][^>]*value=["\']([^"\']*)["\']', form_response.text)
        uuid_match = re.search(r'name=["\']uuid["\'][^>]*value=["\']([^"\']*)["\']', form_response.text)
        
        form_data = {
            'csrf_token_form': csrf_token,
            'id': id_match.group(1) if id_match else '',
            'uuid': uuid_match.group(1) if uuid_match else '',
            'pid': str(pid),
            'process': 'true',
            'activity': '1',
            'weight': vitals_data.get('weight', ''),
            'height': vitals_data.get('height', ''),
            'bps': vitals_data.get('bps', ''),
            'bpd': vitals_data.get('bpd', ''),
            'pulse': vitals_data.get('pulse', ''),
            'respiration': vitals_data.get('respiration', ''),
            'temperature': vitals_data.get('temperature', ''),
            'oxygen_saturation': vitals_data.get('oxygen_saturation', ''),
            'note': vitals_data.get('note', ''),
            'BMI': '',
            'BMI_status': '',
            'head_circ': '',
            'waist_circ': '',
            'oxygen_flow_rate': '',
            'inhaled_oxygen_concentration': '',
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': self.base_url,
            'Referer': form_url
        }
        
        try:
            response = self.session.post(save_url, data=form_data, headers=headers, verify=False)
            if response.status_code == 200:
                # Check for success indicator (closeTab script)
                if 'closeTab' in response.text or 'saved' in response.text.lower():
                    bp_str = f"{vitals_data.get('bps', '?')}/{vitals_data.get('bpd', '?')}" if vitals_data.get('bps') else "N/A"
                    print(f"        ✓ Added Vitals: BP {bp_str}, HR {vitals_data.get('pulse', '?')}, Temp {vitals_data.get('temperature', '?')}")
                    return True
                else:
                    print(f"        ? Vitals submitted but response unclear")
                    return True  # Probably succeeded
            else:
                print(f"        ✗ Failed Vitals: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"        ✗ Vitals error: {e}")
            return False

    # ==================== LAB RESULTS ====================
    
    def add_lab_results(self, pid, encounter_id, lab_data):
        """
        Add lab results to an encounter using the observation form.
        
        Args:
            pid: Patient ID
            encounter_id: Encounter ID
            lab_data: list of dicts with lab values:
                - code: LOINC code (e.g., '2345-7' for Glucose)
                - description: Test name (e.g., 'Glucose, Serum')
                - value: Result value (e.g., '105')
                - unit: Unit of measure (e.g., 'mg/dL')
                - date: Test date (YYYY-MM-DD)
                - comments: Optional comments
                - reference_range: Optional reference range (e.g., '70-100')
        """
        self.set_active_patient(pid)
        self.set_active_encounter(encounter_id)
        
        form_url = f"{self.base_url}/interface/forms/observation/new.php"
        save_url = f"{self.base_url}/interface/forms/observation/save.php?id=0"
        
        # Get the form to extract CSRF token
        try:
            form_response = self.session.get(form_url, verify=False)
        except Exception as e:
            print(f"        ! Error fetching observation form: {e}")
            return False
        
        csrf_match = re.search(r'name=["\']csrf_token_form["\'][^>]*value=["\']([^"\']+)["\']', form_response.text)
        if not csrf_match:
            print("        ! Could not get CSRF token for observation form")
            return False
        
        # Build form data as list of tuples for multiple labs
        form_data = [('csrf_token_form', csrf_match.group(1))]
        
        for lab in lab_data:
            form_data.extend([
                ('ob_type[]', 'procedure_diagnostic'),
                ('code_type[]', 'LOINC'),
                ('table_code[]', ''),
                ('code[]', lab.get('code', '')),
                ('description[]', lab.get('description', '')),
                ('ob_value[]', str(lab.get('value', ''))),
                ('ob_unit[]', lab.get('unit', '')),
                ('ob_value_phin[]', ''),
                ('code_date[]', lab.get('date', '')),
                ('code_date_end[]', ''),
                ('comments[]', lab.get('comments', '')),
                ('reasonCode[]', ''),
                ('reasonCodeStatus[]', 'completed'),
                ('reasonCodeText[]', ''),
            ])
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': self.base_url,
            'Referer': form_url
        }
        
        try:
            response = self.session.post(save_url, data=form_data, headers=headers, verify=False)
            if response.status_code == 200:
                if 'closeTab' in response.text or 'saved' in response.text.lower():
                    lab_names = [l.get('description', 'Unknown')[:20] for l in lab_data[:3]]
                    print(f"        ✓ Added {len(lab_data)} Lab Result(s): {', '.join(lab_names)}...")
                    return True
                else:
                    print(f"        ? Lab results submitted but response unclear")
                    return True
            else:
                print(f"        ✗ Failed Lab Results: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"        ✗ Lab Results error: {e}")
            return False

    # ==================== MEDICAL/SOCIAL HISTORY ====================
    
    def update_history(self, pid, history_data):
        """
        Update patient's medical and social history.
        
        Args:
            pid: Patient ID
            history_data: dict with history fields:
                - tobacco: Smoking status
                - alcohol: Alcohol use
                - exercise_patterns: Exercise habits
                - recreational_drugs: Drug use
                - coffee: Coffee/caffeine intake
                - counseling: Mental health counseling
                - hazardous_activities: Hazardous activities
                - additional_history: Additional notes
                
                Family history:
                - history_mother: Mother's medical history
                - history_father: Father's medical history
                - history_siblings: Siblings' medical history
                - history_spouse: Spouse's medical history
                - history_offspring: Children's medical history
                
                Family conditions (checkbox-style):
                - relatives_cancer
                - relatives_diabetes
                - relatives_high_blood_pressure
                - relatives_heart_problems
                - relatives_stroke
                - relatives_epilepsy
                - relatives_mental_illness
                - relatives_suicide
        """
        self.set_active_patient(pid)
        
        form_url = f"{self.base_url}/interface/patient_file/history/history_full.php"
        
        csrf_token = self.get_csrf_token(form_url)
        if not csrf_token:
            print("      ! Could not get CSRF token for history form")
            return False
        
        # Build form data
        form_data = {
            'csrf_token_form': csrf_token,
            # Social history
            'form_tobacco': history_data.get('tobacco', ''),
            'form_alcohol': history_data.get('alcohol', ''),
            'form_exercise_patterns': history_data.get('exercise_patterns', ''),
            'form_recreational_drugs': history_data.get('recreational_drugs', ''),
            'form_coffee': history_data.get('coffee', ''),
            'form_counseling': history_data.get('counseling', ''),
            'form_hazardous_activities': history_data.get('hazardous_activities', ''),
            'form_additional_history': history_data.get('additional_history', ''),
            # Family history
            'form_history_mother': history_data.get('history_mother', ''),
            'form_history_father': history_data.get('history_father', ''),
            'form_history_siblings': history_data.get('history_siblings', ''),
            'form_history_spouse': history_data.get('history_spouse', ''),
            'form_history_offspring': history_data.get('history_offspring', ''),
            # Family conditions
            'form_relatives_cancer': history_data.get('relatives_cancer', ''),
            'form_relatives_diabetes': history_data.get('relatives_diabetes', ''),
            'form_relatives_high_blood_pressure': history_data.get('relatives_high_blood_pressure', ''),
            'form_relatives_heart_problems': history_data.get('relatives_heart_problems', ''),
            'form_relatives_stroke': history_data.get('relatives_stroke', ''),
            'form_relatives_epilepsy': history_data.get('relatives_epilepsy', ''),
            'form_relatives_mental_illness': history_data.get('relatives_mental_illness', ''),
            'form_relatives_suicide': history_data.get('relatives_suicide', ''),
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': self.base_url,
            'Referer': form_url
        }
        
        try:
            response = self.session.post(form_url, data=form_data, headers=headers, verify=False)
            if response.status_code == 200:
                print(f"      ✓ Updated Medical/Social History")
                return True
            else:
                print(f"      ✗ Failed History: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"      ✗ History error: {e}")
            return False

    # ==================== INSURANCE ====================
    
    def add_insurance(self, pid, insurance_data, insurance_type="primary"):
        """
        Add insurance information to a patient.
        
        Args:
            pid: Patient ID
            insurance_data: dict with insurance fields:
                - provider: Insurance company name
                - plan_name: Plan name
                - policy_number: Policy number
                - group_number: Group number
                - subscriber_fname: Subscriber first name
                - subscriber_lname: Subscriber last name
                - subscriber_relationship: Relationship (self, spouse, child, etc.)
                - subscriber_DOB: Subscriber DOB
                - copay: Copay amount
            insurance_type: "primary", "secondary", or "tertiary"
        """
        self.set_active_patient(pid)
        
        # Insurance type prefix
        prefix = {'primary': 'i1', 'secondary': 'i2', 'tertiary': 'i3'}.get(insurance_type, 'i1')
        
        # Get the demographics edit page
        form_url = f"{self.base_url}/interface/patient_file/summary/demographics_full.php"
        
        csrf_token = self.get_csrf_token(form_url)
        if not csrf_token:
            print("      ! Could not get CSRF token for insurance form")
            return False
        
        form_data = {
            'csrf_token_form': csrf_token,
            f'form_{prefix}subscriber_relationship': insurance_data.get('subscriber_relationship', 'self'),
            f'{prefix}subscriber_fname': insurance_data.get('subscriber_fname', ''),
            f'{prefix}subscriber_lname': insurance_data.get('subscriber_lname', ''),
            f'{prefix}subscriber_DOB': insurance_data.get('subscriber_DOB', ''),
            f'form_{prefix}provider': insurance_data.get('provider', ''),
            f'{prefix}plan_name': insurance_data.get('plan_name', ''),
            f'{prefix}policy_number': insurance_data.get('policy_number', ''),
            f'{prefix}group_number': insurance_data.get('group_number', ''),
            f'{prefix}subscriber_employer': insurance_data.get('subscriber_employer', ''),
            f'form_copay': insurance_data.get('copay', ''),
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': self.base_url,
            'Referer': form_url
        }
        
        try:
            response = self.session.post(form_url, data=form_data, headers=headers, verify=False)
            if response.status_code == 200:
                print(f"      ✓ Added {insurance_type.title()} Insurance: {insurance_data.get('provider', 'Unknown')}")
                return True
            else:
                print(f"      ✗ Failed Insurance: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"      ✗ Insurance error: {e}")
            return False



# ==================== PATIENT DATA LOADER ====================
# Load patient records from JSONL file for easy management

def load_patients_from_jsonl(filepath=None):
    """
    Load patient records from a JSONL file.
    
    Each line in the JSONL file should be a complete JSON object representing
    a patient with their demographics, medical history, and encounters.
    
    Args:
        filepath: Path to the JSONL file. If None, defaults to 'patients.jsonl'
                  in the same directory as this script.
                  
    Returns:
        List of patient dictionaries
    """
    if filepath is None:
        # Default to patients.jsonl in the same directory as this script
        script_dir = Path(__file__).parent
        filepath = script_dir / "patients.jsonl"
    else:
        filepath = Path(filepath)
    
    if not filepath.exists():
        print(f"  ✗ Patient file not found: {filepath}")
        return []
    
    patients = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:  # Skip empty lines
                continue
            try:
                patient = json.loads(line)
                patients.append(patient)
            except json.JSONDecodeError as e:
                print(f"  ✗ Error parsing line {line_num}: {e}")
                continue
    
    print(f"  ✓ Loaded {len(patients)} patient(s) from {filepath.name}")
    return patients


def import_patient_with_history(emr, patient_data):
    """
    Create a patient and add their complete medical history including
    longitudinal data (multiple encounters with vitals over time).
    
    Args:
        emr: OpenEMRWebSession instance
        patient_data: dict containing demographics, medical history, and encounters
        
    Returns:
        pid if successful, None if failed
    """
    full_name = f"{patient_data['fname']} {patient_data.get('mname', '')} {patient_data['lname']}".replace("  ", " ")
    print(f"\n{'='*60}")
    print(f"Processing: {full_name}")
    print(f"{'='*60}")
    
    # Extract demographics (exclude medical data keys)
    exclude_keys = ['problems', 'medications', 'allergies', 'history', 'insurance', 'encounters']
    demographics = {k: v for k, v in patient_data.items() if k not in exclude_keys}
    
    # Create patient
    print("  Creating patient record...")
    pid = emr.create_patient(demographics)
    
    if not pid:
        print(f"  ✗ Failed to create patient, skipping medical history")
        return None
    
    # Add medical problems
    problems = patient_data.get('problems', [])
    if problems:
        print(f"  Adding {len(problems)} problem(s)...")
        date_past = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        for problem in problems:
            emr.add_problem(
                pid, 
                problem['title'], 
                problem.get('icd10', ''), 
                date_past,
                problem.get('comments', '')
            )
    
    # Add medications
    medications = patient_data.get('medications', [])
    if medications:
        print(f"  Adding {len(medications)} medication(s)...")
        date_past = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M")
        for med in medications:
            emr.add_medication(
                pid,
                med['title'],
                med.get('dosage', ''),
                date_past
            )
    
    # Add allergies
    allergies = patient_data.get('allergies', [])
    if allergies:
        print(f"  Adding {len(allergies)} allergy(ies)...")
        for allergy in allergies:
            emr.add_allergy(
                pid,
                allergy['title'],
                allergy.get('reaction', ''),
                allergy.get('severity', '')
            )
    
    # Update medical/social history
    history = patient_data.get('history', {})
    if history:
        print(f"  Updating medical/social history...")
        emr.update_history(pid, history)
    
    # Add insurance
    insurance = patient_data.get('insurance', {})
    if insurance:
        print(f"  Adding insurance information...")
        emr.add_insurance(pid, insurance, "primary")
    
    # Create longitudinal encounters with vitals and labs
    encounters = patient_data.get('encounters', [])
    if encounters:
        print(f"  Creating {len(encounters)} encounter(s) with vitals/labs...")
        for enc in encounters:
            enc_id = emr.create_encounter(
                pid,
                enc['date'],
                enc.get('reason', 'Office Visit')
            )
            if enc_id:
                if 'vitals' in enc:
                    emr.add_vitals(pid, enc_id, enc['vitals'])
                if 'labs' in enc:
                    emr.add_lab_results(pid, enc_id, enc['labs'])
    
    print(f"  ✓ Completed: {full_name} (PID: {pid})")
    return pid


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("=" * 60)
    print("  OpenEMR Combined Patient Import & Enrichment Script")
    print("  With Longitudinal Data Support")
    print("=" * 60)
    
    print("\nLoading patient data from JSONL file...")
    PATIENTS = load_patients_from_jsonl()
    
    if not PATIENTS:
        print("No patients to import. Check patients.jsonl file.")
        exit(1)
    
    print("\nInitializing Web Session...")
    emr = OpenEMRWebSession(OPENEMR_URL, USERNAME, PASSWORD)
    
    print("Logging in...")
    if not emr.login():
        print("Failed to login!")
        exit(1)
    
    print(f"\nStarting import of {len(PATIENTS)} patient(s)...")
    print("Each patient includes: demographics, problems, medications,")
    print("allergies, history, insurance, and longitudinal encounters.\n")
    
    results = {"success": [], "failed": []}
    
    for patient in PATIENTS:
        pid = import_patient_with_history(emr, patient)
        name = f"{patient['fname']} {patient['lname']}"
        if pid:
            results["success"].append((name, pid))
        else:
            results["failed"].append(name)
    
    # Summary
    print("\n" + "=" * 60)
    print("  IMPORT SUMMARY")
    print("=" * 60)
    print(f"  Successful: {len(results['success'])}")
    for name, pid in results["success"]:
        print(f"    - {name} (PID: {pid})")
    
    if results["failed"]:
        print(f"  Failed: {len(results['failed'])}")
        for name in results["failed"]:
            print(f"    - {name}")
    
    # Stats
    total_encounters = sum(len(p.get('encounters', [])) for p in PATIENTS)
    total_problems = sum(len(p.get('problems', [])) for p in PATIENTS)
    total_meds = sum(len(p.get('medications', [])) for p in PATIENTS)
    print(f"\n  Data imported:")
    print(f"    - {total_problems} medical problems")
    print(f"    - {total_meds} medications")
    print(f"    - {total_encounters} encounters with vitals")
    
    print("\n  Import Complete!")

