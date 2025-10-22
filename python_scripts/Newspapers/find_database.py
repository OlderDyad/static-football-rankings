import pyodbc

def find_databases():
    """Find all databases on each SQL Server instance"""
    
    print("=== Finding HS-Football Database ===")
    
    servers = [
        'McKnights-PC',  # Default instance
        'McKnights-PC\\SQLEXPRESS',
        'McKnights-PC\\SQLEXPRESS01'
    ]
    
    for server in servers:
        print(f"\n{'='*60}")
        print(f"Checking server: {server}")
        print('='*60)
        
        try:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server};"
                f"Trusted_Connection=yes;"
                f"CONNECTION TIMEOUT=5;"
            )
            
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            
            # List all databases
            cursor.execute("""
                SELECT name, database_id, create_date 
                FROM sys.databases 
                WHERE state = 0  -- Online databases only
                ORDER BY name
            """)
            
            databases = cursor.fetchall()
            
            print(f"Found {len(databases)} databases:")
            found_football = False
            
            for db in databases:
                db_name = db[0]
                print(f"  - {db_name}")
                
                # Check for variations of our database name
                if any(keyword in db_name.lower() for keyword in ['football', 'hs-football', 'highschool']):
                    print(f"    ⭐ POSSIBLE MATCH: {db_name}")
                    found_football = True
                    
                    # Check if it has our table
                    try:
                        cursor.execute(f"USE [{db_name}]")
                        cursor.execute("""
                            SELECT COUNT(*) 
                            FROM INFORMATION_SCHEMA.TABLES 
                            WHERE TABLE_NAME = 'HS_Team_Name_Alias'
                        """)
                        table_exists = cursor.fetchone()[0]
                        
                        if table_exists:
                            cursor.execute("SELECT COUNT(*) FROM dbo.HS_Team_Name_Alias")
                            alias_count = cursor.fetchone()[0]
                            print(f"    🎯 FOUND IT! {alias_count} aliases in HS_Team_Name_Alias table")
                            
                            # This is our database!
                            print(f"\n🏆 YOUR DATABASE IS HERE:")
                            print(f"   Server: {server}")
                            print(f"   Database: {db_name}")
                            print(f"   Aliases: {alias_count}")
                    except Exception as e:
                        print(f"    ❌ Error checking table: {e}")
            
            if not found_football:
                print("  ⚠️ No football-related databases found")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
    
    print(f"\n{'='*60}")
    print("SEARCH COMPLETE")
    print('='*60)

if __name__ == "__main__":
    find_databases()
