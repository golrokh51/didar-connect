import sys, json, sqlite3, os
from pathlib import Path
from datetime import date
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QComboBox,QTextEdit,QPushButton,QLabel,QTableWidget,QTableWidgetItem,QTabWidget,QMessageBox,QDialog,QDialogButtonBox,QAbstractItemView,QHeaderView,QInputDialog,QCheckBox,QScrollArea,QDoubleSpinBox)
from PySide6.QtCore import Qt,QStandardPaths
from cryptography.fernet import Fernet,InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
import base64

FIELDS=['First name','Last name','Email','Phone','Country of origin (optional)','Preferred language','University','Department','Program','Academic level','Supervisor','Referral source','Referrer name','Referrer email','Referral date','Expected arrival','Consent','Status','Assigned mentor','Next action','Follow-up date','Needs / notes']
NEEDS_GROUPS={
 'Pre-arrival & settlement':['Pre-arrival preparation','Temporary accommodation','Long-term housing','Airport arrival and transportation'],
 'Administrative & essential services':['University registration','Administrative procedures','Health insurance and healthcare','Banking and mobile phone services'],
 'Language & practical support':['French language support','English language support','Digital and technological support','Financial resources'],
 'Integration & mentorship':['Social and cultural integration','Peer mentorship','Academic integration','Community activities','Referral to specialized services']}
ROLES=['International student','Newcomer','Volunteer','Peer mentor','Committee member','Participant','Staff / coordinator','Partner contact','Other']
def roles(data):
 return data.get('Roles',['International student'])
def person_id(i): return f'DIDAR-P-{i:06d}'
def student_id(i): return f'DIDAR-IS-{i:06d}'
STATUSES=['Initial contact','Consultation scheduled','Needs assessment','Awaiting mentor','Active accompaniment','Completed','Withdrawn']
class Store:
 def __init__(self,path,password):
  self.db=sqlite3.connect(path); self.db.execute('PRAGMA foreign_keys=ON')
  self.db.executescript('CREATE TABLE IF NOT EXISTS config(k TEXT PRIMARY KEY,v BLOB); CREATE TABLE IF NOT EXISTS people(id INTEGER PRIMARY KEY AUTOINCREMENT,payload BLOB NOT NULL); CREATE TABLE IF NOT EXISTS interactions(id INTEGER PRIMARY KEY AUTOINCREMENT,person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,payload BLOB NOT NULL);')
  row=self.db.execute("SELECT v FROM config WHERE k='salt'").fetchone(); salt=row[0] if row else os.urandom(16)
  self.key=Fernet(base64.urlsafe_b64encode(Scrypt(salt=salt,length=32,n=2**15,r=8,p=1).derive(password.encode())))
  if row: self.key.decrypt(self.db.execute("SELECT v FROM config WHERE k='check'").fetchone()[0])
  else:
   self.db.executemany('INSERT INTO config VALUES (?,?)',[('salt',salt),('check',self.key.encrypt(b'DIDAR'))]); self.db.commit()
  self.db.executescript("CREATE TABLE IF NOT EXISTS assignments(id INTEGER PRIMARY KEY AUTOINCREMENT, mentor_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE, student_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE, payload BLOB NOT NULL); CREATE TABLE IF NOT EXISTS volunteer_hours(id INTEGER PRIMARY KEY AUTOINCREMENT, person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE, payload BLOB NOT NULL);")
  self.db.executescript("CREATE TABLE IF NOT EXISTS committees(id INTEGER PRIMARY KEY AUTOINCREMENT,payload BLOB NOT NULL); CREATE TABLE IF NOT EXISTS programs(id INTEGER PRIMARY KEY AUTOINCREMENT,committee_id INTEGER NOT NULL REFERENCES committees(id),payload BLOB NOT NULL); CREATE TABLE IF NOT EXISTS memberships(id INTEGER PRIMARY KEY AUTOINCREMENT,committee_id INTEGER NOT NULL REFERENCES committees(id),person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,payload BLOB NOT NULL,UNIQUE(committee_id,person_id)); CREATE TABLE IF NOT EXISTS registrations(id INTEGER PRIMARY KEY AUTOINCREMENT,program_id INTEGER NOT NULL REFERENCES programs(id),person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,payload BLOB NOT NULL,UNIQUE(program_id,person_id));")
 def records(self,kind):
  columns={'committees':'id,payload','programs':'id,committee_id,payload','memberships':'id,committee_id,person_id,payload','registrations':'id,program_id,person_id,payload'}
  return [(*r[:-1],self.dec(r[-1])) for r in self.db.execute('SELECT '+columns[kind]+' FROM '+kind+' ORDER BY id')]
 def save_record(self,kind,links,data,i=None):
  cols={'committees':(), 'programs':('committee_id',), 'memberships':('committee_id','person_id'), 'registrations':('program_id','person_id')}[kind]
  if len(links)!=len(cols): raise ValueError('Invalid relationships.')
  if kind in ('committees','programs'):
   if not data.get('Name','').strip(): raise ValueError('Name is required.')
   if any(r[0]!=i and r[-1].get('Name','').strip().casefold()==data['Name'].strip().casefold() and (kind=='committees' or r[1]==links[0]) for r in self.records(kind)): raise ValueError('A record with this name already exists.')
  for field in ('Start date','End date'):
   if data.get(field): date.fromisoformat(data[field])
  if data.get('Start date') and data.get('End date') and data['End date']<data['Start date']: raise ValueError('End date precedes start date.')
  if kind in ('memberships','registrations') and any(r[0]!=i and tuple(r[1:-1])==tuple(links) for r in self.records(kind)): raise ValueError('This person already has a record here; edit the existing record.')
  with self.db:
   if i is None:
    fields=cols+('payload',); i=self.db.execute('INSERT INTO '+kind+'('+','.join(fields)+') VALUES ('+','.join('?' for _ in fields)+')',(*links,self.enc(data))).lastrowid
   else:
    self.db.execute('UPDATE '+kind+' SET '+','.join(c+'=?' for c in cols+('payload',))+' WHERE id=?',(*links,self.enc(data),i))
   if kind in ('memberships','registrations'):
    person=dict(self.people())[links[1]]; role='Committee member' if kind=='memberships' else 'Volunteer' if data.get('Role')=='Volunteer' else 'Participant' if data.get('Role')=='Participant' else None
    if role and role not in roles(person):
     person['Roles']=roles(person)+[role]; self.db.execute('UPDATE people SET payload=? WHERE id=?',(self.enc(person),links[1]))
  return i
 def assignments(self):
  return [(i,m,t,self.dec(p)) for i,m,t,p in self.db.execute('SELECT id,mentor_id,student_id,payload FROM assignments ORDER BY id')]
 def assign(self,m,t,d,i=None):
  people=dict(self.people())
  if m==t or (d['status'] in ('Proposed','Active') and ('Peer mentor' not in roles(people[m]) or 'International student' not in roles(people[t]))): raise ValueError('Select a different eligible mentor and student.')
  if d['status']=='Active' and any(j!=i and mm==m and tt==t and a['status']=='Active' for j,mm,tt,a in self.assignments()): raise ValueError('This pair already has an active assignment.')
  if i is None: i=self.db.execute('INSERT INTO assignments(mentor_id,student_id,payload) VALUES (?,?,?)',(m,t,self.enc(d))).lastrowid
  else: self.db.execute('UPDATE assignments SET payload=? WHERE id=?',(self.enc(d),i))
  self.db.commit(); return i
 def hours(self,i):
  return [(j,self.dec(p)) for j,p in self.db.execute('SELECT id,payload FROM volunteer_hours WHERE person_id=? ORDER BY id DESC',(i,))]
 def save_hours(self,i,d,j=None):
  date.fromisoformat(d['date'])
  if not 0<d['hours']<=24: raise ValueError('Hours must be greater than zero and at most 24.')
  if j is None: j=self.db.execute('INSERT INTO volunteer_hours(person_id,payload) VALUES (?,?)',(i,self.enc(d))).lastrowid
  else: self.db.execute('UPDATE volunteer_hours SET payload=? WHERE id=? AND person_id=?',(self.enc(d),j,i))
  self.db.commit(); return j
 def enc(self,d): return self.key.encrypt(json.dumps(d,ensure_ascii=False).encode())
 def dec(self,d): return json.loads(self.key.decrypt(d))
 def people(self): return [(i,self.dec(p)) for i,p in self.db.execute('SELECT id,payload FROM people ORDER BY id')]
 def save(self,d,i=None):
  if i is None: i=self.db.execute('INSERT INTO people(payload) VALUES (?)',(self.enc(d),)).lastrowid
  else: self.db.execute('UPDATE people SET payload=? WHERE id=?',(self.enc(d),i))
  self.db.commit(); return i
 def log(self,i,d): self.db.execute('INSERT INTO interactions(person_id,payload) VALUES (?,?)',(i,self.enc(d))); self.db.commit()
 def history(self,i): return [self.dec(p) for (p,) in self.db.execute('SELECT payload FROM interactions WHERE person_id=? ORDER BY id DESC',(i,))]
 def delete(self,i): self.db.execute('DELETE FROM people WHERE id=?',(i,)); self.db.commit(); self.db.execute('VACUUM')
 def backup(self,path):
  with sqlite3.connect(path) as dest: self.db.backup(dest)

class Editor(QDialog):
 def __init__(self,parent,data):
  super().__init__(parent); self.setWindowTitle('Student profile'); self.resize(720,700); layout=QVBoxLayout(self); tabs=QTabWidget(); layout.addWidget(tabs); self.inputs={}
  for name,fields in [('Personal',FIELDS[:6]),('Academic',FIELDS[6:11]),('Referral',FIELDS[11:16]),('Accompaniment',FIELDS[16:])]:
   page=QWidget(); form=QFormLayout(page); tabs.addTab(page,name)
   for f in fields:
    if f in ('Status','Consent'):
     w=QComboBox(); w.addItems(STATUSES if f=='Status' else ['Pending','Granted','Declined','Withdrawn']); w.setCurrentText(data.get(f,'Initial contact' if f=='Status' else 'Pending'))
    elif f=='Needs / notes': w=QTextEdit(); w.setPlainText(data.get(f,''))
    else: w=QLineEdit(data.get(f,'')); w.setPlaceholderText('YYYY-MM-DD' if f in ('Referral date','Follow-up date') else '')
    self.inputs[f]=w; form.addRow('Assigned mentor (legacy note; see Mentor assignments)' if f=='Assigned mentor' else f,w)
  self.original=data.copy(); self.needs={}
  page=QWidget(); layout_needs=QVBoxLayout(page); scroll=QScrollArea(); scroll.setWidgetResizable(True); content=QWidget(); checks=QVBoxLayout(content)
  for group,items in NEEDS_GROUPS.items():
   heading=QLabel(group); heading.setStyleSheet('font-weight:bold;color:#397a84;'); checks.addWidget(heading)
   for item in items:
    cb=QCheckBox(item); cb.setChecked(item in data.get('Selected needs',[])); checks.addWidget(cb); self.needs[item]=cb
  checks.addStretch(); scroll.setWidget(content); layout_needs.addWidget(scroll); tabs.addTab(page,'Needs Assessment')
  b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); b.accepted.connect(self.validate); b.rejected.connect(self.reject); layout.addWidget(b)
 def values(self):
  result=self.original.copy(); result.update({f:(w.currentText() if isinstance(w,QComboBox) else w.toPlainText() if isinstance(w,QTextEdit) else w.text().strip()) for f,w in self.inputs.items()}); result['Selected needs']=[item for item,cb in self.needs.items() if cb.isChecked()]; result['Roles']=list(dict.fromkeys(roles(result)+['International student'])); return result
 def validate(self):
  d=self.values()
  if not d['First name'] or not d['Last name']: QMessageBox.warning(self,'Missing information','Enter first and last name.'); return
  for f in ('Referral date','Follow-up date'):
   if d[f]:
    try: date.fromisoformat(d[f])
    except ValueError: QMessageBox.warning(self,'Invalid date',f+' must be YYYY-MM-DD.'); return
  self.accept()

class PersonEditor(QDialog):
 def __init__(self,parent,data):
  super().__init__(parent); self.original=data.copy(); self.setWindowTitle('Central person profile'); self.resize(600,650); layout=QVBoxLayout(self); form=QFormLayout(); layout.addLayout(form); self.inputs={}
  for f in FIELDS[:6]+['Organization / affiliation','Personal notes']:
   w=QTextEdit() if f=='Personal notes' else QLineEdit(); (w.setPlainText if isinstance(w,QTextEdit) else w.setText)(data.get(f,'')); self.inputs[f]=w; form.addRow(f,w)
  layout.addWidget(QLabel('Roles — select all that apply')); self.checks={}
  for role in ROLES:
   cb=QCheckBox(role); cb.setChecked(role in roles(data)); self.checks[role]=cb; layout.addWidget(cb)
   if role=='International student' and role in roles(data): cb.setEnabled(False); cb.setToolTip('Existing student case is retained. Close it in the student module when appropriate.')
  buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); buttons.accepted.connect(self.validate); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
 def values(self):
  d=self.original.copy(); d.update({f:w.toPlainText() if isinstance(w,QTextEdit) else w.text().strip() for f,w in self.inputs.items()}); d['Roles']=[r for r,w in self.checks.items() if w.isChecked()]; return d
 def validate(self):
  d=self.values()
  if not d['First name'] or not d['Last name'] or not d['Roles']: QMessageBox.warning(self,'Missing information','Enter first and last name and select at least one role.'); return
  self.accept()

def full_name(d): return (d.get('First name','')+' '+d.get('Last name','')).strip()
def is_helper(d): return bool(set(roles(d)) & {'Volunteer','Peer mentor'})
class HelperEditor(QDialog):
 def __init__(self,parent,data):
  super().__init__(parent); self.setWindowTitle('Volunteer / mentor profile'); self.resize(620,650); self.original=data.copy(); form=QFormLayout(self); self.inputs={}
  for f in FIELDS[:6]+['Organization / affiliation','Department','Program','Languages spoken','Skills / expertise','Availability','Support areas','Maximum active students','Volunteer status','Confidentiality agreement','Personal notes']:
   if f in ('Volunteer status','Confidentiality agreement'):
    w=QComboBox(); w.addItems(['Pending','Active','Unavailable','Inactive'] if f=='Volunteer status' else ['Pending','Signed','Declined']); w.setCurrentText(data.get(f,'Pending'))
   elif f in ('Skills / expertise','Availability','Support areas','Personal notes'):
    w=QTextEdit(); w.setPlainText(data.get(f,'')); w.setMaximumHeight(65)
   else: w=QLineEdit(data.get(f,''))
   self.inputs[f]=w; form.addRow(f,w)
  self.checks={}
  for r in ['Volunteer','Peer mentor']:
   cb=QCheckBox(r); cb.setChecked(r in roles(data)); self.checks[r]=cb; form.addRow(cb)
  b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); form.addRow(b); b.accepted.connect(self.validate); b.rejected.connect(self.reject)
 def values(self):
  d=self.original.copy(); d.update({f:w.currentText() if isinstance(w,QComboBox) else w.toPlainText() if isinstance(w,QTextEdit) else w.text().strip() for f,w in self.inputs.items()}); d['Roles']=[r for r in roles(d) if r not in self.checks]+[r for r,c in self.checks.items() if c.isChecked()]; return d
 def validate(self):
  d=self.values(); cap=d['Maximum active students']
  if not d['First name'] or not d['Last name'] or not is_helper(d) or (cap and (not cap.isdigit() or int(cap)<1)):
   QMessageBox.warning(self,'Check profile','Enter names, at least one helper role, and a positive whole-number capacity or leave capacity blank.'); return
  self.accept()
class Window(QMainWindow):
 def __init__(self,store,folder):
  super().__init__(); self.store=store; self.folder=folder; self.mode='people'; self.setWindowTitle('DIDAR Connect — v0.5'); self.resize(1250,750)
  root=QWidget(); self.setCentralWidget(root); outer=QHBoxLayout(root); side=QVBoxLayout(); outer.addLayout(side); brand=QLabel('DIDAR\nCONNECT'); brand.setObjectName('brand'); side.addWidget(brand)
  for name,mode in [('People registry','people'),('International students','students'),('Volunteers & mentors','helpers')]:
   b=QPushButton(name); b.clicked.connect(lambda checked=False,m=mode:self.switch(m)); side.addWidget(b)
  self.helper_buttons=[]
  for label,fn in [('Add helper role to selected person',self.helper_role),('Mentor assignments',self.assignment_dialog),('Volunteer hours',self.hours_dialog)]:
   b=QPushButton(label); b.clicked.connect(fn); side.addWidget(b); self.helper_buttons.append(b)
  for label,kind in [('Committees','committees'),('Committee memberships','memberships'),('Programs','programs'),('Program registrations / team','registrations')]:
   b=QPushButton(label); b.clicked.connect(lambda checked=False,k=kind:self.organization_dialog(k)); side.addWidget(b)
  storage=QPushButton('Database location'); storage.clicked.connect(lambda:QMessageBox.information(self,'Database location',str(self.folder/'didar.sqlite'))); side.addWidget(storage)
  side.addStretch(); backup=QPushButton('Create database backup'); backup.clicked.connect(self.backup); side.addWidget(backup)
  main=QVBoxLayout(); outer.addLayout(main,1); self.title=QLabel(); self.title.setObjectName('title'); main.addWidget(self.title); self.stats=QLabel(); main.addWidget(self.stats); bar=QHBoxLayout(); main.addLayout(bar); self.search=QLineEdit(); self.search.setPlaceholderText('Search name, ID, email, role…'); self.search.textChanged.connect(self.refresh); bar.addWidget(self.search,1)
  self.filter=QComboBox(); self.filter.addItems(['All roles']+ROLES); self.filter.currentTextChanged.connect(self.refresh); bar.addWidget(self.filter)
  self.add_button=QPushButton(); self.add_button.clicked.connect(self.add); bar.addWidget(self.add_button)
  self.case_button=QPushButton('Open / add student profile'); self.case_button.clicked.connect(self.open_case); bar.addWidget(self.case_button)
  for text,fn in [('Edit profile',self.edit),('Log interaction',self.log),('History',self.history),('Delete',self.delete)]:
   b=QPushButton(text); b.clicked.connect(fn); bar.addWidget(b)
  self.table=QTableWidget(0,6); self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.SingleSelection); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.table.doubleClicked.connect(self.edit); main.addWidget(self.table); self.switch('people')
 def switch(self,mode):
  self.mode=mode; people=mode=='people'; helper=mode=='helpers'; self.title.setText({'people':'Central people registry','students':'International student accompaniment','helpers':'Volunteers & mentors'}[mode]); self.add_button.setText({'people':'Add person','students':'Add student','helpers':'Add volunteer / mentor'}[mode]); self.case_button.setVisible(people); self.filter.setVisible(people); self.search.clear(); self.table.setHorizontalHeaderLabels(['Person ID','Name','Roles','Email','Affiliation','Language'] if people else ['Person ID','Name','Roles','Availability','Status','Total hours'] if helper else ['Student ID','Name','University','Status','Next action','Follow-up']); self.refresh()
 def refresh(self,*args):
  if not hasattr(self,'table'): return
  all_people=self.store.people(); people=all_people if self.mode=='people' else [(i,d) for i,d in all_people if is_helper(d)] if self.mode=='helpers' else [(i,d) for i,d in all_people if 'International student' in roles(d)]
  self.stats.setText(f'{len(all_people)} people  •  {sum("International student" in roles(d) for _,d in all_people)} students  •  {sum("Volunteer" in roles(d) for _,d in all_people)} volunteers  •  {sum("Peer mentor" in roles(d) for _,d in all_people)} peer mentors' if self.mode=='people' else f'{len(people)} helpers • {sum(a[3]["status"]=="Active" for a in self.store.assignments())} active assignments' if self.mode=='helpers' else f'{len(people)} students  •  {sum(d.get("Status") not in ("Completed","Withdrawn") for _,d in people)} open cases')
  q=self.search.text().casefold(); role=self.filter.currentText(); self.rows=[(i,d) for i,d in people if (self.mode!='people' or role=='All roles' or role in roles(d)) and (q in ' '.join(map(str,d.values())).casefold() or q in person_id(i).casefold() or ('International student' in roles(d) and q in student_id(i).casefold()) or q in ' '.join(roles(d)).casefold())]; self.table.setRowCount(len(self.rows))
  for r,(i,d) in enumerate(self.rows):
   name=d.get('First name','')+' '+d.get('Last name',''); vals=[person_id(i),name,', '.join(roles(d)),d.get('Email',''),d.get('Organization / affiliation') or d.get('University',''),d.get('Preferred language','')] if self.mode=='people' else [person_id(i),name,', '.join(roles(d)),d.get('Availability',''),d.get('Volunteer status','Pending'),f'{sum(h["hours"] for _,h in self.store.hours(i)):.2f}'] if self.mode=='helpers' else [student_id(i),name,d.get('University',''),d.get('Status','Initial contact'),d.get('Next action',''),d.get('Follow-up date','')]
   for c,v in enumerate(vals): self.table.setItem(r,c,QTableWidgetItem(v))
 def selected(self):
  r=self.table.currentRow()
  if r<0 or r>=len(self.rows): QMessageBox.information(self,'Select a person','Select a record first.'); return None
  return self.rows[r]
 def persist(self,data,i=None):
  email=data.get('Email','').strip().casefold(); name=(data.get('First name','').strip().casefold(),data.get('Last name','').strip().casefold())
  for j,d in self.store.people():
   if j==i: continue
   if (email and email==d.get('Email','').strip().casefold()) or name==(d.get('First name','').strip().casefold(),d.get('Last name','').strip().casefold()):
    if QMessageBox.question(self,'Possible duplicate',f'{person_id(j)} has a matching name or email. Save anyway? Use the existing profile instead if this is the same person.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes: return False
    break
  if i is not None and any(a['status']=='Active' and ((m==i and ('Peer mentor' not in roles(data) or data.get('Volunteer status')!='Active' or data.get('Confidentiality agreement')!='Signed')) or (t==i and data.get('Consent')!='Granted')) for _,m,t,a in self.store.assignments()):
   QMessageBox.warning(self,'Active assignments','Complete or cancel active assignments before changing mentor eligibility or withdrawing student consent.'); return False
  self.store.save(data,i); self.refresh(); return True
 def add(self):
  d=PersonEditor(self,{'Roles':[]}) if self.mode=='people' else HelperEditor(self,{'Roles':['Volunteer']}) if self.mode=='helpers' else Editor(self,{'Referral date':date.today().isoformat()})
  if d.exec(): self.persist(d.values())
 def edit(self,*args):
  s=self.selected()
  if s:
   i,data=s; d=PersonEditor(self,data) if self.mode=='people' else HelperEditor(self,data) if self.mode=='helpers' else Editor(self,data)
   if d.exec(): self.persist(d.values(),i)
 def helper_role(self):
  s=self.selected()
  if s:
   i,data=s; d=HelperEditor(self,data)
   if d.exec(): self.persist(d.values(),i)
 def assignment_dialog(self):
  dlg=QDialog(self); dlg.setWindowTitle('Mentor assignments'); dlg.resize(950,500); v=QVBoxLayout(dlg); table=QTableWidget(0,6); table.setHorizontalHeaderLabels(['Mentor','Student','Start','Status','Support / notes','End']); table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); table.setSelectionBehavior(QAbstractItemView.SelectRows); table.setEditTriggers(QAbstractItemView.NoEditTriggers); v.addWidget(table); rows=[]
  def refresh():
   rows[:]=self.store.assignments(); people=dict(self.store.people()); table.setRowCount(len(rows))
   for r,(i,m,t,d) in enumerate(rows):
    for c,value in enumerate([full_name(people[m]),full_name(people[t]),d['start'],d['status'],d['notes'],d['end']]): table.setItem(r,c,QTableWidgetItem(value))
  def edit(existing=None):
   people=self.store.people(); formdlg=QDialog(dlg); formdlg.setWindowTitle('Mentor assignment'); f=QFormLayout(formdlg); mentor=QComboBox(); student=QComboBox(); detail=QLabel(); detail.setWordWrap(True)
   for i,d in people:
    if 'Peer mentor' in roles(d) or (existing and i==existing[1]): mentor.addItem(full_name(d)+' — '+person_id(i),i)
    if 'International student' in roles(d): student.addItem(full_name(d)+' — '+student_id(i),i)
   if not mentor.count() or not student.count(): QMessageBox.information(dlg,'Missing profiles','Register a peer mentor and student first.'); return
   def info(*args):
    d=dict(people)[mentor.currentData()]; t=dict(people)[student.currentData()]; n=sum(m==mentor.currentData() and a['status']=='Active' for _,m,_,a in self.store.assignments()); detail.setText(f"Mentor: {d.get('Organization / affiliation','')} | {d.get('Languages spoken','')} | {d.get('Availability','')}\nSkills: {d.get('Skills / expertise','')}\nSupport areas: {d.get('Support areas','')}\nActive assignments: {n} / {d.get('Maximum active students') or 'unspecified'}\nStudent: {t.get('University','')} | {t.get('Preferred language','')}\nNeeds: {', '.join(t.get('Selected needs',[]))}")
   mentor.currentIndexChanged.connect(info); student.currentIndexChanged.connect(info); data=existing[3] if existing else {}; start=QLineEdit(data.get('start',date.today().isoformat())); end=QLineEdit(data.get('end','')); status=QComboBox(); status.addItems(['Proposed','Active','Completed','Cancelled']); status.setCurrentText(data.get('status','Proposed')); notes=QTextEdit(); notes.setPlainText(data.get('notes',''))
   if existing: mentor.setCurrentIndex(mentor.findData(existing[1])); student.setCurrentIndex(student.findData(existing[2])); mentor.setEnabled(False); student.setEnabled(False)
   for label,w in [('Mentor',mentor),('Student',student),('Matching information',detail),('Start date',start),('End date',end),('Status',status),('Support / notes',notes)]: f.addRow(label,w)
   info(); buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); f.addRow(buttons); buttons.accepted.connect(formdlg.accept); buttons.rejected.connect(formdlg.reject)
   if formdlg.exec():
    try:
     a=date.fromisoformat(start.text()); z=date.fromisoformat(end.text()) if end.text() else None
     if z and z<a: raise ValueError('End date precedes start date.')
     if status.currentText()=='Active':
      d=dict(people)[mentor.currentData()]; t=dict(people)[student.currentData()]; count=sum(m==mentor.currentData() and x['status']=='Active' and (not existing or j!=existing[0]) for j,m,_,x in self.store.assignments()); cap=d.get('Maximum active students','')
      if d.get('Volunteer status')!='Active' or d.get('Confidentiality agreement')!='Signed' or t.get('Consent')!='Granted': raise ValueError('Active assignment requires an active mentor, signed confidentiality agreement and granted student consent.')
      if cap and count>=int(cap): raise ValueError('Mentor capacity reached.')
     self.store.assign(mentor.currentData(),student.currentData(),{'start':start.text(),'end':end.text(),'status':status.currentText(),'notes':notes.toPlainText()},existing[0] if existing else None); refresh(); self.refresh()
    except ValueError as e: QMessageBox.warning(dlg,'Cannot save assignment',str(e))
  bar=QHBoxLayout(); v.addLayout(bar)
  for label,fn in [('New assignment',lambda:edit()),('Edit selected',lambda:edit(rows[table.currentRow()]) if 0<=table.currentRow()<len(rows) else None)]:
   b=QPushButton(label); b.clicked.connect(fn); bar.addWidget(b)
  refresh(); dlg.exec()
 def hours_dialog(self):
  s=self.selected()
  if not s:return
  i,d=s
  if not is_helper(d): QMessageBox.information(self,'Helper required','Select a volunteer or mentor first.'); return
  dlg=QDialog(self); dlg.setWindowTitle('Volunteer hours — '+full_name(d)); dlg.resize(650,450); v=QVBoxLayout(dlg); total=QLabel(); v.addWidget(total); table=QTableWidget(0,3); table.setHorizontalHeaderLabels(['Date','Hours','Activity / notes']); table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); table.setEditTriggers(QAbstractItemView.NoEditTriggers); table.setSelectionBehavior(QAbstractItemView.SelectRows); v.addWidget(table); rows=[]
  def refresh():
   rows[:]=self.store.hours(i); total.setText(f'Total volunteer hours: {sum(x["hours"] for _,x in rows):.2f}'); table.setRowCount(len(rows))
   for r,(_,x) in enumerate(rows):
    for c,y in enumerate([x['date'],str(x['hours']),x['notes']]): table.setItem(r,c,QTableWidgetItem(y))
  def edit(existing=None):
   data=existing[1] if existing else {}; ed=QDialog(dlg); f=QFormLayout(ed); dt=QLineEdit(data.get('date',date.today().isoformat())); h=QDoubleSpinBox(); h.setRange(0.01,24); h.setDecimals(2); h.setValue(data.get('hours',1)); note=QTextEdit(); note.setPlainText(data.get('notes','')); f.addRow('Date (YYYY-MM-DD)',dt); f.addRow('Hours',h); f.addRow('Activity / notes',note); b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); f.addRow(b); b.accepted.connect(ed.accept); b.rejected.connect(ed.reject)
   if ed.exec():
    try: self.store.save_hours(i,{'date':dt.text(),'hours':h.value(),'notes':note.toPlainText()},existing[0] if existing else None); refresh(); self.refresh()
    except ValueError as e: QMessageBox.warning(dlg,'Invalid entry',str(e))
  for label,fn in [('Log hours',lambda:edit()),('Edit selected',lambda:edit(rows[table.currentRow()]) if 0<=table.currentRow()<len(rows) else None)]:
   b=QPushButton(label); b.clicked.connect(fn); v.addWidget(b)
  refresh(); dlg.exec()
 def organization_dialog(self,kind):
  titles={'committees':'Committees','programs':'Programs','memberships':'Committee memberships','registrations':'Program registrations / team'}
  fields={
   'committees':[('Name',None),('Name (French)',None),('Name (Persian)',None),('Status',['Planned','Active','Inactive','Archived']),('Mandate','text'),('Notes','text')],
   'programs':[('Name',None),('Name (French)',None),('Name (Persian)',None),('Status',['Planned','Active','Completed','Cancelled','Archived']),('Start date',None),('End date',None),('Objectives','text'),('Target audience',None),('Notes','text')],
   'memberships':[('Role',['Member','Coordinator','Co-coordinator','Secretary','Volunteer','Advisor']),('Status',['Proposed','Active','Ended']),('Start date',None),('End date',None),('Responsibilities','text'),('Notes','text')],
   'registrations':[('Role',['Participant','Volunteer','Facilitator','Coordinator']),('Status',['Pending','Active','Completed','Withdrawn','Cancelled']),('Start date',None),('End date',None),('Consent',['Pending','Granted','Declined','Withdrawn']),('Responsibilities / support','text'),('Notes','text')]}
  dlg=QDialog(self); dlg.setWindowTitle(titles[kind]); dlg.resize(1050,600); layout=QVBoxLayout(dlg); search=QLineEdit(); search.setPlaceholderText('Search records…'); layout.addWidget(search); stats=QLabel(); layout.addWidget(stats)
  linklabels={'committees':[], 'programs':['Committee'], 'memberships':['Committee','Person'], 'registrations':['Program','Person']}[kind]
  headers=['ID']+linklabels+[f for f,_ in fields[kind] if f in ('Name','Role','Status','Start date','End date','Consent')]; table=QTableWidget(0,len(headers)); table.setHorizontalHeaderLabels(headers); table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); table.setSelectionBehavior(QAbstractItemView.SelectRows); table.setSelectionMode(QAbstractItemView.SingleSelection); table.setEditTriggers(QAbstractItemView.NoEditTriggers); layout.addWidget(table); rows=[]
  def choices(label):
   if label=='Person': return [(i,full_name(d)+' — '+person_id(i)) for i,d in self.store.people()]
   return [(r[0],r[-1]['Name']+(' — '+str(r[0]))) for r in self.store.records('committees' if label=='Committee' else 'programs')]
  def refresh(*args):
   allrows=self.store.records(kind); rows.clear(); values=[]; q=search.text().casefold(); maps=[dict(choices(l)) for l in linklabels]; prefix={'committees':'COM','programs':'PRG','memberships':'MEM','registrations':'REG'}[kind]
   for r in allrows:
    d=r[-1]; cells=[f'DIDAR-{prefix}-{r[0]:06d}']+[m.get(i,str(i)) for m,i in zip(maps,r[1:-1])]+[d.get(f,'') for f in headers[1+len(linklabels):]]
    if q in (' '.join(cells)+' '+str(d)).casefold(): rows.append(r); values.append(cells)
   stats.setText(f'{len(rows)} of {len(allrows)} records • {sum(r[-1].get("Status")=="Active" for r in allrows)} active'); table.setRowCount(len(rows))
   for i,cells in enumerate(values):
    for j,value in enumerate(cells): table.setItem(i,j,QTableWidgetItem(value))
  def edit(existing=None):
   ed=QDialog(dlg); ed.setWindowTitle(titles[kind]); ed.resize(650,650); form=QFormLayout(ed); links=[]; inputs={}; data=existing[-1] if existing else {}
   for j,label in enumerate(linklabels):
    w=QComboBox()
    for i,name in choices(label): w.addItem(name,i)
    if not w.count(): QMessageBox.information(dlg,'Missing records','Register a '+label.lower()+' first.'); return
    if existing: w.setCurrentIndex(w.findData(existing[j+1])); w.setEnabled(False)
    links.append(w); form.addRow(label,w)
   for f,opts in fields[kind]:
    if isinstance(opts,list): w=QComboBox(); w.addItems(opts); w.setCurrentText(data.get(f,opts[0]))
    elif opts=='text': w=QTextEdit(); w.setMaximumHeight(90); w.setPlainText(data.get(f,''))
    else: w=QLineEdit(data.get(f,date.today().isoformat() if f=='Start date' else '')); w.setPlaceholderText('YYYY-MM-DD' if 'date' in f else '')
    inputs[f]=w; form.addRow(f,w)
   b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); form.addRow(b); b.accepted.connect(ed.accept); b.rejected.connect(ed.reject)
   while ed.exec():
    try:
     d={f:w.currentText() if isinstance(w,QComboBox) else w.toPlainText().strip() if isinstance(w,QTextEdit) else w.text().strip() for f,w in inputs.items()}; self.store.save_record(kind,[w.currentData() for w in links],d,existing[0] if existing else None); refresh(); self.refresh(); break
    except (ValueError,sqlite3.IntegrityError) as e: QMessageBox.warning(ed,'Cannot save',str(e))
  def edit_selected(*args):
   if 0<=table.currentRow()<len(rows): edit(rows[table.currentRow()])
  bar=QHBoxLayout(); layout.addLayout(bar)
  for label,fn in [('Add record',lambda:edit()),('Edit selected',edit_selected)]:
   b=QPushButton(label); b.clicked.connect(fn); bar.addWidget(b)
  if kind=='committees':
   b=QPushButton('Manage memberships'); b.clicked.connect(lambda:self.organization_dialog('memberships')); bar.addWidget(b)
  if kind=='programs':
   b=QPushButton('Manage registrations / team'); b.clicked.connect(lambda:self.organization_dialog('registrations')); bar.addWidget(b)
  table.doubleClicked.connect(edit_selected); search.textChanged.connect(refresh); refresh(); dlg.exec()
 def open_case(self):
  s=self.selected()
  if s:
   i,data=s; d=Editor(self,data)
   if d.exec(): self.persist(d.values(),i)
 def log(self):
  s=self.selected()
  if not s:return
  dlg=QDialog(self); dlg.setWindowTitle('Record interaction'); form=QFormLayout(dlg); dt=QLineEdit(date.today().isoformat()); kind=QComboBox(); kind.addItems(['Email','Video call','Phone','In-person','Referral','Other']); note=QTextEdit(); form.addRow('Date',dt); form.addRow('Type',kind); form.addRow('Outcome / notes',note); b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); form.addRow(b); b.accepted.connect(dlg.accept); b.rejected.connect(dlg.reject)
  if dlg.exec():
   try: date.fromisoformat(dt.text())
   except ValueError: QMessageBox.warning(self,'Invalid date','Use YYYY-MM-DD.'); return
   self.store.log(s[0],{'date':dt.text(),'type':kind.currentText(),'note':note.toPlainText()})
 def history(self):
  s=self.selected()
  if not s:return
  dlg=QDialog(self); dlg.setWindowTitle('Interaction history'); dlg.resize(650,450); v=QVBoxLayout(dlg); t=QTextEdit(); t.setReadOnly(True); t.setPlainText('\n\n'.join(f"{x['date']} — {x['type']}\n{x['note']}" for x in self.store.history(s[0])) or 'No interactions yet.'); v.addWidget(t); dlg.exec()
 def delete(self):
  s=self.selected()
  if s and QMessageBox.question(self,'Delete person','Permanently delete this person, all roles, student information, interaction history, mentor assignments, volunteer hours, committee memberships and program registrations? Existing backups will retain copies.')==QMessageBox.Yes: self.store.delete(s[0]); self.refresh()
 def backup(self):
  from datetime import datetime
  p=self.folder/'backups'; p.mkdir(exist_ok=True); target=p/('didar-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite'); self.store.backup(target); QMessageBox.information(self,'Backup created',str(target))

def main():
 app=QApplication(sys.argv); app.setApplicationName('DIDAR Connect'); folder=Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)); folder.mkdir(parents=True,exist_ok=True); path=folder/'didar.sqlite'; new=not path.exists(); password,ok=QInputDialog.getText(None,'DIDAR Connect','Create a strong database passphrase (at least 12 characters):' if new else 'Enter database passphrase:',QLineEdit.Password)
 if not ok:return
 if new and len(password)<12: QMessageBox.warning(None,'Passphrase','Use at least 12 characters.'); return
 if new:
  confirm,ok=QInputDialog.getText(None,'Confirm passphrase','Repeat passphrase:',QLineEdit.Password)
  if not ok or confirm!=password: QMessageBox.warning(None,'Passphrase','Passphrases do not match.'); return
 try: store=Store(path,password)
 except InvalidToken: QMessageBox.critical(None,'Access denied','Incorrect passphrase.'); return
 app.setStyleSheet('QWidget {font-size:13px;} QMainWindow {background:#f5f7f8;} QLabel#brand {background:#07384B;color:white;padding:18px;font-size:22px;font-weight:bold;} QLabel#title {font-size:25px;font-weight:bold;color:#07384B;} QPushButton {padding:8px;border:1px solid #a9b9bf;border-radius:5px;} QPushButton:hover {background:#dcebed;} QLineEdit,QComboBox,QTextEdit {padding:7px;} QHeaderView::section {background:#07384B;color:white;padding:9px;}')
 window=Window(store,folder); window.show(); sys.exit(app.exec())
if __name__=='__main__': main()
