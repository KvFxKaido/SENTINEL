import { useRef, useEffect } from 'react';
import type { Message } from '../types';

interface MainPanelProps {
  messages: Message[];
}

function NarrativeBlock({ message }: { message: Message }) {
  const time = message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <div className="codec-frame p-4 faction-nexus">
      <div className="flex items-center gap-2 mb-2 text-xs text-sentinel-dim">
        <span>{time}</span>
        <span className="text-sentinel-accent uppercase tracking-wider">Narrative</span>
      </div>
      <p className="text-sentinel-secondary leading-relaxed whitespace-pre-wrap">
        {message.content}
      </p>
    </div>
  );
}

function ChoiceBlock({ message }: { message: Message }) {
  const time = message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <div className="codec-frame p-4 border-sentinel-warning">
      <div className="flex items-center gap-2 mb-2 text-xs text-sentinel-dim">
        <span>{time}</span>
        <span className="text-sentinel-warning uppercase tracking-wider">Choice</span>
      </div>
      {message.content && (
        <p className="text-sentinel-secondary mb-3">{message.content}</p>
      )}
      <div className="space-y-2">
        {message.options?.map((option, i) => (
          <div
            key={i}
            className="flex items-start gap-3 p-2 rounded hover:bg-sentinel-bg cursor-pointer transition-colors group"
          >
            <span className="text-sentinel-accent font-bold">{i + 1}.</span>
            <span className="text-sentinel-secondary group-hover:text-sentinel-accent transition-colors">
              {option}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function PlayerBlock({ message }: { message: Message }) {
  const time = message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <div className="flex justify-end">
      <div className="codec-frame p-3 max-w-[80%] border-sentinel-accent">
        <div className="flex items-center gap-2 mb-1 text-xs text-sentinel-dim">
          <span className="text-sentinel-accent uppercase tracking-wider">You</span>
          <span>{time}</span>
        </div>
        <p className="text-sentinel-accent">{message.content}</p>
      </div>
    </div>
  );
}

function SystemBlock({ message }: { message: Message }) {
  return (
    <div className="p-3 bg-sentinel-bg border-l-2 border-sentinel-dim">
      <pre className="text-sentinel-dim text-sm font-mono whitespace-pre-wrap">
        {message.content}
      </pre>
    </div>
  );
}

export function MainPanel({ messages }: MainPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto p-4 space-y-4"
    >
      {messages.map(message => {
        switch (message.type) {
          case 'narrative':
            return <NarrativeBlock key={message.id} message={message} />;
          case 'choice':
            return <ChoiceBlock key={message.id} message={message} />;
          case 'player':
            return <PlayerBlock key={message.id} message={message} />;
          case 'system':
            return <SystemBlock key={message.id} message={message} />;
          default:
            return null;
        }
      })}
    </div>
  );
}
