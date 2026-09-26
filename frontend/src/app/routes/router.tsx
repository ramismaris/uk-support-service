import { createBrowserRouter } from 'react-router'
import { isAdmin, isClient, isStaff } from '@/entities/user'
import { AppearancePage } from '@/pages/appearance'
import { ContentLayout, SectionEditor } from '@/pages/content'
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
        children: [
          {
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
            path: routePaths.appearance,
            element: (
              <RequireRole allow={isAdmin}>
                <AppearancePage />
              </RequireRole>
            ),
          },
          {
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
  { path: '*', element: <NotFoundPage /> },
])
