<!-- GAP-022:COMPLETED — 16 of 16 done. -->
# hoi4_spreadsheet_doc_worker — Platform-Agnostic Checklist

**Purpose:** Update and maintain mod CSV/XLSX tables for data tracking and documentation.

## Checklist
- [ ] CSV files use consistent column headers
- [ ] No missing values in required columns
- [ ] IDs match implementation files (event IDs, focus IDs, decision keys)
- [ ] Data is sorted logically (by ID, by country, by category)
- [ ] Spreadsheet is referenced in mod documentation
- [ ] No duplicate rows

## Output Format
```
## Spreadsheet Audit: <filename>
### Rows: N
### Columns: N
### Errors: N
### Missing Values: N
```
