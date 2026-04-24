import json, os, boto3, requests

TABLE_NAME = os.environ['TABLE_NAME']

dynamodb = boto3.resource('dynamodb')
table    = dynamodb.Table(TABLE_NAME)
bedrock  = boto3.client('bedrock-runtime')   # region auto-detected from Lambda execution env

CORS_HEADERS = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Content-Type': 'application/json'
}

def lambda_handler(event, context):
    method = event.get('httpMethod', '')

    # Handle CORS preflight
    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    # Parse request body
    try:
        body = json.loads(event.get('body') or '{}')
    except (json.JSONDecodeError, TypeError):
        return _err(400, 'Invalid JSON body')

    session_id = body.get('session_id')
    question   = body.get('question', '').strip()

    if not session_id:
        return _err(401, 'Missing session_id')
    if not question:
        return _err(400, 'Missing question')

    # Look up the Google access token
    res = table.get_item(Key={'session_id': session_id})
    if 'Item' not in res:
        return _err(401, 'Session expired — please reconnect your Google account')

    token = res['Item']['access_token']

    # ── Fetch Gmail snippets ──────────────────────────────────────────────────
    gmail_context = _get_gmail(token)

    # ── Fetch Calendar events ─────────────────────────────────────────────────
    calendar_context = _get_calendar(token)

    # ── Ask Claude via Bedrock ────────────────────────────────────────────────
    system_prompt = (
        "You are a helpful assistant with access to the user's Gmail and Google Calendar. "
        "Answer the user's question using only the data provided. "
        "Be concise and friendly."
    )
    user_message = (
        f"Gmail (recent messages):\n{gmail_context}\n\n"
        f"Calendar (upcoming events):\n{calendar_context}\n\n"
        f"Question: {question}"
    )

    try:
        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 1024,
                'system': system_prompt,
                'messages': [{'role': 'user', 'content': user_message}]
            })
        )
        answer = json.loads(response['body'].read())['content'][0]['text']
    except Exception as e:
        return _err(502, f'AI error: {str(e)}')

    return {
        'statusCode': 200,
        'headers':    CORS_HEADERS,
        'body':       json.dumps({'answer': answer})
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_gmail(token):
    """Fetch the 5 most recent email subjects + snippets."""
    try:
        auth = {'Authorization': f'Bearer {token}'}
        list_resp = requests.get(
            'https://www.googleapis.com/gmail/v1/users/me/messages?maxResults=5',
            headers=auth
        ).json()

        messages = list_resp.get('messages', [])
        if not messages:
            return 'No recent emails found.'

        results = []
        for msg in messages:
            detail = requests.get(
                f"https://www.googleapis.com/gmail/v1/users/me/messages/{msg['id']}?format=metadata&metadataHeaders=Subject&metadataHeaders=From",
                headers=auth
            ).json()
            headers = {h['name']: h['value'] for h in detail.get('payload', {}).get('headers', [])}
            snippet = detail.get('snippet', '')
            results.append(f"From: {headers.get('From','?')} | Subject: {headers.get('Subject','?')} | {snippet}")

        return '\n'.join(results)
    except Exception as e:
        return f'Could not fetch Gmail: {str(e)}'


def _get_calendar(token):
    """Fetch upcoming calendar events for the next 7 days."""
    try:
        from datetime import datetime, timezone, timedelta
        now   = datetime.now(timezone.utc)
        end   = now + timedelta(days=7)
        params = {
            'timeMin':      now.isoformat(),
            'timeMax':      end.isoformat(),
            'maxResults':   10,
            'singleEvents': 'true',
            'orderBy':      'startTime'
        }
        resp = requests.get(
            'https://www.googleapis.com/calendar/v3/calendars/primary/events',
            headers={'Authorization': f'Bearer {token}'},
            params=params
        ).json()

        events = resp.get('items', [])
        if not events:
            return 'No upcoming events in the next 7 days.'

        results = []
        for e in events:
            start = e.get('start', {}).get('dateTime') or e.get('start', {}).get('date', '?')
            results.append(f"{start}: {e.get('summary', 'Untitled event')}")

        return '\n'.join(results)
    except Exception as e:
        return f'Could not fetch Calendar: {str(e)}'


def _err(status, message):
    return {
        'statusCode': status,
        'headers':    CORS_HEADERS,
        'body':       json.dumps({'error': message})
    }
