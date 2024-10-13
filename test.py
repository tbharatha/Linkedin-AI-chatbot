from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import sys
sys.path.append("/opt/miniconda3/envs/pivot/bin/python")
# from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import xlsxwriter
import random
class Linkedin:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Running headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        self.service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=self.service)
        self.data = []


    def login(self, username, password):
        try:
            print("Logging in...")
            self.driver.get('https://www.linkedin.com/login')
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'username')))
            print("Login page loaded")
            self.driver.find_element(By.ID, 'username').send_keys(username)
            self.driver.find_element(By.ID, 'password').send_keys(password)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            # print(self.driver.current_url)
            # self.driver.save_screenshot('login_page_error.png')
            try:
                WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH, "//button[text()='Verify']")))
                print("CAPTCHA detected. Please solve it manually in the browser.")
                
                # Wait for the user to solve the CAPTCHA and confirm in the terminal
                input("After solving the CAPTCHA manually, press Enter to continue...")

                # Wait for LinkedIn feed after CAPTCHA is solved
                WebDriverWait(self.driver, 20).until(EC.url_contains("feed"))
                print("Successfully logged in after CAPTCHA!")
            except Exception:
                print("No CAPTCHA. Checking for OTP verification...")

                # Check for OTP input field
                try:
                    WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'input__email_verification_pin')))
                    print("OTP verification detected. Please enter the OTP code sent to your email.")

                    # Prompt the user for OTP input
                    otp_code = input("Enter the OTP code: ")

                    # Submit the OTP code
                    self.driver.find_element(By.ID, 'input__email_verification_pin').send_keys(otp_code)
                    self.driver.find_element(By.XPATH, "//button[@type='submit']").click()

                    # Wait for feed page to ensure OTP verification is successful
                    WebDriverWait(self.driver, 20).until(EC.url_contains("feed"))
                    print("Successfully logged in after OTP verification!")
                except Exception as e:
                    print(f"OTP verification not found or failed: {e}")
                    self.driver.save_screenshot('login_verification_or_error.png')
                    print("Saved screenshot of potential verification page.")
                    return False
        except Exception as e:
            print(f"Error: {e}")
            self.driver.save_screenshot('login_failure.png')
            return False

    def search_and_scrape(self, search_key, num_pages=1):
        keyword = "%20".join(word.capitalize() for word in search_key.split())
        
        for page in range(1, num_pages + 1):
            search_url = f"https://www.linkedin.com/search/results/people/?keywords={keyword}&origin=SUGGESTION&page={page}"
            print(f"Navigating to: {search_url}")
            self.driver.get(search_url)
            
            try:
                time.sleep(random.uniform(5, 10))  # Random delay to avoid detection
                WebDriverWait(self.driver, 60).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'entity-result__title-text'))
                )
            except Exception as e:
                print(f"Error waiting for page to load: {e}")
                continue 
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            people_links = [link['href'] for link in soup.find_all('a', class_='app-aware-link') if '/in/' in link['href']]
            
            print(f"Found {len(people_links)} profile links on page {page}")

            if len(people_links) == 0:
                print("No profile links found, there may be an issue with the HTML structure or LinkedIn limiting visibility.")

            for i, link in enumerate(people_links):
                try:
                    profile_url = link if link.startswith('https') else f"https://www.linkedin.com{link}"
                    self.scrape_profile(profile_url)
                except Exception as e:
                    print(f"Error retrieving profile link {i+1}: {e}")

    def scrape_profile(self, profile_url):
        print(f"Scraping profile: {profile_url}")
        self.driver.get(profile_url)
        time.sleep(random.uniform(5, 10))  # Random delay
        page = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        profile_data = {
            'Name': page.find("h1", class_='text-heading-xlarge').text.strip() if page.find("h1", class_='text-heading-xlarge') else 'None',
            'Current Position': page.find('div', class_='text-body-medium').text.strip() if page.find('div', class_='text-body-medium') else 'None',
            'Location': page.find('span', class_='text-body-small').text.strip() if page.find('span', class_='text-body-small') else 'None',
            'Profile URL': profile_url
        }
        
        # Extracting skills
        try:
            self.driver.get(profile_url + 'details/skills/')
            time.sleep(5)
            skills_page = BeautifulSoup(self.driver.page_source, 'html.parser')
            skills = [skill.text.strip() for skill in skills_page.find_all('span', class_='pv-skill-category-entity__name-text')]
            profile_data['Skills'] = ', '.join(skills) if skills else 'None'
        except Exception as e:
            print(f"Error scraping skills: {e}")
            profile_data['Skills'] = 'None'
        
        print(f"Scraped profile data: {profile_data}")
        self.data.append(profile_data)

    def write_data(self):
        print(f"Number of profiles scraped: {len(self.data)}")
        workbook = xlsxwriter.Workbook("linkedin_search_data.xlsx")
        worksheet = workbook.add_worksheet('People')
        bold = workbook.add_format({'bold': True})
        
        headers = ['Name', 'Current Position', 'Location', 'Profile URL', 'Skills']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, bold)
        
        for row, profile in enumerate(self.data, start=1):
            worksheet.write(row, 0, profile['Name'])
            worksheet.write(row, 1, profile['Current Position'])
            worksheet.write(row, 2, profile['Location'])
            worksheet.write(row, 3, profile['Profile URL'])
            worksheet.write(row, 4, profile['Skills'])
        
        workbook.close()

    def start(self, username, password, search_key, num_pages=1):
        self.login(username, password)
        self.search_and_scrape(search_key, num_pages)
        self.write_data()
        self.driver.quit()

if __name__ == "__main__":
    linkedin_scraper = Linkedin()
    linkedin_scraper.start(
        username='',
        password='',
        search_key='data analyst',
        num_pages= 2
    )
