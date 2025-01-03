from fastapi import FastAPI, HTTPException, Depends, APIRouter, Query
from bson import ObjectId
from app.schemas.OrderSchemas import Order, Medicine
from app.database import order_collection
from datetime import datetime
from app.routes.Userauth import get_current_user
from app.schemas.UserSchemas import User
router = APIRouter()

# Helper to convert ObjectId to string
def object_id_str(obj):
    obj["id"] = str(obj.pop("_id"))
    return obj

@router.post("/orders")
def create_order(order: Order):
    # Convert the order Pydantic model to a dictionary
    order_dict = order.dict()

    # Ensure the date is in the correct format and convert it to a datetime object
    if "date" not in order_dict or not order_dict["date"]:
        # If date is not provided, set it to the current date
        order_dict["date"] = datetime.now()  # Store as datetime object
    else:
        try:
            # Validate and convert the provided date string to a datetime object
            order_dict["date"] = datetime.strptime(order_dict["date"], "%d-%m-%Y")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Please use 'DD-MM-YYYY'."
            )

    # Insert the order into the database
    result = order_collection.insert_one(order_dict)
    if result.inserted_id:
        return {"id": str(result.inserted_id), "message": "Order created successfully"}
    raise HTTPException(status_code=500, detail="Failed to create order")

# GET API to retrieve all orders
@router.get("/orders")
def get_orders(
    from_date: str = Query(None, description="Filter orders from this date (DD-MM-YYYY)"),
    to_date: str = Query(None, description="Filter orders up to this date (DD-MM-YYYY)"),
):
    query = {}
    # Build date filter query
    if from_date or to_date:
        query["date"] = {}
        if from_date:
            try:
                # Convert from_date to YYYY-MM-DD format for comparison
                from_date_dt = datetime.strptime(from_date, "%d-%m-%Y")
                # from_date_str = from_date_dt.strftime("%Y-%m-%d")
                query["date"]["$gte"] = from_date_dt
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid from_date format. Use DD-MM-YYYY.")
        if to_date:
            try:
                # Convert to_date to YYYY-MM-DD format for comparison
                to_date_dt = datetime.strptime(to_date, "%d-%m-%Y")
                # to_date_str = to_date_dt.strftime("%Y-%m-%d")
                query["date"]["$lte"] = to_date_dt
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid to_date format. Use DD-MM-YYYY.")

    # Log the query for debugging
    print("Generated Query:", query)

    orders = []
    for order in order_collection.find(query):
        orders.append(object_id_str(order))

    if not orders:
        raise HTTPException(status_code=404, detail="No orders found")
    return orders


# GET API to retrieve a single order by ID
@router.get("/orders/{order_id}")
def get_order(order_id: str,current_user: User = Depends(get_current_user)):  # Remove 'async'
    order = order_collection.find_one({"_id": ObjectId(order_id)})  # Remove 'await'
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if current_user["role"] == "admin":
        return object_id_str(order)
    elif current_user["role"] == "delivery":
        return {
            "patient_name": order["patient_name"],
            "mobile_no": order["mobile_no"],
            "address":order["address"],
            "pincode": order["pincode"],
            "total_amount": order["total_amount"],
            "mode_of_payment": order["mode_of_payment"]
        }


# DELETE API to delete an order by ID
@router.delete("/orders/{order_id}")
def delete_order(order_id: str):  # Remove 'async'
    result = order_collection.delete_one({"_id": ObjectId(order_id)})  # Remove 'await'
    if result.deleted_count == 1:
        return {"message": "Order deleted successfully"}
    raise HTTPException(status_code=404, detail="Order not found")


@router.put("/orders/{order_id}")
def update_order(order_id: str, updated_order: Order):
    order_dict = updated_order.dict(exclude_unset=True)  # Exclude unset fields
    result = order_collection.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": order_dict}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    if result.modified_count == 0:
        return {"message": "No changes were made to the order"}
    return {"message": "Order updated successfully"}