import { useEffect, useRef, useState } from 'react'
import { useRoomContext } from '@livekit/components-react'
import { RoomEvent } from 'livekit-client'
import MessageBubble from './MessageBubble.jsx'

export default function ChatWindow({ userMessages = [] }) {
  const room   = useRoomContext()
  const [transcriptMessages, setTranscriptMessages] = useState([])
  const bottomRef = useRef(null)

  const messages = [...transcriptMessages, ...userMessages].sort(
    (a, b) => new Date(a.timestamp) - new Date(b.timestamp)
  )

  useEffect(() => {
    if (!room) return

    const onTranscription = (segments, participant) => {
      if (!segments || segments.length === 0) return

      const isAgent = participant?.identity !== room.localParticipant?.identity
      const now     = new Date().toISOString()

      const finalSegments    = segments.filter((s) => s.final)
      const nonFinalSegments = segments.filter((s) => !s.final)

      if (finalSegments.length > 0) {
        const text = finalSegments.map((s) => s.text).join(' ').trim()
        if (text) {
          setTranscriptMessages((prev) => {
            const last = prev[prev.length - 1]
            if (last && last.isAgent === isAgent && !last.isFinal) {
              return [
                ...prev.slice(0, -1),
                { id: last.id, text, isAgent, timestamp: now, isFinal: true },
              ]
            }
            return [
              ...prev,
              { id: `${Date.now()}-${Math.random()}`, text, isAgent, timestamp: now, isFinal: true },
            ]
          })
        }
      } else if (nonFinalSegments.length > 0) {
        const text = nonFinalSegments.map((s) => s.text).join(' ').trim()
        if (text) {
          setTranscriptMessages((prev) => {
            const last = prev[prev.length - 1]
            if (last && last.isAgent === isAgent && !last.isFinal) {
              return [...prev.slice(0, -1), { ...last, text, timestamp: now }]
            }
            return [
              ...prev,
              { id: `${Date.now()}-${Math.random()}`, text, isAgent, timestamp: now, isFinal: false },
            ]
          })
        }
      }
    }

    room.on(RoomEvent.TranscriptionReceived, onTranscription)
    return () => room.off(RoomEvent.TranscriptionReceived, onTranscription)
  }, [room])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex-1 overflow-y-auto chat-scroll bg-slate-50 px-6 py-4">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-slate-50 pb-3 border-b border-slate-100 mb-4">
        <h2 className="text-slate-700 font-semibold text-base">Conversation</h2>
        <p className="text-slate-400 text-xs">Live transcript — ABC Dental AI Receptionist</p>
      </div>

      {messages.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-center py-16">
          <div className="w-14 h-14 rounded-full bg-brand-primary/10 flex items-center justify-center mb-4">
            <svg className="w-7 h-7 text-brand-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <p className="text-slate-400 text-sm">Waiting for the AI receptionist to greet you…</p>
          <p className="text-slate-300 text-xs mt-1">Enable your microphone to speak</p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
