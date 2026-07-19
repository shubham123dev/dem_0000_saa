import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import type { AgentActivityItem, AgentActivityStatus } from '../agent-activity.model';

const STATUS_LABELS: Readonly<Record<AgentActivityStatus, string>> = {
  idle: 'Idle',
  working: 'Working',
  connecting: 'Connecting',
  live: 'Live',
  reconnecting: 'Reconnecting',
  cancellation_requested: 'Cancellation requested',
  completed: 'Completed',
  clarification_required: 'Needs input',
  proposal_ready: 'Proposal ready',
  cancelled: 'Cancelled',
  failed: 'Failed',
  stopped: 'Watching stopped',
  interrupted: 'Connection interrupted'
};

@Component({
  selector: 'app-assistant-activity',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './assistant-activity.component.html',
  styleUrl: './assistant-activity.component.scss'
})
export class AssistantActivityComponent {
  @Input() items: readonly AgentActivityItem[] = [];
  @Input() status: AgentActivityStatus = 'idle';

  get statusLabel(): string {
    return STATUS_LABELS[this.status];
  }
}
