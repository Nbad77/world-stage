import React from 'react'
import ReactDOM from 'react-dom/client'
import { ClerkProvider } from '@clerk/clerk-react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App'
import SignInPage from './components/SignInPage'
import SignUpPage from './components/SignUpPage'
import './index.css'
import './tailwind.css'
import './dashboard.css'
import './mobile.css'

const CLERK_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

if (!CLERK_KEY) {
  console.warn('[AUTH] VITE_CLERK_PUBLISHABLE_KEY is not set — running in guest mode')
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {CLERK_KEY ? (
      <ClerkProvider publishableKey={CLERK_KEY}>
        <BrowserRouter>
          <Routes>
            <Route path="/sign-in/*" element={<SignInPage />} />
            <Route path="/sign-up/*" element={<SignUpPage />} />
            <Route path="/*" element={<App />} />
          </Routes>
        </BrowserRouter>
      </ClerkProvider>
    ) : (
      <BrowserRouter>
        <Routes>
          <Route path="/*" element={<App />} />
        </Routes>
      </BrowserRouter>
    )}
  </React.StrictMode>
)
