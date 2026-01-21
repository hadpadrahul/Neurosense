
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api/v1"
TEST_USER = "authtestuser_v1"
TEST_PASS = "testpassword123"

def print_result(name, response, expected_status):
    if response.status_code == expected_status:
        print(f"[OK] {name} ({response.status_code})")
        return True
    else:
        print(f"[FAIL] {name} ({response.status_code})")
        print(f"Response: {response.text}")
        return False

def run_auth_test():
    print("--- Auth API Verification ---")

    # 1. Register
    reg_url = f"{BASE_URL}/register/"
    reg_data = {"username": TEST_USER, "password": TEST_PASS}
    # cleanup first if exists? No easy way via API without login. 
    # Just try to register. If fails (already exists), we proceed to login.
    
    print(f"Testing Register: {TEST_USER}")
    resp = requests.post(reg_url, json=reg_data)
    
    if resp.status_code == 400 and "already exists" in resp.text:
         print(f"[WARN] User {TEST_USER} already exists. Proceeding to login.")
    else:
         print_result("Register", resp, 201)

    # 2. Login (Get Token)
    login_url = f"{BASE_URL}/token/"
    resp = requests.post(login_url, json=reg_data)
    if not print_result("Login", resp, 200):
        return

    tokens = resp.json()
    access_token = tokens['access']
    refresh_token = tokens['refresh']
    print("Tokens retrieved successfully.")

    # 3. Access Protected Route (Before Logout)
    headers = {"Authorization": f"Bearer {access_token}"}
    hist_url = f"{BASE_URL}/history/"
    resp = requests.get(hist_url, headers=headers)
    print_result("Access History (Pre-Logout)", resp, 200)

    # 4. Logout (Blacklist Token)
    logout_url = f"{BASE_URL}/logout/"
    logout_data = {"refresh": refresh_token}
    resp = requests.post(logout_url, json=logout_data, headers=headers)
    print_result("Logout", resp, 205)

    # 5. Verify Token Rejected (After Logout)
    # Note: SimpleJWT blacklist invalidates the REFRESH token, preventing new access tokens.
    # The ACCESS token might still be valid until it expires (stateless). 
    # To test blacklist effectively, we should try to refresh the token.
    
    refresh_url = f"{BASE_URL}/token/refresh/"
    resp = requests.post(refresh_url, json={"refresh": refresh_token})
    if resp.status_code == 401 or resp.status_code == 400:
        print(f"[OK] Refresh Token Invalidated ({resp.status_code})")
    else:
        print(f"[FAIL] Refresh Token still valid! ({resp.status_code})")
        print(resp.text)

if __name__ == "__main__":
    run_auth_test()
