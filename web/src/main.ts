import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

import './styles/theme.css'
import './styles/fonts.css'
import './styles/animations.css'
import './styles/nes-compat.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
