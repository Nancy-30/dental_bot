import { useState, useCallback } from 'react'
import { LiveKitRoom } from '@livekit/components-react'
import Sidebar from './components/Sidebar.jsx'
import ChatWindow from './components/ChatWindow.jsx'
import VoiceControls from './components/VoiceControls.jsx'

const API_BASE = ''   // proxied via Vite to http://localhost:7000

export default function App() {
  const [connectionDetails, setConnectionDetails] = useState(null)
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState('')
  const [userMessages, setUserMessages] = useState([])

  const connect = useCallback(async () => {
    setIsConnecting(true)
    setError('')
    try {
      const res = await fetch(`${API_BASE}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      setConnectionDetails(data)
    } catch (err) {
      setError(err.message || 'Could not connect to server.')
    } finally {
      setIsConnecting(false)
    }
  }, [])

  const handleDisconnect = useCallback(() => {
    setConnectionDetails(null)
    setUserMessages([])
  }, [])

  const handleUserTextSent = useCallback((text) => {
    setUserMessages((prev) => [
      ...prev,
      {
        id: `txt-${Date.now()}-${Math.random()}`,
        text,
        isAgent: false,
        timestamp: new Date().toISOString(),
        isFinal: true,
      },
    ])
  }, [])

  // ── Landing screen ────────────────────────────────────────────────────────────
  if (!connectionDetails) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-gradient-to-br from-brand-dark to-brand-panel">
        <div className="flex flex-col items-center gap-6">
          {/* Logo */}
          <div className={`w-24 h-24 rounded-full bg-brand-primary flex items-center justify-center shadow-2xl shadow-brand-primary/40
            ${isConnecting ? 'animate-pulse' : ''}`}>
            {/* Tooth icon */}
            <svg className="w-12 h-12 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C9.5 2 7.5 3 6 4.5 4.5 6 4 7.5 4 9c0 2 .8 3.5 1.5 5C6.2 15.5 7 17.5 7 19c0 1.1.9 2 2 2s2-.9 2-2v-2c0-.6.4-1 1-1s1 .4 1 1v2c0 1.1.9 2 2 2s2-.9 2-2c0-1.5.8-3.5 1.5-5C19.2 12.5 20 11 20 9c0-1.5-.5-3-2-4.5C16.5 3 14.5 2 12 2z"/>
            </svg>
          </div>

          {/* Title */}
          <div className="text-center">
            <h1 className="text-white font-bold text-2xl">ABC Dental Clinic</h1>
            <p className="text-brand-accent text-sm mt-1">AI Receptionist — Available 24/7</p>
          </div>

          {/* Capabilities hint */}
          <div className="text-center text-gray-400 text-xs max-w-xs">
            Book appointments, get clinic info, and get help instantly.
          </div>

          {/* States */}
          {isConnecting ? (
            <div className="flex flex-col items-center gap-2">
              <svg className="w-6 h-6 text-brand-primary animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              <p className="text-gray-400 text-sm">Connecting…</p>
            </div>
          ) : error ? (
            <div className="text-center">
              <p className="text-red-400 text-sm bg-red-900/30 px-4 py-2 rounded-lg">{error}</p>
              <button
                onClick={connect}
                className="mt-3 px-6 py-2.5 bg-brand-primary hover:bg-brand-accent text-white text-sm
                           font-medium rounded-xl transition-all active:scale-95"
              >
                Retry
              </button>
            </div>
          ) : (
            <button
              onClick={connect}
              className="mt-2 px-8 py-4 bg-brand-primary hover:bg-brand-accent text-white font-semibold
                         text-base rounded-2xl shadow-xl shadow-brand-primary/30 transition-all
                         duration-200 active:scale-95 flex items-center gap-3"
            >
              {/* Mic icon */}
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5zm6 6c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
              </svg>
              Start Conversation
            </button>
          )}
        </div>
      </div>
    )
  }

  // ── Main voice UI ─────────────────────────────────────────────────────────────
  return (
    <LiveKitRoom
      serverUrl={connectionDetails.livekit_url}
      token={connectionDetails.token}
      connect={true}
      audio={true}
      video={false}
      onDisconnected={handleDisconnect}
      className="h-screen w-screen"
    >
      <div className="flex h-screen w-screen overflow-hidden bg-slate-50">
        <Sidebar onStop={handleDisconnect} roomName={connectionDetails.room_name} />

        <div className="flex flex-col flex-1 min-w-0">
          <ChatWindow userMessages={userMessages} />
          <VoiceControls onUserTextSent={handleUserTextSent} />
        </div>
      </div>
    </LiveKitRoom>
  )
}
