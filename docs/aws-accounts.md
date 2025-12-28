# AWS Accounts - Sports Betting Analytics

## Account Structure

| Environment | Account ID | Email | Purpose |
|-------------|------------|-------|---------|
| **Development** | `540477485595` | `glogankaranovich+sports-betting-dev@gmail.com` | Development and feature testing |
| **Staging** | `352312075009` | `glogankaranovich+sports-betting-staging@gmail.com` | Pre-production validation |
| **Production** | `198784968537` | `glogankaranovich+sports-betting-prod@gmail.com` | Live production workloads |
| **Pipeline** | `083314012659` | `glogankaranovich+sports-betting-pipeline@gmail.com` | CI/CD pipelines and shared services |

## Account Access

All accounts are managed through AWS Organizations with cross-account roles:
- **Role Name**: `OrganizationAccountAccessRole`
- **Access Method**: Assume role from management account
- **Region**: `us-east-1` (primary)

## AWS CLI Profiles

Configure profiles using the commands in the setup section below.

## Security Notes

- Each account has isolated resources and billing
- Cross-account access requires role assumption
- All accounts use the same region (us-east-1) for simplicity
- Pipeline account handles deployments to all environments

---
*Created: 2025-12-28*
*Project: Sports Betting Analytics*
