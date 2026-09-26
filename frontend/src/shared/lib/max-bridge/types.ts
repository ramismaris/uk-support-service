// Only the fields we use from https://st.max.ru/js/max-web-app.js.
export interface MaxWebApp {
  initData: string
  // The start_param format is confirmed live in Ф2, so keep it unknown here.
  initDataUnsafe?: { start_param?: unknown }
}

declare global {
  interface Window {
    WebApp?: MaxWebApp
  }
}
