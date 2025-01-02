from fastapi import FastAPI, HTTPException, Depends, APIRouter
from bson import ObjectId
from app.schemas.OrderSchemas import Order, Medicine
from app.database import order_collection

router = APIRouter()

# Helper to convert ObjectId to string
def object_id_str(obj):
    obj["id"] = str(obj.pop("_id"))
    return obj

# POST API to create an order
@router.post("/orders")
def create_order(order: Order):  # Remove 'async'
    order_dict = order.dict()
    result = order_collection.insert_one(order_dict)  # Remove 'await'
    if result.inserted_id:
        return {"id": str(result.inserted_id), "message": "Order created successfully"}
    raise HTTPException(status_code=500, detail="Failed to create order")

# GET API to retrieve all orders
@router.get("/orders")
def get_orders():  # Remove 'async'
    orders = []
    for order in order_collection.find():  # Use regular 'for' loop
        orders.append(object_id_str(order))
    if not orders:
        raise HTTPException(status_code=404, detail="No orders found")
    return orders

# GET API to retrieve a single order by ID
@router.get("/orders/{order_id}")
def get_order(order_id: str):  # Remove 'async'
    order = order_collection.find_one({"_id": ObjectId(order_id)})  # Remove 'await'
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return object_id_str(order)

# DELETE API to delete an order by ID
@router.delete("/orders/{order_id}")
def delete_order(order_id: str):  # Remove 'async'
    result = order_collection.delete_one({"_id": ObjectId(order_id)})  # Remove 'await'
    if result.deleted_count == 1:
        return {"message": "Order deleted successfully"}
    raise HTTPException(status_code=404, detail="Order not found")