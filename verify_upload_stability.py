
import os
import requests
import time

URL = "http://127.0.0.1:8000/api/v1/resumes/upload"

def test_upload_stability():
    """
    Test upload endpoint stability by hitting it.
    """
    print(f"Testing Upload Stability at {URL}")
    
    # Create a dummy resume file
    with open("temp_resume.txt", "w") as f:
        f.write("John Doe\nSoftware Engineer\nExperience: Google 2020-2024\nEducation: MIT 2016-2020")
    
    try:
        t0 = time.time()
        files = {'file': ('temp_resume.txt', open("temp_resume.txt", 'rb'), 'text/plain')}
        
        print("Sending request...")
        resp = requests.post(URL, files=files, timeout=60)
        
        print(f"Status: {resp.status_code}")
        if resp.status_code == 201:
            print("SUCCESS: Upload completed.")
            print(f"Response: {resp.text[:100]}...")
        else:
            print(f"FAILURE: {resp.status_code}")
            print(f"Error: {resp.text}")
            
        print(f"Duration: {time.time() - t0:.2f}s")
        
    except Exception as e:
        print(f"EXCEPTION: {e}")
    finally:
        if os.path.exists("temp_resume.txt"):
            os.remove("temp_resume.txt")

if __name__ == "__main__":
    test_upload_stability()
