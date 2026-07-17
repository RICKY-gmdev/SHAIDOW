import { Component, ElementRef, ViewChild, AfterViewChecked, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { marked } from 'marked';
import { ChatService } from '../services/chat.service';
import { ChatMessage } from '../models/chat.models';
import { ToolAnimationComponent } from '../tool-animation/tool-animation.component';
import { SidebarComponent } from '../sidebar/sidebar.component';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, ToolAnimationComponent, SidebarComponent],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.scss',
})
export class ChatComponent implements AfterViewChecked {
  @ViewChild('chatList') chatListEl!: ElementRef<HTMLDivElement>;
  @ViewChild('toolAnim') toolAnim!: ToolAnimationComponent;
  @ViewChild('sidebar') sidebarRef!: SidebarComponent;

  messages = signal<ChatMessage[]>([]);
  userInput = '';
  isResponding = signal(false);
  showWelcome = signal(true);

  private currentThreadId: string | null = null;
  private abortController: AbortController | null = null;
  private shouldScroll = false;

  constructor(private chatService: ChatService, private router: Router) { }

  ngAfterViewChecked(): void {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  renderMarkdown(text: string | undefined): string {
    if (!text) return '';
    return marked.parse(text, { async: false }) as string;
  }

  async onSend(): Promise<void> {
    const text = this.userInput.trim();
    if (!text || this.isResponding()) return;

    this.showWelcome.set(false);
    this.userInput = '';
    this.addMessage({ id: crypto.randomUUID(), author: 'You', text });

    const aiMessage: ChatMessage = { id: crypto.randomUUID(), author: 'SHAIDOW', text: '...', isStreaming: true };
    this.addMessage(aiMessage);

    this.isResponding.set(true);
    this.abortController = new AbortController();

    let firstChunkReceived = false;
    let capturedImageUrl: string | undefined;
    const toolsUsed: string[] = [];
    const pendingTools = new Set<string>();

    try {
      for await (const event of this.chatService.streamChat(text, this.currentThreadId, this.abortController.signal)) {
        switch (event.type) {
          case 'text_chunk':
            // Only used for direct (no-tool) answers, which still stream token-by-token.
            if (!firstChunkReceived) {
              aiMessage.text = event.content ?? '';
              firstChunkReceived = true;
            } else {
              aiMessage.text = (aiMessage.text ?? '') + (event.content ?? '');
            }
            this.messages.update((msgs) => [...msgs]);
            break;

          case 'tool_start':
            this.toolAnim?.showTool(event.tool ?? 'default');
            if (event.tool) {
              pendingTools.add(event.tool);
              if (!toolsUsed.includes(event.tool)) toolsUsed.push(event.tool);
            }
            aiMessage.status = 'Finding more relevant details...';
            break;

          case 'tool_end': {
            this.toolAnim?.hideTool(event.tool ?? 'default');
            if (event.tool) pendingTools.delete(event.tool);

            const output = event.output ?? '';

            // 1. Check for Image markers first
            if (output.startsWith('IMAGE_URL::')) {
              const rawUrl = output.replace('IMAGE_URL::', '').trim();
              // Normalize URL if needed
              capturedImageUrl = rawUrl.startsWith('http') ? rawUrl : `https://shaidow-backend-ml.azurewebsites.net${rawUrl}`;

              // Display a placeholder message in the chat
              aiMessage.text = (aiMessage.text ?? '') + '\n\n*Image retrieved successfully.*';
            }
            // 2. Handle standard text tool outputs
            else if (output.length > 0) {
              aiMessage.text = aiMessage.text ? `${aiMessage.text}\n\n${output}` : output;
            }

            aiMessage.status = pendingTools.size > 0 ? 'Finding more relevant details...' : undefined;
            this.messages.update((msgs) => [...msgs]);
            break;
          }

          case 'stream_end':
            aiMessage.status = undefined;
            if (aiMessage.text?.startsWith('* (Using')) aiMessage.text = '';
            if (capturedImageUrl) {
              this.addMessage({ id: crypto.randomUUID(), author: 'SHAIDOW', imageUrl: capturedImageUrl });
            }
            if (toolsUsed.length) {
              aiMessage.text = (aiMessage.text ?? '') + `\n\n---\n*Tools used: ${toolsUsed.join(', ')}*`;
            }
            aiMessage.isStreaming = false;
            this.currentThreadId = event.threadId ?? this.currentThreadId;
            this.finishResponding();
            break;

          case 'error':
            aiMessage.status = undefined;
            aiMessage.text = (aiMessage.text ?? '') + `\n\nSYSTEM ERROR: ${event.content}`;
            aiMessage.isStreaming = false;
            this.finishResponding();
            break;
        }
        this.messages.update((msgs) => [...msgs]);
        this.shouldScroll = true;
      }
    } catch (err: any) {
      aiMessage.status = undefined;
      if (err?.name === 'AbortError') {
        aiMessage.text = (aiMessage.text ?? '') + '\n\n*(stopped)*';
      } else {
        aiMessage.text = `CRITICAL ERROR: ${err}`;
      }
      aiMessage.isStreaming = false;
      this.finishResponding();
      this.messages.update((msgs) => [...msgs]);
    }
  }

  private finishResponding(): void {
    this.isResponding.set(false);
    this.toolAnim?.clearAll();
    this.sidebarRef?.loadThreads();
  }

  stopResponse(): void {
    this.abortController?.abort();
    // finishResponding() will also run from inside the try/catch's AbortError path,
    // but calling it here too makes the UI feel instant rather than waiting on the throw.
    this.finishResponding();
  }

  private addMessage(message: ChatMessage): void {
    this.messages.update((msgs) => [...msgs, message]);
    this.shouldScroll = true;
  }

  private scrollToBottom(): void {
    const el = this.chatListEl?.nativeElement;
    if (el) el.scrollTop = el.scrollHeight;
  }

  openGallery(): void {
    this.router.navigate(['/gallery']);
  }

  async onThreadSelected(threadId: string): Promise<void> {
    this.abortController?.abort(); // stop any in-flight response before switching threads
    this.currentThreadId = threadId;
    this.showWelcome.set(false);
    try {
      const history = await this.chatService.getMessages(threadId);
      this.messages.set(history);
      this.shouldScroll = true;
    } catch {
      this.messages.set([{ id: crypto.randomUUID(), author: 'SHAIDOW', text: 'Could not load this conversation.' }]);
    }
  }

  onNewChat(): void {
    this.abortController?.abort();
    this.currentThreadId = null;
    this.messages.set([]);
    this.showWelcome.set(true);
  }
}
