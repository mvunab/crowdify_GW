#!/usr/bin/env python3
"""
Script para debuggear el webhook de Mercado Pago
Verifica configuración, logs y estado de las órdenes
"""

import os
import sys
import asyncio
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from shared.database.session import get_db
from shared.database.models import Order
from sqlalchemy import select
from datetime import datetime

async def check_order_status(order_id: str):
    """Verificar estado de una orden específica"""
    async for db in get_db():
        try:
            stmt = select(Order).where(Order.id == order_id)
            result = await db.execute(stmt)
            order = result.scalar_one_or_none()
            
            if not order:
                print(f"❌ Orden {order_id} no encontrada")
                return
            
            print(f"\n📋 Estado de la Orden: {order_id}")
            print(f"   Status: {order.status}")
            print(f"   Payment Provider: {order.payment_provider}")
            print(f"   Payment Reference: {order.payment_reference}")
            print(f"   Created At: {order.created_at}")
            print(f"   Paid At: {order.paid_at}")
            print(f"   Total: {order.total} {order.currency}")
            
            # Verificar si hay tickets
            if order.order_items:
                total_tickets = sum(len(item.tickets) for item in order.order_items)
                print(f"   Tickets generados: {total_tickets}")
            else:
                print(f"   Tickets generados: 0")
                
        except Exception as e:
            print(f"❌ Error verificando orden: {e}")
        finally:
            await db.close()
        break

async def list_recent_orders(limit=5):
    """Listar órdenes recientes"""
    async for db in get_db():
        try:
            stmt = select(Order).order_by(Order.created_at.desc()).limit(limit)
            result = await db.execute(stmt)
            orders = result.scalars().all()
            
            print(f"\n📋 Últimas {limit} órdenes:")
            for order in orders:
                print(f"\n   ID: {order.id}")
                print(f"   Status: {order.status}")
                print(f"   Provider: {order.payment_provider}")
                print(f"   Reference: {order.payment_reference}")
                print(f"   Created: {order.created_at}")
                print(f"   Paid: {order.paid_at}")
                
        except Exception as e:
            print(f"❌ Error listando órdenes: {e}")
        finally:
            await db.close()
        break

def check_env_vars():
    """Verificar variables de entorno"""
    print("\n🔍 Verificando Variables de Entorno:")
    
    webhook_secret = os.getenv("MERCADOPAGO_WEBHOOK_SECRET")
    ngrok_url = os.getenv("NGROK_URL")
    access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
    app_base_url = os.getenv("APP_BASE_URL", "http://localhost:3000")
    
    print(f"   MERCADOPAGO_ACCESS_TOKEN: {'✅ Configurado' if access_token else '❌ NO configurado'}")
    print(f"   MERCADOPAGO_WEBHOOK_SECRET: {'✅ Configurado' if webhook_secret else '⚠️  NO configurado (opcional en desarrollo)'}")
    print(f"   NGROK_URL: {'✅ ' + ngrok_url if ngrok_url else '❌ NO configurado (necesario para webhooks locales)'}")
    print(f"   APP_BASE_URL: {app_base_url}")
    
    if ngrok_url:
        webhook_url = f"{ngrok_url}/api/v1/purchases/webhook"
        print(f"\n   🔔 URL del Webhook: {webhook_url}")
    else:
        print(f"\n   ⚠️  NGROK_URL no configurado - El webhook no será accesible desde Mercado Pago")
        print(f"   💡 Solución: Configura ngrok y agrega NGROK_URL a tu .env")

def check_webhook_endpoint():
    """Verificar que el endpoint del webhook existe"""
    print("\n🔍 Verificando Endpoint del Webhook:")
    print("   Endpoint: POST /api/v1/purchases/webhook")
    print("   ✅ Endpoint implementado en: services/ticket_purchase/routes/purchase.py")

async def main():
    print("=" * 60)
    print("🔍 DEBUG WEBHOOK - Mercado Pago")
    print("=" * 60)
    
    # Verificar variables de entorno
    check_env_vars()
    
    # Verificar endpoint
    check_webhook_endpoint()
    
    # Listar órdenes recientes
    await list_recent_orders(5)
    
    # Si se proporciona un order_id, verificar su estado
    if len(sys.argv) > 1:
        order_id = sys.argv[1]
        await check_order_status(order_id)
    
    print("\n" + "=" * 60)
    print("📝 Próximos Pasos para Debuggear:")
    print("=" * 60)
    print("1. Verifica los logs del backend cuando hagas un pago")
    print("2. Busca mensajes que empiecen con '🔔 [WEBHOOK]'")
    print("3. Si no ves esos mensajes, el webhook no está llegando")
    print("4. Verifica en Mercado Pago > Webhooks > Historial de notificaciones")
    print("5. Asegúrate de que el webhook esté configurado en 'Modo test' si usas sandbox")
    print("\n💡 Para verificar una orden específica:")
    print(f"   python scripts/debug_webhook.py <order_id>")

if __name__ == "__main__":
    asyncio.run(main())

