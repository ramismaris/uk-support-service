import { useMutation } from '@tanstack/react-query'
import { uploadImage } from '../api/upload-image'

export function useUploadImage() {
  return useMutation({ mutationFn: uploadImage })
}
