import json, os, uuid, time, urllib.parse, boto3, requests

CLIENT_ID     = os.environ['GOOGLE_CLIENT_ID']
CLIENT_SECRET = os.environ['GOOGLE_CLIENT_SECRET']
REDIRECT_URI  = os.environ['REDIRECT_URI']
FRONTEND_URL  = os.environ['FRONTEND_URL']
TABLE_NAME    = os.environ['TABLE_NAME']

dynamodb = boto3.resource('dynamodb')
table    = dynamodb.Table(TABLE_NAME)

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.readonly'
]

CORS_HEADERS = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Content-Type': 'application/json'
}

def lambda_handler(event, context):
    path   = event.get('path', '')
    method = event.get('httpMethod', '')

    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    if path == '/auth':
        params = urllib.parse.urlencode({
            'client_id':     CLIENT_ID,
            'redirect_uri':  REDIRECT_URI,
            'response_type': 'code',
            'scope':         ' '.join(SCOPES),
            'access_type':   'offline',
            'prompt':        'consent'
        })
        return _redirect(f'https://accounts.google.com/o/oauth2/auth?{params}')

    if path == '/callback':
        code = (event.get('queryStringParameters') or {}).get('code')
        if not code:
            return {
                'statusCode': 400,
                'headers':    CORS_HEADERS,
                'body':       json.dumps({'error': 'Missing code parameter'})
            }

        token_resp = requests.post('https://oauth2.googleapis.com/token', data={
            'code':          code,
            'client_id':     CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'redirect_uri':  REDIRECT_URI,
            'grant_type':    'authorization_code'
        })

        token = token_resp.json()

        if 'access_token' not in token:
            return {
                'statusCode': 502,
                'headers':    CORS_HEADERS,
                'body':       json.dumps({'error': 'Token exchange failed', 'detail': token})
            }

        session_id = str(uuid.uuid4())
        table.put_item(Item={
            'session_id':   session_id,
            'access_token': token['access_token'],
            'ttl':          int(time.time()) + 3600
        })

        return _redirect(f'{FRONTEND_URL}?session_id={session_id}')

    return {
        'statusCode': 404,
        'headers':    CORS_HEADERS,
        'body':       json.dumps({'error': 'Not found'})
    }

def _redirect(url):
    return {
        'statusCode': 302,
        'headers':    {'Location': url},
        'body':       ''
    }
