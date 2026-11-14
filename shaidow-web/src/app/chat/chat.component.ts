import { Component, ElementRef, ViewChild, AfterViewChecked, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
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
  private readonly mlBaseUrl = 'https://shaidow-ml-n-ekb9aqdebfgresga.centralindia-01.azurewebsites.net';

  constructor(
    private chatService: ChatService,
    private router: Router,
    private sanitizer: DomSanitizer
  ) {}

  ngAfterViewChecked(): void {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  renderMarkdown(text: string | undefined): SafeHtml {
    if (!text) return '';
    const rawHtml = marked.parse(text, { async: false, breaks: true, gfm: true }) as string;

    const enhancedHtml = rawHtml.replace(
      /<pre><code(?: class="language-([a-zA-Z0-9_+-]+)")?>([\s\S]*?)<\/code><\/pre>/g,
      (_match, lang, codeContent) => {
        const label = (lang || 'code').toUpperCase();
        return `
          <div class="code-box">
            <div class="code-box-header">
              <span class="code-lang">${label}</span>
              <button type="button" class="code-copy-btn" onclick="
                const codeEl = this.closest('.code-box').querySelector('code');
                navigator.clipboard.writeText(codeEl ? codeEl.innerText : '');
                this.textContent = 'Copied!';
                setTimeout(() => (this.textContent = 'Copy'), 1500);
              ">Copy</button>
            </div>
            <pre><code class="language-${lang || 'plaintext'}">${codeContent}</code></pre>
          </div>
        `;
      }
    );

    return this.sanitizer.bypassSecurityTrustHtml(enhancedHtml);
  }

  async onSend(): Promise<void> {
    const text = this.userInput.trim();
    if (!text || this.isResponding()) return;

    this.showWelcome.set(false);
    this.userInput = '';
    this.addMessage({ id: crypto.randomUUID(), author: 'You', text });

    const aiMessage: ChatMessage = {
      id: crypto.randomUUID(),
      author: 'SHAIDOW',
      text: '...',
      isStreaming: true,
    };
    this.addMessage(aiMessage);

    this.isResponding.set(true);
    this.abortController = new AbortController();

    let firstChunkReceived = false;
    let capturedImageUrl: string | undefined;
    const toolsUsed: string[] = [];
    const pendingTools = new Set<string>();

    try {
      for await (const event of this.chatService.streamChat(
        text,
        this.currentThreadId,
        this.abortController.signal
      )) {
        switch (event.type) {
          case 'text_chunk':
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
            aiMessage.status = 'Orchestrating specialist sub-agent...';
            break;

          case 'tool_end': {
            this.toolAnim?.hideTool(event.tool ?? 'default');
            if (event.tool) pendingTools.delete(event.tool);

            const output = (event.output ?? '').trim();

            if (output.startsWith('IMAGE_URL::')) {
              const rawUrl = output.replace('IMAGE_URL::', '').trim();
              capturedImageUrl = rawUrl.startsWith('http')
                ? rawUrl
                : `${this.mlBaseUrl}${rawUrl.startsWith('/') ? '' : '/'}${rawUrl}`;
            }

            aiMessage.status =
              pendingTools.size > 0
                ? 'Orchestrating specialist sub-agent...'
                : 'Synthesizing final response...';
            this.messages.update((msgs) => [...msgs]);
            break;
          }

          case 'stream_end':
            aiMessage.status = undefined;
            if (aiMessage.text === '...') {
              aiMessage.text = capturedImageUrl ? 'Here is the visual you requested.' : '';
            }
            if (capturedImageUrl) {
              this.addMessage({
                id: crypto.randomUUID(),
                author: 'SHAIDOW',
                imageUrl: capturedImageUrl,
              });
            }
            if (toolsUsed.length) {
              aiMessage.text =
                (aiMessage.text ?? '') + `\n\n---\n*Tools used: ${toolsUsed.join(', ')}*`;
            }
            aiMessage.isStreaming = false;
            this.currentThreadId = event.threadId ?? this.currentThreadId;
            this.finishResponding();
            break;

          case 'error':
            aiMessage.status = undefined;
            if (aiMessage.text === '...') aiMessage.text = '';
            aiMessage.text =
              (aiMessage.text ?? '') + `\n\n**SYSTEM ERROR:** ${event.content}`;
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
    this.abortController?.abort();
    this.currentThreadId = threadId;
    this.showWelcome.set(false);
    try {
      const history = await this.chatService.getMessages(threadId);
      this.messages.set(history);
      this.shouldScroll = true;
    } catch {
      this.messages.set([
        {
          id: crypto.randomUUID(),
          author: 'SHAIDOW',
          text: 'Could not load this conversation.',
        },
      ]);
    }
  }

  onNewChat(): void {
    this.abortController?.abort();
    this.currentThreadId = null;
    this.messages.set([]);
    this.showWelcome.set(true);
  }
}
