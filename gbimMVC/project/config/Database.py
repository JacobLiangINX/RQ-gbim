import mysql.connector

connection = mysql.connector(
    host = "10.55.23.168:33060",
    user = "root",
    password = "1688"
)

cursor = connection.cursor()
