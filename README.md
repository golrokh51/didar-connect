# DIDAR Connect V1.1 — Individual support & case management
Single-user, offline community management system. Python 3.10–3.13 recommended. This source release is not a prebuilt or notarized application and is not security-audited.


## V1.1 update (macOS)

- Close all DIDAR versions. In V1.0 first create a manual backup, record the database path and keep a protected second copy. Create a Git feature branch from your V1.0 release.
- Copy `main.py`, `support_cases.py`, `support_ui.py`, `storage_tools.py`, `test_store.py`, and `README.md` to the existing project. Dependencies, icon, build script and database location are unchanged. Do not replace `.git`, `.gitignore`, `.venv` or the external database.
- Run `python test_store.py` (eight PASS groups expected). Then run `python main.py --data-dir "$HOME/DIDAR-Connect-test-v1.1"` and test only with fictional records. When ready, `bash build_macos.sh`, test `open -n "dist/DIDAR Connect.app" --args --data-dir "$HOME/DIDAR-Connect-test-v1.1"`, and replace the installed app only after closing it. Verify the real database path and original passphrase before production use. Never use old and new app versions on the same database.
- One new table `support_cases` is created at first authenticated launch. Existing records are not rewritten. Older V1.0 backups cannot be restored via the V1.1 same-schema restore UI; retain them for rollback with V1.0 (close all versions and restore to a separate directory, never discard a live database). Make a fresh V1.1 backup after migration.

### Using the module

Register a person as usual. New optional general roles: Support recipient, Community member, Supporter, Donor. Reason for engagement is optional and non-sensitive. Do not label people by abuse, disability or other sensitive experiences. Support recipient is not automatically assigned; it remains visible in the general registry if selected. Use a general role such as Participant if appropriate.

Select the person in People Registry and click **Support cases**, or use **Individual support & accompaniment** in the sidebar. New support case creates a separate case ID. Select a committee and coordinator if appropriate, record dates/status, document consent and its date before adding sensitive details, then select relevant self-reported circumstances and needs. Use the Services & referrals and Follow-up history tabs to track assistance. Save the case after editing entries. Multiple cases may link to one person. Safe contact defaults to no contact authorized, and voicemail defaults to disallowed. Sharing consent is separate and requires a scope. Withdraw consent by revoking contact and sharing permissions; previously recorded details are retained until corrected/deleted according to policy. No automatic messages, transfers or referrals occur.

### Privacy and limitations

All case content, including categories, committee/coordinator references, services and history, is stored in an authenticated encrypted payload using the existing database key. Person-to-case linkage, identifiers, timestamps implicit in encryption tokens and record counts are not encrypted. Case records are excluded from general person search, ordinary interaction history, public directory export and existing impact reports. The case module offers an internal aggregate summary with counts 1–4 suppressed, not an anonymity guarantee. Existing general report data is unchanged; never put sensitive details in general notes or other modules. There is no separate case password, access control by role, access audit log, automatic inactivity lock, automated retention or case-specific public reporting. The manual Lock & close action remains. Deleting a case removes its services/history from the live DB; deleting a person cascades to their cases; earlier backups retain copies. Deletion is not guaranteed forensic erasure. Review consent, retention and confidentiality procedures before using real sensitive information. Enable FileVault, keep protected backups and complete an independent security/privacy review. GUI and macOS bundle need local validation. This is not an emergency service or professional legal/clinical record system.

## V1.0 quick start (macOS)

1. In V0.9 create a manual backup, record the exact Database location and quit. Keep a protected second backup off the computer. Never run V0.9 and V1.0 against the same database simultaneously.
2. Copy the new source files and assets into the existing Git working tree. Preserve `.git`, `.gitignore`, `.venv` and the external database. Activate the venv and run:

```sh
python -m pip install -r requirements-build.txt
python test_store.py
python main.py --data-dir "$HOME/DIDAR-Connect-test-v1"
```

The explicit test directory is separate from the real database; approve creation there, use a dummy passphrase and dummy records only. Verify all modules, reports, home dashboard, manual backup, restore (edit a dummy record, restore an earlier snapshot, verify both restored record and safety backup), lock & close and relaunch. Quit the source app.

```sh
bash build_macos.sh
open -n "dist/DIDAR Connect.app" --args --data-dir "$HOME/DIDAR-Connect-test-v1"
```

Confirm the packaged app sees your existing dummy records. Check PDF/Excel exports from the bundle. Quit it, open `dist` in Finder (`open dist`), and drag `DIDAR Connect.app` to Applications (or `~/Applications`). Do not overwrite an older app without preserving it. Launch normally only after testing. Check the Database & backups location matches V0.9 exactly; cancel if unexpectedly prompted to create a new database. If necessary launch with `--data-dir` and the recorded V0.9 directory. Test with the installed bundle before using real data. The app needs no Terminal or venv for normal launch after a successful build. The build is native to the Mac/Python architecture, not a cross-platform installer. If macOS blocks the local build, diagnose signing or permissions rather than disabling Gatekeeper. The bundle uses local/ad hoc signing as provided by PyInstaller, not Developer ID signing or notarization. Windows packaging is deferred.

## V1.0 features and storage safeguards

- Home dashboard with current registry totals, open cases, active assignments, completed activities and overdue follow-ups; refresh manually after changes.
- Database & backups shows the full path, file size, backup count and latest copy; opens the folder in Finder. The usual macOS path is `~/Library/Application Support/DIDAR Connect/didar.sqlite`. A different existing Qt location is preferred if it is the only database; ambiguous paths are rejected. `--data-dir` deliberately overrides this selection. Confirm the path on your own Mac.
- One automatic snapshot on the first successful login each calendar day. It captures the database at that login, not later edits. Use manual backups after important work. Copies are not automatically deleted or moved off-device; manage retention and protected off-device backups yourself.
- Restore validates the SQLite integrity, exact current schema, foreign keys, database salt and encrypted payloads. It creates a safety snapshot before restoring via SQLite backup. Only compatible same-database backups are accepted. This is not an import/merge or a recovery mechanism for a lost passphrase. For older incompatible backups, keep the original untouched and migrate a separate copy using the original passphrase before restoration.
- Lock & close exits the process; relaunch to unlock. No automatic idle lock. V1.0 uses a local Qt lock file to prevent concurrent V1.0 instances for the same directory; earlier releases do not respect this lock. Close them first. This is not a multi-user database.
- Existing Fernet payload encryption and passphrase are retained; SQLite metadata, IDs, relationships and counts are visible. New files use restrictive defaults on POSIX; existing permissions are not automatically changed. Use FileVault, a password manager, restricted access and protected backups. Exported files are not encrypted. No privacy compliance certification or independent security audit. Defer real personal data until your local validation and organizational privacy/security review are complete.
- All seven headless test groups pass in the build environment; GUI, macOS packaging, Gatekeeper behavior and application launch have not been tested here. The macOS build script must be run locally. No database or personal data is shipped.

## Historical development notes
The following sections describe earlier versions; use the V1.0 instructions above for the current release.

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

## V0.7 — Institutional partners
Back up V0.6 and close it before replacing main.py, README.md and test_store.py. Four new tables are created automatically. Register organizations, link existing people as contacts, record incoming/outgoing referrals and organization interactions with follow-up dates. Existing text referral fields in student profiles are retained; create structured referrals manually. Partner contacts and referrals link to people; deleting a person removes these links. Archive organizations rather than deleting them. No external synchronization, automatic reminders or consent enforcement. No real data is included. Test on dummy records before production use.

## V0.8 — Community resource directory
Back up V0.7 and close it. Copy main.py, resource_directory.py, README.md, requirements.txt and test_store.py into your existing project. Install updated dependencies (`python -m pip install -r requirements.txt`). The database path/passphrase are unchanged; a new encrypted-payload resources table is created automatically. Community resources supports search, category/university/status and audience eligibility filters, add/edit, CSV template, CSV and XLSX import (first active worksheet, exact template headers), and public JSON export. Imports validate all rows before insertion, skip duplicates by name/category/university and always disable publication. Use Unknown rather than guessing eligibility. Public export includes only active records with a verification date and explicit Publish=Yes, excludes internal notes and does not read participant data. Review all public fields for personal information and verify facts before publishing; no automatic website upload or live eligibility verification. Archive outdated resources. Existing files with different headers require manual mapping to the template. Run python test_store.py; Qt GUI testing is still required.


## V0.9 — Statistics and impact reports
Back up the previous database and close the application. Copy main.py, impact_reports.py (new), resource_directory.py, requirements.txt, README.md and test_store.py into your project, preserving .git, .gitignore and .venv. Install updated dependencies with `python -m pip install -r requirements.txt`, then run `python test_store.py` and `python main.py`. No database schema changes.

Open Statistics & impact reports. Leave either date blank for an unbounded period, or select inclusive YYYY-MM-DD dates. Select all committees or one committee; refresh and export the same filtered aggregate report as XLSX or PDF. Committee filtering applies only to program-linked activities and registrations; student, volunteer, institutional and global snapshot statistics are deliberately omitted for committee reports because those records lack reliable committee links. Independent activities are included only in the all-committee view.

Definitions are included in exports: count attended records only at completed activities, deduplicate people for unique counts, distinguish registrations from attendance, count student contacts from documented interactions, and treat student needs and case statuses as current values for the referral-date cohort. Undated period records are excluded. Current registry snapshots ignore date filters. Expenses use recorded completed-activity totals only. Volunteer hours are independently logged, not inferred. Reports include fixed indicators and program/committee IDs, not names or notes.

Exports are unencrypted internal aggregate reports, not certified anonymous: small counts, dates and program identifiers may permit re-identification. Do not publish or share externally without disclosure review. No automatic suppression or historical reconstruction of deleted or changed records. No new personal fields collected. No GUI runtime testing in the build environment; test using a separate dummy database before live use.
