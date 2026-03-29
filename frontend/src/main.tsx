import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import App from "./App"
import PrivacyPolicy from "./pages/PrivacyPolicy"
import TermsAndConditions from "./pages/TermsAndConditions"

const rootElement = document.getElementById("root")
if (!rootElement) throw new Error("Root element not found")

const path = window.location.pathname
let Page = App
if (path === "/privacy-policy") Page = PrivacyPolicy
else if (path === "/terms-and-conditions") Page = TermsAndConditions

createRoot(rootElement).render(
  <StrictMode>
    <Page />
  </StrictMode>
)
