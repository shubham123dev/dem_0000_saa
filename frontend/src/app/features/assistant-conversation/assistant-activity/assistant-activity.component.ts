import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import type { AgentActivityItem, AgentRunConnectionState } from '../agent-activity.model';

@Component({
  selector: 'app-assistant-activity',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './assistant-activity.component.html',
  styleUrl: './assistant-activity.component.scss'
})
export class AssistantActivityComponent {
  @Input() items: readonly AgentActivityItem[] = [];
  @Input() connection: AgentRunConnectionState = 'closed';
  @Input() cancellationRequested = false;
}
