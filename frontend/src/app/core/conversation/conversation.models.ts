export interface ConversationListItem {
  readonly id: string;
  readonly title: string | null;
  readonly summary: string | null;
  readonly status: string;
  readonly messageCount: number;
  readonly pinned: boolean;
  readonly lastMessageAt: string | null;
  readonly createdAt: string;
  readonly updatedAt: string;
}

export interface ConversationListResponse {
  readonly conversations: ConversationListItem[];
  readonly total: number;
  readonly hasMore: boolean;
}

export interface ConversationMessage {
  readonly id: string;
  readonly conversationId: string;
  readonly runId: string | null;
  readonly parentId: string | null;
  readonly sequence: number;
  readonly role: 'user' | 'assistant';
  readonly content: string;
  readonly mode: string | null;
  readonly answerSource: string | null;
  readonly safeMetadata: Record<string, unknown> | null;
  readonly createdAt: string;
}

export interface ConversationHistoryResponse {
  readonly conversationId: string;
  readonly title: string | null;
  readonly messages: ConversationMessage[];
  readonly hasBranches: boolean;
}

export interface ConversationSearchResult {
  readonly messageId: string;
  readonly conversationId: string;
  readonly conversationTitle: string | null;
  readonly role: string;
  readonly snippet: string;
  readonly createdAt: string;
}

export interface ConversationSearchResponse {
  readonly results: ConversationSearchResult[];
  readonly total: number;
}

export interface ConversationUpdateRequest {
  readonly title?: string | null;
  readonly pinned?: boolean;
}

export interface ContextBlockInfo {
  readonly id: string;
  readonly blockType: 'soul' | 'memory' | 'knowledge' | 'skill';
  readonly key: string;
  readonly description: string | null;
  readonly maxTokens: number | null;
  readonly currentTokens: number | null;
  readonly providerType: 'readonly' | 'writable' | 'searchable' | 'loadable';
  readonly loaded: boolean;
}

export interface ContextMemoryStatus {
  readonly blocks: ContextBlockInfo[];
  readonly totalTokensUsed: number;
  readonly memoryUsagePercent: number;
}
