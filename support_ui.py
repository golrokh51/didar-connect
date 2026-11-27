"""Qt interface for private support cases. Deliberately separate from global search."""
from datetime import date
import sqlite3
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QComboBox,QLineEdit,QTextEdit,QPushButton,QTableWidget,QTableWidgetItem,QAbstractItemView,QHeaderView,QMessageBox,QDialogButtonBox,QTabWidget,QWidget,QCheckBox,QScrollArea)
from PySide6.QtCore import Qt
import support_cases as sc


def person_label(i,d):
    return f'DIDAR-P-{i:06d} — '+(d.get('First name','')+' '+d.get('Last name','')).strip()


def table(headers):
    t=QTableWidget(0,len(headers)); t.setHorizontalHeaderLabels(headers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows); t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    return t


def fill(t,rows):
    t.setRowCount(len(rows))
    for i,row in enumerate(rows):
        for j,value in enumerate(row): t.setItem(i,j,QTableWidgetItem(str(value)))


def message(parent,text): QMessageBox.warning(parent,'Cannot save',text)


def form_page(tabs,name):
    scroll=QScrollArea(); scroll.setWidgetResizable(True); page=QWidget(); form=QFormLayout(page); scroll.setWidget(page); tabs.addTab(scroll,name); return form


class CaseEditor(QDialog):
    def __init__(self,parent,store,existing=None,person=None):
        super().__init__(parent); self.store=store; self.existing=existing; self.setWindowTitle('Confidential support case'); self.resize(850,680)
        self.data=sc.blank(); self.data.update(existing[2] if existing else {})
        d=self.data; layout=QVBoxLayout(self)
        notice=QLabel('Private, self-reported information only. Record the minimum needed for support. Do not record detailed narratives, diagnoses or unverified legal conclusions. DIDAR is not an emergency or clinical service.'); notice.setWordWrap(True); layout.addWidget(notice)
        tabs=QTabWidget(); layout.addWidget(tabs); self.fields={}; self.checks={}
        form=form_page(tabs,'Case'); self.person=QComboBox(); self.person.addItem('Select a person…',None)
        people=store.people()
        for i,p in people: self.person.addItem(person_label(i,p),i)
        if existing or person is not None:
            self.person.setCurrentIndex(self.person.findData(existing[1] if existing else person)); self.person.setEnabled(False)
        form.addRow('Person',self.person)
        self.link(form,'Committee ID',[(r[0],r[-1].get('Name','')) for r in store.records('committees')])
        self.link(form,'Coordinator ID',[(i,person_label(i,p)) for i,p in people])
        for f,opts in [('Opened',None),('Status',sc.STATUSES),('Closed',None),('Referral source',None),('Follow-up date',None),('Next action','text')]: self.field(form,f,opts)
        form=form_page(tabs,'Consent & safe contact')
        for f,opts in [('Consent',sc.CONSENT),('Consent date',None),('Sharing consent',sc.CONSENT),('Sharing scope','text'),('Safe contact',sc.CONTACT),('Voicemail allowed','bool'),('Contact instructions','text')]: self.field(form,f,opts)
        form.addRow(QLabel('No messages are sent by this application. Confirm safety and permission before any contact or external disclosure.'))
        form=form_page(tabs,'Circumstances')
        self.checks['Circumstances']={}
        for group,items in sc.CIRCUMSTANCES.items():
            title=QLabel(group); title.setStyleSheet('font-weight:bold'); form.addRow(title)
            for item in items:
                cb=QCheckBox(item); cb.setChecked(item in d['Circumstances']); self.checks['Circumstances'][item]=cb; form.addRow(cb)
        form=form_page(tabs,'Needs & notes'); self.checks['Needs']={}
        for item in sc.NEEDS:
            cb=QCheckBox(item); cb.setChecked(item in d['Needs']); self.checks['Needs'][item]=cb; form.addRow(cb)
        self.field(form,'Notes','text')
        self.services=[dict(x) for x in d['Services']]; self.history=[dict(x) for x in d['History']]
        self.collection(tabs,'Services & referrals',self.services,[('Date',None),('Need',sc.NEEDS),('Status',sc.SERVICE_STATUS),('Resource / organization',None),('Outcome / notes','text')])
        self.collection(tabs,'Follow-up history',self.history,[('Date',None),('Type',['Consultation','Meeting','Phone','Email','Referral','Follow-up','Other']),('Outcome / notes','text')])
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); buttons.accepted.connect(self.save); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def link(self,form,name,choices):
        w=QComboBox(); w.addItem('Not assigned',None)
        for i,label in choices: w.addItem(label,i)
        w.setCurrentIndex(max(0,w.findData(self.data.get(name)))); self.fields[name]=w; form.addRow(name.replace(' ID',''),w)

    def field(self,form,name,opts):
        w=self.widget(opts,self.data[name]); self.fields[name]=w; form.addRow(name,w)
        if isinstance(w,QLineEdit) and ('date' in name.lower() or name in ('Opened','Closed')): w.setPlaceholderText('YYYY-MM-DD')

    @staticmethod
    def widget(opts,value):
        if isinstance(opts,list): w=QComboBox(); w.addItems(opts); w.setCurrentText(value or opts[0])
        elif opts=='text': w=QTextEdit(); w.setPlainText(value or ''); w.setMaximumHeight(100)
        elif opts=='bool': w=QCheckBox(); w.setChecked(bool(value))
        else: w=QLineEdit(value or '')
        return w

    @staticmethod
    def value(w):
        if isinstance(w,QComboBox): return w.currentText()
        if isinstance(w,QCheckBox): return w.isChecked()
        if isinstance(w,QTextEdit): return w.toPlainText().strip()
        return w.text().strip()

    def collection(self,tabs,title,entries,fields):
        page=QWidget(); layout=QVBoxLayout(page); tabs.addTab(page,title); t=table([name for name,_ in fields]); layout.addWidget(t)
        def refresh(): fill(t,[[x.get(name,'') for name,_ in fields] for x in entries])
        def edit(index=None):
            if self.fields['Consent'].currentText()!='Granted': message(self,'Grant and document consent before adding or editing case details.'); return
            dlg=QDialog(self); dlg.setWindowTitle(title); dlg.resize(590,350); form=QFormLayout(dlg); inputs={}; d=entries[index] if index is not None else {'Date':date.today().isoformat()}
            for name,opts in fields:
                w=self.widget(opts,d.get(name,'')); inputs[name]=w; form.addRow(name,w)
            b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); form.addRow(b); b.accepted.connect(dlg.accept); b.rejected.connect(dlg.reject)
            while dlg.exec():
                record={k:self.value(w) for k,w in inputs.items()}
                try: sc.day(record['Date'],True)
                except ValueError as e: message(dlg,str(e)); continue
                if index is None: entries.append(record)
                else: entries[index]=record
                refresh(); break
        def selected(): return t.currentRow() if 0<=t.currentRow()<len(entries) else None
        def remove():
            i=selected()
            if i is not None and QMessageBox.question(self,'Remove entry','Remove this entry when the case is saved?',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes: entries.pop(i); refresh()
        bar=QHBoxLayout(); layout.addLayout(bar)
        for label,fn in [('Add entry',lambda:edit()),('Edit selected',lambda:edit(selected()) if selected() is not None else None),('Remove selected',remove)]:
            b=QPushButton(label); b.clicked.connect(fn); bar.addWidget(b)
        refresh()

    def save(self):
        d=dict(self.data)
        d.update({k:w.currentData() if k in ('Committee ID','Coordinator ID') else self.value(w) for k,w in self.fields.items()})
        d.update({k:[item for item,w in checks.items() if w.isChecked()] for k,checks in self.checks.items()}); d['Services']=self.services; d['History']=self.history
        try: sc.save(self.store,self.person.currentData(),d,self.existing[0] if self.existing else None)
        except (ValueError,sqlite3.Error) as e: message(self,str(e)); return
        self.accept()


def open_cases(parent,store,person=None):
    dlg=QDialog(parent); dlg.resize(1000,560); dlg.setWindowTitle('Individual support & accompaniment — private'); layout=QVBoxLayout(dlg)
    note=QLabel('Confidential workspace. Case details are excluded from ordinary profile search and existing impact exports. Close this window when not in use.'); note.setWordWrap(True); layout.addWidget(note)
    search=QLineEdit(); search.setPlaceholderText('Search case ID, person ID, name or status (not sensitive details)'); layout.addWidget(search)
    t=table(['Case ID','Person','Opened','Status','Follow-up date']); layout.addWidget(t); rows=[]
    def refresh(*args):
        people=dict(store.people()); q=search.text().casefold(); rows.clear(); cells=[]
        for r in sc.records(store,person):
            i,p,d=r; v=[sc.case_id(i),person_label(p,people[p]),d['Opened'],d['Status'],d['Follow-up date']]
            if q in ' '.join(v).casefold(): rows.append(r); cells.append(v)
        fill(t,cells)
    def selected(): return rows[t.currentRow()] if 0<=t.currentRow()<len(rows) else None
    def edit(existing=None):
        if not store.people(): message(dlg,'Add a person in the People Registry first.'); return
        if CaseEditor(dlg,store,existing,person).exec(): refresh()
    def remove():
        r=selected()
        if r and QMessageBox.question(dlg,'Delete support case','Permanently delete this case and its service and follow-up records from the live database? Previous backups may retain copies.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes: sc.delete(store,r[0]); refresh()
    def summary(): QMessageBox.information(dlg,'Private aggregate summary — not for publication','\n'.join(f'{k}: {v}' for k,v in sc.private_summary(store).items())+'\nSmall counts are suppressed, but aggregates are not guaranteed anonymous.')
    bar=QHBoxLayout(); layout.addLayout(bar)
    for label,fn in [('New support case',lambda:edit()),('Open / edit selected',lambda:edit(selected()) if selected() else None),('Delete case',remove),('Private summary (all cases)',summary),('Close',dlg.accept)]:
        b=QPushButton(label); b.clicked.connect(fn); bar.addWidget(b)
    search.textChanged.connect(refresh); t.doubleClicked.connect(lambda *_:edit(selected()) if selected() else None); refresh(); dlg.exec()
