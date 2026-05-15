---
name: agent-escrow
description: "AI-powered escrow agent for freelance payments, NFT commissions, and micro-services on X Layer with auto-verification and dispute resolution"
version: "1.0.0"
author: "oliva9595"
tags:
  - escrow
  - payments
  - xlayer
  - x402
  - freelance
---

# Agent Escrow — AI-Powered Payment Protection

## Overview

This skill enables the AI agent to create, manage, and resolve escrow payments on X Layer (chain ID `196`). Unlike traditional escrow services that require manual verification, Agent Escrow uses AI to automatically verify deliverables (GitHub repos, IPFS files, URLs, API endpoints) and resolve disputes with evidence-based evaluation.

**Key capabilities:**
- Create escrow contracts via natural language (single, multi-milestone, or x402 micro-payment)
- AI auto-verification of deliverables (code, files, URLs, API responses)
- Smart dispute resolution with partial release recommendations
- Templates for freelance, NFT commissions, API services, and group payments

## Trigger Keywords

### Activate this skill when the user mentions:
- "create escrow", "set up escrow", "lock funds", "payment protection", "secure payment"
- "hire with escrow", "pay freelancer safely", "escrow for job", "hold payment"
- "verify delivery", "check submission", "deliverable ready", "finished the job"
- "release payment", "approve work", "pay them", "release funds", "send payment"
- "dispute", "not satisfied", "reject delivery", "complaint", "refund"
- "milestone payment", "split payment into phases", "pay per milestone"
- "micro-payment", "pay per API call", "x402", "pay per use", "usage-based payment"
- "escrow status", "my escrows", "check escrow", "escrow list"

### DO NOT activate this skill when:
- User asks about swapping tokens without payment/escrow context → use `okx-dex-swap`
- User asks about yield farming or bridge → use `xlayer-bridge-yield`
- User asks about wallet balance only → use `okx-wallet-portfolio`
- User discusses trading, meme coins, or prediction markets
- User asks about lending/borrowing protocols (Aave, Compound)
- User asks about token security only → use `okx-security`

## Pre-flight Checks

Before using this skill, ensure:

1. The `onchainos` CLI is installed and configured:
   ```bash
   npx skills add okx/onchainos-skills
   ```
2. Python 3.8+ is available (for helper scripts):
   ```bash
   python3 --version
   ```
3. The user has a funded wallet with stablecoins (USDC/USDT) on X Layer or a supported source chain
4. The `onchainos wallet` is logged in and authenticated

## Safety Configuration

This plugin operates in **dry-run mode by default**. All escrow operations simulate without executing real transactions unless the user explicitly confirms.

### Default Safety Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `mode` | `dry-run` | No real transactions unless user says "execute" or "confirm" |
| `max_escrow_amount` | `5000` | Maximum USD value per escrow contract |
| `dispute_window_hours` | `48` | Hours after delivery for client to review/dispute |
| `auto_release_on_timeout` | `true` | Auto-release to provider if client doesn't respond within window |
| `min_verification_score` | `0.7` | Minimum AI verification score (0-1) to recommend approval |

---

## Commands

### 1. Create Escrow

Creates a new escrow contract. Supports three modes: **standard** (single delivery), **milestone** (multi-phase), and **micro** (x402 pay-per-call).

**When to use**: When the user asks "create escrow", "set up payment protection", "lock funds for a job", "hire someone with escrow", "pay freelancer safely", "secure a payment", "milestone escrow", "split payment into phases", "micro-payment escrow", "pay per API call", or "x402 payment".

**Workflow (standard mode)**:
1. Parse user request for: amount, token, description, deadline, verification method
2. Run escrow manager to generate contract parameters:
   ```bash
   python3 scripts/escrow_manager.py create --amount <AMOUNT> --token <TOKEN> --description "<DESC>" --deadline <DAYS> --verify-type <TYPE> --verify-target "<TARGET>"
   ```
3. Security check on token (required because escrow involves locking user funds):
   ```bash
   onchainos security token-scan --address <TOKEN_ADDRESS> --chain 196 --format json
   ```
4. Check client balance (to verify sufficient funds before locking):
   ```bash
   onchainos portfolio all-balances --chain 196 --format json
   ```
5. **Present escrow terms to user** and **WAIT FOR CONFIRMATION**:
   ```
   Escrow Summary:
   ├── Amount: 200 USDC
   ├── Deadline: May 25, 2026 (7 days)
   ├── Deliverable: "Frontend dashboard code"
   ├── Verification: GitHub repo link
   ├── Dispute window: 48 hours
   └── Auto-release: Yes (if no response in 48h)
   Confirm? (yes/no)
   ```
6. On confirm, execute deposit:
   ```bash
   onchainos swap swap --from USDC --to USDC --amount <AMOUNT> --chain 196 --format json
   ```
7. Return escrow ID and shareable details for the provider.

**Milestone mode**: If user specifies multiple phases, use:
```bash
python3 scripts/escrow_manager.py create-milestones --total <AMOUNT> --milestones '<JSON_ARRAY>'
```
Each milestone has its own deadline, verify type, and amount. Funds release progressively as each milestone passes verification. Disputes apply per-milestone, not the entire escrow.

**Micro mode (x402)**: If user specifies pay-per-call, use:
```bash
python3 scripts/escrow_manager.py create-micro --budget <AMOUNT> --per-call <RATE> --provider "<URL>"
```
Each API call triggers x402 payment: `onchainos payment x402-pay --url <URL> --amount <RATE> --chain 196 --format json`. Agent alerts at 80% budget usage and auto-pauses when depleted.

**Output format**: Present escrow terms as a **tree diagram** (shown above). End with: "Escrow [ID] created. Share these details with the provider."

**Supported verification types**:
| Type | What agent checks | Example target |
|------|------------------|----------------|
| `github` | Repo exists, has commits after start date, code compiles | `github.com/user/repo` |
| `ipfs` | IPFS hash is pinned and accessible | `QmXxx...` or `ipfs://...` |
| `url` | URL returns HTTP 200 with expected content | `https://app.example.com` |
| `api` | API endpoint responds correctly | `https://api.example.com/health` |
| `manual` | No auto-verify, client approves manually | Description text |

---

### 2. Verify Delivery

AI-powered verification of a submitted deliverable against escrow requirements.

**When to use**: When the provider says "I've finished the job", "delivery ready", "check my submission", "here's the link", "work is done", "deliverable submitted", or when the agent receives a deliverable link.

**Workflow**:
1. Retrieve escrow details:
   ```bash
   python3 scripts/escrow_manager.py get --escrow-id <ID>
   ```
2. Run AI verification (checks vary by type — see table above):
   ```bash
   python3 scripts/delivery_verifier.py --escrow-id <ID> --deliverable "<LINK>" --type <TYPE>
   ```
3. Generate verification report:
   ```
   Verification Report — Escrow #ESC-2026-0042
   ├── Checks:
   │   ├── ✅ Repository exists (14 commits after start date)
   │   ├── ✅ README matches scope
   │   ├── ⚠️ No tests found
   │   └── ✅ Code compiles successfully
   ├── Score: 0.85 / 1.00
   └── Recommendation: APPROVE (score > 0.7 threshold)
   ```
4. Notify client with report and ask for approval.

**Output format**: Present as a **tree diagram** with check results (✅/⚠️/❌), score, and recommendation (APPROVE/REVIEW/REJECT). End with: "Recommend [action]. Approve release? (yes/no/dispute)"

---

### 3. Release Funds

Releases escrowed funds to the provider after verification or client approval.

**When to use**: When the client says "approve", "release payment", "looks good, pay them", "accept delivery", "send the money", or when auto-release triggers after dispute window timeout.

**Workflow**:
1. Verify escrow status is DELIVERED (not already released or disputed)
2. Check verification score — warn if below `min_verification_score`
3. **REQUIRE CLIENT CONFIRMATION** before releasing
4. Execute transfer:
   ```bash
   onchainos wallet send --to <PROVIDER_ADDRESS> --amount <AMOUNT> --token USDC --chain 196 --format json
   ```
5. Update escrow status:
   ```bash
   python3 scripts/escrow_manager.py update --escrow-id <ID> --status completed --tx-hash <HASH>
   ```

**Output format**: "✅ Released [amount] USDC to [address]. TX: [hash]. Escrow [ID] completed."

---

### 4. Dispute Resolution

AI-powered dispute resolution when client rejects a deliverable.

**When to use**: When the client says "I'm not satisfied", "this isn't what I asked for", "dispute", "reject delivery", "not happy with the work", "request refund", or when provider contests a rejection.

**Workflow**:
1. Collect evidence from both parties:
   ```bash
   python3 scripts/dispute_resolver.py analyze --escrow-id <ID> --client-reason "<REASON>" --provider-evidence "<EVIDENCE>"
   ```
2. AI evaluates: original scope vs deliverable, verification scores, complaint specificity, evidence quality
3. Generate resolution with options:
   ```
   Dispute Analysis — Escrow #ESC-2026-0042
   ├── AI Assessment: "Core deliverable meets requirements.
   │   Mobile responsiveness was not in original scope."
   ├── Recommendation: PARTIAL RELEASE (85% provider, 15% refund)
   └── Options:
       A) Accept AI recommendation (85/15 split)
       B) Full release to provider
       C) Full refund to client
       D) Escalate to multi-sig arbitration
   ```
4. Execute agreed resolution.

**Output format**: Present as a **tree diagram** with assessment, recommendation, and 4 options. Both parties must agree before execution.

---

## Examples

### Example 1: Simple Freelance Escrow

**User**: "Create escrow: 500 USDC for a landing page, deliver in 7 days, verify the live URL"

1. Creates escrow with verify_type=url → presents terms → user confirms
2. Dev builds page → submits URL → Agent checks HTTP 200 + SSL + content
3. Score: 0.90 → Recommendation: APPROVE → Client says "approve" → Release 500 USDC

### Example 2: Multi-Milestone Project

**User**: "Milestone escrow: Phase 1 design 200 USDC, Phase 2 code 500 USDC, Phase 3 deploy 300 USDC"

1. Creates 3-milestone escrow, locks 1000 USDC total
2. Each phase: provider submits → agent verifies → client approves → partial release

### Example 3: Dispute with Partial Release

**User**: "I'm not happy with the code, it's missing error handling"

1. Agent analyzes scope vs deliverable → error handling not in original scope
2. Recommends: 85% to provider ($425), 15% refund ($75) → both agree → split executed

### Example 4: API Micro-Payments

**User**: "Micro-escrow: 10 USDC budget, 0.01 per call to api.dataservice.com"

1. Creates x402 micro-escrow → 1000 calls max → alerts at 80% usage → pauses when depleted

---

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| "Insufficient balance" | Not enough tokens | Ask user to fund wallet or reduce amount |
| "Amount exceeds max" | Safety limit exceeded | Show limit, ask to confirm override |
| "Escrow not found" | Invalid ID | Ask user to check the escrow ID |
| "Already released" | Funds already sent | Show completion receipt |
| "Deadline expired" | Provider missed deadline | Offer: extend or refund client |
| "Verification failed" | Deliverable doesn't pass | Show failed checks, suggest fixes |
| "Provider unreachable" | x402 endpoint down | Pause micro-escrow, alert user |
| "onchainos not found" | CLI not installed | Run `npx skills add okx/onchainos-skills` |

---

## Security Notices

> **RISK DISCLAIMER**: This plugin facilitates peer-to-peer payments through escrow on X Layer. While escrow reduces counterparty risk, it does not eliminate all risks. AI verification is advisory and should not replace human judgment for high-value transactions. Use at your own risk.

- **Default Mode**: Dry-run (no real transactions unless explicitly confirmed)
- **Private Keys**: NEVER handled — all signing via onchainos TEE wallet
- **Dispute Protection**: AI recommendations are advisory; both parties must agree
- **Amount Limits**: Default $5,000 cap prevents accidental large deposits
- **Auto-Release**: Protects providers from non-responsive clients (configurable)

## Skill Routing

- For token swaps → use `okx-dex-swap`
- For bridging to X Layer → use `xlayer-bridge-yield`
- For security scanning → use `okx-security`
- For wallet operations → use `okx-wallet-portfolio`
- For risk checks → use `agent-risk-firewall`
