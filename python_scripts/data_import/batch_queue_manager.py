# batch_queue_manager.py
# Manages queued batches waiting for standardization and final import

import os
import json
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
import pandas as pd
import sys

# === CONFIGURATION ===
STAGING_DIRECTORY = "J:/Users/demck/Google Drive/Documents/Football/HSF/Newspapers/Staged"
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
        'status': 'staged',  # staged -> standardized -> imported
        'created_at': datetime.now().isoformat(),
        'file_count': file_count,
        'game_count': game_count,
        'source_files': source_files,
        'standardized_at': None,
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
    standardized = [b for b in queue['batches'] if b['status'] == 'standardized']
    imported = [b for b in queue['batches'] if b['status'] == 'imported']
    
    print(f"\n📊 Summary:")
    print(f"  - Staged (ready for standardization): {len(staged)}")
    print(f"  - Standardized (ready for import): {len(standardized)}")
    print(f"  - Imported (complete): {len(imported)}")
    
    if staged:
        print(f"\n🔵 STAGED BATCHES (ready for standardization):")
        for b in staged:
            print(f"  • {b['batch_id'][:8]}... | {b['game_count']} games | {b['file_count']} files | {b['created_at'][:10]}")
    
    if standardized:
        print(f"\n🟢 STANDARDIZED BATCHES (ready for import):")
        for b in standardized:
            print(f"  • {b['batch_id'][:8]}... | {b['game_count']} games | Standardized: {b['standardized_at'][:10]}")
    
    if imported:
        print(f"\n✅ IMPORTED BATCHES (complete):")
        for b in imported[-5:]:  # Show last 5
            print(f"  • {b['batch_id'][:8]}... | {b['game_count']} games | Imported: {b['imported_at'][:10]}")
        if len(imported) > 5:
            print(f"  ... and {len(imported) - 5} more")
    
    print("\n" + "="*80 + "\n")

def mark_batch_standardized(batch_id):
    """Mark a batch as standardized."""
    queue = load_queue()
    for batch in queue['batches']:
        if batch['batch_id'] == batch_id:
            batch['status'] = 'standardized'
            batch['standardized_at'] = datetime.now().isoformat()
            save_queue(queue)
            logger.info(f"✅ Batch {batch_id} marked as standardized")
            return True
    logger.error(f"Batch {batch_id} not found in queue")
    return False

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

# === BATCH PROCESSING ===

def standardize_all_staged():
    """Standardize all batches that are in 'staged' status."""
    queue = load_queue()
    staged_batches = [b for b in queue['batches'] if b['status'] == 'staged']
    
    if not staged_batches:
        print("\n📭 No staged batches to standardize\n")
        return
    
    print(f"\n🔧 Standardizing {len(staged_batches)} batches...\n")
    
    with engine.begin() as connection:
        for batch in staged_batches:
            batch_id = batch['batch_id']
            logger.info(f"Standardizing batch: {batch_id}")
            
            try:
                query = text(f"EXEC dbo.sp_StandardizeStagedScores_v2 @BatchID = '{batch_id}';")
                connection.execute(query)
                mark_batch_standardized(batch_id)
                logger.info(f"✅ Batch {batch_id} standardized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to standardize batch {batch_id}: {e}")
    
    print(f"\n✅ Standardization complete for {len(staged_batches)} batches\n")

def import_all_standardized():
    """Import all batches that are in 'standardized' status."""
    queue = load_queue()
    standardized_batches = [b for b in queue['batches'] if b['status'] == 'standardized']
    
    if not standardized_batches:
        print("\n📭 No standardized batches to import\n")
        return
    
    print(f"\n📥 Importing {len(standardized_batches)} batches to HS_Scores...\n")
    
    with engine.begin() as connection:
        for batch in standardized_batches:
            batch_id = batch['batch_id']
            logger.info(f"Importing batch: {batch_id}")
            
            try:
                # Your final import procedure - adjust this to match your actual SP name
                query = text(f"EXEC dbo.sp_ImportFromStaging @BatchID = '{batch_id}';")
                connection.execute(query)
                mark_batch_imported(batch_id)
                logger.info(f"✅ Batch {batch_id} imported successfully")
            except Exception as e:
                logger.error(f"❌ Failed to import batch {batch_id}: {e}")
    
    print(f"\n✅ Import complete for {len(standardized_batches)} batches\n")

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
        print("2. Standardize all staged batches")
        print("3. Import all standardized batches")
        print("4. Process all (standardize + import)")
        print("5. Mark batch as standardized (manual)")
        print("6. Mark batch as imported (manual)")
        print("7. Exit")
        print("="*60)
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            show_queue_status()
        
        elif choice == '2':
            standardize_all_staged()
        
        elif choice == '3':
            import_all_standardized()
        
        elif choice == '4':
            standardize_all_staged()
            import_all_standardized()
        
        elif choice == '5':
            batch_id = input("Enter BatchID: ").strip()
            mark_batch_standardized(batch_id)
        
        elif choice == '6':
            batch_id = input("Enter BatchID: ").strip()
            mark_batch_imported(batch_id)
        
        elif choice == '7':
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