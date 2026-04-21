/**
 * A single chat message bubble.
 * isAgent=true  → left-aligned blue bubble (AI receptionist)
 * isAgent=false → right-aligned slate bubble (patient)
 */
export default function MessageBubble({ message }) {
  const { text, isAgent, timestamp, isFinal } = message

  const time = new Date(timestamp).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  })

  if (isAgent) {
    return (
      <div className="flex items-end gap-2 max-w-[80%]">
        {/* Avatar */}
        <div className="w-7 h-7 rounded-full bg-brand-primary flex-shrink-0 flex items-center justify-center mb-1">
          <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C9.5 2 7.5 3 6 4.5 4.5 6 4 7.5 4 9c0 2 .8 3.5 1.5 5C6.2 15.5 7 17.5 7 19c0 1.1.9 2 2 2s2-.9 2-2v-2c0-.6.4-1 1-1s1 .4 1 1v2c0 1.1.9 2 2 2s2-.9 2-2c0-1.5.8-3.5 1.5-5C19.2 12.5 20 11 20 9c0-1.5-.5-3-2-4.5C16.5 3 14.5 2 12 2z"/>
          </svg>
        </div>

        <div>
          <div className={`px-4 py-3 rounded-2xl rounded-bl-sm shadow-sm
            bg-white border border-slate-100 text-slate-800 text-sm leading-relaxed
            ${!isFinal ? 'opacity-70 italic' : ''}
          `}>
            {text || (
              <span className="flex gap-1 items-center py-0.5">
                <span className="w-1.5 h-1.5 bg-slate-400 rounded-full dot-1" />
                <span className="w-1.5 h-1.5 bg-slate-400 rounded-full dot-2" />
                <span className="w-1.5 h-1.5 bg-slate-400 rounded-full dot-3" />
              </span>
            )}
          </div>
          <p className="text-slate-400 text-xs mt-1 ml-1">{time}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-end gap-2 max-w-[80%] ml-auto flex-row-reverse">
      {/* Avatar */}
      <div className="w-7 h-7 rounded-full bg-slate-500 flex-shrink-0 flex items-center justify-center mb-1">
        <span className="text-white text-xs font-bold">P</span>
      </div>

      <div>
        <div className="px-4 py-3 rounded-2xl rounded-br-sm bg-brand-dark text-white text-sm leading-relaxed shadow-sm">
          {text}
        </div>
        <p className="text-slate-400 text-xs mt-1 mr-1 text-right">{time}</p>
      </div>
    </div>
  )
}
