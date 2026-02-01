# batch_queue_manager.py
# Manages queued batches waiting for standardization and final import

import os
import json
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
import pandas as pd
import sys
import shutil

# === CONFIGURATION ===
STAGING_DIRECTORY = "J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"
COMPLETED_DIRECTORY = "C:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Completed"
QUEUE_FILE = os.path.join(STAGING_DIRECTORY, 'batch_queue.json')
SERVER_NAME = "McKnights-PC\\SQLEXPRESS01"
DATABASE_NAME = "hs_football_database"

# === Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
db_connection_str = f'mssql+pyodbc://{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
engine = create_engine(db_connection_str)

# === QUEUE MANAGEMENT ===

def load_queue():
    """Load the batch queue from disk."""
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, 'r') as f:
            return json.load(f)
    return {'batches': []}

def save_queue(queue_data):
    """Save the batch queue to disk."""
    with open(QUEUE_FILE, 'w') as f:
        json.dump(queue_data, f, indent=2)
    logger.info(f"Queue saved with {len(queue_data['batches'])} batches")

def add_batch_to_queue(batch_id, file_count, game_count, source_files):
    """Add a new batch to the queue."""
    queue = load_queue()
    
    # Check if batch already exists
    existing = [b for b in queue['batches'] if b['batch_id'] == batch_id]
    if existing:
        logger.warning(f"Batch {batch_id} already in queue. Skipping.")
        return
    
    batch_info = {
        'batch_id': batch_id,
        'status': 'staged',  # staged -> imported
        'created_at': datetime.now().isoformat(),
        'file_count': file_count,
        'game_count': game_count,
        'source_files': source_files,
        'imported_at': None
    }
    
    queue['batches'].append(batch_info)
    save_queue(queue)
    logger.info(f"✅ Added batch {batch_id} to queue ({game_count} games from {file_count} files)")

def show_queue_status():
    """Display current queue status."""
    queue = load_queue()
    
    if not queue['batches']:
        print("\n📭 Queue is empty\n")
        return
    
    print("\n" + "="*80)
    print("BATCH QUEUE STATUS")
    print("="*80)
    
    staged = [b for b in queue['batches'] if b['status'] == 'staged']
    imported = [b for b in queue['batches'] if b['status'] == 'imported']
    
    print(f"\n📊 Summary:")
    print(f"  - Staged (ready to import to HS_Scores): {len(staged)}")
    print(f"  - Imported (in HS_Scores table): {len(imported)}")
    
    if staged:
        print(f"\n🔵 STAGED BATCHES (ready to import):")
        for b in staged:
            print(f"  • {b['batch_id'][:8]}... | {b['game_count']} games | {b['file_count']} files | {b['created_at'][:10]}")
    
    if imported:
        print(f"\n✅ IMPORTED BATCHES (complete):")
        for b in imported[-5:]:  # Show last 5
            print(f"  • {b['batch_id'][:8]}... | {b['game_count']} games | Imported: {b['imported_at'][:10]}")
        if len(imported) > 5:
            print(f"  ... and {len(imported) - 5} more")
    
    print("\n" + "="*80 + "\n")

def mark_batch_imported(batch_id):
    """Mark a batch as imported."""
    queue = load_queue()
    for batch in queue['batches']:
        if batch['batch_id'] == batch_id:
            batch['status'] = 'imported'
            batch['imported_at'] = datetime.now().isoformat()
            save_queue(queue)
            logger.info(f"✅ Batch {batch_id} marked as imported")
            return True
    logger.error(f"Batch {batch_id} not found in queue")
    return False

def move_source_files_to_completed(batch_info):
    """Move source CSV files to completed directory after successful import."""
    if not os.path.exists(COMPLETED_DIRECTORY):
        os.makedirs(COMPLETED_DIRECTORY)
        logger.info(f"Created completed directory: {COMPLETED_DIRECTORY}")
    
    source_files = batch_info.get('source_files', [])
    moved_count = 0
    failed_files = []
    
    for filename in source_files:
        source_path = os.path.join(STAGING_DIRECTORY, filename)
        dest_path = os.path.join(COMPLETED_DIRECTORY, filename)
        
        try:
            if os.path.exists(source_path):
                shutil.move(source_path, dest_path)
                moved_count += 1
                logger.info(f"Moved {filename} to completed directory")
            else:
                logger.warning(f"Source file not found: {filename}")
                failed_files.append(filename)
        except Exception as e:
            logger.error(f"Failed to move {filename}: {e}")
            failed_files.append(filename)
    
    if moved_count > 0:
        logger.info(f"✅ Moved {moved_count} CSV files to completed directory")
    if failed_files:
        logger.warning(f"⚠️  Could not move {len(failed_files)} files: {', '.join(failed_files)}")
    
    return moved_count, failed_files

# === BATCH PROCESSING ===

def import_all_staged():
    """Import all batches from RawScores_Staging directly to HS_Scores."""
    queue = load_queue()
    staged_batches = [b for b in queue['batches'] if b['status'] == 'staged']
    
    if not staged_batches:
        print("\n📭 No staged batches to import\n")
        return
    
    print(f"\n📥 Importing {len(staged_batches)} batches to HS_Scores...\n")
    
    total_moved = 0
    total_failed = []
    
    with engine.begin() as connection:
        for batch in staged_batches:
            batch_id = batch['batch_id']
            logger.info(f"Importing batch: {batch_id}")
            
            try:
                # Insert from staging to HS_Scores using correct column names
                query = text(f"""
                    INSERT INTO HS_Scores (ID, Season, Date, Home, Visitor, Home_Score, Visitor_Score, OT, Forfeit)
                    SELECT NEWID(), Season, GameDate, HomeTeamRaw, VisitorTeamRaw, HomeScore, VisitorScore, 
                           CASE WHEN Overtime IS NOT NULL AND Overtime <> '' THEN 1 ELSE 0 END,
                           CASE WHEN (HomeScore + VisitorScore) = 1 THEN 1 ELSE 0 END
                    FROM RawScores_Staging
                    WHERE BatchID = '{batch_id}'
                """)
                result = connection.execute(query)
                rows_imported = result.rowcount
                
                # Mark as imported first
                mark_batch_imported(batch_id)
                logger.info(f"✅ Batch {batch_id} imported successfully ({rows_imported} games)")
                
                # Move CSV files to completed directory
                moved, failed = move_source_files_to_completed(batch)
                total_moved += moved
                total_failed.extend(failed)
                
            except Exception as e:
                logger.error(f"❌ Failed to import batch {batch_id}: {e}")
    
    print(f"\n✅ Import complete for {len(staged_batches)} batches")
    print(f"📁 Moved {total_moved} CSV files to completed directory")
    
    if total_failed:
        print(f"⚠️  Warning: Could not move {len(total_failed)} files")
        print(f"   Files: {', '.join(total_failed[:5])}")
        if len(total_failed) > 5:
            print(f"   ... and {len(total_failed) - 5} more")
    
    print(f"\n⚠️  IMPORTANT: Run duplicate removal next:")
    print(f"   EXEC [dbo].[RemoveDuplicateGamesParameterized] @SeasonStart = 1877, @SeasonEnd = 2025;\n")

def verify_batch_in_staging(batch_id):
    """Verify that a batch exists in RawScores_Staging."""
    query = text(f"SELECT COUNT(*) as cnt FROM dbo.RawScores_Staging WHERE BatchID = '{batch_id}'")
    with engine.connect() as conn:
        result = conn.execute(query).fetchone()
        return result[0] > 0 if result else False

# === MAIN MENU ===

def main():
    """Interactive menu for batch queue management."""
    while True:
        print("\n" + "="*60)
        print("BATCH QUEUE MANAGER")
        print("="*60)
        print("1. Show queue status")
        print("2. Import all staged batches to HS_Scores")
        print("3. Mark batch as imported (manual)")
        print("4. Exit")
        print("="*60)
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            show_queue_status()
        
        elif choice == '2':
            import_all_staged()
        
        elif choice == '3':
            batch_id = input("Enter BatchID: ").strip()
            mark_batch_imported(batch_id)
        
        elif choice == '4':
            print("\n👋 Goodbye!\n")
            break
        
        else:
            print("\n❌ Invalid option\n")

if __name__ == "__main__":
    # Allow adding a batch from command line
    if len(sys.argv) > 1 and sys.argv[1] == 'add':
        if len(sys.argv) < 5:
            print("Usage: python batch_queue_manager.py add <batch_id> <file_count> <game_count> [source_file1,source_file2,...]")
            sys.exit(1)
        
        batch_id = sys.argv[2]
        file_count = int(sys.argv[3])
        game_count = int(sys.argv[4])
        source_files = sys.argv[5].split(',') if len(sys.argv) > 5 else []
        
        add_batch_to_queue(batch_id, file_count, game_count, source_files)
    else:
        main()