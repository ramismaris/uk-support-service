import { api, unwrap } from '@/shared/api'

export interface ThemeBody {
  companyName: string
  primaryColor: string
  logoFileId: number | null
}

export function saveTheme(body: ThemeBody) {
  return unwrap(
    api.PUT('/api/v1/admin/content/theme', {
      body: {
        company_name: body.companyName.trim(),
        primary_color: body.primaryColor.toLowerCase(),
        logo_file_id: body.logoFileId,
      },
    }),
  )
}
