# agent-escrow

AI-powered escrow agent for OKX OnchainOS — payment protection for freelance work, NFT commissions, API services, and peer-to-peer transactions on X Layer.

## What It Does

1. **Create Escrow** — Lock funds via natural language with configurable deadlines and verification
2. **AI Verify** — Auto-check deliverables (GitHub repos, IPFS files, URLs, APIs)
3. **Release Funds** — Approve payment after verification passes
4. **Dispute Resolution** — AI analyzes evidence, recommends fair partial releases
5. **Milestones** — Multi-phase payments with per-milestone verification
6. **x402 Micro-Payments** — Pay-per-call API escrows via OKX payment protocol

## Key Differentiators

- **AI verification** — Agent checks deliverables automatically (not just manual approve/reject)
- **Smart disputes** — Evidence-based partial release, not "wait 7 days and hope"
- **Conversational** — Create escrow by talking to AI, no app or UI needed
- **Near-zero gas** — X Layer gas ~$0.001 makes even $5 escrows economical
- **x402 integration** — Native OKX micro-payment protocol for pay-per-use services

## Install

```bash
npx skills add okx/plugin-store --skill agent-escrow
```

## Usage Examples

```
"Create escrow 200 USDC for logo design, deliver in 5 days, verify via IPFS"
"Check delivery for escrow ESC-2026-0001"
"I'm not satisfied with the code — open dispute"
"Create milestone escrow: 3 phases, 1000 USDC total"
"Set up micro-payment: 10 USDC budget, 0.01 per API call"
```

## License

MIT
