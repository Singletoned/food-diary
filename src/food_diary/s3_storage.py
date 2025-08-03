"""
S3-based storage for the food diary application.
Replaces database with JSON files stored in S3.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Storage:
    """S3-based storage that replaces database functionality."""

    def __init__(self):
        self.bucket_name = os.getenv("DATA_BUCKET")
        if not self.bucket_name:
            raise ValueError("DATA_BUCKET environment variable not set")
        
        self.s3_client = boto3.client("s3")
        logger.info(f"S3Storage initialized with bucket: {self.bucket_name}")

    def _get_user_profile_key(self, user_id: int) -> str:
        """Get S3 key for user profile."""
        return f"users/{user_id}/profile.json"

    def _get_user_entries_key(self, user_id: int) -> str:
        """Get S3 key for user entries."""
        return f"users/{user_id}/entries.json"

    def _read_json_from_s3(self, key: str) -> Optional[Dict]:
        """Read JSON object from S3."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return json.loads(response["Body"].read().decode("utf-8"))
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            logger.error(f"Error reading {key} from S3: {e}")
            raise

    def _write_json_to_s3(self, key: str, data: Dict, if_none_match: bool = False) -> bool:
        """Write JSON object to S3 with optional conditional write."""
        try:
            extra_args = {}
            if if_none_match:
                # Only write if the object doesn't exist (for new users)
                extra_args["IfNoneMatch"] = "*"
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(data, indent=2),
                ContentType="application/json",
                **extra_args
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "PreconditionFailed":
                # Conditional write failed (object already exists)
                return False
            logger.error(f"Error writing {key} to S3: {e}")
            raise

    def create_or_update_user(self, github_id: int, username: str, name: str = None, 
                            email: str = None, avatar_url: str = None) -> Dict[str, Any]:
        """Create or update a user profile."""
        # First, try to find existing user by github_id
        existing_user = self.get_user_by_github_id(github_id)
        
        if existing_user:
            # Update existing user
            user_id = existing_user["id"]
            profile_key = self._get_user_profile_key(user_id)
            
            # Update profile data
            profile_data = {
                "id": user_id,
                "github_id": github_id,
                "username": username,
                "name": name,
                "email": email,
                "avatar_url": avatar_url,
                "created_at": existing_user["created_at"],
                "updated_at": datetime.now().isoformat()
            }
            
            self._write_json_to_s3(profile_key, profile_data)
            logger.info(f"Updated user {user_id} (github_id: {github_id})")
            return profile_data
        else:
            # Create new user with auto-incrementing ID
            user_id = self._get_next_user_id()
            profile_key = self._get_user_profile_key(user_id)
            
            profile_data = {
                "id": user_id,
                "github_id": github_id,
                "username": username,
                "name": name,
                "email": email,
                "avatar_url": avatar_url,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Try conditional write to avoid race conditions
            if self._write_json_to_s3(profile_key, profile_data, if_none_match=True):
                # Also initialize empty entries file
                entries_key = self._get_user_entries_key(user_id)
                self._write_json_to_s3(entries_key, {"entries": []})
                
                logger.info(f"Created new user {user_id} (github_id: {github_id})")
                return profile_data
            else:
                # Race condition - another process created this user
                logger.warning(f"Race condition creating user {user_id}, retrying...")
                return self.create_or_update_user(github_id, username, name, email, avatar_url)

    def get_user_by_github_id(self, github_id: int) -> Optional[Dict[str, Any]]:
        """Find user by GitHub ID by scanning user profiles."""
        try:
            # List all user profile objects
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix="users/",
                Delimiter="/"
            )
            
            # Check each user directory
            for prefix in response.get("CommonPrefixes", []):
                user_dir = prefix["Prefix"]  # e.g., "users/123/"
                try:
                    user_id = int(user_dir.split("/")[1])
                    profile = self._read_json_from_s3(self._get_user_profile_key(user_id))
                    if profile and profile.get("github_id") == github_id:
                        return profile
                except (ValueError, IndexError):
                    continue
            
            return None
        except ClientError as e:
            logger.error(f"Error searching for user with github_id {github_id}: {e}")
            return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by user ID."""
        profile_key = self._get_user_profile_key(user_id)
        return self._read_json_from_s3(profile_key)

    def _get_next_user_id(self) -> int:
        """Get next available user ID by scanning existing users."""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix="users/",
                Delimiter="/"
            )
            
            max_id = 0
            for prefix in response.get("CommonPrefixes", []):
                user_dir = prefix["Prefix"]  # e.g., "users/123/"
                try:
                    user_id = int(user_dir.split("/")[1])
                    max_id = max(max_id, user_id)
                except (ValueError, IndexError):
                    continue
            
            return max_id + 1
        except ClientError as e:
            logger.error(f"Error getting next user ID: {e}")
            # Fallback to timestamp-based ID
            return int(datetime.now().timestamp())

    def get_entries(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all entries for a user."""
        entries_key = self._get_user_entries_key(user_id)
        entries_data = self._read_json_from_s3(entries_key)
        
        if entries_data is None:
            return []
        
        # Sort by event_datetime descending
        entries = entries_data.get("entries", [])
        entries.sort(key=lambda x: x.get("event_datetime", x.get("timestamp", "")), reverse=True)
        return entries

    def create_entry(self, user_id: int, timestamp: str, event_datetime: str = None, 
                    text: str = "", photo: str = None) -> Dict[str, Any]:
        """Create a new entry for a user."""
        entries_key = self._get_user_entries_key(user_id)
        entries_data = self._read_json_from_s3(entries_key) or {"entries": []}
        
        # Get next entry ID
        max_id = 0
        for entry in entries_data["entries"]:
            max_id = max(max_id, entry.get("id", 0))
        
        new_entry = {
            "id": max_id + 1,
            "user_id": user_id,
            "timestamp": timestamp,
            "event_datetime": event_datetime or timestamp,
            "text": text,
            "photo": photo,
            "synced": True,
            "created_at": datetime.now().isoformat()
        }
        
        entries_data["entries"].append(new_entry)
        self._write_json_to_s3(entries_key, entries_data)
        
        logger.info(f"Created entry {new_entry['id']} for user {user_id}")
        return new_entry

    def update_entry(self, user_id: int, entry_id: int, timestamp: str = None, 
                    event_datetime: str = None, text: str = None, photo: str = None) -> bool:
        """Update an existing entry."""
        entries_key = self._get_user_entries_key(user_id)
        entries_data = self._read_json_from_s3(entries_key)
        
        if not entries_data:
            return False
        
        # Find and update the entry
        for entry in entries_data["entries"]:
            if entry["id"] == entry_id and entry["user_id"] == user_id:
                if timestamp is not None:
                    entry["timestamp"] = timestamp
                if event_datetime is not None:
                    entry["event_datetime"] = event_datetime
                if text is not None:
                    entry["text"] = text
                if photo is not None:
                    entry["photo"] = photo
                
                entry["updated_at"] = datetime.now().isoformat()
                
                self._write_json_to_s3(entries_key, entries_data)
                logger.info(f"Updated entry {entry_id} for user {user_id}")
                return True
        
        return False

    def delete_entry(self, user_id: int, entry_id: int) -> bool:
        """Delete an entry."""
        entries_key = self._get_user_entries_key(user_id)
        entries_data = self._read_json_from_s3(entries_key)
        
        if not entries_data:
            return False
        
        # Find and remove the entry
        original_count = len(entries_data["entries"])
        entries_data["entries"] = [
            entry for entry in entries_data["entries"] 
            if not (entry["id"] == entry_id and entry["user_id"] == user_id)
        ]
        
        if len(entries_data["entries"]) < original_count:
            self._write_json_to_s3(entries_key, entries_data)
            logger.info(f"Deleted entry {entry_id} for user {user_id}")
            return True
        
        return False


# Global storage instance - initialized lazily
storage = None

def get_storage():
    """Get or create the global storage instance."""
    global storage
    if storage is None:
        storage = S3Storage()
    return storage