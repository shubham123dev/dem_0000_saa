import { computed, inject, Injectable, signal } from '@angular/core';
import { toObservable } from '@angular/core/rxjs-interop';
import { catchError, EMPTY, switchMap, tap } from 'rxjs';
import { ConversationApiService } from '../../core/conversation/conversation-api.service';
import type { ConversationListItem, ConversationSearchResult } from '../../core/conversation/conversation.models';
import { OrganizationRouteService } from '../../core/routing/organization-route.service';

@Injectable({ providedIn: 'root' })
export class ConversationListStore {
  private readonly api = inject(ConversationApiService);
  private readonly orgRoute = inject(OrganizationRouteService);

  private readonly conversationsState = signal<ConversationListItem[]>([]);
  private readonly loadingState = signal(false);
  private readonly activeIdState = signal<string | null>(null);
  private readonly searchQueryState = signal('');
  private readonly totalState = signal(0);
  private readonly searchResultsState = signal<ConversationSearchResult[]>([]);
  private readonly searchModeState = signal(false);

  readonly conversations = this.conversationsState.asReadonly();
  readonly loading = this.loadingState.asReadonly();
  readonly activeConversationId = this.activeIdState.asReadonly();
  readonly searchQuery = this.searchQueryState.asReadonly();
  readonly total = this.totalState.asReadonly();
  readonly searchResults = this.searchResultsState.asReadonly();
  readonly searchMode = this.searchModeState.asReadonly();

  readonly activeConversation = computed(() => {
    const id = this.activeIdState();
    if (!id) return null;
    return this.conversationsState().find((c) => c.id === id) ?? null;
  });

  readonly activeTitle = computed(() => {
    return this.activeConversation()?.title ?? 'New conversation';
  });

  load(): void {
    const orgId = this.orgRoute.organizationId();
    if (!orgId) return;

    this.loadingState.set(true);
    const search = this.searchQueryState() || undefined;

    this.api
      .listConversations(orgId, { limit: 50, search })
      .pipe(
        tap((response) => {
          this.conversationsState.set(response.conversations);
          this.totalState.set(response.total);
          this.loadingState.set(false);
        }),
        catchError(() => {
          this.loadingState.set(false);
          return EMPTY;
        })
      )
      .subscribe();
  }

  select(conversationId: string): void {
    this.activeIdState.set(conversationId);
  }

  createNew(): void {
    this.activeIdState.set(null);
  }

  setSearch(query: string): void {
    this.searchQueryState.set(query);
    if (query.length >= 2) {
      // Switch to cross-conversation search mode
      this.searchModeState.set(true);
      this.searchMessages(query);
    } else {
      this.searchModeState.set(false);
      this.searchResultsState.set([]);
      this.load();
    }
  }

  private searchMessages(query: string): void {
    const orgId = this.orgRoute.organizationId();
    if (!orgId) return;

    this.loadingState.set(true);
    this.api
      .searchConversations(orgId, query)
      .pipe(
        tap((response) => {
          this.searchResultsState.set(response.results);
          this.loadingState.set(false);
        }),
        catchError(() => {
          this.loadingState.set(false);
          return EMPTY;
        })
      )
      .subscribe();
  }

  clearSearch(): void {
    this.searchQueryState.set('');
    this.searchModeState.set(false);
    this.searchResultsState.set([]);
    this.load();
  }

  rename(conversationId: string, title: string): void {
    const orgId = this.orgRoute.organizationId();
    if (!orgId) return;

    this.api.updateConversation(orgId, conversationId, { title }).subscribe(() => {
      this.conversationsState.update((list) =>
        list.map((c) => (c.id === conversationId ? { ...c, title } : c))
      );
    });
  }

  togglePin(conversationId: string): void {
    const orgId = this.orgRoute.organizationId();
    if (!orgId) return;

    const item = this.conversationsState().find((c) => c.id === conversationId);
    if (!item) return;
    const pinned = !item.pinned;

    this.api.updateConversation(orgId, conversationId, { pinned }).subscribe(() => {
      this.conversationsState.update((list) =>
        list.map((c) => (c.id === conversationId ? { ...c, pinned } : c))
      );
      // Re-sort: pinned first
      this.conversationsState.update((list) =>
        [...list].sort((a, b) => {
          if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
          return 0;
        })
      );
    });
  }

  remove(conversationId: string): void {
    const orgId = this.orgRoute.organizationId();
    if (!orgId) return;

    this.api.deleteConversation(orgId, conversationId).subscribe(() => {
      this.conversationsState.update((list) => list.filter((c) => c.id !== conversationId));
      this.totalState.update((t) => t - 1);
      if (this.activeIdState() === conversationId) {
        this.activeIdState.set(null);
      }
    });
  }

  /** Called after a new run completes to refresh the list. */
  refreshAfterRun(): void {
    this.load();
  }
}
