from sqlalchemy.sql.functions import user
from database.engine import DbManager
from sqlalchemy import select
from utils.client import Client
from utils.models import Proxy
from loguru import logger
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError


class OPDbManager(DbManager):
    def __init__(self, db_path, base):
        super().__init__(db_path, base)

    async def create_base_note(self, pk, proxy):
        await super().create_base_note(pk, proxy)

    async def get_run_data(self):
        async with self.session.begin():
            result = await self.session.execute(select(self.base))
            users = result.scalars().all()
            return [{'client': Client(user.private_key), 'proxy': Proxy(user.proxy)}
                    for user in users]
            
    async def add_extra_columns(self, table_name="op_base"):
        try:
            engine = self.get_engine()
            async with engine.begin() as conn:
                result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
                existing_columns = [row[1] for row in result]

                columns_to_add = {}

                for column, column_type in columns_to_add.items():
                    if column not in existing_columns:
                        await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column} {column_type}"))

                await conn.commit()
        except SQLAlchemyError as e:
            logger.error(f"Failed to add columns: {str(e)}")
            await conn.rollback()
