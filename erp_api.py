from fastapi import FastAPI, Query
from inventory_tool import check_warehouse_inventory

app = FastAPI(
    title="Field Service ERP Inventory API",
    description="Mock ERP inventory API for spare-part lookup",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "ERP Inventory API",
    }


@app.get("/inventory")
def get_inventory(
    part_name: str = Query(..., min_length=1)
):
    """Return verified inventory information for a spare part."""
    return check_warehouse_inventory(part_name)