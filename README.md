# DIDAR Connect V0.6
Single-user, offline student accompaniment prototype. Python 3.10–3.13 recommended.

## macOS
Open Terminal in the extracted folder:
```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```
Windows: use `py -m venv .venv`, `.venv\Scripts\activate`, then the same pip and Python commands.

On first launch choose and confirm a strong passphrase. No real student data is bundled. Add the first student manually from the referral email. Use the profile tabs and interaction history; record consent accurately and collect only necessary information.

Storage: Qt AppLocalDataLocation (shown when creating a backup). Records and interaction payloads use authenticated Fernet encryption with a passphrase-derived Scrypt key. SQLite structure, IDs and record counts are not encrypted. No password recovery. Keep the passphrase separately in a password manager. Enable FileVault or BitLocker. Backups are manual, encrypted at payload level, and retain deleted records if created before deletion. For restoration, close the application, preserve the existing database, and replace didar.sqlite with a copy of the backup using the same passphrase. Test with dummy records before real data. No automatic backups, multiuser access, separate case/people tables, exports, or formal privacy/security audit yet. Keep database and backups out of Git and public cloud folders. The application is an early prototype, not a compliance-certified system.

## v0.2 update
Back up your existing database before updating. Quit the app, replace main.py in your existing project with the new main.py, and launch as before. The application name, database location and passphrase are unchanged. Existing profiles and notes are preserved; the new Needs Assessment tab stores selected needs in the encrypted profile. Search includes selected needs. No schema migration is required. Test with dummy data first.

## v0.3 — Central people registry
Back up v0.2, close it, replace main.py and launch with the same environment and passphrase. Existing students automatically appear in People registry with role International student, without rewriting their stored records. Their original DIDAR-IS IDs remain unchanged; the same numeric ID is used for DIDAR-P IDs. Select Add person to register a new contact and choose one or more roles. For an existing person, select Open / add student profile to add or edit student-specific details without duplicating the person. Role filters and search are available. A possible duplicate name or email triggers a warning, not an automatic merge. Deletion in either view deletes the entire person and history; close student cases using status instead. This release supports one student profile per person and shared interaction history, not separate multiple case records or dedicated volunteer/mentor assignments. Data remains encrypted at payload level, not full database encryption. UI runtime testing is still required.

## v0.4 — Volunteers and mentors
Back up v0.3, quit, replace main.py and restart using the same environment and passphrase. New assignment and hours tables are created automatically. Existing IDs, student needs and interactions are retained.
- Volunteers & mentors: add or edit a helper profile, availability, expertise, languages, support areas, capacity and confidentiality status. For existing people, select their record in People and use Add helper role to selected person rather than creating duplicates.
- Mentor assignments: choose mentor and student, compare needs and mentor information manually, record proposed/active/completed/cancelled status, dates and notes. Activation requires granted student consent, active mentor status, signed confidentiality agreement and available capacity. Existing free-text Assigned mentor is a legacy note, not automatically migrated or synchronized. Use Mentor assignments as the authoritative list. End active assignments before withdrawing consent or changing mentor eligibility; no information is sent to mentors automatically.
- Volunteer hours: select a helper, click Volunteer hours, log or edit date, duration and activity; totals are calculated automatically.
- Assignment and hour payloads are encrypted, but IDs, relationships and counts are not. Keep protected backups. Deleting a person also deletes linked assignments and their hours. Mark people inactive instead when preserving history is appropriate.
- Matching is manual, not an automatic recommendation algorithm. No exports or GUI runtime testing yet. Headless storage checks: run python test_store.py in the project directory. Test the interface with dummy records before live use.

## V0.5 — Committees and programs

Back up and close the previous version, then replace main.py. No new dependencies. Existing database path and passphrase remain unchanged. Four new tables are created automatically.

- Committees: names in English/French/Persian, mandate, status and notes.
- Committee memberships: select an existing person, role (including coordinator), dates, responsibilities and status.
- Programs: select a committee, enter multilingual names, dates, objectives, target audience and status.
- Program registrations / team: select program and existing person, role, consent, dates, responsibilities and status.
- Database location: displays the exact local SQLite file path.

No real records are preloaded. One membership per person per committee and one registration per person per program; edit these to change status or role. Roles added to the central profile are retained as historical roles. Each program belongs to one committee. Archive committees/programs using status; no destructive organization deletion is offered. Registration consent is tracked, not enforced as a workflow gate. Personal payloads are encrypted; relationship IDs and schema are not. No automatic synchronization with website, student cases or volunteer hours. Test GUI with dummy data before real use. Headless tests: python test_store.py (run from this folder).

## V0.6 — Activities and attendance
Back up V0.5, close it, replace main.py, README.md and test_store.py. No new dependencies. Two additional tables are created automatically. Activities can be independent or associated with a program. Enter date, times (HH:MM), location, type, status, series label, objectives, expense amount and evaluation notes. Create one activity per occurrence; series labels group recurring activities conceptually, not automatic scheduling. Attendance links existing people to activities and records role, registration/attendance status and consent. Duplicate person/activity pairs are prevented. Volunteer hours remain in the existing separate module; no automatic synchronization. Expenses are a single total field, not accounting records. Consent is tracked but not enforced. No anonymous attendance counts or exports yet. Payload encryption and existing storage limitations remain unchanged. Run python test_store.py; GUI requires testing with dummy data before real use.
