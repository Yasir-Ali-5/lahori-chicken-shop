import csv
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app, inventory_service


client = TestClient(app)


def test_login_page_renders():
    response = client.get("/")
    assert response.status_code == 200
    assert "Inventory Management System" in response.text


def test_invalid_password_shows_error():
    response = client.post("/", data={"password": "wrong"})
    assert response.status_code == 200
    assert "Invalid Password" in response.text


def test_login_redirects_to_dashboard():
    response = client.post("/", data={"password": "123456789"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"


def test_stock_endpoint_reports_available_stock(tmp_path):
    inventory_service.base_dir = tmp_path
    inventory_service._initialize()

    client.post("/", data={"password": "123456789"}, follow_redirects=False)
    purchase_response = client.post(
        "/purchase",
        data={
            "product": "Pure Asil Desi",
            "weight": "5",
            "quantity": "7",
            "purchase_rate": "250",
            "supplier_name": "Supplier A",
            "date": "2026-07-25",
            "notes": "",
        },
        follow_redirects=False,
    )
    assert purchase_response.status_code == 200

    stock_response = client.get("/stock/Pure%20Asil%20Desi")
    assert stock_response.status_code == 200
    assert stock_response.json()["available_stock"] == 7


def test_monthly_csv_files_are_created_for_purchase_and_sale(tmp_path):
    inventory_service.base_dir = tmp_path
    inventory_service._initialize()

    inventory_service.add_purchase({
        "date": "2026-07-25",
        "product": "Pure Asil Desi",
        "weight": 5.5,
        "quantity": 3,
        "purchase_rate": 250,
        "supplier": "Supplier A",
        "notes": "Fresh batch",
    })
    inventory_service.add_sale({
        "date": "2026-07-25",
        "product": "Pure Asil Desi",
        "quantity": 1,
        "sale_rate": 300,
        "customer": "Customer X",
        "notes": "Delivered",
    })

    month_dir = tmp_path / "July-2026"
    purchase_file = month_dir / "pure_aseel_purchase.csv"
    sale_file = month_dir / "pure_aseel_sales.csv"

    assert purchase_file.exists()
    assert sale_file.exists()

    with purchase_file.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    with sale_file.open(newline="", encoding="utf-8") as handle:
        sale_rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["Product Name"] == "Pure Asil Desi"
    assert len(sale_rows) == 1
    assert sale_rows[0]["Product Name"] == "Pure Asil Desi"


def test_new_month_receives_previous_month_stock_as_opening_balance(tmp_path):
    inventory_service.base_dir = tmp_path
    inventory_service._initialize()

    inventory_service.add_purchase({
        "date": "2026-07-15",
        "product": "Pure Asil Desi",
        "weight": 5,
        "quantity": 4,
        "purchase_rate": 250,
        "supplier": "Supplier A",
        "notes": "Fresh batch",
    })

    august_folder = inventory_service._get_month_folder_path("2026-08-01")
    inventory_service._ensure_month_files(august_folder)

    purchase_file = august_folder / "pure_aseel_purchase.csv"
    with purchase_file.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    opening_balance_rows = [row for row in rows if row.get("Remarks") == "Opening balance carried from previous month"]
    assert len(opening_balance_rows) == 1
    assert opening_balance_rows[0]["Quantity"] == "4"
