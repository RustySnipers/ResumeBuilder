
import requests
import time
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_optimization_flow():
    """
    Test Upload -> Optimize -> Export flow.
    """
    print(f"Testing Optimization Flow at {BASE_URL}")
    
    # 1. Upload
    print("\n--- 1. UPLOAD ---")
    with open("temp_resume.txt", "w") as f:
        f.write("John Smith\nCustomer Service\nExperience: Retail 2018-2020\nEducation: High School")
    
    resume_id = None
    try:
        files = {'file': ('temp_resume.txt', open("temp_resume.txt", 'rb'), 'text/plain')}
        resp = requests.post(f"{BASE_URL}/resumes/upload", files=files, timeout=60)
        if resp.status_code == 201:
            data = resp.json()
            resume_id = data['id']
            print(f"SUCCESS: Uploaded ID {resume_id}")
        else:
            print(f"FAILURE UPLOAD: {resp.status_code} - {resp.text}")
            return
    except Exception as e:
        print(f"EXCEPTION UPLOAD: {e}")
        return

    # 2. Optimize
    print("\n--- 2. OPTIMIZE ---")
    payload = {
        "resume_id": resume_id,
        "job_description": "We need a Senior Customer Success Manager with 5+ years experience, leadership skills, and Salesforce knowledge."
    }
    
    new_resume_id = None
    try:
        t0 = time.time()
        print("Optimizing (this uses LLM, wait ~30-60s)...")
        resp = requests.post(f"{BASE_URL}/jobs/optimize", json=payload, timeout=300)
        dur = time.time() - t0
        if resp.status_code == 200:
            data = resp.json()
            new_resume_id = data['new_resume_id']
            print(f"SUCCESS: Optimization completed in {dur:.2f}s")
            print(f"New Resume ID: {new_resume_id}")
            print(f"Message: {data['message']}")
        else:
            print(f"FAILURE OPTIMIZE: {resp.status_code} - {resp.text}")
            return

    except Exception as e:
        print(f"EXCEPTION OPTIMIZE: {e}")
        return

    # 3. Verify Export of NEW Resume
    print("\n--- 3. EXPORT NEW RESUME ---")
    try:
        # Try markdown export
        exp_payload = {"resume_id": new_resume_id, "template": "standard_ats", "format": "markdown"}
        resp = requests.post(f"{BASE_URL}/export/markdown", json=exp_payload, timeout=30)
        if resp.status_code == 200:
            print("SUCCESS: Exported Optimized Resume (Markdown)")
            print(f"Content Preview: {resp.text[:100]}...")
        else:
            print(f"FAILURE EXPORT: {resp.status_code} - {resp.text}")

        # 4. Verify Improved ATS Score
        print("\n--- 4. ANALYZE NEW RESUME ---")
        an_payload = {"resume_id": new_resume_id, "job_description": payload["job_description"]}
        resp = requests.post(f"{BASE_URL}/jobs/analyze", json=an_payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            score = data['ats_score']
            print(f"SUCCESS: Analysis Complete. New ATS Score: {score}")
            if score > 70:
                print("PASS: Score is high!")
            else:
                print(f"WARN: Score is still low ({score})")
        else:
            print(f"FAILURE ANALYSIS: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        print(f"EXCEPTION EXPORT: {e}")

if __name__ == "__main__":
    test_optimization_flow()
