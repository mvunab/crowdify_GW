# Resumen Ejecutivo: Sistema de Productos para Niños

## 🎯 Objetivo Principal
Permitir la compra de productos para niños de forma independiente a las entradas, similar al modelo de cine, donde puedes comprar cualquier producto sin necesidad de tener una entrada.

## 📋 Características Clave

### 1. **Productos Independientes**
- Cada entrada puede tener productos asociados (productos para niños)
- Los productos se pueden comprar sin tener entrada al evento
- Cada producto tiene su propio stock y precio

### 2. **Formulario de Niños**
- Se mantiene el formulario actual de datos de niños
- Se aplica cuando se compra un producto de tipo `child_ticket` o `child_product`
- Incluye: datos personales, medicamentos, alergias, contacto de emergencia

### 3. **Compra Múltiple**
- Un usuario puede comprar múltiples productos en una sola transacción
- No hay límite de cantidad (excepto por stock)
- Cada producto requiere completar el formulario de niño

### 4. **Stock Independiente**
- Cada producto tiene su propio stock (`stock` y `stock_available`)
- Se gestiona independientemente del stock de entradas
- Se valida antes de permitir la compra

### 5. **Compra como Visitante**
- Endpoint público para compras sin autenticación
- Requiere datos de contacto del comprador
- Los tickets/productos se asocian al comprador visitante

## 🔌 Endpoints Principales

### Públicos
- `GET /api/v1/events/{event_id}/child-products` - Listar productos disponibles
- `POST /api/v1/purchases/child-products/guest` - Comprar como visitante

### Autenticados
- `POST /api/v1/purchases/child-products` - Comprar productos (requiere login)
- `GET /api/v1/purchases/child-products/{order_id}` - Ver estado de compra

## 📊 Modelos de Datos Nuevos

1. **OrderServiceItemChildDetail** - Detalles de niño para productos
2. **OrderServiceItemChildMedication** - Medicamentos de niños en productos
3. Modificaciones a **Order** - Campos para visitantes
4. Modificaciones a **EventService** - Campos para productos de niños

## 🔄 Flujo de Compra

```
Usuario/Visitante
    ↓
Ver productos disponibles
    ↓
Seleccionar productos y cantidad
    ↓
Completar formulario de niño (por cada producto)
    ↓
Validar stock disponible
    ↓
Crear orden y generar link de pago
    ↓
Completar pago
    ↓
Confirmar orden y generar tickets/productos
```

## ✅ Criterios de Aceptación

- ✅ Comprar productos sin entrada al evento
- ✅ Mantener formulario actual de niños
- ✅ Comprar múltiples productos
- ✅ Stock independiente por producto
- ✅ Compra como visitante funcional
- ✅ Integración con sistema de pagos

## 🚀 Próximos Pasos

1. Revisar y aprobar la HU
2. Crear migraciones de base de datos
3. Implementar servicios backend
4. Crear endpoints
5. Implementar frontend
6. Testing y validación

