import pyodbc
import platform

def test_sql_connections():
    """Test SQL Server connections with different server names"""
    
    print("=== SQL Server Connection Test ===")
    print(f"Computer: {platform.node()}")
    
    # Check available drivers
    print("\nAvailable ODBC drivers:")
    drivers = pyodbc.drivers()
    for driver in drivers:
        print(f"  - {driver}")
    
    # Different server names to try
    servers = [
        '.',  # Local default instance
        '.\\SQLEXPRESS',
        '.\\SQLEXPRESS01', 
        'McKnights-PC',  # Using the actual computer name
        'McKnights-PC\\SQLEXPRESS',
        'McKnights-PC\\SQLEXPRESS01',
        'DESKTOP-5JLHK21',  # Original name from script
        'DESKTOP-5JLHK21\\SQLEXPRESS',
        'DESKTOP-5JLHK21\\SQLEXPRESS01',
        '(local)',
        '(local)\\SQLEXPRESS',
        '(local)\\SQLEXPRESS01'
    ]
    
    successful_connections = []
    
    for server in servers:
        print(f"\n{'='*50}")
        print(f"Testing server: {server}")
        print('='*50)
        
        try:
            # Simple connection string with timeout
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server};"
                f"Trusted_Connection=yes;"
                f"CONNECTION TIMEOUT=5;"
            )
            
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            
            # Get server info
            cursor.execute("SELECT @@SERVERNAME as ServerName, @@VERSION as Version")
            row = cursor.fetchone()
            server_name = row[0]
            version = row[1]
            
            print(f"✅ SUCCESS!")
            print(f"   Server Name: {server_name}")
            # Split version to avoid backslash in f-string
            version_parts = version.split('\n')
            print(f"   Version: {version_parts[0]}")
            
            # Check for our database
            cursor.execute("SELECT name FROM sys.databases WHERE name = 'HS-Football'")
            db = cursor.fetchone()
            
            if db:
                print(f"🎯 'HS-Football' database FOUND!")
                
                # Test our table
                cursor.execute("USE [HS-Football]")
                cursor.execute("SELECT COUNT(*) FROM dbo.HS_Team_Name_Alias")
                count = cursor.fetchone()[0]
                print(f"📊 HS_Team_Name_Alias has {count} records")
                
                # Save this as a successful connection
                successful_connections.append({
                    'server': server,
                    'actual_name': server_name,
                    'alias_count': count
                })
                
            else:
                print(f"❌ 'HS-Football' database not found")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Failed: {str(e)[:150]}...")
    
    # Summary
    print(f"\n{'='*50}")
    print("SUMMARY")
    print('='*50)
    
    if successful_connections:
        print("✅ Found working connections:")
        for conn in successful_connections:
            print(f"\n🏆 Server: {conn['server']}")
            print(f"   Actual name: {conn['actual_name']}")
            print(f"   Alias count: {conn['alias_count']}")
        
        # Recommend the first working connection
        best_conn = successful_connections[0]
        print(f"\n🎯 RECOMMENDED SERVER: {best_conn['server']}")
        print("\nUpdate your main script with:")
        print(f"server = '{best_conn['server']}'")
        
        # Generate the correct connection string
        if '\\' in best_conn['server']:
            # Named instance - need URL encoding for SQLAlchemy
            encoded_server = best_conn['server'].replace('\\', '%5C')
            conn_str = f"mssql+pyodbc://{encoded_server}/HS-Football?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
        else:
            # Default instance
            conn_str = f"mssql+pyodbc://{best_conn['server']}/HS-Football?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
        
        print(f"connection_string = '{conn_str}'")
        
    else:
        print("❌ No working connections found!")
        print("\nTroubleshooting:")
        print("1. Open SQL Server Configuration Manager")
        print("2. Enable TCP/IP and Named Pipes for all instances")
        print("3. Restart SQL Server services")
        print("4. Check if Windows Firewall is blocking connections")
        print("5. Try running this script as Administrator")

if __name__ == "__main__":
    test_sql_connections()
