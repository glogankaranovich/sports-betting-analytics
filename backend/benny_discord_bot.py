"""Benny Discord Bot — interactive chat via slash commands."""

import json
import os
import hashlib
import hmac
import boto3
import logging
import struct

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DISCORD_PUBLIC_KEY = os.environ.get('DISCORD_PUBLIC_KEY', '')

# --- Pure-Python Ed25519 (no native deps) ---
# Minimal implementation for Discord signature verification only.

_P = 2**255 - 19
_D = -121665 * pow(121666, _P - 2, _P) % _P
_I = pow(2, (_P - 1) // 4, _P)
_L = 2**252 + 27742317777372353535851937790883648493

def _sha512(data):
    return hashlib.sha512(data).digest()

def _inv(x):
    return pow(x, _P - 2, _P)

def _recover_x(y, sign):
    y2 = y * y % _P
    x2 = (y2 - 1) * _inv(_D * y2 + 1) % _P
    if x2 == 0:
        return 0 if sign == 0 else None
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0:
        x = x * _I % _P
    if (x * x - x2) % _P != 0:
        return None
    if x % 2 != sign:
        x = _P - x
    return x

def _point_add(P, Q):
    if P is None: return Q
    if Q is None: return P
    x1, y1, z1, t1 = P
    x2, y2, z2, t2 = Q
    a = (y1 - x1) * (y2 - x2) % _P
    b = (y1 + x1) * (y2 + x2) % _P
    c = 2 * t1 * t2 * _D % _P
    d = 2 * z1 * z2 % _P
    e = b - a; f = d - c; g = d + c; h = b + a
    return (e*f%_P, g*h%_P, f*g%_P, e*h%_P)

def _point_mul(s, P):
    Q = None
    while s > 0:
        if s & 1:
            Q = _point_add(Q, P)
        P = _point_add(P, P)
        s >>= 1
    return Q

def _decode_point(b):
    y = int.from_bytes(b, 'little')
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    if x is None:
        raise ValueError("Invalid point")
    return (x, y, 1, x * y % _P)

_BY = 4 * _inv(5) % _P
_BX = _recover_x(_BY, 0)
_B = (_BX, _BY, 1, _BX * _BY % _P)

def _encode_point(P):
    zi = _inv(P[2])
    x = P[0] * zi % _P
    y = P[1] * zi % _P
    return (y | ((x & 1) << 255)).to_bytes(32, 'little')

def _ed25519_verify(public_key_bytes, signature, message):
    if len(signature) != 64 or len(public_key_bytes) != 32:
        raise ValueError("Bad length")
    R = _decode_point(signature[:32])
    A = _decode_point(public_key_bytes)
    s = int.from_bytes(signature[32:], 'little')
    if s >= _L:
        raise ValueError("Bad s")
    h = int.from_bytes(_sha512(signature[:32] + public_key_bytes + message), 'little') % _L
    sB = _point_mul(s, _B)
    hA = _point_mul(h, A)
    RhA = _point_add(R, hA)
    if _encode_point(sB) != _encode_point(RhA):
        raise ValueError("Signature mismatch")


def verify_signature(event):
    """Verify Discord request signature using pure-Python Ed25519."""
    sig = bytes.fromhex(event['headers'].get('x-signature-ed25519', ''))
    timestamp = event['headers'].get('x-signature-timestamp', '')
    body = event['body']
    pub = bytes.fromhex(DISCORD_PUBLIC_KEY)
    _ed25519_verify(pub, sig, f"{timestamp}{body}".encode())


def get_benny_context():
    """Fetch Benny's current state for Claude context."""
    from benny_trader import BennyTrader
    trader = BennyTrader(version='v1')
    return trader.get_dashboard_data()


def ask_claude(question, ctx):
    """Send question + context to Claude via Bedrock."""
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

    bankroll = ctx.get('current_bankroll', 100)
    starting = ctx.get('weekly_budget', 100)
    win_rate = ctx.get('win_rate', 0)
    roi = ctx.get('roi', 0)
    total = ctx.get('total_bets', 0)
    pending = ctx.get('pending_bets', 0)
    recent = ctx.get('recent_bets', [])[:10]

    recent_text = ""
    for b in recent:
        status = b.get('status', 'pending')
        emoji = '✅' if status == 'won' else '❌' if status == 'lost' else '⏳'
        recent_text += f"\n  {emoji} {b.get('game', '?')} | {b.get('prediction', '?')} | ${float(b.get('bet_amount', 0)):.2f} | conf: {float(b.get('confidence', 0)):.0%}"

    sports_text = ""
    for sport, perf in ctx.get('sports_performance', {}).items():
        sports_text += f"\n  {sport}: {perf.get('record', '?')} ({perf.get('win_rate', 0):.0%})"

    prompt = f"""You are Benny, an AI sports betting agent. You speak casually and confidently.
You use data to back up your opinions. Keep responses under 200 words unless asked for detail.

CURRENT STATE:
- Bankroll: ${bankroll:.2f} / ${starting:.2f} weekly budget
- Total bets: {total} | Win rate: {win_rate:.0%} | ROI: {roi:.1%}
- Pending bets: {pending}

RECENT BETS:{recent_text or ' None'}

BY SPORT:{sports_text or ' No data yet'}

USER QUESTION: {question}

Respond as Benny. Be specific with numbers. If you don't have data on something, say so."""

    response = bedrock.invoke_model(
        modelId='us.anthropic.claude-sonnet-4-5-20250929-v1:0',
        body=json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 500,
            'messages': [{'role': 'user', 'content': prompt}],
        }),
    )
    result = json.loads(response['body'].read())
    return result['content'][0]['text']


def handler(event, context):
    """Handle Discord interactions."""
    # Async followup invocation (self-invoked)
    if event.get('followup'):
        question = event['question']
        app_id = event['app_id']
        token = event['token']
        logger.info(f"Followup for: {question}")

        try:
            benny_context = get_benny_context()
            answer = ask_claude(question, benny_context)
            if len(answer) > 1990:
                answer = answer[:1990] + "..."
        except Exception as e:
            logger.error(f"Error: {e}")
            answer = f"Sorry, I hit an error: {str(e)[:200]}"

        from urllib import request as urllib_request
        url = f"https://discord.com/api/v10/webhooks/{app_id}/{token}"
        data = json.dumps({"content": answer}).encode()
        req = urllib_request.Request(url, data=data, headers={
            "Content-Type": "application/json",
            "User-Agent": "Benny/1.0",
        })
        urllib_request.urlopen(req, timeout=10)
        return {'statusCode': 200}

    # Verify signature
    try:
        verify_signature(event)
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        return {'statusCode': 401, 'body': 'Invalid signature'}

    body = json.loads(event['body'])

    # PING — Discord verification handshake
    if body.get('type') == 1:
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'type': 1}),
        }

    # Slash command
    if body.get('type') == 2:
        question = body['data']['options'][0]['value']
        token = body['token']
        app_id = body['application_id']
        logger.info(f"Question: {question}")

        # Invoke self asynchronously to do the actual work
        boto3.client('lambda').invoke(
            FunctionName=context.function_name,
            InvocationType='Event',
            Payload=json.dumps({
                'followup': True,
                'question': question,
                'app_id': app_id,
                'token': token,
            }),
        )

        # Immediate deferred response (type 5 = "Benny is thinking...")
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'type': 5}),
        }

    return {'statusCode': 400, 'body': 'Unknown interaction type'}
