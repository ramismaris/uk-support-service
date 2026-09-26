import { Button, MaxUI } from '@maxhub/max-ui'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '../styles/index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MaxUI>
      <div className="p-4 text-brand">UK</div>
      <Button className="bg-red-500">Проверка каскада</Button>
    </MaxUI>
  </StrictMode>,
)
