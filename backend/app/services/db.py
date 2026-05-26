from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

_url = os.getenv("DATABASE_URL", "")
# Supabase / cloud PostgreSQL requires SSL
_connect_args = {"sslmode": "require"} if "supabase" in _url else {}
engine = create_engine(_url, connect_args=_connect_args)