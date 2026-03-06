"""Quick smoke-test for the Tiantian fundgz API."""
import json
import re
import urllib3
import requests

urllib3.disable_warnings()

CODES = ["000001", "110011", "161725"]

for code in CODES:
    url = f"https://fundgz.1234567.com.cn/js/{code}.js"
    headers = {
        "Referer": "https://fund.eastmoney.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=8, verify=False)
        resp.raise_for_status()
        raw = resp.text.strip()
        m = re.match(r"jsonpgz\((.*)\)", raw)
        d = json.loads(m.group(1)) if m else {}
        print(
            f"{code} | {d.get('name','?'):20s} "
            f"nav={d.get('dwjz')}  gsz={d.get('gsz')}  "
            f"gszzl={d.get('gszzl')}%  time={d.get('gztime')}"
        )
    except Exception as e:
        print(f"{code} ERROR: {e}")

