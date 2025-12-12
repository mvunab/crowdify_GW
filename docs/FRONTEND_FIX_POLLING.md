# Fix: Polling Infinito en usePurchaseCallback

## Problema Detectado

El hook `usePurchaseCallback` tiene un bug en el manejo del `finally` block que causa polling infinito.

## Código Corregido

Reemplaza la función `verifyPurchaseStatus` con esta versión:

```typescript
const verifyPurchaseStatus = async (orderId: string) => {
  // Verificar si ya hay una verificación en curso para esta orden
  if (isVerifying && verificationStartedRef.current === orderId) {
    return;
  }

  // Verificar si el componente está montado
  if (!isMountedRef.current) {
    return;
  }

  setIsVerifying(true);
  verificationStartedRef.current = orderId;

  // Flag para controlar si debemos limpiar isVerifying al final
  let shouldResetVerifying = true;

  try {
    // Verificar estado de la orden usando purchasesService
    const result = await purchasesService.getPurchaseStatus(orderId);

    // Verificar nuevamente si el componente está montado
    if (!isMountedRef.current) {
      return;
    }

    if (result.error) {
      debugError("verifyPurchaseStatus", "Error del servicio:", result.error);
      toast.error(t("purchase.error"), {
        description:
          result.error || "Error al verificar el estado de la compra",
      });
      verificationStartedRef.current = null;
      return;
    }

    const orderStatus = result.data?.status;
    debugLog("verifyPurchaseStatus", `Estado de orden: ${orderStatus}`);

    // =====================================================
    // ESTADOS FINALES - Detener polling completamente
    // =====================================================
    if (orderStatus === "completed") {
      debugLog(
        "verifyPurchaseStatus",
        "✅ Orden completada. Deteniendo polling."
      );

      // Limpiar TODO antes de cualquier otra cosa
      verificationStartedRef.current = null;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      setRetryCount(0);

      // Actualizar tickets si hay usuario
      if (user) {
        await fetchMyTickets();
      }

      // Guardar confirmación y limpiar pendiente
      localStorage.setItem(`payment_confirmed_${orderId}`, "true");
      localStorage.removeItem(`pending_order_${orderId}`);

      // Notificar a otros componentes
      window.dispatchEvent(
        new CustomEvent("paymentConfirmed", { detail: { orderId } })
      );

      return; // FIN - No más polling
    }

    if (
      orderStatus === "cancelled" ||
      orderStatus === "refunded" ||
      orderStatus === "failed"
    ) {
      debugLog(
        "verifyPurchaseStatus",
        "❌ Orden cancelada/fallida. Deteniendo polling."
      );

      verificationStartedRef.current = null;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }

      toast.error(t("purchase.cancelled"), {
        description: "El pago fue cancelado o falló",
      });

      localStorage.removeItem(`pending_order_${orderId}`);
      return; // FIN - No más polling
    }

    // =====================================================
    // ESTADOS PENDIENTES - Continuar polling con límite
    // =====================================================
    if (orderStatus === "pending" || orderStatus === "processing") {
      const currentRetryCount = retryCount;

      // Verificar límite de reintentos
      if (currentRetryCount >= MAX_RETRIES) {
        debugLog(
          "verifyPurchaseStatus",
          `⏰ Límite de reintentos alcanzado (${MAX_RETRIES})`
        );
        verificationStartedRef.current = null;
        toast.warning(t("purchase.processing"), {
          description:
            "El pago está tomando más tiempo de lo esperado. Te notificaremos por correo.",
        });
        return; // FIN - Límite alcanzado
      }

      // Toast informativo (solo cada 3 intentos)
      if (currentRetryCount === 0 || currentRetryCount % 3 === 0) {
        toast.info(t("purchase.processing"), {
          description: `Verificando estado del pago... (intento ${
            currentRetryCount + 1
          }/${MAX_RETRIES})`,
        });
      }

      // Incrementar contador
      setRetryCount((prev) => prev + 1);

      // 🔴 IMPORTANTE: NO resetear isVerifying porque vamos a seguir verificando
      shouldResetVerifying = false;

      // Limpiar timeout anterior
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      // Programar siguiente verificación
      timeoutRef.current = setTimeout(() => {
        if (!isMountedRef.current) return;

        // Verificar si ya se completó mientras esperábamos
        const paymentConfirmed = localStorage.getItem(
          `payment_confirmed_${orderId}`
        );
        if (paymentConfirmed === "true") {
          debugLog(
            "verifyPurchaseStatus",
            "Pago confirmado externamente. Deteniendo."
          );
          verificationStartedRef.current = null;
          setIsVerifying(false);
          return;
        }

        // Continuar verificando
        setIsVerifying(false); // Reset para permitir la siguiente llamada
        verifyPurchaseStatus(orderId);
      }, 5000);

      return;
    }

    // Estado desconocido - limpiar
    debugLog("verifyPurchaseStatus", `Estado desconocido: ${orderStatus}`);
    verificationStartedRef.current = null;
  } catch (error) {
    debugError("verifyPurchaseStatus", "Excepción:", error);
    verificationStartedRef.current = null;
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (isMountedRef.current) {
      toast.error(t("purchase.error"), {
        description: "Error al verificar el estado de la compra",
      });
    }
  } finally {
    // 🔴 FIX: Solo resetear si no estamos esperando otro intento
    if (isMountedRef.current && shouldResetVerifying) {
      setIsVerifying(false);
    }
  }
};
```

## Cambios Clave

1. **Variable `shouldResetVerifying`**: Controla si el `finally` debe resetear el estado
2. **No resetear en pending/processing**: Cuando programamos un nuevo timeout, NO reseteamos `isVerifying`
3. **Agregar `failed` a estados finales**: El estado `failed` también debe detener el polling
4. **Logs mejorados**: Para debug más claro

## También verificar en `purchasesService.ts`

Asegúrate de que `getPurchaseStatus` maneje errores 429:

```typescript
export const purchasesService = {
  async getPurchaseStatus(orderId: string) {
    try {
      const response = await api.get(`/purchases/${orderId}/status`);
      return { data: response.data, error: null };
    } catch (error: any) {
      // Manejar rate limiting
      if (error.response?.status === 429) {
        return {
          data: { status: "pending" }, // Tratar como pendiente
          error: null,
        };
      }
      return { data: null, error: error.message };
    }
  },
};
```

## Verificación

Después de aplicar los cambios:

1. Haz una compra de prueba
2. Observa la consola del navegador
3. Deberías ver:
   - `[usePurchaseCallback] Estado de orden: pending` (varios)
   - `[usePurchaseCallback] ✅ Orden completada. Deteniendo polling.` (una vez)
   - **No más logs después de esto**
