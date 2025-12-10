"""
Run ScoreStream scraper with opponent seeds
"""

from scorestream_batch_scraper import scrape_scorestream_batch

print("="*70)
print("🌱 LOADING OPPONENT SEEDS")
print("="*70)

# Load opponent seeds
with open('opponent_seeds.txt', 'r', encoding='utf-8') as f:
    seed_urls = [line.strip() for line in f 
                 if line.strip() and line.startswith('http')]

print(f"✅ Loaded {len(seed_urls)} opponent seed URLs")
print(f"\nStarting scraper with these seeds...")
print("="*70)

try:
    # Run scraper with opponent seeds
    games, remaining = scrape_scorestream_batch(start_urls=seed_urls, resume=False)
    
    print("\n" + "="*70)
    print("✅ BATCH COMPLETE")
    print("="*70)
    print(f"Games scraped: {len(games)}")
    print(f"Teams remaining in queue: {len(remaining)}")
    
except KeyboardInterrupt:
    print("\n🛑 Stopped by user (Ctrl+C)")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()