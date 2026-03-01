import os
from supabase import create_client


def get_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")
    return create_client(url, key)


def load_db():
    client = get_client()
    response = client.table("items").select("*").execute()
    return {row["item_id"]: row["data"] for row in response.data}


def save_item(item_id, item_data):
    client = get_client()
    client.table("items").upsert({"item_id": item_id, "data": item_data}).execute()


def delete_item(item_id):
    client = get_client()
    client.table("items").delete().eq("item_id", item_id).execute()
