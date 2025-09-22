# SQLite Forensic Exporter 🔍📊

A professional, cross-platform Python tool for extracting and exporting data from SQLite databases with forensic analysis capabilities. Perfect for digital forensics, data analysis, and application data examination.

## Features

### 🎯 Core Functionality
- **Multi-Source Export**: Export single databases or entire folders of SQLite files
- **Recursive Scanning**: Process nested directory structures with `--recursive` flag
- **Smart Table Detection**: Automatically discover and export all tables from any SQLite database
- **Cross-Platform**: Works seamlessly on Windows, Linux, and macOS

### 🔬 Forensic Enhancements
- **Timestamp Conversion**: Automatic detection and conversion of common timestamp formats:
  - **Webkit Epoch** (Chrome timestamps)
  - **Unix Epoch** (standard timestamps)
  - **Apple Cocoa** (iOS/macOS timestamps)
- **Locked Database Handling**: Automatically creates temporary copies of locked databases
- **Memory-Efficient Streaming**: Processes large tables in chunks to handle massive databases

### 📊 Export Flexibility
- **Selective Table Export**: Export specific tables with `--tables` parameter
- **Preview Mode**: Limit rows with `--limit` for quick data sampling
- **Custom Output Directories**: Specify output location with `--output`
- **External SQLite Support**: Use system SQLite binaries when needed

## Installation

### Prerequisites
- Python 3.6 or higher
- No external dependencies required (uses built-in `sqlite3` module)

### Quick Start
```bash
# Clone or download the script
git clone https://github.com/ethic-bakeery/sqlite-forensic-exporter.git
cd sqlite-forensic-exporter

# Or simply download sqlite_exporter.py to your desired location
```

## Usage Examples

### Basic Export Operations
```bash
# Export a single database
python sqlite_exporter.py --file "C:\path\to\chrome_history.sqlite"

# Export all databases in a folder
python sqlite_exporter.py --folder "C:\Users\user\AppData\Local\Google\Chrome"

# Export recursively through subdirectories
python sqlite_exporter.py --folder "C:\mobile_forensics" --recursive
```

### Advanced Forensic Analysis
```bash
# Export specific tables with row limit (preview mode)
python sqlite_exporter.py --file "History" --tables urls,visits --limit 500

# Custom output directory
python sqlite_exporter.py --folder "C:\evidence" --output "C:\exports" --recursive

# Use external SQLite binary
python sqlite_exporter.py --file "webdata.db" --sqlite-binary "C:\sqlite\sqlite3.exe"
```

### Common Forensic Scenarios
```bash
# Chrome browser analysis
python sqlite_exporter.py --folder "%LOCALAPPDATA%\Google\Chrome\User Data" --recursive

# Mobile app data extraction
python sqlite_exporter.py --folder "/path/to/android/app/data" --recursive --output "./mobile_export"

# Quick preview of specific tables
python sqlite_exporter.py --file "messages.db" --tables messages,contacts --limit 100
```

## Command Line Reference

### Required Parameters (One of)
- `--file PATH`: Export a single SQLite database file
- `--folder PATH`: Export all SQLite databases in a folder

### Optional Parameters
- `--recursive`: Include subfolders when using `--folder`
- `--output DIR`: Custom output directory (default: `./sqlite_exports`)
- `--tables TABLE1,TABLE2`: Export only specific tables
- `--limit N`: Limit rows exported per table (preview mode)
- `--sqlite-binary PATH`: Use external SQLite binary

### Help Command
```bash
python sqlite_exporter.py --help
```

## Output Structure

### File Naming Convention
```
📁 sqlite_exports/
├── database1_table1.csv
├── database1_table2.csv
├── database2_table1.csv
└── database2_table2.csv
```

### CSV File Format
- **Column headers** included automatically
- **Original data** preserved exactly
- **Additional columns** for timestamp conversion:
  - `timestamp_column_converted`: Human-readable datetime
  - `timestamp_column_type`: Detected timestamp format

## Supported Applications

This tool works with SQLite databases from various sources:

### 🌐 Web Browsers
- Google Chrome/Chromium
- Mozilla Firefox
- Microsoft Edge
- Safari

### 📱 Mobile Applications
- Android apps
- iOS apps
- WhatsApp
- Signal
- Telegram

### 💻 System & Applications
- Windows system databases
- macOS application data
- Various software configurations

## Forensic Features

### Timestamp Conversion
Automatically detects and converts multiple timestamp formats:
- **Webkit**: Chrome history, downloads (microseconds since 1601)
- **Unix**: Standard timestamps (seconds since 1970)
- **Unix MS**: Milliseconds since 1970
- **Cocoa**: Apple timestamps (seconds since 2001)

### Error Handling
- **Graceful failures**: Skips invalid files with warnings
- **Detailed logging**: All errors logged to `export_errors.log`
- **Progress reporting**: Real-time console updates

### Performance Optimizations
- **Chunked processing**: Handles large tables without memory issues
- **Locked file handling**: Temporary copy mechanism for busy databases
- **Efficient scanning**: Quick database validation before processing

## Use Cases

### 🕵️ Digital Forensics
- Extract browser history and cookies
- Analyze application usage patterns
- Recover deleted data from SQLite databases

### 🔍 Data Analysis
- Export application data for analysis
- Convert SQLite data to CSV for tools like Excel, Pandas
- Batch process multiple databases

### 🛠️ Development & Testing
- Quick database inspection
- Data migration and backup
- Testing database contents

## Troubleshooting

### Common Issues
```bash
# Permission denied errors
python sqlite_exporter.py --folder "C:\Program Files" --recursive
# → Run as Administrator or copy files to accessible location

# Unicode errors on Windows
# → Tool automatically handles encoding issues

# Database locked errors  
# → Tool automatically creates temporary copies
```

### Log Files
- **Console output**: Real-time progress and errors
- **export_errors.log**: Detailed error information
- **CSV files**: Exported data with forensic enhancements
---

**Quick Start Tip**: For immediate use, download `sqlite_exporter.py` and run:
```bash
python sqlite_exporter.py --file "your_database.db"
```

For more examples and advanced usage, refer to the documentation above.
