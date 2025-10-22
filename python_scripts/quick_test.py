
import pyodbc
import os

def quick_test():
    """Quick test of SQL Server connection"""
    
    print("=== Quick SQL Server Test ===")
    
    # Check available drivers
    print("Available ODBC drivers:")
    for driver in pyodbc.drivers():
        print(f"  - {driver}")
    
    # Test different server names
    servers = [
        '.',  # Local default instance
        '.\\SQLEXPRESS',
        '.\\SQLEXPRESS01', 
        'DESKTOP-5JLHK21',
        'DESKTOP-5JLHK21\\SQLEXPRESS',
        'DESKTOP-5JLHK21\\SQLEXPRESS01',
        '(local)',
        '(local)\\SQLEXPRESS',
        '(local)\\SQLEXPRESS01'
    ]
    
    for server in servers:
        print(f"\nTrying server: {server}")
        try:
            # Simple connection string
            conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};Trusted_Connection=yes;CONNECTION TIMEOUT=5;"
            
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            
            # Get server info
            cursor.execute("SELECT @@SERVERNAME as ServerName, @@VERSION as Version")
            row = cursor.fetchone()
            print(f"  ✅ SUCCESS!")
            print(f"     Server: {row.ServerName}")
            print(f"     Version: {row.Version.split('\\n')[0]}")
            
            # Check for our database
            cursor.execute("SELECT name FROM sys.databases WHERE name = 'HS-Football'")
            db = cursor.fetchone()
            
            if db:
                print(f"  🎯 'HS-Football' database FOUND!")
                
                # Test our table
                cursor.execute("USE [HS-Football]")
                cursor.execute("SELECT COUNT(*) FROM dbo.HS_Team_Name_Alias")
                count = cursor.fetchone()[0]
                print(f"  📊 HS_Team_Name_Alias has {count} records")
                
                # This is our correct server!
                print(f"\n🏆 FOUND THE RIGHT SERVER: {server}")
                print("Update your script with:")
                print(f"server = '{server}'")
                
            else:
                print(f"  ❌ 'HS-Football' database not found")
            
            conn.close()
            
        except Exception as e:
            print(f"  ❌ Failed: {str(e)[:100]}")

if __name__ == "__main__":
    quick_test()
