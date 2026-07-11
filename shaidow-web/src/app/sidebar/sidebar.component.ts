import { Component, OnInit, Output, EventEmitter, signal } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { ChatService } from '../services/chat.service';
import { AuthService } from '../services/auth.service';
import { ThreadSummary } from '../models/chat.models';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, DatePipe],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss',
})
export class SidebarComponent implements OnInit {
  threads = signal<ThreadSummary[]>([]);
  activeThreadId = signal<string | null>(null);
  isCollapsed = signal(typeof window !== 'undefined' && window.innerWidth < 768);

  @Output() threadSelected = new EventEmitter<string>();
  @Output() newChat = new EventEmitter<void>();

  constructor(private chatService: ChatService, private auth: AuthService) {}

  ngOnInit(): void {
    this.loadThreads();
  }

  toggleCollapse(): void {
    this.isCollapsed.update((v) => !v);
  }

  private isMobile(): boolean {
    return window.innerWidth < 768;
  }

  async loadThreads(): Promise<void> {
    try {
      const threads = await this.chatService.getThreads();
      this.threads.set(threads);
    } catch {
      this.threads.set([]);
    }
  }

  async deleteThread(event: Event, id: string): Promise<void> {
    event.stopPropagation();
    if (!confirm('Delete this conversation?')) return;

    try {
      await this.chatService.deleteThread(id);
      this.threads.update((list) => list.filter((t) => t.id !== id));
      if (this.activeThreadId() === id) {
        this.activeThreadId.set(null);
        this.newChat.emit();
      }
    } catch {
      // silent fail is fine here - worst case the thread just stays in the list
    }
  }

  selectThread(id: string): void {
    this.activeThreadId.set(id);
    this.threadSelected.emit(id);
    if (this.isMobile()) this.isCollapsed.set(true);
  }

  onNewChat(): void {
    this.activeThreadId.set(null);
    this.newChat.emit();
    if (this.isMobile()) this.isCollapsed.set(true);
  }

  logout(): void {
    this.auth.logout();
    window.location.href = '/login';
  }
}