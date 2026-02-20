import urllib.request, urllib.error, json
base='http://127.0.0.1:5000'

def post(path, data, token=None):
    req=urllib.request.Request(base+path, data=json.dumps(data).encode('utf-8'), headers={'Content-Type':'application/json'})
    if token:
        req.add_header('Authorization', 'Bearer '+token)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            body = r.read().decode()
            print(path, '->', r.status)
            print(body)
            try:
                return r.status, json.loads(body)
            except Exception:
                return r.status, body
    except urllib.error.HTTPError as e:
        body=e.read().decode()
        print(path, 'HTTPERR', e.code, body)
        return e.code, body
    except Exception as e:
        print(path, 'ERR', e)
        return None, None

# Register doctor
status, body = post('/api/register', {'name':'Dr Smith','email':'doctor@example.com','password':'password123','role':'doctor'})
# Register patient assigned to doctor if doctor created
if isinstance(body, dict) and 'user_id' in body:
    doctor_id = body['user_id']
    status2, body2 = post('/api/register', {'name':'John Doe','email':'patient@example.com','password':'password123','role':'patient','assigned_doctor_id':doctor_id})
else:
    print('Doctor registration failed; skipping patient registration')

# Login patient
status3, body3 = post('/api/login', {'email':'patient@example.com','password':'password123'})
if isinstance(body3, dict) and 'token' in body3:
    token=body3['token']
    # Create daily log
    post('/api/patient/daily-log', {'date':'2026-02-20','pain_level':4,'mood_level':3,'sleep_hours':7.0,'appetite':'good','swelling':False,'body_part':'knee','note_text':'Feeling okay'}, token=token)
    # Get my logs (GET)
    try:
        req=urllib.request.Request(base+'/api/patient/my-logs', headers={'Authorization':'Bearer '+token})
        with urllib.request.urlopen(req, timeout=5) as r:
            body = r.read().decode()
            print('/api/patient/my-logs ->', r.status)
            print(body)
    except Exception as e:
        print('GET my-logs failed', e)
else:
    print('Patient login failed; cannot create logs')
