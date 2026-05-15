#!/usr/bin/env python3
"""Escrow manager for agent-escrow plugin.

Creates, tracks, and manages escrow contracts.
Stores escrow state as JSON files in a local data directory.

Usage:
    python3 escrow_manager.py create --amount 200 --token USDC --description "Logo design" --deadline 7 --verify-type github --verify-target "github.com/user/repo"
    python3 escrow_manager.py create-milestones --total 1000 --milestones '[...]'
    python3 escrow_manager.py create-micro --budget 10 --per-call 0.01 --provider "https://api.example.com"
    python3 escrow_manager.py get --escrow-id ESC-2026-0001
    python3 escrow_manager.py update --escrow-id ESC-2026-0001 --status completed --tx-hash 0x...
    python3 escrow_manager.py list
    python3 escrow_manager.py usage --escrow-id ESC-2026-0001

Output: JSON escrow record.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
ESCROW_FILE = os.path.join(DATA_DIR, "escrows.json")

MAX_ESCROW_AMOUNT = 5000
DISPUTE_WINDOW_HOURS = 48

VALID_STATUSES = [
    "created", "funded", "in_progress", "delivered",
    "verified", "disputed", "completed", "refunded", "expired",
]

VALID_VERIFY_TYPES = ["github", "ipfs", "url", "api", "manual"]


def load_escrows():
    """Load escrow database from JSON file."""
    if not os.path.exists(ESCROW_FILE):
        return {"escrows": [], "next_id": 1}
    with open(ESCROW_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_escrows(db):
    """Save escrow database to JSON file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(ESCROW_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)


def generate_id(db):
    """Generate next escrow ID."""
    now = datetime.now(timezone.utc)
    eid = f"ESC-{now.year}-{db['next_id']:04d}"
    db["next_id"] += 1
    return eid


def create_escrow(args):
    """Create a single escrow contract."""
    amount = float(args.amount)
    if amount <= 0:
        return {"error": "Amount must be positive"}
    if amount > MAX_ESCROW_AMOUNT:
        return {"error": f"Amount ${amount} exceeds max ${MAX_ESCROW_AMOUNT}. Use --force to override."}

    if args.verify_type not in VALID_VERIFY_TYPES:
        return {"error": f"Invalid verify type '{args.verify_type}'. Must be one of: {VALID_VERIFY_TYPES}"}

    db = load_escrows()
    escrow_id = generate_id(db)
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(days=int(args.deadline))

    escrow = {
        "id": escrow_id,
        "type": "standard",
        "status": "created",
        "amount": amount,
        "token": args.token.upper(),
        "description": args.description,
        "created_at": now.isoformat(),
        "deadline": deadline.isoformat(),
        "deadline_days": int(args.deadline),
        "verify_type": args.verify_type,
        "verify_target": args.verify_target or "",
        "dispute_window_hours": DISPUTE_WINDOW_HOURS,
        "auto_release_on_timeout": True,
        "verification_score": None,
        "deliverable": None,
        "tx_hash_deposit": None,
        "tx_hash_release": None,
        "client_address": None,
        "provider_address": None,
        "dispute": None,
    }

    db["escrows"].append(escrow)
    save_escrows(db)

    return {
        "action": "escrow_created",
        "escrow": escrow,
        "message": f"Escrow {escrow_id} created: {amount} {args.token.upper()} for '{args.description}'. Deadline: {deadline.strftime('%Y-%m-%d')}. Verify: {args.verify_type}.",
    }


def create_milestones(args):
    """Create a multi-milestone escrow."""
    total = float(args.total)
    milestones = json.loads(args.milestones)

    milestone_sum = sum(float(m.get("amount", 0)) for m in milestones)
    if abs(milestone_sum - total) > 0.01:
        return {"error": f"Milestone amounts ({milestone_sum}) don't match total ({total})"}

    db = load_escrows()
    parent_id = generate_id(db)
    now = datetime.now(timezone.utc)

    milestone_records = []
    for i, m in enumerate(milestones):
        m_id = f"{parent_id}-M{i+1}"
        deadline = now + timedelta(days=int(m.get("deadline_days", 7)))
        record = {
            "id": m_id,
            "parent_id": parent_id,
            "milestone_index": i + 1,
            "name": m.get("name", f"Milestone {i+1}"),
            "amount": float(m["amount"]),
            "status": "pending" if i > 0 else "created",
            "verify_type": m.get("verify_type", "manual"),
            "target": m.get("target", ""),
            "deadline": deadline.isoformat(),
            "verification_score": None,
        }
        milestone_records.append(record)

    escrow = {
        "id": parent_id,
        "type": "milestone",
        "status": "created",
        "amount": total,
        "token": args.token.upper() if hasattr(args, "token") and args.token else "USDC",
        "description": f"Multi-milestone project ({len(milestones)} phases)",
        "created_at": now.isoformat(),
        "milestones": milestone_records,
        "current_milestone": 1,
        "completed_milestones": 0,
        "released_amount": 0,
    }

    db["escrows"].append(escrow)
    save_escrows(db)

    return {
        "action": "milestone_escrow_created",
        "escrow": escrow,
        "message": f"Milestone escrow {parent_id} created: {total} USDC across {len(milestones)} phases.",
    }


def create_micro(args):
    """Create a micro-payment (x402) escrow."""
    budget = float(args.budget)
    per_call = float(args.per_call)
    max_calls = int(budget / per_call)

    db = load_escrows()
    escrow_id = generate_id(db)
    now = datetime.now(timezone.utc)

    escrow = {
        "id": escrow_id,
        "type": "micro",
        "status": "created",
        "budget": budget,
        "per_call": per_call,
        "max_calls": max_calls,
        "calls_made": 0,
        "amount_spent": 0.0,
        "amount_remaining": budget,
        "provider_url": args.provider,
        "token": "USDC",
        "created_at": now.isoformat(),
    }

    db["escrows"].append(escrow)
    save_escrows(db)

    return {
        "action": "micro_escrow_created",
        "escrow": escrow,
        "message": f"Micro-escrow {escrow_id}: {budget} USDC budget, {per_call} per call, max {max_calls} calls to {args.provider}.",
    }


def get_escrow(args):
    """Get escrow details by ID."""
    db = load_escrows()
    for e in db["escrows"]:
        if e["id"] == args.escrow_id:
            return {"escrow": e}
    return {"error": f"Escrow {args.escrow_id} not found"}


def update_escrow(args):
    """Update escrow status."""
    db = load_escrows()
    for e in db["escrows"]:
        if e["id"] == args.escrow_id:
            if args.status and args.status in VALID_STATUSES:
                e["status"] = args.status
            if args.tx_hash:
                if e.get("status") == "completed":
                    e["tx_hash_release"] = args.tx_hash
                else:
                    e["tx_hash_deposit"] = args.tx_hash
            if args.deliverable:
                e["deliverable"] = args.deliverable
                e["status"] = "delivered"
            save_escrows(db)
            return {"action": "escrow_updated", "escrow": e}
    return {"error": f"Escrow {args.escrow_id} not found"}


def list_escrows(args):
    """List all escrows."""
    db = load_escrows()
    status_filter = args.status if hasattr(args, "status") and args.status else None
    escrows = db["escrows"]
    if status_filter:
        escrows = [e for e in escrows if e.get("status") == status_filter]
    summary = []
    for e in escrows:
        summary.append({
            "id": e["id"],
            "type": e.get("type", "standard"),
            "status": e.get("status"),
            "amount": e.get("amount", e.get("budget")),
            "description": e.get("description", e.get("provider_url", "")),
        })
    return {"escrows": summary, "count": len(summary)}


def usage_report(args):
    """Get micro-escrow usage report."""
    db = load_escrows()
    for e in db["escrows"]:
        if e["id"] == args.escrow_id:
            if e.get("type") != "micro":
                return {"error": f"Escrow {args.escrow_id} is not a micro-escrow"}
            pct_used = (e["calls_made"] / e["max_calls"] * 100) if e["max_calls"] > 0 else 0
            alert = None
            if pct_used >= 80:
                alert = f"WARNING: Budget {pct_used:.0f}% used. {e['amount_remaining']:.2f} USDC remaining."
            return {
                "escrow_id": e["id"],
                "calls_made": e["calls_made"],
                "max_calls": e["max_calls"],
                "amount_spent": round(e["amount_spent"], 4),
                "amount_remaining": round(e["amount_remaining"], 4),
                "percent_used": round(pct_used, 1),
                "alert": alert,
            }
    return {"error": f"Escrow {args.escrow_id} not found"}


def main():
    parser = argparse.ArgumentParser(description="Manage escrow contracts")
    sub = parser.add_subparsers(dest="command", required=True)

    # create
    p_create = sub.add_parser("create", help="Create standard escrow")
    p_create.add_argument("--amount", required=True, help="Amount in token units")
    p_create.add_argument("--token", default="USDC", help="Token symbol")
    p_create.add_argument("--description", required=True, help="Job description")
    p_create.add_argument("--deadline", default="7", help="Deadline in days")
    p_create.add_argument("--verify-type", default="manual", help="Verification type")
    p_create.add_argument("--verify-target", default="", help="Verification target")

    # create-milestones
    p_mile = sub.add_parser("create-milestones", help="Create milestone escrow")
    p_mile.add_argument("--total", required=True, help="Total amount")
    p_mile.add_argument("--milestones", required=True, help="JSON array of milestones")
    p_mile.add_argument("--token", default="USDC", help="Token symbol")

    # create-micro
    p_micro = sub.add_parser("create-micro", help="Create x402 micro-escrow")
    p_micro.add_argument("--budget", required=True, help="Total budget")
    p_micro.add_argument("--per-call", required=True, help="Cost per API call")
    p_micro.add_argument("--provider", required=True, help="Provider URL")

    # get
    p_get = sub.add_parser("get", help="Get escrow by ID")
    p_get.add_argument("--escrow-id", required=True, help="Escrow ID")

    # update
    p_update = sub.add_parser("update", help="Update escrow")
    p_update.add_argument("--escrow-id", required=True, help="Escrow ID")
    p_update.add_argument("--status", default=None, help="New status")
    p_update.add_argument("--tx-hash", default=None, help="Transaction hash")
    p_update.add_argument("--deliverable", default=None, help="Deliverable link")

    # list
    p_list = sub.add_parser("list", help="List escrows")
    p_list.add_argument("--status", default=None, help="Filter by status")

    # usage
    p_usage = sub.add_parser("usage", help="Micro-escrow usage report")
    p_usage.add_argument("--escrow-id", required=True, help="Escrow ID")

    args = parser.parse_args()

    commands = {
        "create": create_escrow,
        "create-milestones": create_milestones,
        "create-micro": create_micro,
        "get": get_escrow,
        "update": update_escrow,
        "list": list_escrows,
        "usage": usage_report,
    }

    result = commands[args.command](args)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
