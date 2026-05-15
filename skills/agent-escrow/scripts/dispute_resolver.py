#!/usr/bin/env python3
"""Dispute resolver for agent-escrow plugin.

AI-powered dispute analysis that compares original scope vs deliverable,
evaluates evidence from both parties, and recommends a fair resolution.

Usage:
    python3 dispute_resolver.py analyze --escrow-id ESC-2026-0001 --client-reason "Missing feature X" --provider-evidence "Feature X was not in scope"
    python3 dispute_resolver.py resolve --escrow-id ESC-2026-0001 --resolution partial --split 85

Output: JSON dispute analysis with resolution recommendation.
"""

import argparse
import json
import sys

# Resolution types
RESOLUTION_FULL_RELEASE = "full_release"       # 100% to provider
RESOLUTION_FULL_REFUND = "full_refund"         # 100% to client
RESOLUTION_PARTIAL = "partial"                  # Split between both
RESOLUTION_ESCALATE = "escalate"               # Need external arbitrator


def analyze_dispute(escrow, client_reason, provider_evidence, verification_score=None):
    """Analyze dispute and recommend resolution.

    Uses heuristic scoring based on:
    1. Verification score (if available) — did the deliverable pass checks?
    2. Scope analysis — does the complaint match the original description?
    3. Evidence quality — how specific are the claims?

    Args:
        escrow: dict with escrow details (description, amount, verify_type)
        client_reason: string — client's complaint
        provider_evidence: string — provider's counter-argument
        verification_score: float 0-1 or None

    Returns:
        dict with analysis and recommendation
    """
    analysis_points = []
    provider_score = 50  # Start at 50/100 (neutral)

    # Factor 1: Verification score (strongest signal)
    if verification_score is not None:
        if verification_score >= 0.8:
            analysis_points.append({
                "factor": "Automated Verification",
                "finding": f"Deliverable passed verification with score {verification_score:.0%}",
                "impact": "Strongly favors provider",
            })
            provider_score += 25
        elif verification_score >= 0.5:
            analysis_points.append({
                "factor": "Automated Verification",
                "finding": f"Deliverable partially passed verification ({verification_score:.0%})",
                "impact": "Partially favors provider",
            })
            provider_score += 10
        else:
            analysis_points.append({
                "factor": "Automated Verification",
                "finding": f"Deliverable failed verification ({verification_score:.0%})",
                "impact": "Favors client",
            })
            provider_score -= 20

    # Factor 2: Scope analysis — check if complaint is about scope creep
    scope_keywords = ["not in scope", "extra", "additional", "wasn't asked", "beyond", "upgrade"]
    description = escrow.get("description", "").lower()
    reason_lower = client_reason.lower()
    evidence_lower = provider_evidence.lower()

    # Is client complaining about something not in the original scope?
    scope_creep = any(kw in evidence_lower for kw in scope_keywords)
    if scope_creep:
        # Check if the missing feature was actually in the description
        complaint_words = set(reason_lower.split())
        scope_words = set(description.split())
        overlap = complaint_words & scope_words

        if len(overlap) < 2:
            analysis_points.append({
                "factor": "Scope Analysis",
                "finding": "Client's complaint appears to be about features not in the original scope",
                "impact": "Favors provider — likely scope creep by client",
            })
            provider_score += 15
        else:
            analysis_points.append({
                "factor": "Scope Analysis",
                "finding": "Disputed feature has some overlap with original scope",
                "impact": "Inconclusive — needs human review",
            })

    # Factor 3: Evidence specificity
    client_specific = len(client_reason) > 50 and any(c in client_reason for c in ".,;:!?")
    provider_specific = len(provider_evidence) > 50 and any(c in provider_evidence for c in ".,;:!?")

    if provider_specific and not client_specific:
        analysis_points.append({
            "factor": "Evidence Quality",
            "finding": "Provider provided detailed evidence; client complaint is vague",
            "impact": "Slightly favors provider",
        })
        provider_score += 10
    elif client_specific and not provider_specific:
        analysis_points.append({
            "factor": "Evidence Quality",
            "finding": "Client provided detailed complaint; provider response is vague",
            "impact": "Slightly favors client",
        })
        provider_score -= 10
    else:
        analysis_points.append({
            "factor": "Evidence Quality",
            "finding": "Both parties provided comparable evidence",
            "impact": "Neutral",
        })

    # Factor 4: Delivery timing
    # If deliverable was submitted, some work was done
    if escrow.get("deliverable"):
        analysis_points.append({
            "factor": "Work Completion",
            "finding": "Provider did submit a deliverable (work was attempted)",
            "impact": "Provider should receive at least partial payment",
        })
        provider_score = max(provider_score, 30)  # At least 30% if they delivered something

    # Generate recommendation
    provider_score = max(0, min(100, provider_score))
    amount = float(escrow.get("amount", 0))

    if provider_score >= 80:
        recommendation = RESOLUTION_FULL_RELEASE
        provider_pct = 100
        rationale = "Evidence strongly supports provider. Recommend full release."
    elif provider_score >= 60:
        provider_pct = provider_score
        recommendation = RESOLUTION_PARTIAL
        rationale = f"Partial completion detected. Recommend {provider_pct}% to provider."
    elif provider_score >= 40:
        provider_pct = provider_score
        recommendation = RESOLUTION_PARTIAL
        rationale = f"Disputed but work was done. Recommend {provider_pct}% to provider, {100-provider_pct}% refund."
    elif provider_score >= 20:
        provider_pct = provider_score
        recommendation = RESOLUTION_PARTIAL
        rationale = f"Significant issues found. Recommend {provider_pct}% to provider, {100-provider_pct}% refund."
    else:
        recommendation = RESOLUTION_FULL_REFUND
        provider_pct = 0
        rationale = "Deliverable does not meet requirements. Recommend full refund."

    provider_amount = round(amount * provider_pct / 100, 2)
    client_refund = round(amount - provider_amount, 2)

    return {
        "escrow_id": escrow.get("id"),
        "dispute_summary": {
            "client_complaint": client_reason,
            "provider_response": provider_evidence,
            "original_scope": escrow.get("description", "Not specified"),
        },
        "analysis": analysis_points,
        "provider_score": provider_score,
        "recommendation": recommendation,
        "rationale": rationale,
        "proposed_split": {
            "provider_amount": provider_amount,
            "provider_pct": provider_pct,
            "client_refund": client_refund,
            "client_pct": 100 - provider_pct,
        },
        "resolution_options": [
            {"option": "A", "action": f"Accept AI recommendation: {provider_pct}% to provider (${provider_amount}), {100-provider_pct}% refund (${client_refund})"},
            {"option": "B", "action": f"Full release: 100% to provider (${amount})"},
            {"option": "C", "action": f"Full refund: 100% to client (${amount})"},
            {"option": "D", "action": "Escalate to multi-sig arbitration"},
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Resolve escrow disputes")
    sub = parser.add_subparsers(dest="command", required=True)

    # analyze
    p_analyze = sub.add_parser("analyze", help="Analyze dispute")
    p_analyze.add_argument("--escrow-id", required=True, help="Escrow ID")
    p_analyze.add_argument("--client-reason", required=True, help="Client's complaint")
    p_analyze.add_argument("--provider-evidence", required=True, help="Provider's counter")
    p_analyze.add_argument("--escrow-data", default=None, help="JSON escrow data")
    p_analyze.add_argument("--verification-score", type=float, default=None, help="Prior verification score")

    # resolve
    p_resolve = sub.add_parser("resolve", help="Execute resolution")
    p_resolve.add_argument("--escrow-id", required=True, help="Escrow ID")
    p_resolve.add_argument("--resolution", required=True, choices=["full_release", "full_refund", "partial"])
    p_resolve.add_argument("--split", type=int, default=50, help="Provider percentage for partial")

    args = parser.parse_args()

    if args.command == "analyze":
        # Load escrow data
        if args.escrow_data:
            escrow = json.loads(args.escrow_data)
        else:
            escrow = {"id": args.escrow_id, "description": "Not available", "amount": 0}

        result = analyze_dispute(
            escrow,
            args.client_reason,
            args.provider_evidence,
            args.verification_score,
        )
    elif args.command == "resolve":
        result = {
            "escrow_id": args.escrow_id,
            "resolution": args.resolution,
            "provider_pct": args.split if args.resolution == "partial" else (100 if args.resolution == "full_release" else 0),
            "status": "resolved",
            "message": f"Dispute resolved: {args.resolution}",
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
