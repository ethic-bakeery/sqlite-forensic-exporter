#!/usr/bin/env python3
"""
SQLite Database Exporter - Professional Forensic Tool
Export SQLite databases to CSV format with forensic enhancements
"""

import sqlite3
import os
import sys
import argparse
import csv
import tempfile
import shutil
import logging
from datetime import datetime, timedelta
import re
from pathlib import Path

# Configure logging with proper encoding
try:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('export_errors.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
except UnicodeEncodeError:
    # Fallback for systems with encoding issues
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('export_errors.log', encoding='utf-8')
        ]
    )

logger = logging.getLogger(__name__)

class SQLiteExporter:
    def __init__(self, output_dir="./sqlite_exports", use_external_binary=None):
        self.output_dir = Path(output_dir)
        self.use_external_binary = use_external_binary
        self.sqlite_binary_path = use_external_binary if use_external_binary else None
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.stats = {
            'databases_processed': 0,
            'tables_exported': 0,
            'files_skipped': 0,
            'errors': 0
        }
        
        # Common timestamp patterns for forensic analysis
        self.timestamp_patterns = {
            'webkit_epoch': datetime(1601, 1, 1),  # Chrome timestamps
            'unix_epoch': datetime(1970, 1, 1),
            'apple_cocoa': datetime(2001, 1, 1),   # Apple Cocoa timestamps
        }

    def safe_print(self, message):
        """Safely print messages to console with encoding handling"""
        try:
            print(message)
        except UnicodeEncodeError:
            # Replace problematic characters
            safe_message = message.encode('ascii', 'replace').decode('ascii')
            print(safe_message)

    def is_valid_sqlite_database(self, file_path):
        """Check if file is a valid SQLite database"""
        try:
            if not os.path.isfile(file_path):
                return False
            
            # Check file size first
            if os.path.getsize(file_path) < 16:
                return False
            
            # Check SQLite header (first 16 bytes)
            with open(file_path, 'rb') as f:
                header = f.read(16)
                return header.startswith(b'SQLite format 3\0')
        except Exception as e:
            logger.warning(f"Error checking SQLite header for {file_path}: {e}")
            return False

    def copy_locked_database(self, original_path):
        """Create a temporary copy of a locked database"""
        try:
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, os.path.basename(original_path))
            shutil.copy2(original_path, temp_path)
            return temp_path, temp_dir
        except Exception as e:
            logger.error(f"Failed to copy locked database {original_path}: {e}")
            return None, None

    def get_table_list(self, conn):
        """Get list of all tables in the database"""
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                AND name NOT LIKE 'sqlite_%'
            """)
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting table list: {e}")
            return []

    def convert_timestamp(self, timestamp, timestamp_type='auto'):
        """Convert various timestamp formats to human-readable datetime"""
        if timestamp is None:
            return None, 'unknown'
            
        try:
            # Try to convert to float first
            ts_value = float(timestamp)
            
            if timestamp_type == 'auto':
                # Auto-detect timestamp type based on value range
                if ts_value > 1000000000000000000:  # Very large numbers (Webkit)
                    base_date = self.timestamp_patterns['webkit_epoch']
                    converted = base_date + timedelta(microseconds=ts_value)
                    ts_type = 'webkit'
                elif ts_value > 10000000000:  # Milliseconds since Unix epoch
                    converted = datetime.fromtimestamp(ts_value / 1000)
                    ts_type = 'unix_ms'
                elif ts_value > 1000000000:   # Seconds since Unix epoch
                    converted = datetime.fromtimestamp(ts_value)
                    ts_type = 'unix'
                elif ts_value > 100000000:    # Apple Cocoa (seconds since 2001)
                    base_date = self.timestamp_patterns['apple_cocoa']
                    converted = base_date + timedelta(seconds=ts_value)
                    ts_type = 'cocoa'
                else:
                    return None, 'unknown'
            else:
                # Manual timestamp type specification
                if timestamp_type == 'webkit':
                    base_date = self.timestamp_patterns['webkit_epoch']
                    converted = base_date + timedelta(microseconds=ts_value)
                    ts_type = 'webkit'
                elif timestamp_type == 'unix':
                    converted = datetime.fromtimestamp(ts_value)
                    ts_type = 'unix'
                elif timestamp_type == 'unix_ms':
                    converted = datetime.fromtimestamp(ts_value / 1000)
                    ts_type = 'unix_ms'
                elif timestamp_type == 'cocoa':
                    base_date = self.timestamp_patterns['apple_cocoa']
                    converted = base_date + timedelta(seconds=ts_value)
                    ts_type = 'cocoa'
                else:
                    return None, 'unknown'
                    
            return converted.isoformat(), ts_type
            
        except (ValueError, TypeError, OSError):
            return None, 'unknown'

    def detect_timestamp_columns(self, cursor, table_name):
        """Detect potential timestamp columns based on name patterns"""
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            timestamp_columns = []
            timestamp_patterns = [
                r'time', r'date', r'stamp', r'created', r'modified', 
                r'accessed', r'last', r'epoch', r'visit'
            ]
            
            for col in columns:
                col_name = col[1].lower()
                if any(pattern in col_name for pattern in timestamp_patterns):
                    timestamp_columns.append(col[1])
                    
            return timestamp_columns
        except Exception as e:
            logger.warning(f"Could not detect timestamp columns for {table_name}: {e}")
            return []

    def export_table_to_csv(self, db_path, table_name, output_path, limit=None, timestamp_columns=None):
        """Export a single table to CSV with timestamp conversion"""
        temp_db_path = None
        temp_dir = None
        
        try:
            # Handle locked databases
            try:
                conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                conn.text_factory = lambda x: x.decode('utf-8', errors='ignore')
            except (sqlite3.OperationalError, ValueError):
                # If URI mode fails, try regular connection
                try:
                    conn = sqlite3.connect(db_path)
                    conn.text_factory = lambda x: x.decode('utf-8', errors='ignore')
                except sqlite3.OperationalError as e:
                    if "locked" in str(e).lower():
                        logger.info(f"Database locked, creating temporary copy: {db_path}")
                        temp_db_path, temp_dir = self.copy_locked_database(db_path)
                        if temp_db_path:
                            conn = sqlite3.connect(temp_db_path)
                            conn.text_factory = lambda x: x.decode('utf-8', errors='ignore')
                        else:
                            raise e
                    else:
                        raise e

            cursor = conn.cursor()
            
            # Auto-detect timestamp columns if not provided
            if timestamp_columns is None:
                timestamp_columns = self.detect_timestamp_columns(cursor, table_name)
            
            # Get column names
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 0")
            original_columns = [description[0] for description in cursor.description]
            
            # Add extra columns for timestamp conversions
            extra_columns = []
            for col in timestamp_columns:
                if col in original_columns:
                    extra_columns.extend([f"{col}_converted", f"{col}_type"])
            
            all_columns = original_columns + extra_columns
            
            # Prepare query with limit
            query = f"SELECT * FROM {table_name}"
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            
            # Write CSV file
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(all_columns)  # Write header
                
                # Process rows in chunks for large tables
                chunk_size = 1000
                rows_processed = 0
                
                while True:
                    rows = cursor.fetchmany(chunk_size)
                    if not rows:
                        break
                    
                    for row in rows:
                        row_data = list(row)
                        extra_data = []
                        
                        # Convert timestamps
                        for col in timestamp_columns:
                            if col in original_columns:
                                col_index = original_columns.index(col)
                                timestamp_value = row[col_index]
                                converted, ts_type = self.convert_timestamp(timestamp_value)
                                extra_data.extend([converted, ts_type])
                            else:
                                extra_data.extend([None, None])
                        
                        writer.writerow(row_data + extra_data)
                        rows_processed += 1
                        
                        if limit and rows_processed >= limit:
                            break
                    
                    if limit and rows_processed >= limit:
                        break
            
            logger.info(f"Exported {rows_processed} rows from table '{table_name}'")
            self.stats['tables_exported'] += 1
            return True, rows_processed
            
        except Exception as e:
            logger.error(f"Error exporting table {table_name} from {db_path}: {e}")
            self.stats['errors'] += 1
            return False, 0
            
        finally:
            if 'conn' in locals():
                conn.close()
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Could not clean up temp directory {temp_dir}: {e}")

    def export_database(self, db_path, tables=None, limit=None, recursive=False):
        """Export all tables from a single database"""
        if not self.is_valid_sqlite_database(db_path):
            logger.warning(f"Skipping invalid SQLite database: {db_path}")
            self.stats['files_skipped'] += 1
            return
        
        db_name = Path(db_path).stem
        self.safe_print(f"Processing database: {db_path}")
        
        try:
            # Get list of tables to export
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            all_tables = self.get_table_list(conn)
            conn.close()
            
            if tables:
                # Filter tables based on user input
                tables_to_export = [t for t in all_tables if t in tables]
                if not tables_to_export:
                    logger.warning(f"No matching tables found in {db_path} for: {tables}")
                    return
            else:
                tables_to_export = all_tables
            
            for table_name in tables_to_export:
                # Create safe filename
                safe_db_name = re.sub(r'[^\w\-_.]', '_', db_name)
                safe_table_name = re.sub(r'[^\w\-_.]', '_', table_name)
                csv_filename = f"{safe_db_name}_{safe_table_name}.csv"
                output_path = self.output_dir / csv_filename
                
                self.safe_print(f"  Exporting table: {table_name}")
                success, row_count = self.export_table_to_csv(db_path, table_name, output_path, limit)
                
                if success:
                    success_msg = f"    [SUCCESS] Saved {row_count} rows to: {output_path}"
                    self.safe_print(success_msg)
                    logger.info(success_msg)
                else:
                    error_msg = f"    [ERROR] Failed to export: {table_name}"
                    self.safe_print(error_msg)
                    logger.error(error_msg)
            
            self.stats['databases_processed'] += 1
            
        except Exception as e:
            error_msg = f"Error processing database {db_path}: {e}"
            self.safe_print(f"    [ERROR] {error_msg}")
            logger.error(error_msg)
            self.stats['errors'] += 1

    def find_sqlite_files(self, folder_path, recursive=False):
        """Find all SQLite files in a folder"""
        sqlite_files = []
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            logger.error(f"Folder does not exist: {folder_path}")
            return []
        
        # Look for common SQLite file extensions
        extensions = ['.sqlite', '.db', '.sqlite3', '.db3', '.s3db', '.sl3']
        
        try:
            if recursive:
                pattern = "**/*"
            else:
                pattern = "*"
            
            for file_path in folder_path.glob(pattern):
                if file_path.is_file():
                    # Check by extension first
                    if any(file_path.name.lower().endswith(ext) for ext in extensions):
                        sqlite_files.append(file_path)
                    # Also check files without extension that might be SQLite databases
                    elif self.is_valid_sqlite_database(file_path):
                        sqlite_files.append(file_path)
        
        except Exception as e:
            logger.error(f"Error searching for SQLite files in {folder_path}: {e}")
        
        return sqlite_files

    def export_folder(self, folder_path, recursive=False, tables=None, limit=None):
        """Export all SQLite databases in a folder"""
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            self.safe_print(f"[ERROR] Folder does not exist: {folder_path}")
            return
        
        sqlite_files = self.find_sqlite_files(folder_path, recursive)
        self.safe_print(f"Found {len(sqlite_files)} SQLite files in {folder_path}")
        
        for db_file in sqlite_files:
            self.export_database(db_file, tables, limit, recursive)

    def print_summary(self):
        """Print export summary"""
        summary_lines = [
            "\n" + "="*50,
            "EXPORT SUMMARY",
            "="*50,
            f"SUCCESS - Databases processed: {self.stats['databases_processed']}",
            f"SUCCESS - Tables exported: {self.stats['tables_exported']}",
            f"WARNING - Files skipped: {self.stats['files_skipped']}",
            f"ERROR - Errors encountered: {self.stats['errors']}",
            f"OUTPUT - Output directory: {self.output_dir.absolute()}",
            "="*50
        ]
        
        for line in summary_lines:
            self.safe_print(line)

def main():
    parser = argparse.ArgumentParser(
        description="Professional SQLite Database Exporter for Forensic Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sqlite_exporter.py --file /path/to/database.sqlite
  python sqlite_exporter.py --folder /path/to/folder --recursive
  python sqlite_exporter.py --file History --tables urls,visits --limit 100
  python sqlite_exporter.py --folder C:\\forensic_data --output C:\\exports --recursive
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', help='Single SQLite database file to export')
    group.add_argument('--folder', help='Folder containing SQLite databases')
    
    parser.add_argument('--recursive', action='store_true', 
                       help='Include subfolders when using --folder')
    parser.add_argument('--output', default='./sqlite_exports',
                       help='Output directory for CSV files (default: ./sqlite_exports)')
    parser.add_argument('--tables', 
                       help='Comma-separated list of specific tables to export')
    parser.add_argument('--limit', type=int,
                       help='Limit number of rows exported per table (for preview)')
    parser.add_argument('--sqlite-binary',
                       help='Path to external SQLite binary (e.g., sqlite3.exe)')
    
    args = parser.parse_args()
    
    # Set up exporter
    exporter = SQLiteExporter(
        output_dir=args.output,
        use_external_binary=args.sqlite_binary
    )
    
    # Parse tables list
    tables = None
    if args.tables:
        tables = [t.strip() for t in args.tables.split(',')]
    
    try:
        exporter.safe_print("STARTING SQLite Database Export")
        exporter.safe_print("="*50)
        
        if args.file:
            exporter.export_database(args.file, tables, args.limit)
        elif args.folder:
            exporter.export_folder(args.folder, args.recursive, tables, args.limit)
        
        exporter.print_summary()
        
    except KeyboardInterrupt:
        exporter.safe_print("\n[INFO] Export interrupted by user")
        logger.info("Export interrupted by user")
    except Exception as e:
        error_msg = f"Fatal error during export: {e}"
        exporter.safe_print(f"[FATAL] {error_msg}")
        logger.error(error_msg, exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
