# Discord Bot Integration — Interactive Benny

## Overview

Add a Discord bot that lets you interact with Benny in real-time. Beyond one-way notifications (bet placed, bet settled), you can ask Benny questions and get AI-powered responses.

## Two Capabilities

### 1. Notifications (webhook — simple)

Replace SMS/SES with Discord webhook. Same approach as Archy's trading agent.

```
Benny places bet → SQS → Notification Processor → Discord webhook POST
Bet settles       → Outcome Collector            → Discord webhook POST
Weekly report     → Weekly Reporter               → Discord webhook POST
```

Messages:
- Bet placed: game, pick, confidence, stake, AI reasoning
- Bet settled: result, P&L, updated bankroll
- Weekly summary: record, ROI, bankroll balance

### 2. Interactive Chat (bot — new)

A Discord bot that listens for messages and responds using Claude + Benny's data.

Example interactions:
```
You:   @Benny why did you take Chiefs -3.5?
Benny: I had 72% confidence on Chiefs. Their offense ranks 3rd in EPA/play
       and the Broncos are 2-5 ATS on the road. Line moved from -2.5 to -3.5
       which concerned me, but the team stats gap was too large to ignore.

You:   @Benny what do you like for NBA tonight?
Benny: Looking at tonight's slate, I see two games above my 65% threshold:
       • Celtics -6.5 vs Hornets (71% conf) — Celtics 8-2 ATS last 10
       • Thunder ML vs Lakers (68% conf) — SGA averaging 32 PPG last 5
       I'll place bets on these when my next run fires at 10 AM ET.

You:   @Benny how's your bankroll looking?
Benny: This week: $100 starting → $118.40 current (+18.4%)
       Record: 6W-3L (67% win rate)
       Best bet: Packers ML +155 → Won $15.50
       Worst bet: Lakers -4.5 → Lost $12.00

You:   @Benny what do you think about Mahomes over 275.5 passing yards?
Benny: I don't have a model prediction on that specific prop, but here's
       what I see: Mahomes has gone over 275.5 in 7 of his last 10 games.
       The opponent allows 260 passing yards/game (22nd in NFL). Weather
       is clear, no wind. I'd lean over but my confidence would be moderate
       — maybe 60%, below my 65% threshold for betting.
```

## Architecture

### Discord Bot Setup

```
Discord Developer Portal → New Application → Bot → Copy Token
                                                  → Enable "Message Content Intent"
                                                  → Generate invite URL with bot + message permissions
                                                  → Add bot to your private server
```

### Request Flow

```
User sends message mentioning @Benny
  → Discord sends HTTP POST to API Gateway endpoint
  → Lambda handler:
      1. Parse the user's question
      2. Fetch relevant context from DynamoDB:
         - Current bankroll and week record
         - Recent bets (last 7 days)
         - Upcoming games with predictions (if asking about games)
         - Historical performance stats
      3. Build Claude prompt with question + context
      4. Call Bedrock (Claude Sonnet)
      5. POST response back to Discord channel
  → User sees Benny's response in Discord
```

### Lambda Handler (new)

```python
# backend/benny_discord_bot.py

def handler(event, context):
    """Handle Discord interaction."""
    body = json.loads(event['body'])

    # Discord verification (required)
    if body['type'] == 1:  # PING
        return {'statusCode': 200, 'body': json.dumps({'type': 1})}

    # User message
    question = body['data']['options'][0]['value']
    channel_id = body['channel_id']

    # Fetch context from DynamoDB
    context_data = build_context(question)

    # Ask Claude
    response = call_bedrock(question, context_data)

    # Reply in Discord
    post_to_discord(channel_id, response)
```

### Context Builder

Based on the question, fetch relevant data:

| Question Type | Data to Fetch |
|---|---|
| "Why did you bet X?" | That specific bet record (reasoning, confidence, factors) |
| "What do you like tonight?" | Upcoming games with ensemble predictions above threshold |
| "How's your bankroll?" | Current bankroll, week record, recent bets |
| "What about [game/prop]?" | Team stats, odds, model predictions for that matchup |
| "How are you doing on [sport]?" | Performance breakdown by sport |

Don't over-engineer the routing — Claude can figure out what the user is asking. Just include a broad context payload and let the AI pick what's relevant.

### Claude Prompt

```
You are Benny, an AI sports betting agent. You speak casually and confidently
about your bets. You use data to back up your opinions.

CURRENT STATE:
- Bankroll: $118.40 / $100.00 this week (+18.4%)
- Record: 6W-3L (67%)
- Pending bets: 2

RECENT BETS:
[last 10 bets with outcomes]

UPCOMING PREDICTIONS:
[games with confidence > 50%, sorted by confidence]

USER QUESTION: {question}

Respond conversationally. Reference specific stats and numbers.
If you don't have data on something, say so honestly.
Keep responses under 200 words unless the user asks for detail.
```

## Infrastructure

### New Resources
- Lambda: `benny-discord-bot` (512 MB, 30s timeout)
- API Gateway: POST endpoint for Discord interactions
- IAM: Bedrock invoke + DynamoDB read
- Secrets Manager: Discord bot token (add to existing secret)

### Discord Bot Token Storage
Add to existing secrets:
```json
{
  "odds_api_key": "...",
  "discord_bot_token": "...",
  "discord_webhook_url": "..."
}
```

## Implementation Plan

### Step 1: Webhook Notifications (1-2 hours)
- Add `discord_webhook_url` to Secrets Manager
- Add Discord webhook POST to `notification_service.py` as a new channel
- Wire into notification processor
- Test with a manual bet

### Step 2: Discord Bot Application (30 min)
- Create application in Discord Developer Portal
- Create bot, copy token, store in Secrets Manager
- Invite bot to private server
- Register slash command: `/ask [question]`

### Step 3: Bot Lambda (2-3 hours)
- New Lambda: `benny_discord_bot.py`
- API Gateway endpoint for Discord interactions
- Discord signature verification (required by Discord)
- Context builder: query DynamoDB for relevant data
- Bedrock call with question + context
- POST response back to channel

### Step 4: Slash Commands (optional, nicer UX)
Instead of `@Benny why did you...`, register slash commands:
- `/benny ask [question]` — general question
- `/benny bankroll` — current bankroll status
- `/benny bets` — recent bets
- `/benny tonight` — upcoming games Benny likes

## Cost

- Discord bot: Free
- Lambda invocations: ~$0.01/month (you won't ask 1000 questions)
- Bedrock per question: ~$0.01-0.03 (Claude Sonnet, ~1k tokens in/out)
- Total: < $1/month

## Security

- Bot only responds in your private server (guild ID check)
- Discord webhook URL is a secret (anyone with it can post)
- Bot token stored in Secrets Manager, never in code
- API Gateway endpoint validates Discord signature (prevents spoofing)

## Future: Paid Community

Same bot works in a paid Discord server. Subscribers can ask Benny questions — that's a differentiator over read-only signal feeds.

Free tier: read-only signals (delayed)
Paid tier: real-time signals + interactive @Benny chat

This makes the subscription stickier — people stay for the interaction, not just the picks.
