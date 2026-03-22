/**
 * api/config.ts — Base URL configuration
 * local dev: proxy ผ่าน Vite → ใช้ /api
 * production: https://stockradar-api.onrender.com/api
 */
export const API_BASE = import.meta.env.VITE_API_URL || "/api"
export const WS_BASE  = import.meta.env.VITE_WS_URL
  || (window.location.protocol === "https:" ? "wss:" : "ws:") + "//" + window.location.host + "/ws"
