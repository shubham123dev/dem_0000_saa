import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { UiBadgeComponent, UiButtonComponent, UiCalloutComponent } from '../../../shared/ui';
import type { ConversationMessage } from '../agent-conversation.model';
import { AssistantProposalCardComponent } from '../assistant-proposal-card/assistant-proposal-card.component';

@Component({
  selector: 'app-assistant-message',
  standalone: true,
  imports: [DatePipe, UiBadgeComponent, UiButtonComponent, UiCalloutComponent, AssistantProposalCardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './assistant-message.component.html',
  styleUrl: './assistant-message.component.scss'
})
export class AssistantMessageComponent {
  @Input({ required: true }) message!: ConversationMessage;
  @Input() retryAvailable = false;
  @Output() readonly retryRequested = new EventEmitter<void>();
  @Output() readonly reviewProposal = new EventEmitter<string | null>();

  sourceLabel(): string {
    return `${this.message.sourceCount} verified ${this.message.sourceCount === 1 ? 'source' : 'sources'}`;
  }
}
