import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { UiBadgeComponent, UiButtonComponent } from '../../../shared/ui';
import type { ConversationProposal } from '../agent-conversation.model';

@Component({
  selector: 'app-assistant-proposal-card',
  standalone: true,
  imports: [DatePipe, UiBadgeComponent, UiButtonComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './assistant-proposal-card.component.html',
  styleUrl: './assistant-proposal-card.component.scss'
})
export class AssistantProposalCardComponent {
  @Input({ required: true }) proposal!: ConversationProposal;
  @Output() readonly reviewRequested = new EventEmitter<string | null>();

  riskTone(): 'info' | 'warning' | 'danger' {
    return this.proposal.riskLevel === 'high' ? 'danger' : this.proposal.riskLevel === 'medium' ? 'warning' : 'info';
  }
}
