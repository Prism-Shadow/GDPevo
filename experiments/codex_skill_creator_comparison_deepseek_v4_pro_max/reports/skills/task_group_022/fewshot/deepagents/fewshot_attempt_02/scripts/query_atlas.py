#!/usr/bin/env python3
"""Query or transact against the Atlas Commerce Operations API.

Usage:
  python query_atlas.py --base URL --token TOKEN --sql SQL [--endpoint NAME]

Endpoints:
  sql               POST /api/sql         (default, read-only)
  sql-transaction   POST /api/sql/transaction
  schema            GET /api/schema
  data-dictionary   GET /api/data-dictionary
  correction-audit  GET /api/correction-audit

Output: prints the JSON response body to stdout.
Exit code: 0 on success, non-zero on HTTP or application error.
"""

import json, sys, urllib.request, urllib.error

def call_atlas(base_url, token, endpoint, sql=None):
    url = base_url.rstrip('/') + '/api/' + endpoint
    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json',
    }
    method = 'POST' if endpoint.startswith('sql') else 'GET'

    body = None
    if sql is not None:
        body = json.dumps({'sql': sql}).encode('utf-8')

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='replace')
        print(f'HTTP {e.code}: {error_body}', file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f'Connection error: {e.reason}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Atlas Commerce Operations API client')
    parser.add_argument('--base', required=True, help='Base URL')
    parser.add_argument('--token', required=True, help='Bearer token')
    parser.add_argument('--sql', default=None, help='SQL statement for sql/transaction')
    parser.add_argument('--endpoint', default='sql',
                        choices=['sql','sql-transaction','schema','data-dictionary','correction-audit'])
    args = parser.parse_args()
    endpoint = 'sql/transaction' if args.endpoint == 'sql-transaction' else args.endpoint
    result = call_atlas(args.base, args.token, endpoint, args.sql)
    print(json.dumps(result, indent=2))
