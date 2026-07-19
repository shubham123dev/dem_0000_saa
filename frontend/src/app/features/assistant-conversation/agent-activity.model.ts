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
  | 're