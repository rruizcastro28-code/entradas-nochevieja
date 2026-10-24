"""
Automated test suite to verify ticket lifecycle and anti-fraud mechanisms.
"""
import database
import urllib.request
import json
import time

def run_tests():
    print("Iniciando pruebas del sistema de entradas...")
    database.init_db()

    # 1. Test stats initially
    stats = database.get_stats()
    print("1. Estadísticas iniciales:", stats)
    assert stats["max_capacity"] == 499

    # 2. Test create nominal ticket
    ticket = database.create_ticket(
        name="Carlos",
        surname="Martínez",
        dni="12345678Z",
        email="carlos@ejemplo.com",
        phone="612345678",
        price=35.0,
        payment_method="Efectivo",
        notes="Amigo del organizador"
    )
    print(f"2. Entrada emitida: Nº #{ticket['ticket_number']:03d} - Código: {ticket['code']}")
    assert ticket["status"] == "VALIDA"
    assert ticket["dni"] == "12345678Z"

    # 3. Test check DNI exists
    existing = database.check_dni_exists("12345678Z")
    print(f"3. Comprobación de DNI duplicado: {len(existing)} encontradas")
    assert len(existing) == 1

    # 4. Test door scan validation - First time (SHOULD BE VALID)
    status, scanned_t, msg = database.validate_ticket_scan(ticket["code"])
    print(f"4. Primer escaneo en puerta: Estado={status}, Mensaje={msg}")
    assert status == "VALID"
    assert scanned_t["status"] == "USADA"
    assert scanned_t["used_at"] is not None

    # 5. Test door scan validation - Second time (SHOULD BE DETECTED AS FRAUD / ALREADY USED)
    status2, scanned_t2, msg2 = database.validate_ticket_scan(ticket["code"])
    print(f"5. Segundo escaneo (intento de duplicado/fraude): Estado={status2}, Mensaje={msg2}")
    assert status2 == "ALREADY_USED"

    # 6. Test invalid fake code (SHOULD BE NOT_FOUND)
    status3, scanned_t3, msg3 = database.validate_ticket_scan("FAKE-CODE-999")
    print(f"6. Escaneo de código falso: Estado={status3}, Mensaje={msg3}")
    assert status3 == "NOT_FOUND"

    # 7. Test manual door validation via DNI
    # Create second ticket
    ticket2 = database.create_ticket(
        name="Laura",
        surname="Gómez",
        dni="87654321A",
        email="laura@ejemplo.com",
        phone="699887766",
        price=35.0,
        payment_method="Bizum"
    )
    status_dni, t_dni, msg_dni = database.validate_ticket_scan("87654321A")
    print(f"7. Validación manual por DNI: Estado={status_dni}, Titular={t_dni['name']}")
    assert status_dni == "VALID"

    # 8. Test stats after tickets
    stats_after = database.get_stats()
    print("8. Estadísticas finales:", stats_after)
    assert stats_after["sold"] >= 2
    assert stats_after["checked_in"] >= 2

    # Clean up test tickets
    conn = database.get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM tickets WHERE code IN (?, ?)", (ticket["code"], ticket2["code"]))
    conn.commit()
    conn.close()

    print("\n✅ ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE (Tickets de prueba eliminados)!")

if __name__ == "__main__":
    run_tests()
