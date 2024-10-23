import mysql.connector
from mysql.connector import Error

def create_connection():
    """
    Database 연결
    """
    
    connection = None
    try:
        connection = mysql.connector.connect(
            host='localhost', # localhost / db 
            user='user',
            password='wrtn123',
            database='wrtn_proj',
            port=3306 
        )
        print("MySQL 데이터베이스에 성공적으로 연결되었습니다.")
    except Error as e:
        print(f"오류 발생: {e}")
    
    return connection

def create_tables(connection):
    """
    추출에 필요한 테이블 만들기
    """
    try:
        cursor = connection.cursor()

        # categories 테이블 생성
        create_categories_table = """
        CREATE TABLE IF NOT EXISTS categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            category VARCHAR(64) NOT NULL
        );
        """
        cursor.execute(create_categories_table)

        # wrtn_characters 테이블 생성
        create_wrtn_characters_table = """
        CREATE TABLE IF NOT EXISTS wrtn_characters (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            author VARCHAR(255),
            image_url TEXT,
            category INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category) REFERENCES categories(id)
        );
        """
        cursor.execute(create_wrtn_characters_table)
        connection.commit()
        
        
    except Error as e:
        print(f"테이블 생성 중 오류 발생: {e}")


def connect_database() :
    """
    초기 연결 conn 생성
    """
    conn = create_connection() # mysql 연결
    if conn : 
        create_tables(conn)
    
    return conn
