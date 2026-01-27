from sqlalchemy import create_engine, Table, Column, Integer, String, Text, DateTime, MetaData, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
import re

SQLALCHEMY_DATABASE_URL = "sqlite:///./clinical_issues_v2.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
metadata = MetaData()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def sanitize_table_name(name: str) -> str:
    # Remove file extension and non-alphanumeric characters
    name = re.sub(r'\.[^.]+$', '', name)
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    return f"issues_{name}"

def get_dynamic_table(table_name: str):
    return Table(
        table_name, metadata,
        Column('id', Integer, primary_key=True, index=True),
        Column('row_number', String),
        Column('column_name', String),
        Column('issue', String),
        Column('ai_explanation', Text),
        Column('severity', String),
        Column('dataset_name', String),
        Column('edited_by', String, default='AI'),
        Column('created_at', DateTime),
        extend_existing=True
    )

def create_dynamic_table(table_name: str):
    table = get_dynamic_table(table_name)
    metadata.create_all(engine)
    return table

def list_all_issue_tables():
    inspector = inspect(engine)
    return [table for table in inspector.get_table_names() if table.startswith("issues_")]
