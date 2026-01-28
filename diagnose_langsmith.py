import asyncio
import os
import httpx
from dotenv import load_dotenv
from pprint import pprint

load_dotenv()

async def diagnose_langsmith():
    api_key = os.getenv("LANGCHAIN_API_KEY")
    base_url = "https://api.smith.langchain.com/api/v1"
    headers = {"X-API-Key": api_key}
    
    async with httpx.AsyncClient() as client:
        # First get session ID
        session_id = None
        try:
            response = await client.get(f"{base_url}/sessions", headers=headers, params={"limit": 1})
            if response.status_code == 200:
                sessions = response.json()
                if sessions:
                    session_id = sessions[0]["id"]
                    print(f"Found Session ID: {session_id}")
        except Exception as e:
            print(f"Error getting sessions: {e}")

        variants = [
            f"{base_url}/sessions",
        ]
        if session_id:
            variants.append(f"{base_url}/sessions/{session_id}/runs")
            variants.append(f"{base_url}/runs?session_id={session_id}")
        
        for url in variants:
            print(f"\n--- Testing {url} ---")
            try:
                # Try GET
                response = await client.get(url, headers=headers, params={"limit": 1})
                print(f"GET Status: {response.status_code}")
                
                # If runs, try POST
                if "runs" in url:
                    query_url = f"{base_url}/runs/query"
                    print(f"--- Testing POST {query_url} ---")
                    body = {"limit": 1}
                    if session_id:
                        body["session"] = [session_id]
                    
                    response = await client.post(query_url, headers=headers, json=body)
                    print(f"POST Status: {response.status_code}")
                    if response.status_code == 200:
                        print("Success!")
                        runs_data = response.json()
                        runs = runs_data.get("runs", [])
                        if runs:
                            run_id = runs[0]["id"]
                            print(f"Testing GET Details for Run: {run_id}")
                            detail_url = f"{base_url}/runs/{run_id}"
                            detail_resp = await client.get(detail_url, headers=headers)
                            print(f"Detail GET Status: {detail_resp.status_code}")
                            if detail_resp.status_code == 200:
                                print("Detail Success!")
                            else:
                                print(f"Detail Error: {detail_resp.text}")
                    else:
                        print(f"POST Error: {response.text}")
            except Exception as e:
                print(f"Exception for {url}: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose_langsmith())
