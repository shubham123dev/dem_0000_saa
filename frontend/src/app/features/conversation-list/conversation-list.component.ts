import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  Output,
  computed,
  inject,
} from '@angular/core';
import { ConversationListStore } from './conversation-list.store';
import type { ConversationListItem, ConversationSearchResult } from '../../core/conversation/conversation.models';

@Component({
  selector: 'app-conversation-list',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './conversation-list.component.html',
  styleUrl: './conversation-list.component.scss',
})
export class ConversationListComponent {
  readonly store = inject(ConversationListStore);

  @Input() collapsed = false;
  @Output() readonly conversationSelected = new EventEmitter<string>();
  @Output() readonly newConversation = new EventEmitter<void>();

  readonly menuOpenId = computed(() => this.menuId);
  private menuId: string | null = null;
  private renamingId: string | null = null;
  renameValue = '';

  get isRenaming(): string | null {
    return this.renamingId;
  }

  selectConversation(item: ConversationListItem): void {
    this.store.select(item.id);
    this.conversationSelected.emit(item.id);
  }

  createNew(): void {
    this.store.createNew();
    this.newConversation.emit();
  }

  onSearchInput(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.store.setSearch(value);
  }

  clearSearch(): void {
    this.store.clearSearch();
  }

  selectSearchResult(result: ConversationSearchResult): void {
    this.store.select(result.conversationId);
    this.conversationSelected.emit(result.conversationId);
  }

  openMenu(id: string, event: Event): void {
    event.stopPropagation();
    this.menuId = this.menuId === id ? null : id;
  }

  closeMenu(): void {
    this.menuId = null;
  }

  startRename(item: ConversationListItem, event: Event): void {
    event.stopPropagation();
    this.renamingId = item.id;
    this.renameValue = item.title ?? '';
    this.menuId = null;
  }

  confirmRename(id: string): void {
    const title = this.renameValue.trim();
    if (title) {
      this.store.rename(id, title);
    }
    this.renamingId = null;
  }

  cancelRename(): void {
    this.renamingId = null;
  }

  onRenameKeydown(event: KeyboardEvent, id: string): void {
    if (event.key === 'Enter') {
      event.preventDefault();
      this.confirmRename(id);
    } else if (event.key === 'Escape') {
      this.cancelRename();
    }
  }

  togglePin(id: string, event: Event): void {
    event.stopPropagation();
    this.store.togglePin(id);
    this.menuId = null;
  }

  removeConversation(id: string, event: Event): void {
    event.stopPropagation();
    this.store.remove(id);
    this.menuId = null;
  }

  relativeTime(isoString: string | null): string {
    if (!isoString) return '';
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }

  trackById(_index: number, item: ConversationListItem): string {
    return item.id;
  }
}
