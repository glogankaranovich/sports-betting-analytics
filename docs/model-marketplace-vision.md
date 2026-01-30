# Model Marketplace Vision

## Current State
The Models section currently has:
- Overview: Basic model descriptions
- Performance: Analytics for all models
- Comparison: Placeholder for side-by-side comparison

## Future Model Marketplace Structure

### Browse Models (Marketplace)
Card-based marketplace view with:
- Model name, description, creator
- Key performance stats (accuracy, ROI, confidence calibration)
- Price/subscription tiers (free, premium, pro)
- "Subscribe" or "Try Free" buttons
- Filtering by sport, bet type, performance
- Search functionality

### My Models
- Models user has subscribed to
- Active subscriptions and expiration dates
- Usage statistics
- Quick access to model analyses

### Performance Dashboard
- Detailed analytics for subscribed models only
- Historical performance charts
- Confidence calibration graphs
- ROI tracking over time
- Model comparison (only for owned models)

### Leaderboard
- Top performing models ranked by:
  - Overall accuracy
  - ROI
  - Consistency (Brier score)
  - User ratings
- Time period filters (7d, 30d, season, all-time)

## Technical Requirements

### Backend
- [ ] Model subscription system (DynamoDB table)
- [ ] Payment integration (Stripe)
- [ ] Model creator profiles
- [ ] Access control (user can only see analyses from subscribed models)
- [ ] Model performance aggregation API
- [ ] Leaderboard calculation Lambda

### Frontend
- [ ] Marketplace browse UI with model cards
- [ ] Subscription management page
- [ ] Payment flow integration
- [ ] Model detail pages
- [ ] Leaderboard component
- [ ] Filter and search functionality

### Infrastructure
- [ ] Stripe integration for payments
- [ ] Model creator onboarding flow
- [ ] Revenue sharing calculation
- [ ] Subscription renewal automation

## Phased Rollout

### Phase 1: Foundation (Current)
- Basic model descriptions
- Performance analytics for all models
- Free access to all models

### Phase 2: Marketplace UI
- Browse models page with cards
- Model detail pages
- My Models page
- Performance restricted to subscribed models

### Phase 3: Monetization
- Stripe payment integration
- Subscription tiers (free/premium/pro)
- Model creator payouts
- Trial periods

### Phase 4: Community
- User ratings and reviews
- Model creator profiles
- Leaderboard
- Social features (follow creators, share analyses)

## Notes
- Keep current free models available to bootstrap marketplace
- Consider freemium model: basic models free, advanced models paid
- Revenue split: 70% creator, 30% platform
- Minimum performance threshold for marketplace listing
