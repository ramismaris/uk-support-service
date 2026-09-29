import type { Broadcast, BroadcastStatus } from '../api/broadcasts'

export function broadcastProgress(
  broadcast: Pick<Broadcast, 'recipients_total' | 'delivered_count' | 'failed_count'>,
) {
  const handled = broadcast.delivered_count + broadcast.failed_count
  const share = broadcast.recipients_total > 0 ? handled / broadcast.recipients_total : 0
  return { handled, share: Math.min(share, 1) }
}

const labels: Record<BroadcastStatus, string> = {
  SENDING: 'Идёт отправка',
  DONE: 'Отправлена',
  INTERRUPTED: 'Прервана',
}

export function statusLabel(status: BroadcastStatus): string {
  return labels[status]
}
