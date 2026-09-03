import csv,io,datetime
REQUIRED={"transaction_id","date","amount","type","status"}
def validate_csv(data:bytes):
    if len(data)>10*1024*1024: return [],["File exceeds 10 MB"]
    try: text=data.decode("utf-8")
    except UnicodeDecodeError: return [],["File must be UTF-8 encoded"]
    reader=csv.DictReader(io.StringIO(text)); cols=set(reader.fieldnames or [])
    missing=REQUIRED-cols
    if missing:return [],[f"Missing required columns: {', '.join(sorted(missing))}"]
    rows=[]; errors=[]
    for i,r in enumerate(reader,2):
        try:
            if not r.get("transaction_id"): raise ValueError("transaction_id is empty")
            float(r["amount"]); datetime.date.fromisoformat(r["date"][:10])
            rows.append(r)
        except Exception as e: errors.append(f"Row {i}: {e}")
    return rows,errors
