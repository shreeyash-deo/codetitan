import React from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { useSidebar } from '@/hooks/useSidebar'
import { useAuth } from '@/context/AuthContext'
import { useWorkspace } from '@/hooks/useWorkspace'
import { AuthPage } from '@/components/auth/AuthPage'
import { WorkspaceSelectorView } from '@/components/workspace/WorkspaceSelectorView'
import { X, Loader2, Shield } from 'lucide-react'

export const AppShell: React.FC = () => {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()
  const { currentWorkspace, isLoading: wsLoading } = useWorkspace()
  const {
    collapsed,
    toggleSidebar,
    mobileOpen,
    toggleMobile,
    closeMobile,
  } = useSidebar()

  // 1. Initial Session Restoration Loading State
  if (authLoading) {
    return (
      <div className="min-h-screen w-screen bg-[#070C14] flex flex-col items-center justify-center text-slate-100 select-none">
        <div className="p-3.5 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400 mb-3 animate-pulse">
          <Shield className="w-8 h-8" />
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
          <span>Restoring BrandShield session...</span>
        </div>
      </div>
    )
  }

  // 2. Unauthenticated: Show BrandShield Auth Page
  if (!isAuthenticated || !user) {
    return <AuthPage />
  }

  // 3. Workspace Loading State
  if (wsLoading) {
    return (
      <div className="min-h-screen w-screen bg-[#070C14] flex flex-col items-center justify-center text-slate-100 select-none">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
          <span>Loading organisations...</span>
        </div>
      </div>
    )
  }

  // 4. No organisation or multiple organisations with none selected
  if (!currentWorkspace) {
    return <WorkspaceSelectorView />
  }

  // 5. Full Authenticated Application Shell
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      {/* Desktop Sidebar */}
      <div className="hidden lg:flex shrink-0">
        <Sidebar
          collapsed={collapsed}
          onToggleCollapse={toggleSidebar}
        />
      </div>

      {/* Mobile Drawer Backdrop & Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs transition-opacity"
            onClick={closeMobile}
          />

          {/* Drawer content */}
          <div className="fixed inset-y-0 left-0 flex flex-col w-72 bg-[#0B1220] shadow-2xl z-10 animate-in slide-in-from-left duration-200">
            <div className="absolute top-3 right-3 z-20">
              <button
                onClick={closeMobile}
                className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800"
                aria-label="Close menu"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <Sidebar
              collapsed={false}
              onToggleCollapse={closeMobile}
              onItemClick={closeMobile}
            />
          </div>
        </div>
      )}

      {/* Main Viewport */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Header onMobileMenuToggle={toggleMobile} />

        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
