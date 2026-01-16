# Esto es Python
producto = "Mayólica Blanca 60x60"
stock_actual = 100
venta = int(input("¿Cuántas cajas vendiste?: ")) # Pide un dato al usuario

# Lógica básica
if venta <= stock_actual:
    stock_actual -= venta # Resta el stock
    print(f"Venta exitosa. Quedan {stock_actual} cajas de {producto}.")
else:
    print("Error: No tienes suficiente stock.")