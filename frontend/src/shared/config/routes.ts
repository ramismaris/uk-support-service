export const routePaths = {
  home: '/',
  login: '/login',
  staff: '/staff',
  ticket: '/staff/tickets/:id',
  client: '/client',
} as const

export function ticketPath(id: number): string {
  return `/staff/tickets/${id}`
}
