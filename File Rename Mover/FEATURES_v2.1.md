# File Rename Mover v2.1.0 - New Features

## Overview

Version 2.1.0 introduces powerful new features for advanced file organization and renaming.

## New Features

### 1. Custom Sorting Options

Sort files before renaming by multiple criteria:

**Sort By:**
- **Name** - Alphabetical sorting
- **Date Modified** - By modification timestamp
- **Date Created** - By creation timestamp
- **Size** - By file size

**Sort Order:**
- **Ascending** (asc) - Smallest to largest / A to Z / Oldest to newest
- **Descending** (desc) - Largest to smallest / Z to A / Newest to oldest

**Use Case Example:**
Sort photos by date modified (oldest first) to maintain chronological order when renaming.

---

### 2. Multiple Rename Patterns

Choose from several intelligent rename patterns:

#### **Numbering Pattern** (Default)
Simple sequential numbering with custom base name.
```
photo_000001_.jpg
photo_000002_.jpg
photo_000003_.jpg
```

#### **DateTime Pattern**
Include file date/time in the filename.

**Available Formats:**
- `YYYYMMDD` → `photo_20251127_000001_.jpg`
- `YYYY_MM_DD` → `photo_2025-11-27_000001_.jpg`
- `YYYYMMDD_HHMMSS` → `photo_20251127_143022_000001_.jpg`
- `YYYY_MM_DD_HH_MM_SS` → `photo_2025-11-27_14-30-22_000001_.jpg`
- `MMDDYYYY` → `photo_11272025_000001_.jpg`
- `DDMMYYYY` → `photo_27112025_000001_.jpg`

**Options:**
- Include/exclude counter
- Use file date or current date

**Use Case Example:**
Organize photos with their capture date: `vacation_20251127_000001_.jpg`

#### **Prefix Pattern**
Add prefix while keeping original filename.
```
backup_IMG_1234.jpg
backup_IMG_1235.jpg
backup_DSC_5678.jpg
```

**Use Case Example:**
Add version prefix to files: `v2_document.pdf`

#### **Custom Pattern**
Create your own pattern using placeholders:

**Available Placeholders:**
- `{counter}` - Sequential number (000001, 000002...)
- `{date}` - Date in YYYYMMDD format
- `{time}` - Time in HHMMSS format
- `{datetime}` - Combined date and time
- `{year}` - Year (YYYY)
- `{month}` - Month (MM)
- `{day}` - Day (DD)
- `{original}` - Original filename (without extension)

**Examples:**
- `IMG_{year}_{month}_{counter}` → `IMG_2025_11_000001.jpg`
- `{date}_{original}` → `20251127_vacation.jpg`
- `Project_{counter}_{datetime}` → `Project_000001_20251127_143022.jpg`

---

### 3. Folder Organization

Automatically organize files into date-based folder structures:

#### **Flat** (Default)
No subfolders, all files in destination folder.
```
dest_folder/
  photo_000001_.jpg
  photo_000002_.jpg
```

#### **By Year**
Organize into year folders.
```
dest_folder/
  2025/
    photo_000001_.jpg
    photo_000002_.jpg
  2024/
    photo_000003_.jpg
```

#### **By Year/Month**
Two-level organization.
```
dest_folder/
  2025/
    11/
      photo_000001_.jpg
    10/
      photo_000002_.jpg
```

#### **By Year/Month/Day**
Three-level organization.
```
dest_folder/
  2025/
    11/
      27/
        photo_000001_.jpg
      26/
        photo_000002_.jpg
```

#### **By Date**
Single folder named with full date.
```
dest_folder/
  2025-11-27/
    photo_000001_.jpg
  2025-11-26/
    photo_000002_.jpg
```

#### **By Month**
Single folder named with year-month.
```
dest_folder/
  2025-11/
    photo_000001_.jpg
  2025-10/
    photo_000002_.jpg
```

**Use Case Example:**
Organize thousands of photos by year/month for easy browsing.

---

## Combined Workflows

### Workflow 1: Photo Archive
**Goal:** Organize photos chronologically with dates in filenames

**Settings:**
- Sort By: Date Modified (asc)
- Pattern: DateTime (YYYY-MM-DD format, include counter)
- Folder Organization: By Year/Month

**Result:**
```
Photos/
  2025/
    11/
      vacation_2025-11-27_000001_.jpg
      vacation_2025-11-27_000002_.jpg
    10/
      vacation_2025-10-15_000001_.jpg
```

### Workflow 2: Document Backup
**Goal:** Backup files with prefix, maintaining original names

**Settings:**
- Sort By: Name (asc)
- Pattern: Prefix (with "backup" prefix)
- Folder Organization: By Date

**Result:**
```
Backup/
  2025-11-27/
    backup_report.pdf
    backup_spreadsheet.xlsx
```

### Workflow 3: Project Files
**Goal:** Custom naming with project code and date

**Settings:**
- Sort By: Date Created (asc)
- Pattern: Custom (`PRJ_{year}{month}_{counter}`)
- Folder Organization: Flat

**Result:**
```
Project/
  PRJ_202511_000001.docx
  PRJ_202511_000002.docx
```

---

## Configuration Persistence

All settings are automatically saved:
- Last used sorting options
- Last used pattern type and settings
- Last used folder organization
- All previous settings (source/dest folders, extension, base name)

Settings persist between sessions for quick repeated operations.

---

## Technical Architecture

### New Modules

**sorting.py**
- `FileSorter` - Handles file sorting by various criteria
- `SortBy` / `SortOrder` - Enumerations for sorting options

**rename_patterns.py**
- `RenamePattern` - Base class for patterns
- `NumberingPattern` - Simple numbering
- `DateTimePattern` - Date/time based naming
- `PrefixPattern` - Prefix with original name
- `CustomPattern` - User-defined patterns
- `PatternFactory` - Creates pattern instances

**folder_organization.py**
- `FolderOrganizer` - Manages subfolder creation
- `FolderStructure` - Enumeration of organization types

### Updated Modules

**file_operations.py**
- Enhanced `FileRenamer` with pattern and sorting support
- Integrated folder organization
- Pattern-based filename generation

**config.py**
- Extended configuration for new settings
- Stores sorting, pattern, and organization preferences

**ui/main_window_v2.py**
- Completely redesigned interface
- Dropdown selectors for all options
- Live preview of filename examples
- Scrollable interface for all controls

---

## Upgrade Notes

- Version bumped to 2.1.0
- Backward compatible with v2.0.0 configurations
- Old `main_window.py` preserved for reference
- New `main_window_v2.py` is now active
- All existing files and configs remain functional

---

## Future Enhancement Ideas

- [ ] Preview window showing all renames before executing
- [ ] Undo last operation
- [ ] Batch operations with different rules per folder
- [ ] File filtering (by size, date range, etc.)
- [ ] Template library for common patterns
- [ ] Regular expression support in patterns
- [ ] Duplicate file detection
- [ ] Progress bar for large operations
- [ ] Export/import settings profiles
