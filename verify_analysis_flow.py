
import requests
import time
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_full_flow():
    """
    Test Upload -> Analyze flow.
    """
    print(f"Testing Full Flow at {BASE_URL}")
    
    # 1. Upload
    print("\n--- 1. UPLOAD ---")
    with open("temp_resume.txt", "w") as f:
        f.write("John Doe\nSoftware Engineer\nExperience: Google 2020-2024\nEducation: MIT 2016-2020")
    
    resume_id = None
    try:
        files = {'file': ('temp_resume.txt', open("temp_resume.txt", 'rb'), 'text/plain')}
        resp = requests.post(f"{BASE_URL}/resumes/upload", files=files, timeout=60)
        if resp.status_code == 201:
            data = resp.json()
            resume_id = data['id']
            print(f"SUCCESS: Uploaded ID {resume_id}")
        else:
            print(f"FAILURE: {resp.status_code} - {resp.text}")
            return
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return

    # 2. Analyze
    print("\n--- 2. ANALYZE ---")
    payload = {
        "resume_id": resume_id,
        "job_description": "We need a Software Engineer with Google experience and MIT degree."
    }
    
    try:
        # Test Standard Analyze
        t0 = time.time()
        resp = requests.post(f"{BASE_URL}/jobs/analyze", json=payload, timeout=120)
        dur = time.time() - t0
        if resp.status_code == 200:
            print(f"SUCCESS: Analysis completed in {dur:.2f}s")
            print(f"Result: {resp.text[:200]}...")
        else:
            print(f"FAILURE: {resp.status_code} - {resp.text}")

    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_full_flow()
