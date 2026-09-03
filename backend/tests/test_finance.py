from app.services.csv.processor import validate_csv
def test_csv_validation():
    rows,errors=validate_csv(b"transaction_id,date,amount,type,status\nT1,2026-01-01,10,revenue,completed\n")
    assert len(rows)==1 and not errors
def test_bad_csv():
    rows,errors=validate_csv(b"transaction_id,date\nT1,2026-01-01\n")
    assert errors
from app.services.risk.engine import calculate
class T: amount=200000
def test_risk(): assert calculate(T(),0)[0]>=30
