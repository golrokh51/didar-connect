"""Private individual support cases. No Qt dependency for storage and validation."""
from datetime import date

CIRCUMSTANCES = {
 'Violence, abuse & safety': ['Domestic or intimate partner violence','Family violence','Physical violence','Psychological or emotional abuse','Sexual violence','Economic or financial abuse','Harassment','Online harassment','Coercive control'],
 'Discrimination & systemic barriers': ['Gender-based discrimination','Racial or ethnic discrimination','Discrimination based on sexual orientation or gender identity','Disability-related discrimination','Workplace discrimination or harassment','Institutional or systemic injustice','Barriers to accessing justice'],
 'Disability & accessibility': ['Physical accessibility barriers','Sensory accessibility barriers','Cognitive or learning accessibility barriers','Psychosocial accessibility barriers','Chronic illness-related barriers','Other accessibility needs'],
 'Social & economic circumstances': ['Social isolation','Financial hardship','Housing insecurity','Food insecurity','Employment difficulties','Language barriers','Digital exclusion','Family or caregiving difficulties'],
 'Migration & integration': ['Newcomer settlement difficulties','International student challenges','Immigration-related barriers','Refugee or asylum-related challenges','Cultural and social integration difficulties'],
 'Other': ['Other self-identified circumstances','Prefers not to disclose','Not yet assessed']}
NEEDS = ['Information and rights resources','Social support / companionship','Administrative support','Referral to qualified legal services','Referral to qualified psychological services','Referral to specialized safety / violence support','Accessibility accommodations','Institutional navigation / advocacy','Financial assistance resources','Educational support','Digital support','Language support','Community integration','Housing resources','Other']
STATUSES = ['Initial contact','Assessment pending','Assessment completed','Awaiting referral','Active accompaniment','Referred externally','Follow-up','On hold','Completed','Withdrawn']
CONSENT = ['Pending','Granted','Declined','Withdrawn']
CONTACT = ['No contact authorized','In person only','Email','Phone call','SMS','Other agreed method']
SERVICE_STATUS = ['Requested','In progress','Referred','Completed','Declined','Cancelled']
ENGAGEMENT = ['Not specified','Community engagement','Cultural interest','Shared learning','Volunteering','Professional collaboration','Other']

def init(store):
    with store.db:
        store.db.execute('CREATE TABLE IF NOT EXISTS support_cases(id INTEGER PRIMARY KEY AUTOINCREMENT, person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE, payload BLOB NOT NULL)')

def case_id(i): return f'DIDAR-CASE-{i:06d}'

def records(store, person=None):
    sql='SELECT id,person_id,payload FROM support_cases'
    args=() if person is None else (person,)
    if person is not None: sql+=' WHERE person_id=?'
    return [(i,p,store.dec(d)) for i,p,d in store.db.execute(sql+' ORDER BY id',args)]

def day(value, required=False):
    if not value and not required: return
    if not isinstance(value,str) or date.fromisoformat(value).isoformat()!=value: raise ValueError('Dates must use YYYY-MM-DD.')

def blank():
    return {'Opened':date.today().isoformat(),'Closed':'','Status':'Initial contact','Committee ID':None,'Coordinator ID':None,'Referral source':'','Consent':'Pending','Consent date':'','Sharing consent':'Pending','Sharing scope':'','Safe contact':'No contact authorized','Voicemail allowed':False,'Contact instructions':'','Follow-up date':'','Next action':'','Circumstances':[],'Needs':[],'Notes':'','Services':[],'History':[]}

SENSITIVE = ('Circumstances','Needs','Notes','Services','History','Contact instructions','Sharing scope','Next action','Referral source')

def save(store, person, data, i=None):
    old=next((r for r in records(store,person) if r[0]==i),None) if i is not None else None
    if i is not None and old is None: raise ValueError('Case not found for this person.')
    if not store.db.execute('SELECT 1 FROM people WHERE id=?',(person,)).fetchone(): raise ValueError('Select an existing person.')
    d=blank(); d.update(data)
    if d['Status'] not in STATUSES or d['Consent'] not in CONSENT or d['Sharing consent'] not in CONSENT or d['Safe contact'] not in CONTACT: raise ValueError('Invalid status or permission.')
    for k in ('Opened','Closed','Consent date','Follow-up date'): day(d[k],k=='Opened' or (k=='Consent date' and d['Consent']!='Pending'))
    if d['Closed'] and d['Closed']<d['Opened']: raise ValueError('Closing date precedes opening date.')
    if d['Status'] in ('Completed','Withdrawn') and not d['Closed']: raise ValueError('Enter a closing date.')
    if d['Status'] not in ('Completed','Withdrawn') and d['Closed']: raise ValueError('Clear closing date for an open case.')
    for field,table in [('Committee ID','committees'),('Coordinator ID','people')]:
        if d[field] is not None and not store.db.execute('SELECT 1 FROM '+table+' WHERE id=?',(d[field],)).fetchone(): raise ValueError('Selected committee or coordinator no longer exists.')
    if not set(d['Circumstances'])<=set(sum(CIRCUMSTANCES.values(),[])) or not set(d['Needs'])<=set(NEEDS): raise ValueError('Unknown category.')
    if any(x in d['Circumstances'] for x in ('Prefers not to disclose','Not yet assessed')) and len(d['Circumstances'])>1: raise ValueError('Select only the non-disclosure / not assessed option, or actual circumstances.')
    if d['Consent']!='Granted':
        previous=old[2] if old else blank()
        # Allow withdrawal and clearing existing sensitive information, but not adding or changing it.
        for k in SENSITIVE:
            if d[k] and d[k]!=previous.get(k): raise ValueError('Record consent before adding or changing sensitive information. Existing information can be cleared.')
        if d['Sharing consent']=='Granted' or d['Safe contact']!='No contact authorized' or d['Voicemail allowed']: raise ValueError('Without granted consent, revoke sharing and contact permissions.')
    if d['Sharing consent']=='Granted' and not d['Sharing scope'].strip(): raise ValueError('Specify authorized recipient, purpose and information scope.')
    if d['Voicemail allowed'] and d['Safe contact']!='Phone call': raise ValueError('Voicemail requires phone call permission.')
    for s in d['Services']:
        if s['Need'] not in NEEDS or s['Status'] not in SERVICE_STATUS: raise ValueError('Invalid service entry.')
        day(s['Date'],True)
    for h in d['History']: day(h['Date'],True)
    with store.db:
        if i is None: i=store.db.execute('INSERT INTO support_cases(person_id,payload) VALUES (?,?)',(person,store.enc(d))).lastrowid
        else: store.db.execute('UPDATE support_cases SET payload=? WHERE id=? AND person_id=?',(store.enc(d),i,person))
    return i

def delete(store,i):
    with store.db: store.db.execute('DELETE FROM support_cases WHERE id=?',(i,))

def private_summary(store):
    # No circumstance or committee breakdowns, no export. Small counts suppressed.
    rows=records(store); active=[r for r in rows if r[2]['Status'] not in ('Completed','Withdrawn')]
    def safe(n): return str(n) if n==0 or n>=5 else 'Suppressed (1–4)'
    return {'All cases':safe(len(rows)),'Open cases':safe(len(active)),'Unique people with cases':safe(len({p for _,p,_ in rows}))}
