import os
import httpx
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import statistics

load_dotenv()

class LangSmithService:
    def __init__(self):
        self.api_key = os.getenv("LANGCHAIN_API_KEY")
        self.base_url = "https://api.smith.langchain.com/api/v1"
        self.headers = {
            "X-API-Key": self.api_key
        }

    async def _get_session_id(self, project_name: str) -> Optional[str]:
        """Fetch session ID for a given project name."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/sessions", headers=self.headers)
            if response.status_code == 200:
                sessions = response.json()
                for s in sessions:
                    if s.get("name") == project_name:
                        return s.get("id")
        return None

    def _parse_iso(self, iso_str: Optional[str]):
        if not iso_str:
            return None
        try:
            # LangSmith can return more than 6 decimal places for microseconds
            # Example: 2026-01-28T04:56:31.121126789Z
            # Python's fromisoformat only supports up to 6 digits.
            
            s = iso_str.replace("Z", "+00:00")
            if "." in s:
                base, remain = s.split(".")
                # remain could be '121126789+00:00'
                if "+" in remain:
                    ms_part, offset = remain.split("+")
                    ms_part = ms_part[:6] # Truncate to 6 digits
                    s = f"{base}.{ms_part}+{offset}"
                else:
                    s = f"{base}.{remain[:6]}"
            
            return datetime.fromisoformat(s)
        except Exception as e:
            print(f"Error parsing date {iso_str}: {e}")
            return None

    async def get_runs(self, limit: int = 20, offset: int = 0, project_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch runs from LangSmith REST API."""
        if not project_name:
            project_name = os.getenv("LANGCHAIN_PROJECT", "default")

        session_id = await self._get_session_id(project_name)
        if not session_id:
            return []

        body = {
            "session": [session_id],
            "limit": limit,
            "offset": offset,
            "order": "desc"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/runs/query", headers=self.headers, json=body)
            response.raise_for_status()
            data = response.json()
            runs = data.get("runs", [])
            
            # Calculate latency for each run
            for r in runs:
                start = self._parse_iso(r.get("start_time"))
                end = self._parse_iso(r.get("end_time"))
                if start and end:
                    r["latency"] = (end - start).total_seconds()
                else:
                    r["latency"] = 0
            
            return runs

    async def get_run_details(self, run_id: str) -> Dict[str, Any]:
        """Fetch details for a specific run, including its children."""
        async with httpx.AsyncClient() as client:
            # Get the run details (GET works for individual runs)
            run_response = await client.get(f"{self.base_url}/runs/{run_id}", headers=self.headers)
            run_response.raise_for_status()
            run_data = run_response.json()
            
            # Calculate latency for main run
            start = self._parse_iso(run_data.get("start_time"))
            end = self._parse_iso(run_data.get("end_time"))
            if start and end:
                run_data["latency"] = (end - start).total_seconds()
            else:
                run_data["latency"] = 0

            # Get child runs if any (Using POST /query for children)
            children_body = {
                "parent_run": [run_id],
                "limit": 100
            }
            try:
                children_response = await client.post(f"{self.base_url}/runs/query", headers=self.headers, json=children_body)
                if children_response.status_code == 200:
                    children = children_response.json().get("runs", [])
                    for c in children:
                        c_start = self._parse_iso(c.get("start_time"))
                        c_end = self._parse_iso(c.get("end_time"))
                        if c_start and c_end:
                            c["latency"] = (c_end - c_start).total_seconds()
                        else:
                            c["latency"] = 0
                    run_data["children"] = children
                else:
                    run_data["children"] = []
            except:
                run_data["children"] = []

            return run_data

    async def get_stats(self, project_name: Optional[str] = None) -> Dict[str, Any]:
        """Compute statistics from recent runs."""
        if not project_name:
            project_name = os.getenv("LANGCHAIN_PROJECT", "default")

        session_id = await self._get_session_id(project_name)
        if not session_id:
            return {
                "total_traces": 0, "error_rate": 0, "avg_latency": 0,
                "p50": 0, "p95": 0, "p99": 0
            }

        # Fetch last 100 runs to compute stats
        body = {
            "session": [session_id],
            "limit": 100
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/runs/query", headers=self.headers, json=body)
            response.raise_for_status()
            data = response.json()
            runs = data.get("runs", [])

        if not runs:
            return {
                "total_traces": 0, "error_rate": 0, "avg_latency": 0,
                "p50": 0, "p95": 0, "p99": 0
            }

        total_traces = len(runs)
        errors = [r for r in runs if r.get("status") == "error"]
        error_rate = (len(errors) / total_traces) * 100

        # Latencies in seconds
        latencies = []
        for r in runs:
            start = self._parse_iso(r.get("start_time"))
            end = self._parse_iso(r.get("end_time"))
            if start and end:
                latency_sec = (end - start).total_seconds()
                latencies.append(latency_sec)
        
        if not latencies:
            return {
                "total_traces": total_traces,
                "error_rate": round(error_rate, 2),
                "avg_latency": 0, "p50": 0, "p95": 0, "p99": 0
            }

        avg_latency = sum(latencies) / len(latencies)
        latencies.sort()
        
        def get_percentile(sorted_list, percentile):
            if not sorted_list: return 0
            index = int(len(sorted_list) * (percentile / 100))
            return sorted_list[min(index, len(sorted_list) - 1)]

        return {
            "total_traces": total_traces,
            "error_rate": round(error_rate, 2),
            "avg_latency": round(avg_latency, 2),
            "p50": round(get_percentile(latencies, 50), 2),
            "p95": round(get_percentile(latencies, 95), 2),
            "p99": round(get_percentile(latencies, 99), 2)
        }


