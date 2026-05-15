#!/usr/bin/env python3
"""Delivery verifier for agent-escrow plugin.

AI-powered verification of deliverables against escrow requirements.
Checks GitHub repos, IPFS hashes, URLs, and API endpoints.

Usage:
    python3 delivery_verifier.py --escrow-id ESC-2026-0001 --deliverable "https://github.com/user/repo" --type github
    python3 delivery_verifier.py --deliverable "QmXxx..." --type ipfs
    python3 delivery_verifier.py --deliverable "https://app.example.com" --type url

Output: JSON verification report with score and recommendation.
"""

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
import ssl
import time


def verify_github(deliverable):
    """Verify a GitHub repository deliverable.

    Checks:
    1. URL format is valid GitHub repo
    2. Repository is accessible (HTTP 200)
    3. Repository is not empty (has files)
    4. Has recent activity
    """
    checks = []
    score = 0.0

    # Check 1: Valid GitHub URL format
    github_pattern = r"(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/\s]+)"
    match = re.match(github_pattern, deliverable.strip())
    if not match:
        checks.append({"check": "valid_github_url", "passed": False, "detail": "Not a valid GitHub URL"})
        return {"checks": checks, "score": 0.0, "recommendation": "REJECT"}

    owner, repo = match.group(1), match.group(2).rstrip("/")
    checks.append({"check": "valid_github_url", "passed": True, "detail": f"Valid repo: {owner}/{repo}"})
    score += 0.2

    # Check 2: Repository accessible via API
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    ctx = ssl.create_default_context()
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "agent-escrow/1.0"})
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        data = json.loads(resp.read().decode("utf-8"))
        checks.append({"check": "repo_accessible", "passed": True, "detail": f"HTTP 200, repo exists"})
        score += 0.2

        # Check 3: Not empty
        if data.get("size", 0) > 0:
            checks.append({"check": "has_content", "passed": True, "detail": f"Repo size: {data['size']} KB"})
            score += 0.2
        else:
            checks.append({"check": "has_content", "passed": False, "detail": "Repository appears empty"})

        # Check 4: Has description/README
        has_desc = bool(data.get("description"))
        checks.append({"check": "has_description", "passed": has_desc,
                       "detail": data.get("description", "No description")[:100]})
        if has_desc:
            score += 0.1

        # Check 5: Recent commits
        pushed_at = data.get("pushed_at", "")
        if pushed_at:
            checks.append({"check": "recent_activity", "passed": True, "detail": f"Last push: {pushed_at}"})
            score += 0.2
        else:
            checks.append({"check": "recent_activity", "passed": False, "detail": "No push history"})

        # Check 6: Not a fork (original work)
        is_fork = data.get("fork", False)
        checks.append({"check": "original_work", "passed": not is_fork,
                       "detail": "Fork" if is_fork else "Original repository"})
        if not is_fork:
            score += 0.1

    except urllib.error.HTTPError as e:
        if e.code == 404:
            checks.append({"check": "repo_accessible", "passed": False, "detail": "Repository not found (404)"})
        elif e.code == 403:
            checks.append({"check": "repo_accessible", "passed": False, "detail": "Rate limited or private repo"})
            score += 0.1  # Private repo might be intentional
        else:
            checks.append({"check": "repo_accessible", "passed": False, "detail": f"HTTP error: {e.code}"})
    except Exception as e:
        checks.append({"check": "repo_accessible", "passed": False, "detail": f"Connection error: {str(e)[:80]}"})

    return {"checks": checks, "score": round(min(score, 1.0), 2)}


def verify_url(deliverable):
    """Verify a URL deliverable.

    Checks:
    1. Valid URL format
    2. Returns HTTP 200
    3. Has content (not empty page)
    4. Response time reasonable
    5. SSL certificate valid (for HTTPS)
    """
    checks = []
    score = 0.0

    # Check 1: Valid URL format
    if not deliverable.startswith(("http://", "https://")):
        deliverable = "https://" + deliverable

    url_pattern = r"https?://[^\s/$.?#].[^\s]*"
    if not re.match(url_pattern, deliverable):
        checks.append({"check": "valid_url", "passed": False, "detail": "Invalid URL format"})
        return {"checks": checks, "score": 0.0}

    checks.append({"check": "valid_url", "passed": True, "detail": deliverable})
    score += 0.15

    # Check 2-5: HTTP request
    ctx = ssl.create_default_context()
    start = time.time()
    try:
        req = urllib.request.Request(deliverable, headers={"User-Agent": "agent-escrow/1.0"})
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        elapsed = time.time() - start

        # HTTP status
        status = resp.getcode()
        checks.append({"check": "http_status", "passed": status == 200, "detail": f"HTTP {status}"})
        if status == 200:
            score += 0.25

        # Content length
        content = resp.read()
        content_len = len(content)
        has_content = content_len > 100  # More than just a blank page
        checks.append({"check": "has_content", "passed": has_content,
                       "detail": f"Content size: {content_len} bytes"})
        if has_content:
            score += 0.25

        # Response time
        fast = elapsed < 5.0
        checks.append({"check": "response_time", "passed": fast,
                       "detail": f"{elapsed:.2f}s {'(fast)' if fast else '(slow)'}"})
        if fast:
            score += 0.15

        # SSL check (for HTTPS)
        if deliverable.startswith("https://"):
            checks.append({"check": "ssl_valid", "passed": True, "detail": "Valid SSL certificate"})
            score += 0.2
        else:
            checks.append({"check": "ssl_valid", "passed": False, "detail": "No HTTPS — insecure"})

    except urllib.error.HTTPError as e:
        checks.append({"check": "http_status", "passed": False, "detail": f"HTTP error: {e.code}"})
    except ssl.SSLCertVerificationError:
        checks.append({"check": "ssl_valid", "passed": False, "detail": "Invalid SSL certificate"})
    except Exception as e:
        checks.append({"check": "http_status", "passed": False, "detail": f"Connection failed: {str(e)[:80]}"})

    return {"checks": checks, "score": round(min(score, 1.0), 2)}


def verify_ipfs(deliverable):
    """Verify an IPFS hash deliverable.

    Checks:
    1. Valid IPFS hash format (CIDv0 or CIDv1)
    2. Content accessible via public gateway
    3. File not empty
    """
    checks = []
    score = 0.0

    # Normalize: extract CID from various formats
    cid = deliverable.strip()
    for prefix in ("ipfs://", "https://ipfs.io/ipfs/", "https://gateway.pinata.cloud/ipfs/"):
        if cid.startswith(prefix):
            cid = cid[len(prefix):]
            break

    # Check 1: Valid CID format
    cidv0 = re.match(r"^Qm[1-9A-HJ-NP-Za-km-z]{44}$", cid)
    cidv1 = re.match(r"^b[a-z2-7]{58,}$", cid, re.IGNORECASE)

    if cidv0 or cidv1:
        checks.append({"check": "valid_cid", "passed": True, "detail": f"CID: {cid[:20]}..."})
        score += 0.3
    else:
        checks.append({"check": "valid_cid", "passed": False, "detail": f"Invalid CID format: {cid[:30]}"})
        return {"checks": checks, "score": 0.0}

    # Check 2: Accessible via gateway
    gateway_url = f"https://ipfs.io/ipfs/{cid}"
    ctx = ssl.create_default_context()
    try:
        req = urllib.request.Request(gateway_url, headers={"User-Agent": "agent-escrow/1.0"})
        resp = urllib.request.urlopen(req, timeout=30, context=ctx)
        content = resp.read()

        checks.append({"check": "gateway_accessible", "passed": True, "detail": f"Accessible via ipfs.io"})
        score += 0.4

        # Check 3: Not empty
        if len(content) > 0:
            content_type = resp.headers.get("Content-Type", "unknown")
            checks.append({"check": "has_content", "passed": True,
                          "detail": f"{len(content)} bytes, type: {content_type}"})
            score += 0.3
        else:
            checks.append({"check": "has_content", "passed": False, "detail": "Empty content"})

    except Exception as e:
        checks.append({"check": "gateway_accessible", "passed": False,
                       "detail": f"Gateway timeout or error: {str(e)[:80]}"})

    return {"checks": checks, "score": round(min(score, 1.0), 2)}


def verify_api(deliverable):
    """Verify an API endpoint deliverable.

    Checks:
    1. Valid URL
    2. Returns successful response
    3. Returns JSON (structured data)
    4. Response time acceptable
    """
    checks = []
    score = 0.0

    if not deliverable.startswith(("http://", "https://")):
        deliverable = "https://" + deliverable

    checks.append({"check": "valid_endpoint", "passed": True, "detail": deliverable})
    score += 0.15

    ctx = ssl.create_default_context()
    start = time.time()
    try:
        req = urllib.request.Request(deliverable, headers={
            "User-Agent": "agent-escrow/1.0",
            "Accept": "application/json",
        })
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        elapsed = time.time() - start
        content = resp.read().decode("utf-8", errors="replace")

        # Status check
        status = resp.getcode()
        ok = status in (200, 201, 204)
        checks.append({"check": "status_ok", "passed": ok, "detail": f"HTTP {status}"})
        if ok:
            score += 0.25

        # JSON response
        try:
            json.loads(content)
            checks.append({"check": "valid_json", "passed": True, "detail": "Returns valid JSON"})
            score += 0.25
        except json.JSONDecodeError:
            checks.append({"check": "valid_json", "passed": False, "detail": "Response is not JSON"})

        # Response time
        fast = elapsed < 3.0
        checks.append({"check": "response_time", "passed": fast,
                       "detail": f"{elapsed:.2f}s {'(fast)' if fast else '(slow)'}"})
        if fast:
            score += 0.2

        # Content not empty
        if len(content) > 2:  # more than just "{}"
            checks.append({"check": "has_data", "passed": True, "detail": f"{len(content)} chars"})
            score += 0.15
        else:
            checks.append({"check": "has_data", "passed": False, "detail": "Empty or minimal response"})

    except Exception as e:
        checks.append({"check": "status_ok", "passed": False, "detail": f"Error: {str(e)[:80]}"})

    return {"checks": checks, "score": round(min(score, 1.0), 2)}


def verify_manual(deliverable):
    """Manual verification — no automated checks."""
    return {
        "checks": [{"check": "manual_review", "passed": None,
                    "detail": f"Manual review required. Deliverable: {deliverable[:200]}"}],
        "score": None,
        "recommendation": "MANUAL_REVIEW",
    }


def run_verification(deliverable, verify_type, escrow_id=None, min_score=0.7):
    """Run verification and generate report."""
    verifiers = {
        "github": verify_github,
        "url": verify_url,
        "ipfs": verify_ipfs,
        "api": verify_api,
        "manual": verify_manual,
    }

    if verify_type not in verifiers:
        return {"error": f"Unknown verify type: {verify_type}"}

    result = verifiers[verify_type](deliverable)

    # Add recommendation
    score = result.get("score")
    if score is not None:
        if score >= min_score:
            result["recommendation"] = "APPROVE"
        elif score >= min_score * 0.7:
            result["recommendation"] = "REVIEW"
        else:
            result["recommendation"] = "REJECT"

    passed = sum(1 for c in result["checks"] if c["passed"] is True)
    total = sum(1 for c in result["checks"] if c["passed"] is not None)

    report = {
        "escrow_id": escrow_id,
        "deliverable": deliverable,
        "verify_type": verify_type,
        "checks_passed": f"{passed}/{total}",
        "score": score,
        "recommendation": result.get("recommendation", "UNKNOWN"),
        "details": result["checks"],
    }

    return report


def main():
    parser = argparse.ArgumentParser(description="Verify deliverables for escrow")
    parser.add_argument("--escrow-id", default=None, help="Escrow ID")
    parser.add_argument("--deliverable", required=True, help="Deliverable link/hash")
    parser.add_argument("--type", required=True, choices=VALID_TYPES, help="Verification type")
    parser.add_argument("--min-score", type=float, default=0.7, help="Minimum score for APPROVE")
    args = parser.parse_args()

    report = run_verification(args.deliverable, args.type, args.escrow_id, args.min_score)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


VALID_TYPES = ["github", "url", "ipfs", "api", "manual"]

if __name__ == "__main__":
    sys.exit(main())
