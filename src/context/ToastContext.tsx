import React, { createContext, useContext, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, AlertCircle, Info, XCircle, X } from 'lucide-react'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface ToastMessage {
  id: string
  title?: string
  message: string
  type: ToastType
  duration?: number
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType, title?: string) => void
  success: (message: string, title?: string) => void
  error: (message: string, title?: string) => void
  warning: (message: string, title?: string) => void
  info: (message: string, title?: string) => void
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined)

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const addToast = useCallback(
    (message: string, type: ToastType = 'info', title?: string, duration: number = 4000) => {
      const id = `toast-${Date.now()}-${Math.random()}`
      setToasts((prev) => [...prev, { id, message, type, title, duration }])

      if (duration > 0) {
        setTimeout(() => {
          removeToast(id)
        }, duration)
      }
    },
    [removeToast]
  )

  const success = useCallback((msg: string, title?: string) => addToast(msg, 'success', title), [addToast])
  const error = useCallback((msg: string, title?: string) => addToast(msg, 'error', title), [addToast])
  const warning = useCallback((msg: string, title?: string) => addToast(msg, 'warning', title), [addToast])
  const info = useCallback((msg: string, title?: string) => addToast(msg, 'info', title), [addToast])

  return (
    <ToastContext.Provider value={{ toast: addToast, success, error, warning, info }}>
      {children}
      {/* Toast Notification Container */}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm pointer-events-none">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 15, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className={`pointer-events-auto p-3.5 rounded-lg border shadow-xl flex items-start gap-3 text-xs bg-white ${
                t.type === 'success'
                  ? 'border-emerald-200 text-slate-800'
                  : t.type === 'error'
                  ? 'border-rose-200 text-slate-800'
                  : t.type === 'warning'
                  ? 'border-amber-200 text-slate-800'
                  : 'border-blue-200 text-slate-800'
              }`}
            >
              <div className="shrink-0 mt-0.5">
                {t.type === 'success' && <CheckCircle2 className="w-4 h-4 text-emerald-600" />}
                {t.type === 'error' && <XCircle className="w-4 h-4 text-rose-600" />}
                {t.type === 'warning' && <AlertCircle className="w-4 h-4 text-amber-600" />}
                {t.type === 'info' && <Info className="w-4 h-4 text-blue-600" />}
              </div>

              <div className="flex-1 min-w-0">
                {t.title && <div className="font-semibold text-slate-900 mb-0.5">{t.title}</div>}
                <div className="text-slate-600 leading-snug">{t.message}</div>
              </div>

              <button
                onClick={() => removeToast(t.id)}
                className="text-slate-400 hover:text-slate-700 p-0.5 shrink-0"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}

export const useToast = () => {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}
