from flask import Flask, request, jsonify
import cloudscraper
import json
import re
import requests
from bs4 import BeautifulSoup
import os
import gzip
from io import BytesIO
import brotli
import logging
import time
from datetime import datetime, timedelta

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

start_time = datetime.now()

session = cloudscraper.create_scraper()

def load_cookies(session, filename='cookies.json'):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            cookies_raw = json.load(f)
        if not isinstance(cookies_raw, list):
            logger.error("Cookies file must be a list of cookie objects")
            return False
        cookie_dict = {}
        cookie_count = 0
        for cookie in cookies_raw:
            if 'name' in cookie and 'value' in cookie:
                domain = cookie.get('domain', '.freepik.com')
                session.cookies.set(
                    cookie['name'],
                    cookie['value'],
                    domain=domain,
                    path=cookie.get('path', '/')
                )
                cookie_dict[cookie['name']] = cookie['value']
                cookie_count += 1
        logger.info(f"Loaded {cookie_count} cookies")
        logger.info(f"GR_TOKEN: {cookie_dict.get('GR_TOKEN', 'Not found')}")
        logger.info(f"UID: {cookie_dict.get('UID', 'Not found')}")
        if not cookie_dict.get('UID'):
            logger.warning("UID cookie not found. This may cause issues with some API requests.")
        return cookie_dict
    except Exception as e:
        logger.error(f"Error loading cookies: {e}")
        return False

headers = {
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

cookie_dict = load_cookies(session)
if not cookie_dict:
    logger.error("Failed to load cookies. Exiting.")
    exit(1)

@app.route('/', methods=['GET'])
def welcome():
    return jsonify({
        "message": "Welcome to the Freepik Downloader API!",
        "tutorial": "Use the /dl endpoint with a Freepik Premium URL, e.g., /dl?url=https://www.freepik.com/premium-psd/party-template-design_185368128.htm",
        "api_dev": "@ISmartCoder",
        "updates_channel": "t.me/TheSmartDev"
    })

@app.route('/dl', methods=['GET'])
def download_asset():
    start_request_time = time.time()
    asset_url = request.args.get('url')
    if not asset_url:
        logger.error("No URL provided in query parameter")
        return jsonify({
            "error": "No URL provided. Use /dl?url=<freepik_url>",
            "api dev": "@ISmartCoder",
            "Updates Channel": "t.me/TheSmartDev",
            "time taken": f"{time.time() - start_request_time:.2f} seconds",
            "api uptime": str(datetime.now() - start_time)
        }), 400

    logger.info(f"Processing asset URL: {asset_url}")

    try:
        homepage_response = session.get("https://www.freepik.com/", headers=headers, timeout=30)
        logger.info(f"Homepage response: {homepage_response.status_code}")
        if homepage_response.status_code != 200:
            logger.error(f"Failed to load homepage: {homepage_response.status_code}")
            return jsonify({
                "error": f"Failed to load homepage: {homepage_response.status_code}",
                "api dev": "@ISmartCoder",
                "Updates Channel": "t.me/TheSmartDev",
                "time taken": f"{time.time() - start_request_time:.2f} seconds",
                "api uptime": str(datetime.now() - start_time)
            }), 500
    except Exception as e:
        logger.error(f"Error visiting homepage: {e}")
        return jsonify({
            "error": f"Error visiting homepage: {str(e)}",
            "api dev": "@ISmartCoder",
            "Updates Channel": "t.me/TheSmartDev",
            "time taken": f"{time.time() - start_request_time:.2f} seconds",
            "api uptime": str(datetime.now() - start_time)
        }), 500

    profile_url = "https://www.freepik.com/profile"
    try:
        headers['Referer'] = 'https://www.freepik.com/'
        profile_response = session.get(profile_url, headers=headers, timeout=30)
        logger.info(f"Profile page response: {profile_response.status_code}")
        if profile_response.status_code != 200:
            logger.error(f"Failed to access profile page: {profile_response.status_code}")
            return jsonify({
                "error": f"Failed to access profile page: {profile_response.status_code}",
                "api dev": "@ISmartCoder",
                "Updates Channel": "t.me/TheSmartDev",
                "time taken": f"{time.time() - start_request_time:.2f} seconds",
                "api uptime": str(datetime.now() - start_time)
        }), 500
        soup = BeautifulSoup(profile_response.text, 'html.parser')
        if not ("premium" in profile_response.text.lower() or "profile" in profile_response.text.lower()):
            logger.warning("Login may have succeeded, but premium/profile not detected")
    except Exception as e:
        logger.error(f"Error checking login status: {e}")
        return jsonify({
            "error": f"Error checking login status: {str(e)}",
            "api dev": "@ISmartCoder",
            "Updates Channel": "t.me/TheSmartDev",
            "time taken": f"{time.time() - start_request_time:.2f} seconds",
            "api uptime": str(datetime.now() - start_time)
        }), 500

    try:
        headers['Referer'] = profile_url
        asset_response = session.get(asset_url, headers=headers, timeout=30)
        logger.info(f"Asset page response: {asset_response.status_code}")
        if asset_response.status_code != 200:
            logger.error(f"Failed to load asset page: {asset_response.status_code}")
            return jsonify({
                "error": f"Failed to load asset page: {asset_response.status_code}",
                "api dev": "@ISmartCoder",
                "Updates Channel": "t.me/TheSmartDev",
                "time taken": f"{time.time() - start_request_time:.2f} seconds",
                "api uptime": str(datetime.now() - start_time)
            }), 500
    except Exception as e:
        logger.error(f"Error accessing asset page: {e}")
        return jsonify({
            "error": f"Error accessing asset page: {str(e)}",
            "api dev": "@ISmartCoder",
            "Updates Channel": "t.me/TheSmartDev",
            "time taken": f"{time.time() - start_request_time:.2f} seconds",
            "api uptime": str(datetime.now() - start_time)
        }), 500

    soup = BeautifulSoup(asset_response.text, 'html.parser')
    asset_id_match = re.search(r'_(\d+)\.htm', asset_url)
    asset_id = asset_id_match.group(1) if asset_id_match else None
    logger.info(f"Asset ID: {asset_id or 'Not found'}")
    if not asset_id:
        logger.error("Could not extract asset ID from URL")
        return jsonify({
            "error": "Could not extract asset ID from URL",
            "api dev": "@ISmartCoder",
            "Updates Channel": "t.me/TheSmartDev",
            "time taken": f"{time.time() - start_request_time:.2f} seconds",
            "api uptime": str(datetime.now() - start_time)
        }), 400

    wallet_id = None
    wallet_patterns = [
        r'"walletId":"([^"]+)"',
        r"'walletId':'([^']+)'",
        r'walletId["\']?\s*:\s*["\']([^"\']+)["\']',
        r'data-wallet-id["\']?\s*=\s*["\']([^"\']+)["\']',
        r'wallet[_-]?id["\']?\s*:\s*["\']([^"\']+)["\']',
        r'WALLET_ID["\']?\s*:\s*["\']([^"\']+)["\']',
        r'wallet["\']?\s*:\s*["\']([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})["\']',
        r'id["\']?\s*:\s*["\']([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})["\']',
        r'"user_wallet_id":"([^"]+)"',
        r'"wallet_id":"([^"]+)"',
        r'"userId":"([^"]+)"',
        r'"sessionId":"([^"]+)"'
    ]

    logger.info("Searching for wallet ID patterns...")
    for i, pattern in enumerate(wallet_patterns):
        match = re.search(pattern, asset_response.text, re.IGNORECASE)
        if match:
            wallet_id = match.group(1)
            logger.info(f"Wallet ID found with pattern {i+1}: {wallet_id}")
            break

    if not wallet_id:
        logger.info("Wallet ID not found in page, trying to extract from profile...")
        try:
            profile_response = session.get("https://www.freepik.com/profile", headers=headers, timeout=30)
            if profile_response.status_code == 200:
                for i, pattern in enumerate(wallet_patterns):
                    match = re.search(pattern, profile_response.text, re.IGNORECASE)
                    if match:
                        wallet_id = match.group(1)
                        logger.info(f"Wallet ID found in profile with pattern {i+1}: {wallet_id}")
                        break
        except Exception as e:
            logger.error(f"Error getting wallet ID from profile: {e}")

    if not wallet_id:
        logger.info("Trying to extract wallet ID from script tags...")
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string:
                uuid_matches = re.findall(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', script.string, re.IGNORECASE)
                if uuid_matches:
                    for uuid in uuid_matches:
                        if uuid not in ['00000000-0000-0000-0000-000000000000']:
                            wallet_id = uuid
                            logger.info(f"Potential wallet ID found in script: {wallet_id}")
                            break
                    if wallet_id:
                        break

    if not wallet_id:
        logger.info("Trying to find wallet ID in window/user data...")
        window_patterns = [
            r'window\.user\s*=\s*\{[^}]*["\']?wallet[_-]?[iI]d["\']?\s*:\s*["\']([^"\']+)["\']',
            r'window\.USER\s*=\s*\{[^}]*["\']?wallet[_-]?[iI]d["\']?\s*:\s*["\']([^"\']+)["\']',
            r'__INITIAL_STATE__[^}]*wallet[_-]?[iI]d["\']?\s*:\s*["\']([^"\']+)["\']',
            r'USER_DATA[^}]*wallet[_-]?[iI]d["\']?\s*:\s*["\']([^"\']+)["\']',
            r'window\.user\s*=\s*\{[^}]*["\']?user_wallet_id["\']?\s*:\s*["\']([^"\']+)["\']',
            r'window\.USER\s*=\s*\{[^}]*["\']?user_wallet_id["\']?\s*:\s*["\']([^"\']+)["\']',
            r'window\.user\s*=\s*\{[^}]*["\']?userId["\']?\s*:\s*["\']([^"\']+)["\']',
            r'window\.USER\s*=\s*\{[^}]*["\']?sessionId["\']?\s*:\s*["\']([^"\']+)["\']'
        ]
        for pattern in window_patterns:
            match = re.search(pattern, asset_response.text, re.IGNORECASE)
            if match:
                wallet_id = match.group(1)
                logger.info(f"Wallet ID found in window/user data: {wallet_id}")
                break

    if not wallet_id:
        wallet_id = '6b3d01e4-c160-4d2c-9b38-1b5441687f50'
        logger.info(f"Using saved wallet ID: {wallet_id}")

    download_api_url = "https://www.freepik.com/api/regular/download"
    params = {
        'resource': asset_id,
        'action': 'download',
        'walletId': wallet_id,
        'locale': 'en'
    }
    headers['Referer'] = asset_url
    headers['Accept'] = 'application/json, text/plain, */*'

    try:
        api_response = session.get(download_api_url, headers=headers, params=params, timeout=30)
        logger.info(f"API response: {api_response.status_code}")
        logger.info(f"Response headers: {api_response.headers}")

        response_text = api_response.text
        if api_response.headers.get('Content-Encoding') in ['gzip', 'br']:
            logger.info(f"Detected {api_response.headers.get('Content-Encoding')} compression, checking if already decompressed...")
            try:
                json.loads(response_text)
                logger.info("Response appears to be decompressed by cloudscraper")
            except json.JSONDecodeError:
                if api_response.headers.get('Content-Encoding') == 'gzip':
                    logger.info("Attempting manual gzip decompression...")
                    try:
                        compressed_data = BytesIO(api_response.content)
                        response_text = gzip.GzipFile(fileobj=compressed_data).read().decode('utf-8')
                        logger.info("Successfully decompressed gzip response")
                    except Exception as e:
                        logger.error(f"Failed to decompress gzip response: {e}")
                        return jsonify({
                            "error": f"Failed to decompress gzip response: {str(e)}",
                            "api dev": "@ISmartCoder",
                            "Updates Channel": "t.me/TheSmartDev",
                            "time taken": f"{time.time() - start_request_time:.2f} seconds",
                            "api uptime": str(datetime.now() - start_time)
                        }), 500
                elif api_response.headers.get('Content-Encoding') == 'br':
                    logger.info("Attempting manual Brotli decompression...")
                    try:
                        response_text = brotli.decompress(api_response.content).decode('utf-8')
                        logger.info("Successfully decompressed Brotli response")
                    except Exception as e:
                        logger.error(f"Failed to decompress Brotli response: {e}")
                        return jsonify({
                            "error": f"Failed to decompress Brotli response: {str(e)}",
                            "api dev": "@ISmartCoder",
                            "Updates Channel": "t.me/TheSmartDev",
                            "time taken": f"{time.time() - start_request_time:.2f} seconds",
                            "api uptime": str(datetime.now() - start_time)
                        }), 500

        if api_response.status_code == 200:
            logger.info(f"API response received: {response_text}")
            try:
                api_data = json.loads(response_text)
                download_url = api_data.get('url')
                filename = api_data.get('filename', f'asset_{asset_id}.jpg')
                signed_url = api_data.get('signedUrl', '')

                if download_url:
                    logger.info(f"Download URL: {download_url}")
                    logger.info(f"Filename: {filename}")
                    return jsonify({
                        "download url": download_url,
                        "signed url": signed_url,
                        "file name": filename,
                        "api dev": "@ISmartCoder",
                        "Updates Channel": "t.me/TheSmartDev",
                        "time taken": f"{time.time() - start_request_time:.2f} seconds",
                        "api uptime": str(datetime.now() - start_time)
                    }), 200
                else:
                    logger.error("No download URL found in API response")
                    return jsonify({
                        "error": "No download URL found in API response",
                        "api dev": "@ISmartCoder",
                        "Updates Channel": "t.me/TheSmartDev",
                        "time taken": f"{time.time() - start_request_time:.2f} seconds",
                        "api uptime": str(datetime.now() - start_time)
                    }), 500
            except json.JSONDecodeError:
                logger.error("Failed to parse API response as JSON")
                return jsonify({
                    "error": "Failed to parse API response as JSON",
                    "api dev": "@ISmartCoder",
                    "Updates Channel": "t.me/TheSmartDev",
                    "time taken": f"{time.time() - start_request_time:.2f} seconds",
                    "api uptime": str(datetime.now() - start_time)
                }), 500
        else:
            logger.error(f"API request failed: {api_response.status_code}")
            return jsonify({
                "error": f"API request failed: {api_response.status_code}",
                "api dev": "@ISmartCoder",
                "Updates Channel": "t.me/TheSmartDev",
                "time taken": f"{time.time() - start_request_time:.2f} seconds",
                "api uptime": str(datetime.now() - start_time)
            }), 500
    except Exception as e:
        logger.error(f"Error during API request: {e}")
        return jsonify({
            "error": f"Error during API request: {str(e)}",
            "api dev": "@ISmartCoder",
            "Updates Channel": "t.me/TheSmartDev",
            "time taken": f"{time.time() - start_request_time:.2f} seconds",
            "api uptime": str(datetime.now() - start_time)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
