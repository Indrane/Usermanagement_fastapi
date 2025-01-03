from fastapi.security import HTTPBearer
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from datetime import datetime, timedelta
import uuid
from typing import List
from bson import ObjectId

from app.schemas.UserSchemas import Token, UserCreate, User, Userlogin
from app.models.user import User as UserModel
from app.database import users_collection, refresh_tokens_collection, blacklisted_tokens_collection
from app.jwthandler import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
import jwt

router = APIRouter()

bearer_scheme = HTTPBearer()

# Helper functions
async def get_user(username: str):
    user_dict = await run_in_threadpool(users_collection.find_one, {"username": username})
    if user_dict:
        return UserModel(**user_dict)

async def authenticate_user(username: str, password: str):
    user = await get_user(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

async def get_current_user(access_token: str = Depends(bearer_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Extract the token from the HTTPAuthorizationCredentials object
        token = access_token.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        jti: str = payload.get("jti")
        if username is None or jti is None:
            raise credentials_exception
        # Check if the token is blacklisted
        if await run_in_threadpool(blacklisted_tokens_collection.find_one, {"jti": jti}):
            raise credentials_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await run_in_threadpool(users_collection.find_one, {"username": username})
    if user is None:
        raise credentials_exception
    return user

# Login endpoint with refresh token
@router.post("/token", response_model=Token)
async def login_for_access_token(login_data: Userlogin):
    # Fetch the user from MongoDB
    user_dict = await run_in_threadpool(users_collection.find_one, {"email": login_data.email})
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify the password
    if not verify_password(login_data.password, user_dict["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate JWT access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_dict["username"], "jti": str(uuid.uuid4())}, expires_delta=access_token_expires
    )

    # Generate JWT refresh token
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_refresh_token(
        data={"sub": user_dict["username"], "jti": str(uuid.uuid4())}, expires_delta=refresh_token_expires
    )

    # Store refresh token in MongoDB
    await run_in_threadpool(refresh_tokens_collection.insert_one, {
        "token": refresh_token,
        "username": user_dict["username"],
        "expires_at": datetime.utcnow() + refresh_token_expires,
        "revoked": False
    })

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

# Logout endpoint to blacklist token and revoke refresh token
@router.post("/logout")
async def logout(access_token: str = Depends(bearer_scheme)):
    try:
        # Decode the token to get the JWT ID (jti)
        token = access_token.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        username = payload.get("sub")

        # Blacklist the access token
        if jti:
            await run_in_threadpool(blacklisted_tokens_collection.insert_one, {"jti": jti, "revoked_at": datetime.utcnow()})

        # Revoke the refresh token
        await run_in_threadpool(refresh_tokens_collection.update_many, {"username": username}, {"$set": {"revoked": True}})

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error during logout: {str(e)}"
        )
    return {"detail": "User logged out successfully"}

# Refresh token endpoint
@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    current_user: User = Depends(get_current_user)  # Require authentication
):
    """
    Refresh the access token using a valid refresh token.
    Requires a valid access token for authentication.
    """
    try:
        # Check if the refresh token is valid
        refresh_token_data = await run_in_threadpool(refresh_tokens_collection.find_one, {"token": refresh_token})
        if not refresh_token_data or refresh_token_data["revoked"] or refresh_token_data["expires_at"] < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        # Ensure the refresh token belongs to the authenticated user
        if refresh_token_data["username"] != current_user["username"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Refresh token does not belong to the authenticated user",
            )

        # Generate a new access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": refresh_token_data["username"], "jti": str(uuid.uuid4())}, expires_delta=access_token_expires
        )

        return {"access_token": access_token, "token_type": "bearer"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error during token refresh: {str(e)}",
        )

# Register endpoint (unchanged)
@router.post("/register", response_model=User)
async def register_user(user: UserCreate):
    hashed_password = get_password_hash(user.password)
    user_dict = user.dict()
    user_dict["hashed_password"] = hashed_password
    user_dict.pop("password")  # Remove the plain password
    await run_in_threadpool(users_collection.insert_one, user_dict)
    return user_dict

# Get all users endpoint
@router.get("/users", response_model=List[User])
async def get_all_users(current_user: User = Depends(get_current_user)):
    """
    Fetch all users (protected route).
    Only accessible with a valid access token.
    """
    try:
        # Fetch all users from the database
        users = await run_in_threadpool(users_collection.find, {})
        
        # Convert MongoDB cursor to a list of dictionaries
        user_list = []
        for user in users:
            user["_id"] = str(user["_id"])  # Convert ObjectId to string
            user.pop("hashed_password")  # Exclude hashed password from the response
            user_list.append(user)
        
        return user_list
    except Exception as e:
        print(f"Error fetching users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching users",
        )

# Me endpoint (unchanged)
@router.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/users/reset-password")
async def reset_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user)
):
    """
    Reset a user's password by verifying the current password.
    """
    try:
        # Verify the current password
        user_dict = await run_in_threadpool(users_collection.find_one, {"username": current_user["username"]})
        if not user_dict:
            raise HTTPException(status_code=404, detail="User not found")

        if not verify_password(current_password, user_dict["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        # Hash the new password
        hashed_password = get_password_hash(new_password)

        # Update the user's password in the database
        await run_in_threadpool(
            users_collection.update_one,
            {"username": current_user["username"]},
            {"$set": {"hashed_password": hashed_password}}
        )

        return {"message": "Password updated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting password: {str(e)}"
        )


@router.put("/users/{user_id}/update-details")
async def admin_update_user_details(
    user_id: str,
    user_update: User,
    current_user: User = Depends(get_current_user)
):
    """
    Admin updates any user's profile details by user ID.
    """
    try:
        # Verify that the current user is an admin
        if current_user["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied. Admin access required."
            )

        # Validate the user ID
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=400, detail="Invalid user ID format")

        # Convert the update data into a dictionary
        update_data = user_update.dict(exclude_unset=True)

        # Prevent certain fields from being updated
        for restricted_field in ["username", "hashed_password", "_id"]:
            if restricted_field in update_data:
                update_data.pop(restricted_field)

        # Fetch the user to update
        user_dict = await run_in_threadpool(users_collection.find_one, {"_id": ObjectId(user_id)})
        if not user_dict:
            raise HTTPException(status_code=404, detail="User not found")

        # Update the user's details in the database
        await run_in_threadpool(
            users_collection.update_one,
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )

        return {"message": "User details updated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user details: {str(e)}"
        )



@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    disabled: bool,
    current_user: User = Depends(get_current_user)
):
    """
    Enable or disable a user's account by user ID.
    Only accessible to admins or authorized users.
    """
    try:
        # Verify that the current user is an admin
        if current_user["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied. Admin access required."
            )

        # Validate the user ID
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=400, detail="Invalid user ID format")

        # Fetch the user to update
        user_dict = await run_in_threadpool(users_collection.find_one, {"_id": ObjectId(user_id)})
        if not user_dict:
            raise HTTPException(status_code=404, detail="User not found")

        # Update the user's disabled status
        await run_in_threadpool(
            users_collection.update_one,
            {"_id": ObjectId(user_id)},
            {"$set": {"disabled": disabled}}
        )

        status_message = "User account disabled" if disabled else "User account enabled"
        return {"message": status_message}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user status: {str(e)}"
        )
