import json
import os

import mysql.connector


def connect_db():
    return mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="campus_app",
        password=os.environ["CAMPUS_DB_PASSWORD"],
        database="campus_lost_found",
        use_pure=True,
    )


def insert_found_item(
    photo_name: str, photo_clues: dict, embedding: bytes,
    *, found_on=None, found_area=None,
) -> int:
    sql = """
        INSERT INTO found_items
            (photo_name, photo_clues, image_embedding, found_on, found_area)
        VALUES (%s, %s, %s, %s, %s)
    """
    with connect_db() as connection:
        with connection.cursor(prepared=True) as cursor:
            cursor.execute(
                sql, (photo_name, json.dumps(photo_clues), embedding, found_on, found_area)
            )
            item_id = cursor.lastrowid
        connection.commit()
    return item_id


def list_found_items():
    sql = """
        SELECT id, found_on, found_area, image_embedding
        FROM found_items
        ORDER BY id DESC
    """
    with connect_db() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(sql)
            return cursor.fetchall()


def get_found_photo_name(item_id: int) -> str | None:
    with connect_db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT photo_name FROM found_items WHERE id = %s",
                (item_id,),
            )
            row = cursor.fetchone()
            return row[0] if row else None
