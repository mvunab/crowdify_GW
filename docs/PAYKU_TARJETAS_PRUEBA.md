# Tarjetas de Prueba - Payku

## 🎯 Ambiente Sandbox

Para realizar pruebas de transacciones en el ambiente sandbox de Payku, utiliza las siguientes tarjetas:

### ✅ Tarjetas que Generan Transacciones Aprobadas

| Tipo | Número de Tarjeta | CVV | Fecha de Expiración | Notas |
|------|-------------------|-----|---------------------|-------|
| **VISA** | 4051 8856 0044 6623 | 123 | Cualquier fecha válida | Transacciones aprobadas |
| **AMEX** | 3700 0000 0002 032 | 1234 | Cualquier fecha válida | Transacciones aprobadas |
| **Redcompra** | 4051 8842 3993 7763 | - | - | Aprobada (débito Redcompra y prepago) |
| **Prepago VISA** | 4051 8860 0005 6590 | 123 | Cualquier fecha válida | Transacciones aprobadas |

### ❌ Tarjetas que Generan Transacciones Rechazadas

| Tipo | Número de Tarjeta | CVV | Fecha de Expiración | Notas |
|------|-------------------|-----|---------------------|-------|
| **MASTERCARD** | 5186 0595 5959 0568 | 123 | Cualquier fecha válida | Transacciones rechazadas |
| **Redcompra** | 5186 0085 4123 3829 | - | - | Rechazada (débito Redcompra y prepago) |
| **Prepago MASTERCARD** | 5186 1741 1062 9480 | 123 | Cualquier fecha válida | Transacciones rechazadas |

## 🔐 Autenticación con RUT

Cuando aparece el formulario de autenticación con RUT y clave en Payku:

- **RUT:** `11.111.111-1`
- **Clave:** `123`

## 📝 Notas Importantes

1. **Ambiente Sandbox:** Estas tarjetas solo funcionan en el ambiente de pruebas (`https://des.payku.cl`)
2. **Fecha de Expiración:** Para las tarjetas que requieren fecha, usa cualquier fecha futura válida
3. **CVV:** Usa los CVV indicados en la tabla
4. **Redcompra:** Las tarjetas Redcompra no requieren CVV ni fecha de expiración

## 🔗 Endpoints de Payku

- **Sandbox (Pruebas):** `https://des.payku.cl/api`
- **Producción:** `https://app.payku.cl/api`

## 📚 Referencia

Documentación oficial: [Payku API Docs](https://docs.payku.com/)

