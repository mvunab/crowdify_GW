"""
Script de prueba para verificar preferencias con múltiples items
Ejecuta: python test_preference_items.py
"""
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from dotenv import load_dotenv
from services.ticket_purchase.services.mercado_pago_service import MercadoPagoService

# Cargar variables de entorno
load_dotenv()

def test_single_item():
    """Prueba crear preferencia con un solo item (modo compatibilidad)"""
    print("🧪 Prueba 1: Preferencia con un solo item\n")
    
    try:
        service = MercadoPagoService()
        
        preference = service.create_preference(
            order_id="test-order-single-001",
            title="Ticket General - Evento de Prueba",
            total_amount=30000.0,
            currency="CLP",
            description="2 tickets para evento de prueba"
        )
        
        print("✅ Preferencia creada exitosamente!")
        print(f"   Preference ID: {preference['preference_id']}")
        print(f"   Payment Link: {preference['payment_link'][:80]}...")
        print()
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}\n")
        return False

def test_multiple_items():
    """Prueba crear preferencia con múltiples items (tickets + servicios)"""
    print("🧪 Prueba 2: Preferencia con múltiples items\n")
    
    try:
        service = MercadoPagoService()
        
        items = [
            {
                "title": "Ticket General - Concierto Rock",
                "description": "2 ticket(s) para Concierto Rock",
                "quantity": 2,
                "unit_price": 15000.0
            },
            {
                "title": "Servicio VIP",
                "description": "Acceso VIP - Concierto Rock",
                "quantity": 1,
                "unit_price": 5000.0
            },
            {
                "title": "Parking",
                "description": "Estacionamiento - Concierto Rock",
                "quantity": 1,
                "unit_price": 3000.0
            }
        ]
        
        preference = service.create_preference(
            order_id="test-order-multiple-001",
            currency="CLP",
            items=items
        )
        
        print("✅ Preferencia con múltiples items creada exitosamente!")
        print(f"   Preference ID: {preference['preference_id']}")
        print(f"   Payment Link: {preference['payment_link'][:80]}...")
        print()
        print("📋 Items en la preferencia:")
        total = 0
        for i, item in enumerate(items, 1):
            item_total = item['quantity'] * item['unit_price']
            total += item_total
            print(f"   {i}. {item['title']}")
            print(f"      Cantidad: {item['quantity']} × ${item['unit_price']:,.0f} = ${item_total:,.0f}")
        print(f"   Total: ${total:,.0f} CLP")
        print()
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False

def test_variable_prices():
    """Prueba con precios variables (simulando diferentes tipos de tickets)"""
    print("🧪 Prueba 3: Preferencia con precios variables\n")
    
    try:
        service = MercadoPagoService()
        
        items = [
            {
                "title": "Ticket General",
                "description": "Ticket general para evento",
                "quantity": 3,
                "unit_price": 10000.0
            },
            {
                "title": "Ticket VIP",
                "description": "Ticket VIP con beneficios exclusivos",
                "quantity": 1,
                "unit_price": 35000.0
            },
            {
                "title": "Ticket Niño",
                "description": "Ticket con precio especial para niños",
                "quantity": 2,
                "unit_price": 5000.0
            }
        ]
        
        preference = service.create_preference(
            order_id="test-order-variable-001",
            currency="CLP",
            items=items
        )
        
        print("✅ Preferencia con precios variables creada exitosamente!")
        print(f"   Preference ID: {preference['preference_id']}")
        print()
        print("📋 Items con precios variables:")
        total = 0
        for i, item in enumerate(items, 1):
            item_total = item['quantity'] * item['unit_price']
            total += item_total
            print(f"   {i}. {item['title']}")
            print(f"      {item['quantity']} × ${item['unit_price']:,.0f} = ${item_total:,.0f}")
        print(f"   💰 Total: ${total:,.0f} CLP")
        print()
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("  TEST DE PREFERENCIAS CON MÚLTIPLES ITEMS - MERCADO PAGO")
    print("=" * 70)
    print()
    
    results = []
    
    # Ejecutar pruebas
    results.append(("Un solo item", test_single_item()))
    results.append(("Múltiples items", test_multiple_items()))
    results.append(("Precios variables", test_variable_prices()))
    
    # Resumen
    print("=" * 70)
    print("  RESUMEN DE PRUEBAS")
    print("=" * 70)
    print()
    
    for test_name, success in results:
        status = "✅ PASÓ" if success else "❌ FALLÓ"
        print(f"  {status} - {test_name}")
    
    print()
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("🎉 ¡Todas las pruebas pasaron!")
        print("   Las preferencias dinámicas están funcionando correctamente.")
    else:
        print("⚠️  Algunas pruebas fallaron. Revisa los errores arriba.")
    
    print("=" * 70)


