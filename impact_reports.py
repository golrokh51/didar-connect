"""Read-only aggregate reports. No personal labels or free-text fields in output."""
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation

NEEDS = ('Pre-arrival preparation','Temporary accommodation','Long-term housing','Airport arrival and transportation','University registration','Administrative procedures','Health insurance and healthcare','Banking and mobile phone services','French language support','English language support','Digital and technological support','Financial resources','Social and cultural integration','Peer mentorship','Academic integration','Community activities','Referral to specialized services')
STUDENT_STATUS = ('Initial contact','Consultation scheduled','Needs assessment','Awaiting mentor','Active accompaniment','Completed','Withdrawn')
ACTIVITY_STATUS = ('Planned','Completed','Cancelled')
ROLES = ('Participant','Volunteer','Facilitator','Coordinator')
NOTICE = 'Internal aggregate report. Small counts may identify individuals; review before external sharing. No names, personal IDs, contact details or free-text notes are included.'
METHOD = ('Date range is inclusive. Undated or invalid dates are excluded from period metrics. '
          'Attendance means Attended at completed activities only. Unique attendees are deduplicated by person ID; '
          'participant attendees exclude team-only attendance. Registration counts use start date and current status, not historical status. '
          'Student cohort uses referral date; needs and case status are current values, not historical outcomes. '
          'Volunteer hours are logged hours, not inferred from attendance. Recorded expenses include completed activities only; missing or invalid amounts are excluded. '
          'Committee filtering applies only to linked programs, registrations and activities; organization-wide metrics are omitted in a committee report. '
          'Current snapshot metrics ignore the date filter. Deleted records are not counted. Counts do not establish service quality or causal impact.')


def parse_day(value):
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def build_report(store, start='', end='', committee=None):
    lo, hi = parse_day(start), parse_day(end)
    if (start and lo is None) or (end and hi is None):
        raise ValueError('Enter dates as YYYY-MM-DD or leave blank.')
    if lo and hi and lo > hi:
        raise ValueError('Start date must not follow end date.')
    def within(value):
        d = parse_day(value)
        return d is not None and (lo is None or d >= lo) and (hi is None or d <= hi)
    people = dict(store.people())
    committees = store.records('committees')
    if committee is not None and committee not in {r[0] for r in committees}:
        raise ValueError('Unknown committee.')
    programs = [r for r in store.records('programs') if committee is None or r[1] == committee]
    pids = {r[0] for r in programs}
    activities = [r for r in store.records('activities') if (committee is None or r[1] in pids) and within(r[2].get('Date'))]
    completed = {i for i, _, d in activities if d.get('Status') == 'Completed'}
    attendance = [r for r in store.records('attendance') if r[1] in completed and r[3].get('Status') == 'Attended']
    participants = {r[2] for r in attendance if r[3].get('Role') == 'Participant'}
    registrations = [r for r in store.records('registrations') if r[1] in pids and within(r[3].get('Start date'))]
    rows = []
    def add(section, metric, value): rows.append((section, metric, value))
    add('Activities','Activities in period',len(activities))
    for s in ACTIVITY_STATUS: add('Activities',s,sum(d.get('Status')==s for _,_,d in activities))
    add('Activities','Other / unknown status',sum(d.get('Status') not in ACTIVITY_STATUS for _,_,d in activities))
    add('Attendance','Attended records at completed activities',len(attendance))
    add('Attendance','Unique attendees (all roles)',len({r[2] for r in attendance}))
    add('Attendance','Unique participant attendees',len(participants))
    for role in ROLES: add('Attendance',role+' attendance records',sum(r[3].get('Role')==role for r in attendance))
    add('Attendance','Other / unknown role',sum(r[3].get('Role') not in ROLES for r in attendance))
    expenses = Decimal(0); missing = 0
    for i,_,d in activities:
        if i not in completed: continue
        try:
            amount=Decimal(str(d.get('Expenses (CAD)','')))
            if not amount.is_finite() or amount<0: raise ValueError()
            expenses += amount
        except (InvalidOperation,ValueError): missing+=1
    add('Expenses','Recorded completed-activity expenses (CAD)',float(expenses))
    add('Expenses','Completed activities without valid expense amount',missing)
    add('Programs','Programs currently in scope (snapshot)',len(programs))
    add('Programs','Registrations started in period (all roles/statuses)',len(registrations))
    active_regs=[r for r in registrations if r[3].get('Role')=='Participant' and r[3].get('Status') in ('Active','Completed')]
    add('Programs','Active/completed participant registrations',len(active_regs))
    add('Programs','Unique active/completed registered participants',len({r[2] for r in active_regs}))
    for s in ('Pending','Active','Completed','Withdrawn','Cancelled'):
        add('Programs','Registrations currently '+s.lower(),sum(r[3].get('Status')==s for r in registrations))
    # Fixed record identifiers, not user-entered names, keep exports free of arbitrary text.
    for pid,cid,_ in programs:
        acts={i for i,p,_ in activities if p==pid}; a=[r for r in attendance if r[1] in acts]
        section=f'Program PRG-{pid:06d} (COM-{cid:06d})'
        add(section,'Completed activities',len(acts & completed))
        add(section,'Participant attendance records',sum(r[3].get('Role')=='Participant' for r in a))
        add(section,'Unique participant attendees',len({r[2] for r in a if r[3].get('Role')=='Participant'}))
        add(section,'Registrations started',sum(r[1]==pid for r in registrations))
    for cid,_ in committees:
        if committee is not None and cid != committee: continue
        linked={pid for pid,c,_ in programs if c==cid}
        acts={i for i,p,_ in activities if p in linked}; a=[r for r in attendance if r[1] in acts]
        section=f'Committee COM-{cid:06d}'
        add(section,'Completed activities',len(acts & completed))
        add(section,'Unique participant attendees',len({r[2] for r in a if r[3].get('Role')=='Participant'}))
        add(section,'Registrations started',sum(r[1] in linked for r in registrations))
    if committee is None:
        students={i:d for i,d in people.items() if 'International student' in d.get('Roles',['International student'])}
        cohort={i:d for i,d in students.items() if within(d.get('Referral date'))}
        add('Current registry','Registered people',len(people))
        add('Current registry','International students',len(students))
        add('Current registry','Volunteers',sum('Volunteer' in d.get('Roles',[]) for d in people.values()))
        add('Current registry','Peer mentors',sum('Peer mentor' in d.get('Roles',[]) for d in people.values()))
        add('Current registry','Committees',len(committees))
        add('Current registry','Institutional organizations',len(store.records('partners')))
        add('Current registry','Active institutional relationships',sum(d.get('Status')=='Active' for _,d in store.records('partners')))
        add('Current registry','Active mentor assignments',sum(d.get('status')=='Active' for *_,d in store.assignments()))
        add('Current registry','Students without a valid referral date',sum(parse_day(d.get('Referral date')) is None for d in students.values()))
        add('Student cohort','Students referred in period',len(cohort))
        for s in STUDENT_STATUS: add('Student cohort','Current status: '+s,sum(d.get('Status')==s for d in cohort.values()))
        add('Student cohort','Unknown / missing current status',sum(d.get('Status') not in STUDENT_STATUS for d in cohort.values()))
        for need in NEEDS: add('Identified needs',need,sum(need in d.get('Selected needs',[]) for d in cohort.values()))
        contacts=[i for i in students for d in store.history(i) if within(d.get('date')) and d.get('type') in ('Email','Video call','Phone','In-person')]
        add('Student contacts','Documented student contacts in period',len(contacts))
        add('Student contacts','Unique students with documented contacts',len(set(contacts)))
        add('Reach','Unique participant attendees or contacted students',len(participants | set(contacts)))
        hours=[(i,d) for i in people for _,d in store.hours(i) if within(d.get('date'))]
        add('Volunteer contribution','Logged volunteer hours',float(sum((Decimal(str(d['hours'])) for _,d in hours),Decimal(0))))
        add('Volunteer contribution','Unique people with logged hours',len({i for i,_ in hours}))
        add('Mentorship','Assignments started in period',sum(within(d.get('start')) for *_,d in store.assignments()))
        refs=[r for r in store.records('partner_referrals') if within(r[-1].get('Date'))]
        for direction in ('Incoming','Outgoing'): add('Institutional referrals',direction,sum(r[-1].get('Direction')==direction for r in refs))
        add('Institutional referrals','Other / unknown direction',sum(r[-1].get('Direction') not in ('Incoming','Outgoing') for r in refs))
        add('Institutional referrals','Unique people referred',len({r[2] for r in refs}))
        add('Institutional referrals','Organizations involved',len({r[1] for r in refs}))
        add('Institutional referrals','Current completed referrals',sum(r[-1].get('Status')=='Completed' for r in refs))
        add('Institutional referrals','Institutional interactions in period',sum(within(d.get('Date')) for *_,d in store.records('partner_interactions')))
        for status in ('Unverified','Active','Inactive','Archived'):
            add('Resource directory (snapshot)',status,sum(d.get('Status')==status for _,d in store.resources()))
    return {'period':f'{lo.isoformat() if lo else "Earliest dated record"} to {hi.isoformat() if hi else "Latest dated record"}', 'scope':'All committees and independent activities' if committee is None else f'DIDAR-COM-{committee:06d}', 'rows':rows}


def export_excel(path, report):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb=Workbook(); ws=wb.active; ws.title='Impact statistics'
    ws.append(['DIDAR Connect | Internal impact statistics']); ws.merge_cells('A1:C1')
    ws.append(['Period',report['period']]); ws.append(['Scope',report['scope']]); ws.append(['Section','Indicator','Value'])
    for row in report['rows']: ws.append(row)
    ws.freeze_panes='C5'; ws.auto_filter.ref=f'A4:C{ws.max_row}'
    for c,w in [('A',37),('B',67),('C',19)]: ws.column_dimensions[c].width=w
    for row in (ws[1],ws[4]):
        for cell in row: cell.fill=PatternFill('solid',fgColor='07384B'); cell.font=Font(color='FFFFFF',bold=True)
    for r in range(5,ws.max_row+1):
        if r%2==0:
            for c in ws[r]: c.fill=PatternFill('solid',fgColor='F0F5F6')
        ws.cell(r,3).number_format='0.00' if isinstance(ws.cell(r,3).value,float) else '0'
    notes=wb.create_sheet('Definitions'); notes.column_dimensions['A'].width=110
    for text in ('Internal use only',NOTICE, *METHOD.split('. ')):
        notes.append([text]); notes.cell(notes.max_row,1).alignment=Alignment(wrap_text=True,vertical='top'); notes.row_dimensions[notes.max_row].height=32
    wb.save(path)


def export_pdf(path,report):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from xml.sax.saxutils import escape
    styles=getSampleStyleSheet(); teal=colors.HexColor('#07384B'); styles['Title'].textColor=teal
    story=[Paragraph('DIDAR Connect | Impact statistics',styles['Title']),Paragraph(escape(report['period']),styles['Normal']),Paragraph(escape(report['scope']),styles['Normal']),Spacer(1,10),Paragraph(NOTICE,styles['Normal']),Spacer(1,12)]
    data=[['Section','Indicator','Value']]
    for section,metric,value in report['rows']:
        data.append([Paragraph(escape(section),styles['Normal']),Paragraph(escape(metric),styles['Normal']),f'{value:,.2f}' if isinstance(value,float) else str(value)])
    table=Table(data,colWidths=[146,290,69],repeatRows=1,hAlign='LEFT'); table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),teal),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('VALIGN',(0,0),(-1,-1),'TOP'),('ALIGN',(-1,1),(-1,-1),'RIGHT'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F0F5F6')]),('BOTTOMPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5)]))
    story.extend([table,Spacer(1,12),Paragraph('Definitions and limitations',styles['Heading2']),Paragraph(METHOD,styles['Normal'])])
    def footer(canvas,doc):
        canvas.setFont('Helvetica',9); canvas.setFillColor(teal); canvas.drawString(45,25,'DIDAR | Internal use only'); canvas.drawRightString(A4[0]-45,25,str(doc.page))
    SimpleDocTemplate(str(path),pagesize=A4,rightMargin=45,leftMargin=45,topMargin=40,bottomMargin=45).build(story,onFirstPage=footer,onLaterPages=footer)
