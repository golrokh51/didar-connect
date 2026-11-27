"""Resource-only storage helpers, import and export. No participant data access."""
import csv, json
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse
PUBLIC_FIELDS = ('Name','Category','University','Services','Eligibility','International students','Newcomers','Refugee claimants','Website','Public email','Public phone','Address','Languages','Cost','Last verified')
FIELDS = PUBLIC_FIELDS + ('Status','Publish','Internal notes')
ELIGIBILITY = ('Unknown','Yes','No','Conditional')
OPTIONS = {**{f:ELIGIBILITY for f in ('International students','Newcomers','Refugee claimants')},'Status':('Unverified','Active','Inactive','Archived'),'Publish':('No','Yes')}

def normalize(data):
    d={f:str(data.get(f) or '').strip() for f in FIELDS}
    for f,opts in OPTIONS.items():
        d[f]=next((v for v in opts if v.casefold()==d[f].casefold()),opts[0] if not d[f] else '')
        if not d[f]: raise ValueError(f'Invalid {f}; choose {", ".join(opts)}')
    if not d['Name'] or not d['Category']: raise ValueError('Name and Category are required.')
    if d['Last verified']: date.fromisoformat(d['Last verified'])
    if d['Website']:
        u=urlparse(d['Website'])
        if u.scheme not in ('http','https') or not u.hostname: raise ValueError('Website must be an HTTP(S) URL.')
    if d['Publish']=='Yes' and (d['Status']!='Active' or not d['Last verified']): raise ValueError('Publishing requires Active status and a verification date.')
    return d

def key(d):
    return tuple(d[f].casefold() for f in ('Name','Category','University'))

def read_rows(path):
    path=Path(path)
    if path.suffix.lower()=='.csv':
        with path.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.reader(f); return parse_rows(reader)
    if path.suffix.lower()=='.xlsx':
        from openpyxl import load_workbook
        wb=load_workbook(path,read_only=True,data_only=True)
        try: return parse_rows(wb.active.values)
        finally: wb.close()
    raise ValueError('Choose CSV or XLSX.')

def parse_rows(rows):
    rows=iter(rows); headers=[str(x or '').strip() for x in next(rows,())]
    if not {'Name','Category'}.issubset(headers) or len(set(headers))!=len(headers): raise ValueError('Unique headers Name and Category are required. Use the import template.')
    unknown=set(headers)-set(FIELDS)-{''}
    if unknown: raise ValueError('Unrecognized columns: '+', '.join(sorted(unknown)))
    result=[]
    for n,row in enumerate(rows,2):
        if not any(x is not None and str(x).strip() for x in row): continue
        d={k:(v.date().isoformat() if isinstance(v,datetime) else v) for k,v in zip(headers,row) if k}
        d['Publish']='No' # explicit review after import
        try: result.append(normalize(d))
        except ValueError as e: raise ValueError(f'Row {n}: {e}') from e
    return result

def write_template(path):
    with open(path,'w',encoding='utf-8-sig',newline='') as f: csv.writer(f).writerow(FIELDS)

def export_public(path, records):
    data=[{f:d.get(f,'') for f in PUBLIC_FIELDS} for _,d in records if d.get('Publish')=='Yes' and d.get('Status')=='Active' and d.get('Last verified')]
    Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    return len(data)
