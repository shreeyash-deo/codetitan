import { useState, useEffect } from 'react'

export function useSidebar() {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('brandshield_sidebar_collapsed')
      return saved ? JSON.parse(saved) : false
    }
    return false
  })

  const [mobileOpen, setMobileOpen] = useState<boolean>(false)

  useEffect(() => {
    localStorage.setItem('brandshield_sidebar_collapsed', JSON.stringify(collapsed))
  }, [collapsed])

  const toggleSidebar = () => setCollapsed(prev => !prev)
  const toggleMobile = () => setMobileOpen(prev => !prev)
  const closeMobile = () => setMobileOpen(false)

  return {
    collapsed,
    setCollapsed,
    toggleSidebar,
    mobileOpen,
    setMobileOpen,
    toggleMobile,
    closeMobile,
  }
}
