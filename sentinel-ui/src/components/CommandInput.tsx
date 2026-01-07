import { useState, useRef, useEffect } from 'react';

interface CommandInputProps {
  onSubmit: (input: string) => void;
  disabled?: boolean;
}

export function CommandInput({ onSubmit, disabled = false }: CommandInputProps) {
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Focus input on mount
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;

    onSubmit(input.trim());
    setHistory(prev => [input.trim(), ...prev]);
    setInput('');
    setHistoryIndex(-1);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (historyIndex < history.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        setInput(history[newIndex]);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setInput(history[newIndex]);
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setInput('');
      }
    }
  };

  const isCommand = input.startsWith('/');

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-sentinel-border bg-sentinel-surface p-4"
    >
      <div className="flex items-center gap-3">
        <span className={`text-lg ${isCommand ? 'text-sentinel-accent' : 'text-sentinel-dim'}`}>
          {isCommand ? '>' : '»'}
        </span>
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? "Connecting to server..." : "Type a response or /command..."}
          className={`flex-1 bg-transparent border-none outline-none placeholder-sentinel-dim font-mono ${disabled ? 'text-sentinel-dim cursor-not-allowed' : 'text-sentinel-secondary'}`}
          autoComplete="off"
          spellCheck={false}
          disabled={disabled}
        />
        <button
          type="submit"
          disabled={disabled}
          className={`px-4 py-1 font-bold text-sm rounded transition-colors ${disabled ? 'bg-sentinel-dim text-sentinel-bg cursor-not-allowed' : 'bg-sentinel-accent text-sentinel-bg hover:bg-opacity-80'}`}
        >
          SEND
        </button>
      </div>
      <div className="mt-2 text-xs text-sentinel-dim">
        <span className="mr-4">↑↓ History</span>
        <span className="mr-4">Enter to send</span>
        <span>/ for commands</span>
      </div>
    </form>
  );
}
