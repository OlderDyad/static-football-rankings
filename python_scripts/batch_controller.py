"""
Batch Controller - Manage multi-batch scraping with monitoring
"""

import subprocess
import time
import csv
import os
from datetime import datetime
from collections import Counter

def get_stats():
    """Get current scraping statistics"""
    try:
        # Count visited teams
        with open('scraper_progress.csv', 'r') as f:
            visited = len(list(csv.DictReader(f)))
        
        # Count queue
        with open('scraper_queue.csv', 'r') as f:
            queue = len(list(csv.DictReader(f)))
        
        # Count total games
        import glob
        csv_files = glob.glob('scorestream_batch_*.csv')
        total_games = 0
        regions = []
        
        for csv_file in csv_files:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    total_games += 1
                    if row.get('HostState'):
                        regions.append(row['HostState'])
                    if row.get('OpponentState'):
                        regions.append(row['OpponentState'])
        
        region_counts = Counter(regions)
        
        return {
            'visited': visited,
            'queue': queue,
            'games': total_games,
            'regions': region_counts
        }
    except FileNotFoundError:
        return {
            'visited': 0,
            'queue': 0,
            'games': 0,
            'regions': {}
        }

def display_stats(stats, batch_num):
    """Display current statistics"""
    print(f"\n{'='*70}")
    print(f"📊 BATCH #{batch_num} STATISTICS")
    print(f"{'='*70}")
    print(f"✅ Teams visited: {stats['visited']}")
    print(f"📋 Teams in queue: {stats['queue']}")
    print(f"🏈 Total games: {stats['games']}")
    
    if stats['regions']:
        print(f"\n🗺️  Games by Region:")
        for region, count in stats['regions'].most_common():
            print(f"   {region}: {count}")
    
    print(f"{'='*70}\n")

def should_continue():
    """Ask user if they want to continue"""
    while True:
        response = input("Continue with next batch? (y/n/stats): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        elif response in ['s', 'stats']:
            stats = get_stats()
            display_stats(stats, 'Current')
        else:
            print("Please enter 'y' for yes, 'n' for no, or 'stats' for statistics")

def merge_batch_files():
    """Merge all batch files into one master file"""
    import glob
    import pandas as pd
    
    csv_files = sorted(glob.glob('scorestream_batch_*.csv'))
    
    if not csv_files:
        print("⚠️  No batch files to merge")
        return None
    
    print(f"\n🔄 Merging {len(csv_files)} batch files...")
    
    all_data = []
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        all_data.append(df)
    
    merged_df = pd.concat(all_data, ignore_index=True)
    
    # Remove duplicates (same game link)
    original_count = len(merged_df)
    merged_df = merged_df.drop_duplicates(subset=['GameLink'], keep='first')
    removed = original_count - len(merged_df)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"scorestream_merged_{timestamp}.csv"
    merged_df.to_csv(output_file, index=False)
    
    print(f"✅ Merged file: {output_file}")
    print(f"   Total games: {len(merged_df)}")
    print(f"   Duplicates removed: {removed}")
    
    return output_file

def run_batch_scraper(batch_num, resume=False):
    """Run one batch of scraping"""
    print(f"\n{'='*70}")
    print(f"🚀 STARTING BATCH #{batch_num}")
    print(f"{'='*70}")
    print(f"Mode: {'Resume' if resume else 'Continue from queue'}")
    print(f"Press Ctrl+C in scraper window to stop early and save progress")
    print(f"{'='*70}\n")
    
    time.sleep(2)
    
    # Note: In actual use, you'd import and call the function directly
    # This is just showing the structure
    from scorestream_batch_scraper import scrape_scorestream_batch
    
    try:
        games, remaining = scrape_scorestream_batch(resume=resume)
        return True, len(games), len(remaining)
    except KeyboardInterrupt:
        print("\n⚠️  Batch stopped by user")
        return False, 0, 0
    except Exception as e:
        print(f"\n❌ Error in batch: {e}")
        return False, 0, 0

def main():
    """Main batch controller"""
    print("="*70)
    print("🎮 SCORESTREAM BATCH CONTROLLER")
    print("="*70)
    print("This will run the scraper in batches, allowing you to:")
    print("  - Monitor progress between batches")
    print("  - Assess regional drift")
    print("  - Stop and resume at any time")
    print("="*70)
    
    batch_num = 1
    total_batches = 0
    total_games = 0
    
    # Check if resuming
    stats = get_stats()
    if stats['visited'] > 0 or stats['queue'] > 0:
        print(f"\n📂 Existing progress detected:")
        display_stats(stats, 'Current')
        
        resume = input("Resume from saved progress? (y/n): ").lower().strip() == 'y'
    else:
        resume = False
        print("\n🆕 Starting fresh scrape")
    
    while True:
        # Show stats before batch
        stats = get_stats()
        
        if stats['queue'] == 0 and batch_num > 1:
            print("\n✅ Queue is empty - scraping complete!")
            break
        
        # Run batch
        success, games, remaining = run_batch_scraper(batch_num, resume=resume)
        resume = True  # After first batch, always resume from queue
        
        if success:
            total_batches += 1
            total_games += games
            
            # Show updated stats
            stats = get_stats()
            display_stats(stats, batch_num)
            
            # Check if done
            if remaining == 0:
                print("✅ All queued teams processed!")
                break
            
            # Ask to continue
            if not should_continue():
                print("\n⏸️  Pausing scraper. Progress saved.")
                print(f"   To resume: Run this script again")
                break
            
            batch_num += 1
        else:
            print("\n⚠️  Batch did not complete successfully")
            print("   Progress has been saved. You can resume later.")
            break
    
    # Final summary
    print(f"\n{'='*70}")
    print(f"🏁 SCRAPING SESSION COMPLETE")
    print(f"{'='*70}")
    print(f"Batches completed: {total_batches}")
    
    stats = get_stats()
    print(f"Teams visited: {stats['visited']}")
    print(f"Teams remaining: {stats['queue']}")
    print(f"Total games: {stats['games']}")
    
    if stats['regions']:
        print(f"\n🗺️  Coverage by Region:")
        for region, count in stats['regions'].most_common():
            pct = count / sum(stats['regions'].values()) * 100
            print(f"   {region}: {count} ({pct:.1f}%)")
    
    # Offer to merge
    if total_batches > 1:
        merge = input("\nMerge all batch files into one? (y/n): ").lower().strip() == 'y'
        if merge:
            merged_file = merge_batch_files()
            if merged_file:
                print(f"\n✅ Ready for analysis/SQL import: {merged_file}")
    
    print("\n✨ Done!")

if __name__ == "__main__":
    main()
