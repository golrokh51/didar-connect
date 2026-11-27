"""Headless storage tests; no real records or Qt required."""
import ast, pathlib, tempfile, sqlite3, os, json, base64
from datetime import date
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

def load_store(path):
 tree=ast.parse(pathlib.Path(path).read_text()); selected=[n for n in tree.body if (isinstance(n,ast.ClassDef) and n.name=='Store') or (isinstance(n,ast.FunctionDef) and n.name=='roles')]; ns=globals().copy(); exec(compile(ast.Module(body=selected,type_ignores=[]),path,'exec'),ns); return ns['Store']
Store=load_store('main.py')
with tempfile.TemporaryDirectory() as temp:
 p=pathlib.Path(temp)/'test.sqlite'; old=Store(p,'dummy-password-123'); student=old.save({'First name':'Test','Last name':'Student','Selected needs':['Long-term housing'],'Consent':'Granted'}); old.log(student,{'note':'test note'}); old.db.executescript('DROP TABLE assignments; DROP TABLE volunteer_hours;'); old.db.close()
 db=Store(p,'dummy-password-123'); assert db.people()[0][1]['Selected needs']==['Long-term housing']; assert db.history(student)[0]['note']=='test note'; mentor=db.save({'First name':'Test','Last name':'Mentor','Roles':['Volunteer','Peer mentor']}); a=db.assign(mentor,student,{'status':'Active','notes':'private note'}); assert db.assignments()[0][0]==a
 try: db.assign(mentor,student,{'status':'Active'}); raise AssertionError('duplicate allowed')
 except ValueError: pass
 h=db.save_hours(mentor,{'date':'2026-11-26','hours':1.5,'notes':'private activity'}); db.save_hours(mentor,{'date':'2026-11-26','hours':2,'notes':'updated'},h); assert db.hours(mentor)[0][1]['hours']==2
 db.backup(pathlib.Path(temp)/'backup.sqlite'); backup=Store(pathlib.Path(temp)/'backup.sqlite','dummy-password-123'); assert backup.assignments()==db.assignments(); assert backup.hours(mentor)==db.hours(mentor); backup.db.close(); db.delete(mentor); assert not db.assignments() and not db.hours(mentor); db.db.close()
print('PASS: old schema upgrade, needs/history retention, assignment duplicate guard, hours editing, backup, cascade deletion')
with tempfile.TemporaryDirectory() as temp:
 p=pathlib.Path(temp)/'test.sqlite'; db=Store(p,'dummy-password-123'); person=db.save({'First name':'Dummy','Last name':'Person','Roles':['International student'],'Selected needs':['Peer mentorship']}); db.db.executescript('DROP TABLE registrations; DROP TABLE memberships; DROP TABLE programs; DROP TABLE committees;'); db.db.close()
 db=Store(p,'dummy-password-123'); c=db.save_record('committees',[],{'Name':'Test committee','Status':'Active'}); pr=db.save_record('programs',[c],{'Name':'Test program','Status':'Active'}); m=db.save_record('memberships',[c,person],{'Role':'Coordinator','Status':'Active'}); r=db.save_record('registrations',[pr,person],{'Role':'Participant','Status':'Pending'}); assert set(dict(db.people())[person]['Roles'])=={'International student','Committee member','Participant'}; assert dict(db.people())[person]['Selected needs']==['Peer mentorship']; assert db.records('programs')[0][1]==c
 for kind,links,data in [('memberships',[c,person],{'Role':'Member'}),('committees',[],{'Name':'test committee'}),('programs',[c],{'Name':'Another','Start date':'2027-01-01','End date':'2026-01-01'})]:
  try: db.save_record(kind,links,data); raise AssertionError('invalid record accepted')
  except ValueError: pass
 db.save_record('registrations',[pr,person],{'Role':'Participant','Status':'Completed'},r); assert db.records('registrations')[0][-1]['Status']=='Completed'; db.backup(pathlib.Path(temp)/'copy.sqlite'); copy=Store(pathlib.Path(temp)/'copy.sqlite','dummy-password-123'); assert copy.records('memberships')==db.records('memberships'); copy.db.close(); db.delete(person); assert not db.records('memberships') and not db.records('registrations'); assert db.records('programs'); db.db.close()
print('PASS: v0.4 schema upgrade, organization links, role propagation, duplicate/date validation, registration editing, backup, cascade deletion')
with tempfile.TemporaryDirectory() as temp:
 p=pathlib.Path(temp)/'test.sqlite'; db=Store(p,'dummy-password-123'); person=db.save({'First name':'Dummy','Last name':'Person'}); c=db.save_record('committees',[],{'Name':'Committee'}); pr=db.save_record('programs',[c],{'Name':'Program'}); db.db.executescript('DROP TABLE attendance; DROP TABLE activities;'); db.db.close()
 db=Store(p,'dummy-password-123'); assert db.records('programs')[0][0]==pr
 a=db.save_activity(pr,{'Name':'Workshop','Date':'2026-11-26'}); b=db.save_activity(None,{'Name':'Independent event','Date':'2026-11-27'}); att=db.save_attendance(a,person,{'Status':'Registered'}); db.save_attendance(a,person,{'Status':'Attended'},att); assert db.records('attendance')[0][-1]['Status']=='Attended'
 try: db.save_attendance(a,person,{'Status':'Attended'}); raise AssertionError('duplicate allowed')
 except ValueError: pass
 try: db.save_activity(None,{'Name':'Invalid','Date':'bad'}); raise AssertionError('invalid date accepted')
 except ValueError: pass
 db.backup(pathlib.Path(temp)/'copy.sqlite'); copy=Store(pathlib.Path(temp)/'copy.sqlite','dummy-password-123'); assert copy.records('attendance')==db.records('attendance'); copy.db.close(); db.delete(person); assert not db.records('attendance') and len(db.records('activities'))==2; db.db.close()
print('PASS: v0.5 migration, optional program, attendance editing, duplicate guard, date validation, backup and cascade deletion')
