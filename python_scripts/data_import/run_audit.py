# run_audit.py

import sys
import pyodbc
import logging

# === CONFIGURATION ===
DB_CONNECTION_STR = (
    r'DRIVER={ODBC Driver 17 for SQL Server};'
    r'SERVER=localhost,51062;' 
    r'DATABASE=hs_football_database;'
    r'Trusted_Connection=yes;'
)

# === Boilerplate Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_audit_recommendation(cursor):
    """Calls the stored procedure to get the next recommended action."""
    cursor.execute("{CALL dbo.sp_GetNextAuditAction}")
    result = cursor.fetchone()
    return result[0] if result else "No recommendation returned."

def get_review_queue(cursor, batch_id):
    """
    Fetches records from the staging table that are flagged for review OR verification.
    """
    # Added SourceFile to the SELECT list
    sql = """
        SELECT SourceFile, HomeTeamRaw, HomeScore, VisitorTeamRaw, VisitorScore, quality_status, processing_notes
        FROM dbo.RawScores_Staging
        WHERE BatchID = ? AND quality_status IN ('needs_review', 'needs_verification')
        ORDER BY quality_status;
    """
    cursor.execute(sql, batch_id)
    return cursor.fetchall()

def log_audit_results(cursor, batch_id, records_audited, errors_found):
    """Calls the stored procedure to log the results of the audit."""
    sql = "{CALL dbo.sp_LogAuditResult (?, ?, ?)}"
    cursor.execute(sql, batch_id, records_audited, errors_found)
    cnxn.commit()
    logger.info("Successfully logged audit results to the database.")

def main(batch_id):
    """Main function to guide the user through the audit process."""
    try:
        global cnxn
        cnxn = pyodbc.connect(DB_CONNECTION_STR)
        cursor = cnxn.cursor()

        # Step 1: 

        print("--- Records Flagged for Review / Verification ---")
        for row in review_queue:
        # Added the source file name to the end of the print statement
        print(f"  - [{row.quality_status}] {row.HomeTeamRaw} {row.HomeScore}, {row.VisitorTeamRaw} {row.VisitorScore} | NOTE: {row.processing_notes} | FILE: {row.SourceFile}")
        print("-" * 50)

        # Step 2: If an audit is not optional, guide the user
        if "optional" not in recommendation.lower():
            review_queue = get_review_queue(cursor, batch_id)
            if review_queue:
                print("--- Records Flagged for Automatic Review ---")
                for row in review_queue:
                    print(f"  - {row.HomeTeamRaw} {row.HomeScore}, {row.VisitorTeamRaw} {row.VisitorScore} | NOTE: {row.processing_notes}")
                print("-" * 42)
            else:
                print("No records were automatically flagged for review in this batch.")

            # Step 3: Prompt user for audit results
            print("\nPlease perform your audit based on the recommendation.")
            while True:
                try:
                    audited_count = int(input("How many records did you audit? "))
                    error_count = int(input("How many errors did you find? "))
                    break
                except ValueError:
                    print("Invalid input. Please enter whole numbers.")
            
            # Step 4: Log the results back to the database
            log_audit_results(cursor, batch_id, audited_count, error_count)

        else:
            logger.info("No audit action required for this batch.")

    except Exception as e:
        logger.error(f"An error occurred during the audit process: {e}")
    finally:
        if 'cnxn' in locals() and cnxn:
            cnxn.close()
        logger.info("Audit script finished.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_audit.py <BatchID>")
        sys.exit(1)
    
    batch_id_from_command_line = sys.argv[1]
    main(batch_id_from_command_line)