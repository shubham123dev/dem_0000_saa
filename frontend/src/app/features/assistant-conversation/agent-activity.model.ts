import type { AgentRunConnectionState } from '../../core/agent-run/agent-run.models';

export interface AgentActivityItem {
  readonly sequence: number;
  readonly stage: string;
  readonly message: string;
  readonly occurredAt: string;
  readonly state: 'active' | 'completed';
}

export type AgentActivityStatus =
  | 'idle'
  | 'working'
  | 'connecting'
  | 'live'
  | 'reconnecting'
  | 'cancellation_requested'
  | 'completed'
  | 'clarification_required'
  | 'proposal_ready'
  | 'cancelled'
  | 'failed'
  | 'stopped'
  | 'interrupted';

export interface AgentConversationRecovery {
  readonly version: 2;
  readonly organizationScope: string;
  readonly conversationId: string | null;
  readonly activeRunId: string | null;
  readonly lastEventSequence: number;
}

export type { AgentRunConnectionState };
