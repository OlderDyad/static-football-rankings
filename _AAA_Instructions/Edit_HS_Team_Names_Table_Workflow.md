# Workflow: HS Football Data Cleaning
CD C:\Users\demck\OneDrive\Football_2024\static-football-rankings\python_scripts\data_import\
python python pull_sheets_to_sql.py

### **Command Line Quick Reference**

  * **Folder:** `.../python_scripts/data_import`
  * **Images:** Save to `Desktop\HS_Image_Drop` (Name: `ID_Name_Type.png`)

-----

**STEP 1: REFRESH THE SHEET**

  * **Where:** VS Code Terminal
  * **What it does:** Wipes Google Sheet and refills it with SQL data.
  * **Command:**
    ```powershell
    python push_HS_Names_export_to_sheets.py
    ```

-----

**STEP 2: SAVE YOUR EDITS**

  * **Where:** VS Code Terminal
  * **What it does:** Reads rows marked with 'x' in Google Sheets and updates SQL.
  * **Command:**
    ```powershell
    python pull_sheets_to_sql.py
    ```

-----

**STEP 3: PROCESS IMAGES**

  * **Where:** VS Code Terminal
  * **What it does:** Moves files from Desktop folder to Storage and links them in SQL.
  * **Command:**
    ```powershell
    python ingest_images_by_id.py
    ```
    ```

-----
### **Detailed Workflow Steps**

#### **Phase 1: Text Data (Websites, Colors, Year Founded)**

1.  **Refresh:** Run the **Push** script to get the latest list of missing data.
2.  **Edit:** Open "HS Football Data Cleaning" in Google Sheets.
3.  **Find ID:** Locate the team (e.g., New Britain) and note the `ID` in Column B (e.g., `1405`).
4.  **Update:** Fill in the missing text fields.
5.  **Mark for Sync:** Type an **`x`** in the **Sync** column (Column A).
6.  **Save:** Run the **Pull** script.
      * *Result:* Terminal should say `Updated ID 1405: New Britain`.

#### **Phase 2: Image Data (Logos, Helmets)**

1.  **Save:** Download image to `Desktop\HS_Image_Drop`.
2.  **Rename:** Rename the file using the ID from your Google Sheet.
      * **Format:** `ID_AnyName_Type.png`
      * *Example:* `1405_NewBritain_Helmet.png`
      * *Valid Types:* `Mascot` (Logo), `School` (Crest), `Helmet`.
3.  **Ingest:** Run the `ingest_images_by_id.py` script.
      * *Result:* File moves to OneDrive folder; SQL updates automatically.
      * *Note:* You do **not** need to touch the Google Sheet for images.

#### **Phase 3: Verification (Optional)**

1.  Run the **Push** script again.
2.  **Result:** If you fully completed the team (Images + Text), it should **disappear** from the sheet (because it is no longer "missing data").
3.  If it reappears, your new data should be visible in the columns.
