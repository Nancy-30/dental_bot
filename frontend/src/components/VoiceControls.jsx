import { useState, useEffect, useRef } from 'react'
import {
  useLocalParticipant,
  useVoiceAssistant,
  useRoomContext,
  BarVisualizer,
  AudioTrack,
} from '@livekit/components-react'

/**
 * Bottom control bar — mic, speaker, text input, waveform visualizer.
 * Mic starts muted; user must click to unmute and speak.
 */
export default function VoiceControls({ onUserTextSent }) {
  const { localParticipant, isMicrophoneEnabled } = useLocalParticipant()
  const { state: agentState, audioTrack }          = useVoiceAssistant()
  const room = useRoomContext()

  const [ttsMuted, setTtsMuted]   = useState(false)
  const [textInput, setTextInput] = useState('')
  const [isSending, setIsSending] = useState(false)

  const mutedOnMount = useRef(false)

  const isSpeaking  = agentState === 'speaking'
  const isListening = agentState === 'listening'
  const micOn       = isMicrophoneEnabled

  // Mute mic on first publish so user starts with mic off
  useEffect(() => {
    if (!localParticipant || mutedOnMount.current) return
    if (isMicrophoneEnabled) {
      mutedOnMount.current = true
      localParticipant.setMicrophoneEnabled(false)
    }
  }, [localParticipant, isMicrophoneEnabled])

  const toggleMic = async () => {
    if (!localParticipant) return
    try {
      await localParticipant.setMicrophoneEnabled(!micOn)
    } catch (err) {
      console.error('Mic toggle error:', err)
    }
  }

  const toggleTts = () => setTtsMuted((p) => !p)

  const handleSendText = async () => {
    const text = textInput.trim()
    if (!text || isSending || !room) return

    onUserTextSent?.(text)
    setTextInput('')
    setIsSending(true)
    try {
      await room.localParticipant.sendText(text, { topic: 'lk.chat' })
    } catch (err) {
      console.error('Send text error:', err)
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendText() }
  }

  const statusLabel =
    isSending    ? 'Sending…'   :
    !micOn       ? 'Mic off'    :
    ttsMuted     ? 'Spkr off'   :
    isSpeaking   ? 'Speaking'   :
    isListening  ? 'Listening…' :
                   'Ready'

  return (
    <div className="border-t border-slate-100 bg-white px-6 py-4 flex items-center gap-4 flex-shrink-0">

      {/* Agent audio track */}
      {audioTrack && (
        <AudioTrack trackRef={audioTrack} volume={ttsMuted ? 0 : 1} />
      )}

      {/* Agent waveform visualizer */}
      {isSpeaking && audioTrack ? (
        <div className="flex-shrink-0 h-10 w-20 flex items-center gap-1">
          <BarVisualizer
            trackRef={audioTrack}
            barCount={8}
            style={{ height: '100%', width: '100%' }}
            className="[--lk-va-bar-color:#0EA5E9]"
          />
        </div>
      ) : (
        <div className="w-20 flex-shrink-0" />
      )}

      {/* Mic button */}
      <button
        onClick={toggleMic}
        title={micOn ? 'Mute microphone' : 'Unmute microphone'}
        className={`relative flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center
          transition-all duration-200 shadow-md active:scale-95
          ${!micOn
            ? 'bg-slate-200 hover:bg-slate-300 text-slate-500'
            : isListening
              ? 'bg-brand-primary text-white shadow-brand-primary/40 shadow-lg'
              : 'bg-brand-dark hover:bg-slate-800 text-white'
          }`}
      >
        {micOn && isListening && (
          <span className="absolute inset-0 rounded-full bg-brand-primary/30 mic-pulse" />
        )}
        {!micOn ? (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M19 11h-1.7c0 .74-.16 1.43-.43 2.05l1.23 1.23c.56-.98.9-2.09.9-3.28zm-4.02.17c0-.06.02-.11.02-.17V5c0-1.66-1.34-3-3-3S9 3.34 9 5v.18l5.98 5.99zM4.27 3L3 4.27l6.01 6.01V11c0 1.66 1.33 3 2.99 3 .22 0 .44-.03.65-.08l1.66 1.66c-.71.33-1.5.52-2.31.52-2.76 0-5.3-2.1-5.3-5.1H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c.91-.13 1.77-.45 2.54-.9L19.73 21 21 19.73 4.27 3z"/>
          </svg>
        ) : (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5zm6 6c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
          </svg>
        )}
      </button>

      {/* Speaker button */}
      <button
        onClick={toggleTts}
        title={ttsMuted ? 'Unmute speaker' : 'Mute speaker'}
        className={`flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center
          transition-all duration-200 shadow-md active:scale-95
          ${ttsMuted
            ? 'bg-slate-200 hover:bg-slate-300 text-slate-500'
            : 'bg-brand-dark hover:bg-slate-800 text-white'
          }`}
      >
        {ttsMuted ? (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>
          </svg>
        ) : (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
          </svg>
        )}
      </button>

      {/* Status */}
      <div className="flex-shrink-0 text-xs text-slate-400 w-16 leading-tight">
        {statusLabel}
      </div>

      {/* Text input */}
      <input
        type="text"
        value={textInput}
        onChange={(e) => setTextInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={isSending ? 'Sending…' : 'Type a message…'}
        disabled={isSending}
        className="flex-1 min-w-0 px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50
                   text-slate-800 text-sm placeholder-slate-400 focus:outline-none
                   focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/20 transition-all
                   disabled:opacity-60 disabled:cursor-not-allowed"
      />

      {/* Send button */}
      <button
        onClick={handleSendText}
        disabled={!textInput.trim() || isSending}
        className="flex-shrink-0 w-10 h-10 rounded-xl bg-brand-primary hover:bg-brand-accent
                   text-white flex items-center justify-center transition-all duration-200
                   disabled:opacity-40 disabled:cursor-not-allowed active:scale-95"
      >
        {isSending ? (
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
        ) : (
          <svg className="w-4 h-4 rotate-90" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z"/>
          </svg>
        )}
      </button>
    </div>
  )
}
