import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any


class InventoryService:
    PRODUCT_ALIASES = {
        "pure aseel": "Pure Asil Desi",
        "pure asil desi": "Pure Asil Desi",
        "pure asel": "Pure Asil Desi",
        "desi": "Desi",
        "broiler": "Broiler",
    }

    PURCHASE_HEADERS = [
        "Date",
        "Time",
        "Product Name",
        "Weight",
        "Quantity",
        "Rate",
        "Total Amount",
        "Payment Status",
        "Remarks",
    ]

    SALES_HEADERS = [
        "Date",
        "Time",
        "Product Name",
        "Weight",
        "Quantity",
        "Rate",
        "Total Amount",
        "Payment Status",
        "Remarks",
    ]

    def __init__(self) -> None:
        self.product_names = ["Pure Asil Desi", "Desi", "Broiler"]
        self.base_dir = Path(__file__).resolve().parent.parent / "data"
        self.status_message = "Using local CSV files"
        self._initialize()

    def _initialize(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.status_message = f"Using local CSV files in {self.base_dir}"
        self._ensure_month_files(self._get_month_folder_path())

    def _normalize_product_name(self, product: str) -> str:
        value = (product or "").strip()
        return self.PRODUCT_ALIASES.get(value.lower(), value or "Unknown")

    def _get_storage_file_name(self, product: str, record_type: str) -> str:
        canonical = self._normalize_product_name(product)
        if canonical == "Pure Asil Desi":
            prefix = "pure_aseel"
        elif canonical == "Desi":
            prefix = "desi"
        elif canonical == "Broiler":
            prefix = "broiler"
        else:
            prefix = "unknown"

        return f"{prefix}_{record_type}.csv"

    def _get_month_folder_name(self, record_date: str | None = None) -> str:
        if record_date:
            try:
                parsed_date = datetime.fromisoformat(record_date)
            except ValueError:
                try:
                    parsed_date = datetime.strptime(record_date, "%Y-%m-%d")
                except ValueError:
                    parsed_date = datetime.now()
        else:
            parsed_date = datetime.now()

        return f"{parsed_date.strftime('%B')}-{parsed_date.year}"

    def _get_month_folder_path(self, record_date: str | None = None) -> Path:
        folder = self.base_dir / self._get_month_folder_name(record_date)
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def _ensure_month_files(self, folder: Path) -> None:
        for product in self.product_names:
            self._ensure_csv_file(folder, self._get_storage_file_name(product, "purchase"), self.PURCHASE_HEADERS)
            self._ensure_csv_file(folder, self._get_storage_file_name(product, "sales"), self.SALES_HEADERS)

        self._carry_forward_previous_month_stock(folder)

    def _ensure_csv_file(self, folder: Path, filename: str, headers: list[str]) -> Path:
        path = folder / filename
        if not path.exists():
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(headers)
        return path

    def _get_previous_month_folder_path_for_folder(self, folder: Path) -> Path | None:
        try:
            month_name, year_text = folder.name.rsplit("-", 1)
            parsed_date = datetime.strptime(f"{month_name} 1 {year_text}", "%B %d %Y")
        except ValueError:
            return None

        if parsed_date.month == 1:
            previous_month = 12
            previous_year = parsed_date.year - 1
        else:
            previous_month = parsed_date.month - 1
            previous_year = parsed_date.year

        previous_folder_name = f"{datetime(previous_year, previous_month, 1).strftime('%B')}-{previous_year}"
        previous_folder = self.base_dir / previous_folder_name
        if previous_folder.exists():
            return previous_folder
        return None

    def _get_month_start_date(self, folder: Path) -> str:
        try:
            month_name, year_text = folder.name.rsplit("-", 1)
            parsed_date = datetime.strptime(f"{month_name} 1 {year_text}", "%B %d %Y")
        except ValueError:
            return date.today().isoformat()
        return parsed_date.strftime("%Y-%m-%d")

    def _calculate_month_stock_balance(self, folder: Path, product: str) -> int:
        normalized_product = self._normalize_product_name(product)
        purchase_path = folder / self._get_storage_file_name(normalized_product, "purchase")
        sale_path = folder / self._get_storage_file_name(normalized_product, "sales")

        purchased_quantity = sum(int(float(row.get("Quantity", 0) or 0)) for row in self._read_csv_rows(purchase_path))
        sold_quantity = sum(int(float(row.get("Quantity", 0) or 0)) for row in self._read_csv_rows(sale_path))
        return purchased_quantity - sold_quantity

    def _has_opening_balance_row(self, path: Path) -> bool:
        for row in self._read_csv_rows(path):
            if row.get("Remarks", "").strip() == "Opening balance carried from previous month":
                return True
        return False

    def _carry_forward_previous_month_stock(self, folder: Path) -> None:
        previous_folder = self._get_previous_month_folder_path_for_folder(folder)
        if previous_folder is None:
            return

        for product in self.product_names:
            normalized_product = self._normalize_product_name(product)
            purchase_path = folder / self._get_storage_file_name(normalized_product, "purchase")
            if self._has_opening_balance_row(purchase_path):
                continue

            carried_quantity = self._calculate_month_stock_balance(previous_folder, normalized_product)
            if carried_quantity <= 0:
                continue

            row = [
                self._get_month_start_date(folder),
                datetime.now().strftime("%H:%M:%S"),
                normalized_product,
                "",
                carried_quantity,
                "",
                "",
                "Paid",
                "Opening balance carried from previous month",
            ]
            self._append_row(purchase_path, row)

    def _append_row(self, path: Path, row: list[Any]) -> None:
        with path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(row)

    def get_current_month_label(self) -> str:
        return self._get_month_folder_name(date.today().isoformat())

    def add_purchase(self, purchase: dict[str, Any]) -> None:
        folder = self._get_month_folder_path(purchase.get("date"))
        self._ensure_month_files(folder)
        path = self._ensure_csv_file(
            folder,
            self._get_storage_file_name(purchase["product"], "purchase"),
            [
                "Date",
                "Time",
                "Product Name",
                "Weight",
                "Quantity",
                "Rate",
                "Total Amount",
                "Payment Status",
                "Remarks",
            ],
        )

        total_amount = float(purchase.get("weight", 0)) * float(purchase.get("quantity", 0)) * float(purchase.get("purchase_rate", 0))
        row = [
            purchase.get("date", ""),
            datetime.now().strftime("%H:%M:%S"),
            self._normalize_product_name(purchase.get("product", "")),
            purchase.get("weight", ""),
            purchase.get("quantity", ""),
            purchase.get("purchase_rate", ""),
            total_amount,
            purchase.get("payment_status", "Paid"),
            purchase.get("notes", ""),
        ]
        self._append_row(path, row)

    def add_sale(self, sale: dict[str, Any]) -> None:
        folder = self._get_month_folder_path(sale.get("date"))
        self._ensure_month_files(folder)
        path = self._ensure_csv_file(
            folder,
            self._get_storage_file_name(sale["product"], "sales"),
            [
                "Date",
                "Time",
                "Product Name",
                "Weight",
                "Quantity",
                "Rate",
                "Total Amount",
                "Payment Status",
                "Remarks",
            ],
        )

        total_amount = float(sale.get("quantity", 0)) * float(sale.get("sale_rate", 0))
        row = [
            sale.get("date", ""),
            datetime.now().strftime("%H:%M:%S"),
            self._normalize_product_name(sale.get("product", "")),
            "",
            sale.get("quantity", ""),
            sale.get("sale_rate", ""),
            total_amount,
            sale.get("payment_status", "Paid"),
            sale.get("notes", ""),
        ]
        self._append_row(path, row)

    def _read_csv_rows(self, path: Path) -> list[dict[str, str]]:
        if not path.exists():
            return []
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        return [row for row in rows if row]

    def get_available_stock(self, product: str) -> int:
        normalized_product = self._normalize_product_name(product)
        purchased_quantity = 0
        sold_quantity = 0

        if not self.base_dir.exists():
            return 0

        folder = self._get_month_folder_path(date.today().isoformat())
        purchase_path = folder / self._get_storage_file_name(normalized_product, "purchase")
        sale_path = folder / self._get_storage_file_name(normalized_product, "sales")

        for row in self._read_csv_rows(purchase_path):
            quantity = row.get("Quantity", "")
            if quantity:
                purchased_quantity += int(float(quantity))

        for row in self._read_csv_rows(sale_path):
            quantity = row.get("Quantity", "")
            if quantity:
                sold_quantity += int(float(quantity))

        return purchased_quantity - sold_quantity

    def get_month_summary(self) -> list[dict[str, Any]]:
        month_folder = self._get_month_folder_path(date.today().isoformat())
        summaries: list[dict[str, Any]] = []

        for product in self.product_names:
            normalized_product = self._normalize_product_name(product)
            purchase_path = month_folder / self._get_storage_file_name(normalized_product, "purchase")
            sale_path = month_folder / self._get_storage_file_name(normalized_product, "sales")

            purchase_rows = self._read_csv_rows(purchase_path)
            sale_rows = self._read_csv_rows(sale_path)

            purchased_quantity = sum(int(float(row.get("Quantity", 0) or 0)) for row in purchase_rows)
            sold_quantity = sum(int(float(row.get("Quantity", 0) or 0)) for row in sale_rows)
            purchase_total = sum(float(row.get("Total Amount", 0) or 0) for row in purchase_rows)
            sale_total = sum(float(row.get("Total Amount", 0) or 0) for row in sale_rows)
            opening_balance = sum(
                int(float(row.get("Quantity", 0) or 0))
                for row in purchase_rows
                if (row.get("Remarks", "") or "").strip() == "Opening balance carried from previous month"
            )

            summaries.append(
                {
                    "product": normalized_product,
                    "purchased_quantity": purchased_quantity,
                    "sold_quantity": sold_quantity,
                    "purchase_total": round(purchase_total, 2),
                    "sale_total": round(sale_total, 2),
                    "stock_balance": purchased_quantity - sold_quantity,
                    "opening_balance": opening_balance,
                }
            )

        return summaries
