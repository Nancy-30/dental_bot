import { useConnectionState, useVoiceAssistant } from '@livekit/components-react'
import { ConnectionState } from 'livekit-client'

export default function Sidebar({ onStop, roomName }) {
  const connectionState = useConnectionState()
  const { state: agentState } = useVoiceAssistant()

  const isConnected = connectionState === ConnectionState.Connected
  const isSpeaking  = agentState === 'speaking'
  const isListening = agentState === 'listening'
  const isThinking  = agentState === 'thinking'

  return (
    <aside className="w-64 flex-shrink-0 bg-brand-dark flex flex-col h-full border-r border-slate-700/50">

      {/* Logo area */}
      <div className="px-6 py-6 border-b border-slate-700/50">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-10 h-10 rounded-full bg-brand-primary flex items-center justify-center shadow-lg">
            <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C9.5 2 7.5 3 6 4.5 4.5 6 4 7.5 4 9c0 2 .8 3.5 1.5 5C6.2 15.5 7 17.5 7 19c0 1.1.9 2 2 2s2-.9 2-2v-2c0-.6.4-1 1-1s1 .4 1 1v2c0 1.1.9 2 2 2s2-.9 2-2c0-1.5.8-3.5 1.5-5C19.2 12.5 20 11 20 9c0-1.5-.5-3-2-4.5C16.5 3 14.5 2 12 2z"/>
            </svg>
          </div>
          <div>
            <h1 className="text-white font-bold text-sm leading-tight">ABC Dental Clinic</h1>
            <p className="text-brand-accent text-xs">AI Receptionist</p>
          </div>
        </div>
      </div>

      {/* Agent status */}
      <div className="px-6 py-5 border-b border-slate-700/50">
        <p className="text-slate-400 text-xs uppercase tracking-widest mb-3">Agent Status</p>

        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-10 h-10">
            {isSpeaking && (
              <span className="absolute inset-0 rounded-full bg-brand-primary/30 mic-pulse" />
            )}
            <div className={`w-8 h-8 rounded-full flex items-center justify-center
              ${isSpeaking  ? 'bg-brand-primary'  : ''}
              ${isListening ? 'bg-emerald-500'    : ''}
              ${isThinking  ? 'bg-amber-500'      : ''}
              ${!isSpeaking && !isListening && !isThinking ? 'bg-slate-600' : ''}
            `}>
              {isSpeaking && (
                <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.617.784L4.5 13H3a1 1 0 01-1-1V8a1 1 0 011-1h1.5l3.883-3.784a1 1 0 011 .076zM14.657 5.343a8 8 0 010 9.314 1 1 0 01-1.414-1.414 6 6 0 000-6.486 1 1 0 111.414-1.414z" />
                </svg>
              )}
              {isListening && (
                <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clipRule="evenodd" />
                </svg>
              )}
              {isThinking && (
                <div className="flex gap-0.5">
                  <span className="w-1 h-1 bg-white rounded-full dot-1" />
                  <span className="w-1 h-1 bg-white rounded-full dot-2" />
                  <span className="w-1 h-1 bg-white rounded-full dot-3" />
                </div>
              )}
              {!isSpeaking && !isListening && !isThinking && (
                <div className="w-2 h-2 rounded-full bg-slate-400" />
              )}
            </div>
          </div>

          <div>
            <p className="text-white text-sm font-medium capitalize">
              {isSpeaking  ? 'Speaking'  : ''}
              {isListening ? 'Listening' : ''}
              {isThinking  ? 'Thinking…' : ''}
              {!isSpeaking && !isListening && !isThinking ? (isConnected ? 'Ready' : 'Idle') : ''}
            </p>
            <p className="text-slate-500 text-xs">
              {isConnected ? 'Connected' : 'Disconnected'}
            </p>
          </div>
        </div>
      </div>

      {/* Capabilities */}
      <div className="px-6 py-5 flex-1">
        <p className="text-slate-400 text-xs uppercase tracking-widest mb-3">I Can Help With</p>
        <ul className="space-y-2 text-slate-400 text-xs">
          {[
            'Book an Appointment',
            'Reschedule / Cancel',
            'Clinic Hours & Location',
            'Insurance & Billing',
            'Dental Services',
            'Emergency Guidance',
          ].map((cap) => (
            <li key={cap} className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-primary flex-shrink-0" />
              {cap}
            </li>
          ))}
        </ul>
      </div>

      {/* Stop button */}
      <div className="px-6 py-6">
        <button
          onClick={onStop}
          className="w-full py-3 rounded-xl bg-red-600 hover:bg-red-700 text-white font-semibold
                     text-sm transition-all duration-200 shadow-lg active:scale-95"
        >
          End Conversation
        </button>
      </div>
    </aside>
  )
}
