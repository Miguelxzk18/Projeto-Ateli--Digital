import mysql.connector
from mysql.connector import errorcode


DB_CONFIG = {
    'host': os.getenv("DB_HOST", '127.0.0.1'),
    'port': 3306,
    'user': os.getenv("DB_USER", 'root'),
    'password': os.getenv("DB_PASS"),
    'database': os.getenv("DB_NAME", 'mydb')
}

def testar_conexao():
    print("Tentando conectar ao MySQL...")
    try:

        conn = mysql.connector.connect(**DB_CONFIG)
        
        if conn.is_connected():
            print("\n-------------------------------------------")
            print(">>> SUCESSO! Conexão estabelecida.")
            print("-------------------------------------------")
            
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES;")
            tables = cursor.fetchall()
            print("\nTabelas encontradas no banco de dados:")
            for table in tables:
                print(f"- {table[0]}")
            
            cursor.close()
            conn.close()

    except mysql.connector.Error as err:
        print("\n-------------------------------------------")
        print(">>> FALHA! Não foi possível conectar.")
        print("-------------------------------------------")
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Erro: Usuário ou senha incorretos.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print(f"Erro: O banco de dados '{DB_CONFIG['database']}' não existe.")
        elif err.errno == errorcode.CR_CONN_HOST_ERROR:
             print(f"Erro: Não foi possível conectar ao servidor em '{DB_CONFIG['host']}'.")
             print("Verifique se o servidor MySQL está rodando.")
        else:
            print(f"Ocorreu um erro inesperado: {err}")


if __name__ == "__main__":
    testar_conexao()