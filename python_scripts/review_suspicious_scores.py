import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=MCKNIGHTS-PC\\SQLEXPRESS01;"
    "DATABASE=hs_football_database;"
    "Trusted_Connection=yes;"
)
cursor = conn.cursor()

def fetch_pending(n=5):
    cursor.execute("""
        SELECT TOP (?) 
            ID, Date, Season, Home, Visitor,
            Home_Score, Visitor_Score, Flag_Reason,
            Corrected_Home_Score, Corrected_Visitor_Score, Review_Notes
        FROM HS_Scores_Under_Review
        WHERE Validated_Score IS NULL
        ORDER BY Date_Flagged
    """, n)
    return cursor.fetchall()

def display_record(row):
    print("\n" + "="*60)
    print(f"  ID:      {row.ID}")
    print(f"  Date:    {row.Date}  |  Season: {row.Season}")
    print(f"  Home:    {row.Home}")
    print(f"  Visitor: {row.Visitor}")
    print(f"  Score:   {row.Home_Score} - {row.Visitor_Score}  (Flag: {row.Flag_Reason})")
    if row.Corrected_Home_Score or row.Corrected_Visitor_Score:
        print(f"  Already corrected: {row.Corrected_Home_Score} - {row.Corrected_Visitor_Score}")
    if row.Review_Notes:
        print(f"  Notes:   {row.Review_Notes}")
    print("="*60)

def edit_record(row):
    display_record(row)
    print("\nOptions:")
    print("  [enter]  = skip (leave pending)")
    print("  [1]      = mark validated (release to HS_Scores as-is)")
    print("  [0]      = mark bad (delete)")
    print("  [e]      = edit scores")
    print("  [n]      = add/update notes")
    print("  [q]      = quit")

    choice = input("\nChoice: ").strip().lower()

    if choice == "":
        print("  Skipped.")
        return

    elif choice == "q":
        return "quit"

    elif choice == "1":
        cursor.execute("""
            UPDATE HS_Scores_Under_Review
            SET Validated_Score = 1
            WHERE ID = ?
        """, row.ID)
        conn.commit()
        print("  ✓ Marked as validated — will be released to HS_Scores on next run.")

    elif choice == "0":
        confirm = input("  Confirm delete (y/n): ").strip().lower()
        if confirm == "y":
            cursor.execute("""
                UPDATE HS_Scores_Under_Review
                SET Validated_Score = 0
                WHERE ID = ?
            """, row.ID)
            conn.commit()
            print("  ✓ Marked for deletion.")

    elif choice == "e":
        h = row.Corrected_Home_Score or row.Home_Score
        v = row.Corrected_Visitor_Score or row.Visitor_Score

        h_input = input(f"  Home score  [{h}]: ").strip()
        v_input = input(f"  Visitor score [{v}]: ").strip()

        new_h = int(h_input) if h_input else h
        new_v = int(v_input) if v_input else v
        new_margin = new_h - new_v

        notes_input = input(f"  Notes (blank to keep existing): ").strip()
        notes = notes_input if notes_input else row.Review_Notes

        print(f"\n  New score: {new_h} - {new_v}  (Margin: {new_margin})")
        confirm = input("  Save? (y/n): ").strip().lower()
        if confirm == "y":
            cursor.execute("""
                UPDATE HS_Scores_Under_Review
                SET Corrected_Home_Score = ?,
                    Corrected_Visitor_Score = ?,
                    Review_Notes = ?
                WHERE ID = ?
            """, new_h, new_v, notes, row.ID)
            conn.commit()
            print("  ✓ Scores saved. Set validated = 1 when ready to release.")

    elif choice == "n":
        notes_input = input(f"  Notes: ").strip()
        if notes_input:
            cursor.execute("""
                UPDATE HS_Scores_Under_Review
                SET Review_Notes = ?
                WHERE ID = ?
            """, notes_input, row.ID)
            conn.commit()
            print("  ✓ Notes saved.")

def main():
    while True:
        rows = fetch_pending(5)
        if not rows:
            print("\nNo pending records. All done!")
            break

        print(f"\nFetched {len(rows)} pending record(s).")
        for row in rows:
            result = edit_record(row)
            if result == "quit":
                print("\nExiting.")
                conn.close()
                return

        again = input("\nFetch next batch? (y/n): ").strip().lower()
        if again != "y":
            break

    conn.close()

if __name__ == "__main__":
    main()