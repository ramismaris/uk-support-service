import { createBrowserRouter } from 'react-router'
import { isClient, isStaff } from '@/entities/user'
import { ClientHomePage } from '@/pages/client-home'
import { LoginPage } from '@/pages/login'
import { NotFoundPage } from '@/pages/not-found'
import { StaffHomePage } from '@/pages/staff-home'
import { routePaths } from '@/shared/config'
import { AppShell } from '@/widgets/app-shell'
import { StaffRealtime } from '../realtime/StaffRealtime'
import { RequireRole } from './RequireRole'
import { RoleRedirect } from './RoleRedirect'
import { SessionGate } from './SessionGate'

export const router = createBrowserRouter([
  { path: routePaths.login, element: <LoginPage /> },
  {
    path: routePaths.home,
    element: <SessionGate />,
    children: [
      { index: true, element: <RoleRedirect /> },
      {
        path: routePaths.staff,
        element: (
          <RequireRole allow={isStaff}>
            <StaffRealtime />
            <AppShell />
          </RequireRole>
        ),
        children: [{ index: true, element: <StaffHomePage /> }],
      },
      {
        path: routePaths.client,
        element: (
          <RequireRole allow={isClient}>
            <ClientHomePage />
          </RequireRole>
        ),
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
])
