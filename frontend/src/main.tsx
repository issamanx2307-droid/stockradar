import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import App from "./App"
import PrivacyPolicy from "./pages/PrivacyPolicy"

const rootElement = document.getElementById("root")
if (!rootElement) throw new Error("Root element not found")

const isPrivacyPolicy = window.location.pathname === "/privacy-policy"

createRoot(rootElement).render(
  <StrictMode>
    {isPrivacyPolicy ? <PrivacyPolicy /> : <App />}
  </StrictMode>
)
