import { createBrowserRouter } from 'react-router'
import { isAdmin, isClient, isStaff } from '@/entities/user'
import { AppearancePage } from '@/pages/appearance'
import { ContentLayout, SectionEditor } from '@/pages/content'
import { BroadcastPage } from '@/pages/broadcast'
import { DashboardPage } from '@/pages/dashboard'
import { UserCard, UsersIndex, UsersLayout } from '@/pages/users'
import { ClientHomePage } from '@/pages/client-home'
import { LoginPage } from '@/pages/login'
import { NotFoundPage } from '@/pages/not-found'
import { TicketPage, TicketsIndexPage, TicketsLayout } from '@/pages/tickets'
import { routePaths } from '@/shared/config'
import { AppShell } from '@/widgets/app-shell'
import { StaffRealtime } from '../realtime/StaffRealtime'
import { RequireRole } from './RequireRole'
import { RoleRedirect } from './RoleRedirect'
import { RouteError } from './RouteError'
import { SessionGate } from './SessionGate'

export const router = createBrowserRouter([
  { path: routePaths.login, element: <LoginPage />, errorElement: <RouteError /> },
  {
    path: routePaths.home,
    element: <SessionGate />,
    errorElement: <RouteError />,
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
        children: [
          {
            errorElement: <RouteError inline />,
            path: routePaths.dashboard,
            element: (
              <RequireRole allow={isAdmin}>
                <DashboardPage />
              </RequireRole>
            ),
          },
          {
            errorElement: <RouteError inline />,
            path: routePaths.broadcast,
            element: (
              <RequireRole allow={isAdmin}>
                <BroadcastPage />
              </RequireRole>
            ),
          },
          {
            errorElement: <RouteError inline />,
            path: routePaths.content,
            element: (
              <RequireRole allow={isAdmin}>
                <ContentLayout />
              </RequireRole>
            ),
            children: [
              { index: true, element: <SectionEditor /> },
              { path: routePaths.contentSection, element: <SectionEditor /> },
            ],
          },
          {
            errorElement: <RouteError inline />,
            path: routePaths.users,
            element: (
              <RequireRole allow={isAdmin}>
                <UsersLayout />
              </RequireRole>
            ),
            children: [
              { index: true, element: <UsersIndex /> },
              { path: routePaths.user, element: <UserCard /> },
            ],
          },
          {
            errorElement: <RouteError inline />,
            path: routePaths.appearance,
            element: (
              <RequireRole allow={isAdmin}>
                <AppearancePage />
              </RequireRole>
            ),
          },
          {
            errorElement: <RouteError inline />,
            element: <TicketsLayout />,
            children: [
              { index: true, element: <TicketsIndexPage /> },
              { path: routePaths.ticket, element: <TicketPage /> },
            ],
          },
        ],
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
  { path: '*', element: <NotFoundPage />, errorElement: <RouteError /> },
])
