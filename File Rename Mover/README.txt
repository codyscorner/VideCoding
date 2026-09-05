FILE RENAME MOVER  v3.5.1
=========================

Batch-renames files with sequential numbering and moves them into an
organized destination tree. PySide6 (Qt6), dark red theme, portable EXE.

WHAT IT DOES
------------
1. Pick a Source Folder (browse, type, or drag a folder from Explorer).
   The Extension dropdown fills with every extension found in that folder,
   most common first (hover an entry for the file count). You can still type
   an extension by hand.
2. Pick a Destination Folder and a Base Name.
3. Choose sorting, a rename pattern, and folder organization.
4. Click Preview to see every planned move without touching a file.
5. Click Move and Rename. Progress bar + Cancel; UI stays responsive.

RENAMING
--------
- Files become  Base Name_000001.ext, Base Name_000002.ext, ...
- The counter continues after the highest number already in the destination.
- Patterns: numbering | datetime (6 formats, optional counter) | prefix
  (keep original names) | custom with {counter} {date} {time} {datetime}
  {year} {month} {day} {original}
- Sort by name, date modified, date created, or size; asc or desc.

FOLDER ORGANIZATION
-------------------
- Organize into: flat | year | year_month | year_month_day | date | month
  (based on each file's modified date)
- "Folder named after Base Name" checkbox:
      dest\[Base Name]\year\month\day
  Any date organization is created inside the Base Name folder. With this on,
  the counter scan looks only inside dest\[Base Name].
- The example line under the checkbox shows the exact resulting path.

SAFETY
------
- Copy, verify, then delete. Never overwrites an existing file.
- Optional SHA-256 hash verification (Settings).

TEMPLATES
---------
Save / Load / Manage named configurations from the top row. The last used
template is remembered between runs.

FILES IN THIS FOLDER
--------------------
FileRenameMover.exe        the app (single file, no install)
Filemove_config.json       last-used settings, created on first run
Filemove_templates.json    saved templates, created on first run
Archive\                   previous builds

Keep the .json files next to the EXE; the app is portable and reads them
from its own folder.

CHANGES
-------
3.5.1  Two-column form (Extension | Base Name, Rename Pattern | Folder
       Organization). Status box fills the remaining window height.
3.5.0  Extension dropdown auto-filled from the source folder.
3.4.0  "Folder named after Base Name" option. Preview (dry run) button.
3.3.0  Threaded progress bar, Cancel, drag-and-drop folders.

Source, changelog, and build notes:
https://github.com/codyscorner/VideCoding/tree/master/File%20Rename%20Mover
