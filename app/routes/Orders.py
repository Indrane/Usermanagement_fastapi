from fastapi import FastAPI, HTTPException, Depends, APIRouter
from motor.motor_asyncio import AsyncIOMotorClient
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
async def create_order(order: Order):
    order_dict = order.dict()
    result = await order_collection.insert_one(order_dict)  # Use 'await' here
    if result.inserted_id:
        return {"id": str(result.inserted_id), "message": "Order created successfully"}
    raise HTTPException(status_code=500, detail="Failed to create order")

# GET API to retrieve all orders
@router.get("/orders")
async def get_orders():
    orders = []
    async for order in order_collection.find():  # Use 'async for' for async iteration
        orders.append(object_id_str(order))
    if not orders:
        raise HTTPException(status_code=404, detail="No orders found")
    return orders

# GET API to retrieve a single order by ID
@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    order = await order_collection.find_one({"_id": ObjectId(order_id)})  # Use 'await' here
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return object_id_str(order)

# DELETE API to delete an order by ID
@router.delete("/orders/{order_id}")
async def delete_order(order_id: str):
    result = await order_collection.delete_one({"_id": ObjectId(order_id)})  # Use 'await' here
    if result.deleted_count == 1:
        return {"message": "Order deleted successfully"}
    raise HTTPException(status_code=404, detail="Order not found")