export const routePaths = {
  home: '/',
  login: '/login',
  staff: '/staff',
  ticket: '/staff/tickets/:id',
  content: '/staff/content',
  contentSection: '/staff/content/:section',
  users: '/staff/users',
  user: '/staff/users/:id',
  appearance: '/staff/appearance',
  dashboard: '/staff/dashboard',
  broadcast: '/staff/broadcast',
  client: '/client',
} as const

export function ticketPath(id: number): string {
  return `/staff/tickets/${id}`
}

export function contentPath(section: string): string {
  return `/staff/content/${section}`
}

export function userPath(id: number): string {
  return `/staff/users/${id}`
}
