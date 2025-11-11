import mysql.connector

try:
    mydb = mysql.connector.connect(
      host="localhost",
      user="root",
      password="Gb200426",
      database="mydb"
    )

    mycursor = mydb.cursor()

    print("Conexão bem-sucedida. Inserindo item de teste...")

    sql = "INSERT INTO carrinho (id_cliente, id_produto, quantidade) VALUES (%s, %s, %s)"
    val = (1, 1, 2)

    mycursor.execute(sql, val)
    mydb.commit()

    print(mycursor.rowcount, "item inserido no carrinho com sucesso.")

except mysql.connector.Error as err:
    print(f"Erro ao inserir dados: {err}")

finally:
    if 'mydb' in locals() and mydb.is_connected():
        mycursor.close()
        mydb.close()
        print("Conexão com o MySQL fechada.")