#Copyright @ISmartCoder
#Updates Channel: https://t.me/TheSmartDev

from flask import Flask, request, jsonify
import cloudscraper
import json
import re
import os
import threading
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class FreepikDownloader:
    def __init__(self):
        self.session = cloudscraper.create_scraper()
        self.cookies_loaded = False
        self.wallet_id = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,bn;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Connection': 'keep-alive',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://www.freepik.com/',
            'Sec-Ch-Ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
        }
        self.load_cookies()
    
    def load_cookies(self, filename='cookies.json'):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                cookies_raw = json.load(f)
            
            if not isinstance(cookies_raw, list):
                logger.error("Cookies file must be a list of cookie objects")
                return False
            
            cookie_count = 0
            for cookie in cookies_raw:
                if 'name' in cookie and 'value' in cookie:
                    domain = cookie.get('domain', '.freepik.com')
                    self.session.cookies.set(
                        cookie['name'],
                        cookie['value'],
                        domain=domain,
                        path=cookie.get('path', '/')
                    )
                    cookie_count += 1
            
            logger.info(f"Loaded {cookie_count} cookies")
            self.cookies_loaded = True
            return True
            
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            return False
    
    def verify_login(self):
        try:
            homepage_response = self.session.get("https://www.freepik.com/", headers=self.headers, timeout=30)
            if homepage_response.status_code != 200:
                return False
            
            profile_response = self.session.get("https://www.freepik.com/profile", headers=self.headers, timeout=30)
            if profile_response.status_code == 200:
                return "premium" in profile_response.text.lower() or "profile" in profile_response.text.lower()
            
            return False
            
        except Exception as e:
            logger.error(f"Error verifying login: {e}")
            return False
    
    def extract_asset_id(self, url):
        try:
            # Common patterns for Freepik asset IDs
            patterns = [
                r'_(\d+)\.htm',  # Standard pattern: _123456.htm
                r'resource_id=(\d+)',  # Query parameter pattern
                r'\/(\d+)\/',  # ID in URL path
                r'(\d+)(?:\.htm|$)',  # ID at end of URL or before .htm
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            # Fallback: Parse page content for asset ID
            response = self.session.get(url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for data-resource-id or similar attributes
                for attr in ['data-resource-id', 'data-id', 'resource-id']:
                    element = soup.find(attrs={attr: re.compile(r'\d+')})
                    if element and element.get(attr):
                        return element.get(attr)
                
                # Look for script tags with asset ID
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string:
                        script_match = re.search(r'"resourceId"\s*:\s*"(\d+)"', script.string)
                        if script_match:
                            return script_match.group(1)
                        script_match = re.search(r'resource_id\s*=\s*["\']?(\d+)["\']?', script.string)
                        if script_match:
                            return script_match.group(1)
            
            return None
        except Exception as e:
            logger.error(f"Error extracting asset ID: {e}")
            return None
    
    def extract_wallet_id(self, page_content):
        wallet_patterns = [
            r'"walletId":"([^"]+)"',
            r"'walletId':'([^']+)'",
            r'walletId["\']?\s*:\s*["\']([^"\']+)["\']',
            r'data-wallet-id["\']?\s*=\s*["\']([^"\']+)["\']',
            r'wallet[_-]?id["\']?\s*:\s*["\']([^"\']+)["\']',
            r'WALLET_ID["\']?\s*:\s*["\']([^"\']+)["\']',
            r'wallet["\']?\s*:\s*["\']([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})["\']',
            r'id["\']?\s*:\s*["\']([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})["\']'
        ]
        
        for pattern in wallet_patterns:
            match = re.search(pattern, page_content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        soup = BeautifulSoup(page_content, 'html.parser')
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string:
                uuid_matches = re.findall(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', script.string, re.IGNORECASE)
                if uuid_matches:
                    for uuid in uuid_matches:
                        if uuid != '00000000-0000-0000-0000-000000000000':
                            return uuid
        
        return 'e2f46fb3-2bfa-47ec-bf51-8465ac4bc88a'
    
    def get_download_info(self, url):
        try:
            asset_id = self.extract_asset_id(url)
            if not asset_id:
                return {"error": "Could not extract asset ID from URL"}
            
            self.headers['Referer'] = 'https://www.freepik.com/profile'
            asset_response = self.session.get(url, headers=self.headers, timeout=30)
            
            if asset_response.status_code != 200:
                return {"error": f"Failed to load asset page: {asset_response.status_code}"}
            
            wallet_id = self.extract_wallet_id(asset_response.text)
            
            download_api_url = "https://www.freepik.com/api/regular/download"
            params = {
                'resource': asset_id,
                'action': 'download',
                'walletId': wallet_id,
                'locale': 'en'
            }
            
            self.headers['Referer'] = url
            self.headers['Accept'] = 'application/json, text/plain, */*'
            
            api_response = self.session.get(download_api_url, headers=self.headers, params=params, timeout=30)
            
            if api_response.status_code != 200:
                return {"error": f"API request failed: {api_response.status_code}"}
            
            try:
                api_data = api_response.json()
                return {
                    "success": True,
                    "asset_id": asset_id,
                    "wallet_id": wallet_id,
                    "filename": api_data.get('filename', f'asset_{asset_id}'),
                    "download_url": api_data.get('url'),
                    "signed_url": api_data.get('signedUrl')
                }
            except json.JSONDecodeError:
                return {"error": "Failed to parse API response as JSON"}
                
        except Exception as e:
            logger.error(f"Error getting download info: {e}")
            return {"error": f"Internal error: {str(e)}"}

downloader = FreepikDownloader()

@app.route('/')
def index():
    return jsonify({
        "name": "Freepik Downloader API",
        "version": "1.0.0",
        "endpoints": {
            "/": "API documentation",
            "/dl": "Get download information for a Freepik asset"
        },
        "usage": {
            "endpoint": "/dl",
            "method": "GET",
            "parameter": "url",
            "example": "/dl?url=https://www.freepik.com/premium-photo/example_123456.htm"
        }
    })

@app.route('/dl')
def download():
    if not downloader.cookies_loaded:
        return jsonify({
            "error": "Cookies not loaded. Please ensure cookies.json exists."
        }), 500
    
    url = request.args.get('url')
    if not url:
        return jsonify({
            "error": "Missing 'url' parameter",
            "usage": "GET /dl?url=https://www.freepik.com/premium-photo/example_123456.htm"
        }), 400
    
    if not url.startswith('https://www.freepik.com/'):
        return jsonify({
            "error": "Invalid URL. Must be a Freepik URL starting with https://www.freepik.com/"
        }), 400
    
    result = downloader.get_download_info(url)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result)

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": ["/", "/dl"]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "message": "Something went wrong on our end"
    }), 500

if __name__ == '__main__':
    print("Starting Freepik Downloader API...")
    print("Available endpoints:")
    print("   GET /          - API documentation")
    print("   GET /dl?url=   - Get download information")
    print()
    print("Example usage:")
    print("   http://0.0.0.0:5000/dl?url=https://www.freepik.com/premium-photo/example_123456.htm")
    print()
    print("Make sure cookies.json exists in the same directory!")
    print()
    
    app.run(host='0.0.0.0', port=5000, debug=True)