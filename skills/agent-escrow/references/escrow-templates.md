# Escrow Templates

Reference document for AI agent — predefined escrow templates for common use cases.

## Template: Freelance Development

```json
{
  "template": "freelance-dev",
  "defaults": {
    "token": "USDC",
    "deadline_days": 14,
    "verify_type": "github",
    "dispute_window_hours": 48,
    "auto_release_on_timeout": true
  },
  "suggested_milestones": [
    {"name": "Design & Planning", "pct": 20, "verify_type": "url"},
    {"name": "Implementation", "pct": 50, "verify_type": "github"},
    {"name": "Testing & Deployment", "pct": 30, "verify_type": "url"}
  ]
}
```

## Template: NFT Commission

```json
{
  "template": "nft-commission",
  "defaults": {
    "token": "USDC",
    "deadline_days": 7,
    "verify_type": "ipfs",
    "dispute_window_hours": 72,
    "auto_release_on_timeout": true
  }
}
```

## Template: API Service

```json
{
  "template": "api-service",
  "defaults": {
    "token": "USDC",
    "type": "micro",
    "per_call": 0.01,
    "verify_type": "api"
  }
}
```

## Template: Content Writing

```json
{
  "template": "content-writing",
  "defaults": {
    "token": "USDC",
    "deadline_days": 5,
    "verify_type": "url",
    "dispute_window_hours": 48
  }
}
```

## Template: Smart Contract Audit

```json
{
  "template": "smart-contract-audit",
  "defaults": {
    "token": "USDC",
    "deadline_days": 21,
    "verify_type": "github",
    "dispute_window_hours": 96,
    "auto_release_on_timeout": false
  },
  "suggested_milestones": [
    {"name": "Initial Review", "pct": 30, "verify_type": "manual"},
    {"name": "Detailed Report", "pct": 50, "verify_type": "github"},
    {"name": "Fix Verification", "pct": 20, "verify_type": "github"}
  ]
}
```
