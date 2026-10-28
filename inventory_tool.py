import pandas as pd
from pathlib import Path
from crewai.tools import tool
import json
import os
import requests

INVENTORY_FILE = Path(__file__).parent / "inventory.csv"


def check_warehouse_inventory(part_name: str) -> dict:
    if not part_name or not part_name.strip():
        return {"status": "invalid_input"}

    try:
        df = pd.read_csv(INVENTORY_FILE)
    except FileNotFoundError:
        return {"status": "inventory_file_missing"}
    except (OSError, pd.errors.ParserError):
        return {"status": "inventory_read_error"}

    required = {
        "part_id",
        "part_name",
        "stock_count",
        "aisle_location",
    }

    if not required.issubset(df.columns):
        return {"status": "invalid_inventory_schema"}

    normalized_name = str(part_name).strip().casefold()

    df["normalized_part_name"] = (
        df["part_name"]
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    match = df[
        df["normalized_part_name"] == normalized_name
    ]
    
    if match.empty:
        return {"status": "part_not_found"}

    if len(match) > 1:
        return {"status": "duplicate_part_records"}

    row = match.iloc[0]
    stock = pd.to_numeric(row["stock_count"], errors="coerce")

    if pd.isna(stock) or stock < 0 or stock != int(stock):
        return {"status": "invalid_stock_data"}

    stock = int(stock)

    return {
        "status": "available" if stock > 0 else "out_of_stock",
        "part_id": str(row["part_id"]),
        "part_name": str(row["part_name"]),
        "stock_count": stock,
        "aisle_location": str(row["aisle_location"]),
    }


@tool("Check Warehouse Inventory")
def check_inventory_tool(part_name: str) -> str:
    """Check spare-part stock through the ERP inventory API."""

    base_url = os.getenv(
        "ERP_API_BASE_URL",
        "http://127.0.0.1:8001",
    )

    try:
        response = requests.get(
            f"{base_url}/inventory",
            params={"part_name": part_name},
            timeout=10,
        )
        response.raise_for_status()

        return json.dumps(response.json())

    except requests.RequestException:
        return json.dumps({
            "status": "erp_api_unavailable",
            "message": (
                "Inventory API could not be reached. "
                "Please check the ERP API server."
            ),
        })