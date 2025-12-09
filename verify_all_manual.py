import requests
import os
import sys
import time

BASE_URL = "http://localhost:8000"

def print_pass(msg):
    print(f"\033[92m[PASS] {msg}\033[0m")

def print_fail(msg):
    print(f"\033[91m[FAIL] {msg}\033[0m")

def run_test():
    print("--------------------------------------------------")
    print("  MANUAL QA - FINAL SYSTEM VERIFICATION")
    print("--------------------------------------------------")

    # 1. Health Check
    try:
        r = requests.get(f"{BASE_URL}/health")
        if r.status_code == 200:
            print_pass("Server is reachable")
        else:
            print_fail(f"Server returned {r.status_code}")
            sys.exit(1)
    except Exception as e:
        print_fail(f"Connection failed: {e}")
        sys.exit(1)

    # 2. Upload Dummy Resume
    print("\n[TEST] Uploading Dummy PDF Resume...")
    dummy_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n5 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 712 Td\n(Hello World. Python Developer with 5 years exp.) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000117 00000 n\n0000000216 00000 n\n0000000303 00000 n\ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n397\n%%EOF"
    
    # We need a user token for this
    # Login first
    login_data = {"username": "testuser@example.com", "password": "SecurePass123!"}
    # Register if needed
    reg_res = requests.post(f"{BASE_URL}/api/v1/auth/register", json={"email": "testuser@example.com", "password": "SecurePass123!", "full_name": "Test User"})
    if reg_res.status_code not in [200, 201, 400]: 
         print_fail(f"Registration unexpected status: {reg_res.status_code}")
    
    # Login
    auth_res = requests.post(f"{BASE_URL}/api/v1/auth/login", data=login_data)
    if auth_res.status_code != 200:
         print_fail(f"Login failed: {auth_res.text}")
         sys.exit(1)
         
    token = auth_res.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    files = {'file': ('test_resume.pdf', dummy_pdf_content, 'application/pdf')}
    data = {'title': 'QA Test Resume'}
    
    r_upload = requests.post(f"{BASE_URL}/api/v1/resumes/upload", files=files, data=data, headers=headers)
    
    if r_upload.status_code in [200, 201]:
        resume_id = r_upload.json()['id']
        print_pass(f"Upload Successful (ID: {resume_id})")
    else:
        print_fail(f"Upload Failed: {r_upload.text}")
        sys.exit(1)

    # 3. Analyze Resume against a "Job"
    print("\n[TEST] Functionality - Job Analysis...")
    job_payload = {
        "resume_id": resume_id,
        "job_description": "We need a Python Developer with 5 years of experience."
    }
    r_analyze = requests.post(f"{BASE_URL}/api/v1/jobs/analyze", json=job_payload, headers=headers)
    
    if r_analyze.status_code == 200:
        res = r_analyze.json()
        print_pass("Analysis Request Successful")
        print(f"      Matched Keywords: {res.get('matched_keywords')}")
        print(f"      ATS Score: {res.get('ats_score')}")
    else:
        print_fail(f"Analysis Failed: {r_analyze.text}")
        sys.exit(1)

    # 4. Generate DOCX (Standard ATS)
    print("\n[TEST] Export - Standard ATS...")
    export_payload = {"resume_id": resume_id, "template": "standard_ats", "format": "docx"}
    r_export1 = requests.post(f"{BASE_URL}/api/v1/export/docx", json=export_payload, headers=headers)
    
    if r_export1.status_code == 200:
        print_pass(f"Export Standard ATS Successful ({len(r_export1.content)} bytes)")
    else:
        print_fail(f"Export Standard ATS Failed: {r_export1.text}")
        sys.exit(1)

    # 5. Generate DOCX (Modern ATS)
    print("\n[TEST] Export - Modern ATS...")
    export_payload["template"] = "modern_ats"
    r_export2 = requests.post(f"{BASE_URL}/api/v1/export/docx", json=export_payload, headers=headers)
    
    if r_export2.status_code == 200:
        print_pass(f"Export Modern ATS Successful ({len(r_export2.content)} bytes)")
    else:
        print_fail(f"Export Modern ATS Failed: {r_export2.text}")
        sys.exit(1)

    print("\n--------------------------------------------------")
    print("  QA VERIFICATION COMPLETE: ALL SYSTEMS GO")
    print("--------------------------------------------------")

if __name__ == "__main__":
    run_test()
