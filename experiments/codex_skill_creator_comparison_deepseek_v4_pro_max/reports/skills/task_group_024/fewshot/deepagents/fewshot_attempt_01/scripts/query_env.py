#!/usr/bin/env python3
"""Query the task environment API.

Reads TASK_ENV_BASE_URL from the environment (default: http://task-env:9024).
Fetches from the endpoints listed in environment_access.md and prints
pretty-printed JSON to stdout.

Usage:
  python query_env.py work-items          # GET /api/work-items
  python query_env.py work-item WI-...    # GET /api/work-items/{id}
  python query_env.py mix-targets         # GET /api/mix-targets
  python query_env.py sla-policy          # GET /api/sla-policy
  python query_env.py releases            # GET /api/releases
  python query_env.py release REL-...     # GET /api/releases/{id}
  python query_env.py milestones          # GET /api/milestones
  python query_env.py dependencies        # GET /api/dependencies
  python query_env.py blockers            # GET /api/blockers
  python query_env.py query "SQL..."      # POST /api/query (may require token)
"""

import json
import os
import sys
import urllib.request

BASE_URL = os.environ.get("TASK_ENV_BASE_URL", "http://task-env:9024")
API = f"{BASE_URL}/api"

ENDPOINTS = {
    "work-items": "/work-items",
    "work-item": "/work-items",
    "mix-targets": "/mix-targets",
    "sla-policy": "/sla-policy",
    "releases": "/releases",
    "release": "/releases",
    "milestones": "/milestones",
    "dependencies": "/dependencies",
    "blockers": "/blockers",
    "query": "/query",
}


def get_json(path):
    url = f"{API}{path}"
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read())


def post_json(path, body):
    url = f"{API}{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "work-item":
        item_id = sys.argv[2]
        result = get_json(f"/work-items/{item_id}")
    elif cmd == "release":
        release_id = sys.argv[2]
        result = get_json(f"/releases/{release_id}")
    elif cmd == "query":
        sql = sys.argv[2]
        result = post_json("/query", {"query": sql})
    elif cmd in ENDPOINTS:
        result = get_json(ENDPOINTS[cmd])
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

