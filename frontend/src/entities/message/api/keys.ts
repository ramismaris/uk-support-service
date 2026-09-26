export const messageKeys = {
  all: ['messages'] as const,
  list: (ticketId: number) => [...messageKeys.all, ticketId] as const,
}
