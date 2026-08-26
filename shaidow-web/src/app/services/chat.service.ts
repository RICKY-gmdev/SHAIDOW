import { Injectable } from '@angular/core';
import { AuthService } from './auth.service';
import { StreamedEvent, ThreadSummary, ChatMessage } from '../models/chat.models';

const API_BASE = 'https://shaidow-api-new-bjgeh2e4axe3dxhc.centralindia-01.azurewebsites.net/api';

@Injectable({ providedIn: 'root' })
export class ChatService {
  constructor(private auth: AuthService) { }

  // Direct port of MAUI's StreamChatResponseAsync IAsyncEnumerable loop.
  // Same "data:" line parsing, same event types, just via a browser ReadableStream
  // instead of a StreamReader.
  async *streamChat(message: string, threadId: string | null, signal: AbortSignal): AsyncGenerator<StreamedEvent> {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.auth.authHeader(),
      },
      body: JSON.stringify({ message, threadId }),
      signal,
    });

    if (!res.ok || !res.body) {
      yield { type: 'error', content: `Request failed: ${res.status}` };
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() ?? ''; // last chunk may be incomplete, keep it for next read

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data:')) continue;

        const json = trimmed.slice('data:'.length).trim();
        try {
          const parsed: StreamedEvent = JSON.parse(json);
          yield parsed;
          if (parsed.type === 'stream_end') return;
        } catch {
          // malformed line - skip rather than break the whole stream
        }
      }
    }
  }

  async deleteThread(threadId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/threads/${threadId}`, {
      method: 'DELETE',
      headers: this.auth.authHeader(),
    });
    if (!res.ok) throw new Error('Failed to delete thread');
  }

  async getThreads(): Promise<ThreadSummary[]> {
    const res = await fetch(`${API_BASE}/threads`, { headers: this.auth.authHeader() });
    if (!res.ok) throw new Error('Failed to load threads');
    return res.json();
  }

  async getMessages(threadId: string): Promise<ChatMessage[]> {
    const res = await fetch(`${API_BASE}/threads/${threadId}/messages`, { headers: this.auth.authHeader() });
    if (!res.ok) throw new Error('Failed to load messages');
    const raw = await res.json();
    return raw.map((m: any) => ({
      id: m.id,
      author: m.author === 'user' ? 'You' : 'SHAIDOW',
      text: m.text,
      imageUrl: m.imageUrl,
    }));
  }
}
