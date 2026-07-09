export interface ChatMessage {
  id: string;
  author: 'You' | 'SHAIDOW';
  text?: string;
  imageUrl?: string;
  isStreaming?: boolean; // true while tokens are still arriving, drives a subtle pulse in the UI
  status?: string; // transient line like "Finding more relevant details..." while other tools are still running
}

export interface ThreadSummary {
  id: string;
  title: string;
  lastMessageAt: string;
}

export interface StreamedEvent {
  type: 'text_chunk' | 'tool_start' | 'tool_end' | 'stream_end' | 'error';
  content?: string;
  tool?: string;
  output?: string;
  threadId?: string;
}
