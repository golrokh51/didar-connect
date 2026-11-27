"""Headless storage tests; no real records or Qt required."""
import ast, pathlib, tempfile, sqlite3, os, json, base64
from contextlib import closing
from pathlib import Path
from datetime import date
import resource_directory as rd
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
with tempfile.TemporaryDirectory() as temp:
 p=pathlib.Path(temp)/'test.sqlite'; old=Store
 db=old(p,'dummy-password-123'); person=db.save({'First name':'Test','Last name':'Contact','Roles':['Other']}); db.db.executescript('DROP TABLE partner_interactions; DROP TABLE partner_referrals; DROP TABLE partner_contacts; DROP TABLE partners;'); db.db.close()
 db=Store(p,'dummy-password-123'); org=db.save_record('partners',[],{'Name':'Dummy University'}); contact=db.save_record('partner_contacts',[org,person],{'Role':'Professor'}); ref=db.save_record('partner_referrals',[org,person],{'Date':'2026-11-26','Direction':'Incoming'}); interaction=db.save_record('partner_interactions',[org],{'Date':'2026-11-26','Subject':'Dummy meeting'}); assert 'Partner contact' in dict(db.people())[person]['Roles']
 for kind,links,data in [('partners',[],{'Name':'dummy university'}),('partner_contacts',[org,person],{}),('partner_referrals',[org,person],{'Date':'bad'})]:
  try: db.save_record(kind,links,data); raise AssertionError('invalid accepted')
  except ValueError: pass
 db.backup(pathlib.Path(temp)/'copy.sqlite'); copy=Store(pathlib.Path(temp)/'copy.sqlite','dummy-password-123'); assert copy.records('partner_referrals')==db.records('partner_referrals'); copy.db.close(); db.delete(person); assert not db.records('partner_contacts') and not db.records('partner_referrals') and db.records('partners') and db.records('partner_interactions'); db.db.close()
print('PASS: partner schema migration, contacts, referrals, interactions, validation, backup and cascade deletion')
with tempfile.TemporaryDirectory() as temp:
 p=pathlib.Path(temp)/'test.sqlite'; db=Store(p,'dummy-password-123'); person=db.save({'First name':'Private dummy','Last name':'Person'}); db.db.execute('DROP TABLE resources'); db.db.commit(); db.db.close(); db=Store(p,'dummy-password-123'); assert db.people()[0][0]==person
 d={'Name':'Dummy service','Category':'Housing','International students':'Yes','Status':'Active','Last verified':'2026-11-26','Publish':'Yes','Internal notes':'SECRET DUMMY'}; i=db.save_resource(d); assert db.resources()[0][0]==i
 try: db.save_resource(d); raise AssertionError('duplicate accepted')
 except ValueError: pass
 assert db.import_resources([d,{'Name':'Other service','Category':'Legal','Publish':'Yes'}])==(1,1)
 assert db.resources()[1][1]['Publish']=='No'
 from openpyxl import Workbook
 w=Workbook(); w.active.append(['Name','Category']); w.active.append(['Excel service','Language']); x=pathlib.Path(temp)/'sample.xlsx'; w.save(x); assert db.import_resources(rd.read_rows(x))==(1,0)
 c=pathlib.Path(temp)/'sample.csv'; c.write_text('Name,Category\nCSV service,Education\n'); assert db.import_resources(rd.read_rows(c))==(1,0)
 out=pathlib.Path(temp)/'public.json'; assert rd.export_public(out,db.resources())==1; assert 'SECRET DUMMY' not in out.read_text() and 'Private dummy' not in out.read_text()
 db.backup(pathlib.Path(temp)/'backup.sqlite'); copy=Store(pathlib.Path(temp)/'backup.sqlite','dummy-password-123'); assert copy.resources()==db.resources(); copy.db.close(); db.db.close()
print('PASS: resource migration, duplicate guard, CSV/XLSX import, publication defaults, public export isolation and backup')

# V0.9: aggregation semantics, scope, export isolation and no writes.
import impact_reports as ir
with tempfile.TemporaryDirectory() as temp:
 p=pathlib.Path(temp)/'test.sqlite'; db=Store(p,'dummy-password-123')
 student=db.save({'First name':'SECRET STUDENT','Last name':'Private','Email':'private@example.test','Roles':['International student'],'Referral date':'2026-11-26','Selected needs':['Peer mentorship','SECRET NEED'],'Status':'Active accompaniment'})
 mentor=db.save({'First name':'SECRET MENTOR','Roles':['Volunteer','Peer mentor']}); other=db.save({'Roles':['Participant']})
 c=db.save_record('committees',[],{'Name':'SECRET COMMITTEE'}); c2=db.save_record('committees',[],{'Name':'Other committee'}); pr=db.save_record('programs',[c],{'Name':'SECRET PROGRAM'}); pr2=db.save_record('programs',[c2],{'Name':'Other program'})
 for program,day,status,cost,persons in [(pr,'2026-11-26','Completed','10.50',[(student,'Participant'),(mentor,'Volunteer')]),(pr,'2026-11-27','Completed','5.25',[(student,'Participant')]),(pr2,'2026-11-27','Completed','4',[(other,'Participant')]),(None,'2026-11-27','Cancelled','99',[(other,'Participant')]),(pr,'2026-12-01','Completed','100',[(other,'Participant')])]:
  a=db.save_activity(program,{'Name':'SECRET ACTIVITY','Date':day,'Status':status,'Expenses (CAD)':cost})
  for person,role in persons: db.save_attendance(a,person,{'Status':'Attended','Role':role})
 db.save_record('registrations',[pr,student],{'Role':'Participant','Status':'Active','Start date':'2026-11-26'}); db.log(student,{'date':'2026-11-26','type':'Video call','note':'SECRET NOTE'}); db.save_hours(mentor,{'date':'2026-11-27','hours':2.5}); org=db.save_record('partners',[],{'Name':'SECRET ORG'}); db.save_record('partner_referrals',[org,student],{'Date':'2026-11-26','Direction':'Incoming'})
 before=db.db.total_changes; r=ir.build_report(db,'2026-11-26','2026-11-27'); vals={(s,m):v for s,m,v in r['rows']}
 assert vals['Attendance','Unique participant attendees']==2 and vals['Attendance','Attended records at completed activities']==4 and vals['Attendance','Unique attendees (all roles)']==3
 assert vals['Expenses','Recorded completed-activity expenses (CAD)']==19.75 and vals['Volunteer contribution','Logged volunteer hours']==2.5 and vals['Reach','Unique participant attendees or contacted students']==2
 assert vals['Identified needs','Peer mentorship']==1 and vals['Institutional referrals','Incoming']==1 and vals['Programs','Registrations started in period (all roles/statuses)']==1
 scoped=ir.build_report(db,'2026-11-26','2026-11-27',c); sv={(s,m):v for s,m,v in scoped['rows']}; assert sv['Attendance','Unique participant attendees']==1 and sv['Expenses','Recorded completed-activity expenses (CAD)']==15.75; assert not any(s in ('Current registry','Student cohort','Volunteer contribution','Institutional referrals') for s,m,v in scoped['rows'])
 assert db.db.total_changes==before and 'SECRET' not in str(r) and 'private@example.test' not in str(r)
 for start,end in [('2026-12-01','2026-11-01'),('invalid','')]:
  try: ir.build_report(db,start,end); raise AssertionError('bad date range accepted')
  except ValueError: pass
 x=pathlib.Path(temp)/'report.xlsx'; pdf=pathlib.Path(temp)/'report.pdf'; ir.export_excel(x,r); ir.export_pdf(pdf,r)
 from openpyxl import load_workbook
 w=load_workbook(x,read_only=True); assert w.sheetnames==['Impact statistics','Definitions']; assert not any('SECRET' in str(v) or 'private@example.test' in str(v) for sheet in w for row in sheet.values for v in row); w.close(); assert pdf.read_bytes().startswith(b'%PDF-'); db.db.close()
print('PASS: impact reports, date range, committee scope, deduplication, expenses, read-only aggregation and Excel/PDF export')

# V1.0: stable location, daily snapshot, authenticated restore and rollback safety.
import storage_tools as st
with tempfile.TemporaryDirectory() as temp:
 folder=pathlib.Path(temp).resolve(); legacy=folder/'Library/Application Support/DIDAR Connect'; qt=folder/'alternate'; legacy.mkdir(parents=True); qt.mkdir()
 assert st.data_folder(qt,folder,'darwin')==legacy
 assert st.data_folder(qt,folder,'darwin',qt)==qt
 # macOS temporary paths may contain symlink aliases (e.g. /var -> /private/var).
 if os.name != 'nt':
  alias=folder/'qt-alias'; alias.symlink_to(qt,target_is_directory=True)
  assert st.data_folder(alias,folder,'darwin',alias)==qt
  assert st.data_folder(alias,folder,'darwin')==legacy
 (qt/'didar.sqlite').touch(); assert st.data_folder(qt,folder,'darwin')==qt
 if os.name != 'nt':
  assert st.data_folder(alias,folder,'darwin')==qt
 (legacy/'didar.sqlite').touch()
 try: st.data_folder(qt,folder,'darwin'); raise AssertionError('ambiguous path accepted')
 except ValueError: pass
 (legacy/'didar.sqlite').unlink(); (qt/'didar.sqlite').unlink()
 db=Store(folder/'didar.sqlite','dummy-password-123'); person=db.save({'First name':'Before','Last name':'Dummy'}); snap=st.daily_backup(db,folder); assert snap.exists() and st.daily_backup(db,folder) is None
 db.save({'First name':'After','Last name':'Dummy'},person); manual=st.create_backup(db,folder); assert manual.exists()
 safety=st.restore_backup(db,folder,snap); assert dict(db.people())[person]['First name']=='Before'; saved=Store(safety,'dummy-password-123'); assert dict(saved.people())[person]['First name']=='After'; saved.db.close()
 other=Store(folder/'other.sqlite','dummy-password-123'); other.db.close()
 import shutil
 corrupt=folder/'corrupt.sqlite'; shutil.copyfile(snap,corrupt)
 with sqlite3.connect(corrupt) as c: c.execute('UPDATE people SET payload=?',(b'bad-token',))
 old=folder/'old.sqlite'; shutil.copyfile(snap,old)
 with sqlite3.connect(old) as c: c.execute('DROP TABLE resources')
 for invalid in [folder/'didar.sqlite',folder/'other.sqlite',corrupt,old]:
  try: st.restore_backup(db,folder,invalid); raise AssertionError('invalid restore accepted')
  except (ValueError,InvalidToken): pass
 assert dict(db.people())[person]['First name']=='Before'; assert len(st.backups(folder))==3
 before=(folder/'didar.sqlite').read_bytes()
 try: Store(folder/'didar.sqlite','incorrect'); raise AssertionError('wrong passphrase accepted')
 except InvalidToken: pass
 assert (folder/'didar.sqlite').read_bytes()==before
 invalid_file=folder/'empty.sqlite'; invalid_file.touch()
 try: Store(invalid_file,'dummy-password-123'); raise AssertionError('uninitialized file accepted')
 except sqlite3.Error: pass
 db.db.close()
print('PASS: data path, daily backup, authenticated restore, pre-restore safety snapshot and invalid backup rejection')
