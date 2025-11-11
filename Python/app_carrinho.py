import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

try:
    mydb = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME")
    )

    mycursor = mydb.cursor()

    id_usuario_consulta = 1

    sql = "SELECT * FROM carrinho WHERE id_cliente = %s"
    val = (id_usuario_consulta, )

    mycursor.execute(sql, val)

    resultados = mycursor.fetchall()

    if not resultados:
        print(f"O carrinho do usuário {id_usuario_consulta} está vazio.")
    else:
        print(f"Itens no carrinho do usuário {id_usuario_consulta}:")
        for item in resultados:
            print(f"  - ID da Linha: {item[0]}, ID Produto: {item[2]}, Quantidade: {item[3]}")

except mysql.connector.Error as err:
    print(f"Erro ao consultar dados: {err}")

finally:
    if 'mydb' in locals() and mydb.is_connected():
        mycursor.close()
        mydb.close()
        print("\nConexão com o MySQL fechada.")