import { isPhoto, type Message, type MessageFile } from '@/entities/message'

export interface ChatPhoto {
  file: MessageFile
  author: string
  sentAt: string
}

// Every photo of the chat in order, for flipping through them in the viewer.
export function chatPhotos(messages: Message[], residentName: string): ChatPhoto[] {
  return messages.flatMap((message) =>
    message.files.filter(isPhoto).map((file) => ({
      file,
      author:
        message.sender_type === 'CLIENT' ? residentName : (message.author?.first_name ?? 'УК'),
      sentAt: message.created_at,
    })),
  )
}
