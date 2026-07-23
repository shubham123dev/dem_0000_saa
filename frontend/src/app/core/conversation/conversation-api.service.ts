import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, type Observable } from 'rxjs';
import { APP_RUNTIME_CONFIG } from '../config/app-config.token';
import type {
  ConversationHistoryResponse,
  ConversationListItem,
  ConversationListResponse,
  ConversationSearchResponse,
  ConversationUpdateRequest
} from './conversation.models';

function encode(value: string): string {
  return encodeURIComponent(value);
}

function base(organizationId: string): string {
  return `/workplace/organizations/${encode(organizationId)}/agent/conversations`;
}

interface WireConversationListItem {
  id: string;
  title: string | null;
  summary: string | null;
  status: string;
  message_count: number;
  pinned: boolean;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
}

interface WireConversationListResponse {
  conversations: WireConversationListItem[];
  total: number;
  has_more: boolean;
}

interface WireConversationMessage {
  id: string;
  conversation_id: string;
  run_id: string | null;
  parent_id: string | null;
  sequence: number;
  role: 'user' | 'assistant';
  content: string;
  mode: string | null;
  answer_source: string | null;
  safe_metadata: Record<string, unknown> | null;
  created_at: string;
}

interface WireConversationHistoryResponse {
  conversation_id: string;
  title: string | null;
  messages: WireConversationMessage[];
  has_branches: boolean;
}

interface WireSearchResult {
  message_id: string;
  conversation_id: string;
  conversation_title: string | null;
  role: string;
  snippet: string;
  created_at: string;
}

interface WireSearchResponse {
  results: WireSearchResult[];
  total: number;
}

function mapListItem(wire: WireConversationListItem): ConversationListItem {
  return {
    id: wire.id,
    title: wire.title,
    summary: wire.summary,
    status: wire.status,
    messageCount: wire.message_count,
    pinned: wire.pinned,
    lastMessageAt: wire.last_message_at,
    createdAt: wire.created_at,
    updatedAt: wire.updated_at
  };
}

@Injectable({ providedIn: 'root' })
export class ConversationApiService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(APP_RUNTIME_CONFIG);

  private url(path: string): string {
    return `${this.config.apiBaseUrl}${path}`;
  }

  listConversations(
    organizationId: string,
    options: { limit?: number; offset?: number; search?: string } = {}
  ): Observable<ConversationListResponse> {
    let params = new HttpParams();
    if (options.limit !== undefined) params = params.set('limit', options.limit);
    if (options.offset !== undefined) params = params.set('offset', options.offset);
    if (options.search) params = params.set('search', options.search);

    return this.http
      .get<WireConversationListResponse>(this.url(base(organizationId)), { params })
      .pipe(
        map((wire) => ({
          conversations: wire.conversations.map(mapListItem),
          total: wire.total,
          hasMore: wire.has_more
        }))
      );
  }

  getHistory(
    organizationId: string,
    conversationId: string,
    leafId?: string
  ): Observable<ConversationHistoryResponse> {
    let params = new HttpParams();
    if (leafId) params = params.set('leaf_id', leafId);

    return this.http
      .get<WireConversationHistoryResponse>(
        this.url(`${base(organizationId)}/${encode(conversationId)}/messages`),
        { params }
      )
      .pipe(
        map((wire) => ({
          conversationId: wire.conversation_id,
          title: wire.title,
          messages: wire.messages.map((m) => ({
            id: m.id,
            conversationId: m.conversation_id,
            runId: m.run_id,
            parentId: m.parent_id,
            sequence: m.sequence,
            role: m.role,
            content: m.content,
            mode: m.mode,
            answerSource: m.answer_source,
            safeMetadata: m.safe_metadata,
            createdAt: m.created_at
          })),
          hasBranches: wire.has_branches
        }))
      );
  }

  searchConversations(
    organizationId: string,
    query: string,
    limit = 20
  ): Observable<ConversationSearchResponse> {
    const params = new HttpParams().set('q', query).set('limit', limit);
    return this.http
      .get<WireSearchResponse>(this.url(`${base(organizationId)}/search`), { params })
      .pipe(
        map((wire) => ({
          results: wire.results.map((r) => ({
            messageId: r.message_id,
            conversationId: r.conversation_id,
            conversationTitle: r.conversation_title,
            role: r.role,
            snippet: r.snippet,
            createdAt: r.created_at
          })),
          total: wire.total
        }))
      );
  }

  updateConversation(
    organizationId: string,
    conversationId: string,
    body: ConversationUpdateRequest
  ): Observable<void> {
    return this.http.patch<void>(
      this.url(`${base(organizationId)}/${encode(conversationId)}`),
      body
    );
  }

  deleteConversation(organizationId: string, conversationId: string): Observable<void> {
    return this.http.delete<void>(
      this.url(`${base(organizationId)}/${encode(conversationId)}`)
    );
  }
}
