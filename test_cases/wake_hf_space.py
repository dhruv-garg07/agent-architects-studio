import requests, time, json

HF_URL = "https://iotacluster-embedding-model.hf.space/api/predict"

# Wake up the HF space by polling
for i in range(20):
    try:
        r = requests.post(HF_URL, json={"data": ["hello world"]}, timeout=15, stream=True)
        ct = r.headers.get("content-type", "")
        print(f"Attempt {i+1}: Status {r.status_code}, Content-Type: {ct}")
        if r.status_code == 200:
            for line in r.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode())
                        if "dense_embedding" in data:
                            dim = len(data["dense_embedding"])
                            print(f"SUCCESS - Got embedding with {dim} dimensions")
                            exit(0)
                    except json.JSONDecodeError:
                        pass
            print("Got 200 but no embedding yet...")
        else:
            print(f"Space not ready yet (status {r.status_code})...")
    except Exception as e:
        print(f"Attempt {i+1}: Error - {e}")
    time.sleep(5)

print("Failed to wake up HF space after 20 attempts")
exit(1)
