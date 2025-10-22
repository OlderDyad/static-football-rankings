import pyodbc
from sqlalchemy import create_engine
import sys

def test_instances():
    """Test connection to different SQL Server instances"""
    
    # Different instances to try
    instances = [
        'DESKTOP-5JLHK21',  # Default instance (MSSQLSERVER)
        'DESKTOP-5JLHK21\\SQLEXPRESS',
        'DESKTOP-5JLHK21\\SQLEXPRESS01',
    ]
    
    results = {}
    
    for instance in instances:
        print(f"\n{'='*50}")
        print(f"Testing instance: {instance}")
        print('='*50)
        
        # Test connection to master database first
        try:
            conn_str = (
                f'DRIVER={{ODBC Driver 17 for SQL Server}};'
                f'SERVER={instance};'
                f'DATABASE=master;'
                f'Trusted_Connection=yes;'
                f'Connection Timeout=10;'
            )
            
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            
            # List all databases on this instance
            cursor.execute("SELECT name FROM sys.databases WHERE state = 0")
            databases = [row[0] for row in cursor.fetchall()]
            
            print(f"✅ Connected to {instance}")
            print(f"Databases found: {databases}")
            
            # Check if our target database exists
            if 'HS-Football' in databases:
                print(f"🎯 Found 'HS-Football' database on {instance}!")
                
                # Test connection to our database
                cursor.execute("USE [HS-Football]")
                
                # Check our table
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME = 'HS_Team_Name_Alias'
                """)
                table_exists = cursor.fetchone()[0]
                
                if table_exists:
                    print("✅ HS_Team_Name_Alias table found!")
                    
                    # Count aliases
                    cursor.execute("SELECT COUNT(*) FROM dbo.HS_Team_Name_Alias")
                    alias_count = cursor.fetchone()[0]
                    print(f"📊 Total aliases: {alias_count}")
                    
                    results[instance] = {
                        'status': 'success',
                        'has_database': True,
                        'has_table': True,
                        'alias_count': alias_count
                    }
                else:
                    print("❌ HS_Team_Name_Alias table not found")
                    results[instance] = {
                        'status': 'success',
                        'has_database': True,
                        'has_table': False
                    }
            else:
                print("❌ 'HS-Football' database not found")
                results[instance] = {
                    'status': 'success',
                    'has_database': False,
                    'has_table': False
                }
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            results[instance] = {
                'status': 'failed',
                'error': str(e)
            }
    
    return results

def test_sqlalchemy_connections(target_instance):
    """Test SQLAlchemy connection to the target instance"""
    print(f"\n{'='*50}")
    print(f"Testing SQLAlchemy connection to: {target_instance}")
    print('='*50)
    
    # Different connection string formats to try
    if target_instance == 'DESKTOP-5JLHK21':
        # Default instance
        connection_strings = [
            'mssql+pyodbc://DESKTOP-5JLHK21/HS-Football?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes',
            'mssql+pyodbc://./HS-Football?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes',
        ]
    else:
        # Named instance
        escaped_instance = target_instance.replace('\\', '%5C')
        connection_strings = [
            f'mssql+pyodbc://{target_instance}/HS-Football?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes',
            f'mssql+pyodbc://{escaped_instance}/HS-Football?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes',
        ]
    
    for i, conn_str in enumerate(connection_strings):
        print(f"\nTrying connection string #{i+1}:")
        print(conn_str)
        
        try:
            engine = create_engine(conn_str)
            conn = engine.connect()
            
            # Test query
            result = conn.execute("SELECT COUNT(*) FROM dbo.HS_Team_Name_Alias").fetchone()
            print(f"✅ Success! Alias count: {result[0]}")
            
            conn.close()
            engine.dispose()
            return conn_str
            
        except Exception as e:
            print(f"❌ Failed: {e}")
    
    return None

def main():
    print("=== SQL Server Instance and Database Discovery ===")
    
    # Test all instances
    results = test_instances()
    
    # Find the correct instance
    correct_instance = None
    for instance, result in results.items():
        if (result.get('status') == 'success' and 
            result.get('has_database') and 
            result.get('has_table')):
            correct_instance = instance
            break
    
    # Summary
    print(f"\n{'='*50}")
    print("SUMMARY")
    print('='*50)
    
    for instance, result in results.items():
        status = "✅" if result.get('status') == 'success' else "❌"
        has_db = "✅" if result.get('has_database') else "❌"
        has_table = "✅" if result.get('has_table') else "❌"
        
        print(f"\n{instance}:")
        print(f"  Connection: {status}")
        print(f"  Has HS-Football DB: {has_db}")
        print(f"  Has HS_Team_Name_Alias table: {has_table}")
        
        if result.get('alias_count'):
            print(f"  Alias count: {result['alias_count']}")
    
    if correct_instance:
        print(f"\n🎯 FOUND IT! Use this instance: {correct_instance}")
        
        # Test SQLAlchemy connections
        working_conn_str = test_sqlalchemy_connections(correct_instance)
        
        if working_conn_str:
            print(f"\n✅ Working SQLAlchemy connection string:")
            print(working_conn_str)
            print(f"\nUpdate your script with:")
            print(f"server = '{correct_instance}'")
            print(f"connection_string = '{working_conn_str}'")
        else:
            print("\n❌ Could not establish SQLAlchemy connection")
    else:
        print("\n❌ Could not find the correct instance with your database")

if __name__ == "__main__":
    main()
