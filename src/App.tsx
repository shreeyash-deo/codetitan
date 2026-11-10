import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { WorkspaceProvider } from '@/hooks/useWorkspace'
import { ToastProvider } from '@/context/ToastContext'
import { GovernanceProvider } from '@/context/GovernanceContext'
import { AppShell } from '@/components/layout/AppShell'
import { OverviewPage } from '@/pages/OverviewPage'
import { ContentReviewPage } from '@/pages/ContentReviewPage'
import { BrandGuidelinesPage } from '@/pages/BrandGuidelinesPage'
import { ReviewHistoryPage } from '@/pages/ReviewHistoryPage'
import { TeamApprovalsPage } from '@/pages/TeamApprovalsPage'
import { SettingsPage } from '@/pages/SettingsPage'

export const App: React.FC = () => {
  return (
    <WorkspaceProvider>
      <ToastProvider>
        <GovernanceProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<AppShell />}>
                <Route index element={<OverviewPage />} />
                <Route path="content-review" element={<ContentReviewPage />} />
                <Route path="brand-guidelines" element={<BrandGuidelinesPage />} />
                <Route path="review-history" element={<ReviewHistoryPage />} />
                <Route path="team-approvals" element={<TeamApprovalsPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </GovernanceProvider>
      </ToastProvider>
    </WorkspaceProvider>
  )
}

export default App
