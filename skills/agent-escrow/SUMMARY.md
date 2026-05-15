## Overview

agent-escrow is an AI-powered escrow plugin for OKX OnchainOS that provides payment protection for freelance work, NFT commissions, API services, and peer-to-peer transactions on X Layer.

Core operations:

- Create escrow contracts via natural language with configurable deadlines and verification methods
- AI auto-verification of deliverables (GitHub repos, IPFS files, live URLs, API endpoints)
- Smart dispute resolution with evidence-based partial release recommendations
- Multi-milestone escrow with automatic progression and per-phase verification
- x402 micro-payment escrows for pay-per-call API services

Tags: `escrow` `payments` `xlayer` `x402` `freelance` `defi-protocol`

## Prerequisites

- No IP restrictions
- Supported chain: X Layer (chain ID 196) — near-zero gas makes micro-escrow viable
- Supported tokens: USDC, USDT on X Layer
- onchainos CLI installed and authenticated (`npx skills add okx/onchainos-skills`)
- Python 3.8+ installed (for helper scripts)
- A funded wallet with stablecoins on X Layer (or bridge from any supported chain)

## Quick Start

1. **Create an escrow**: Tell the agent "Create escrow: 200 USDC for logo design, deliver in 5 days, verify via IPFS hash". The agent generates escrow terms, shows a summary, and waits for your confirmation before locking funds.

2. **Share with provider**: After creation, the agent returns an escrow ID and shareable details. Send these to the service provider so they know the terms and verification method.

3. **Provider delivers**: When the provider submits their deliverable, the agent auto-verifies it (checks if the IPFS hash resolves, GitHub repo has code, URL returns 200, etc.) and presents a verification report with a score.

4. **Approve or dispute**: If verification passes, approve to release funds. If unsatisfied, open a dispute — the agent analyzes both sides and recommends a fair resolution (full release, partial release, or refund).

5. **Milestone projects**: For larger jobs, create multi-milestone escrows. Each phase has its own deliverable, verification, and payment. Funds release progressively as milestones complete.
