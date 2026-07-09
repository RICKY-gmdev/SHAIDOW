import { Component, OnInit, Output, EventEmitter, Input, signal } from '@angular/core';
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
  @Input() collapsed = false;
  threads = signal<ThreadSummary[]>([]);
  activeThreadId = signal<string | null>(null);

  @Output() threadSelected = new EventEmitter<string>();
  @Output() newChat = new EventEmitter<void>();

  constructor(private chatService: ChatService, private auth: AuthService) { }

  ngOnInit(): void {
    this.loadThreads();
  }

  async loadThreads(): Promise<void> {
    try {
      const threads = await this.chatService.getThreads();
      this.threads.set(threads);
    } catch {
      // Expired/invalid token or backend hiccup - fail quietly, sidebar just stays empty
      // rather than breaking the whole chat page over a non-critical list.
      this.threads.set([]);
    }
  }

  async deleteThread(event: Event, id: string): Promise<void> {
    event.stopPropagation(); // don't trigger selectThread when clicking the delete icon
    if (!confirm('Delete this conversation?')) return;

    try {
      await this.chatService.deleteThread(id);
      this.threads.update(list => list.filter(t => t.id !== id));
      if (this.activeThreadId() === id) {
        this.activeThreadId.set(null);
        this.newChat.emit(); // clear the chat view if we just deleted the open thread
      }
    } catch {
      // silent fail is fine here - worst case the thread just stays in the list
    }
  }

  selectThread(id: string): void {
    this.activeThreadId.set(id);
    this.threadSelected.emit(id);
  }

  onNewChat(): void {
    this.activeThreadId.set(null);
    this.newChat.emit();
  }

  logout(): void {
    this.auth.logout();
    window.location.href = '/login';
  }
}
