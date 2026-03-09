from pathlib import Path
import csv

REQUIRED_COLS = {"customer_id", "amount", "status", "date"}

#def read_csv(path: str) -> list[dict[str, str]]:
with open("sample.csv","r",newline="", encoding="utf-8") as f:
    reader=csv.DictReader(f)
    print(reader.fieldnames)
    rows=[]
    for row in reader:
        rows.append(row)
    print(rows)

