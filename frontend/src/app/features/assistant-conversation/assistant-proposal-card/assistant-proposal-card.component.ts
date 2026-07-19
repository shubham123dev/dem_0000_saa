import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, OnChanges, Output, signal } from '@angular/core';
import { ProposalControlFacade } from '../../../core/action-control/proposal-control.facade';
import { UiBadgeComponent, UiButtonComponent } from '../../../shared/ui';
import type { ConversationProposal } from '../agent-conversation.model';

@Component({
  selector: 'app-assistant-proposal-card',
  standalone: true,
  imports: [DatePipe, UiBadgeComponent, UiButtonComponent],
  providers: [ProposalControlFacade],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './assistant-proposal-card.component.html',
  styleUrl: './assistant-proposal-card.component.scss'
})
export class AssistantProposalCardComponent implements OnChanges {
  @Input({ required: true }) proposal!: ConversationProposal;
  @Output() readonly reviewRequested = new EventEmitter<string | null>();

  readonly decision = signal<'approve' | 'reject' | null>(null);
  readonly reason = signal('');
  readonly confirmation = signal('');

  constructor(readonly control: ProposalControlFacade) {}

  ngOnChanges(): void { this.control.load(this.proposal.id ?? null); }

  riskTone(): 'info' | 'warning' | 'danger' {
    const risk = this.control.proposal()?.risk_level ?? this.proposal.riskLevel;
    return risk === 'high' ? 'danger' : risk === 'medium' ? 'warning' : 'info';
  }

  openDecision(value: 'approve' | 'reject'): void {
    this.reason.set('');
    this.confirmation.set('');
    this.decision.set(value);
  }

  closeDecision(): void { if (!this.control.busy()) this.decision.set(null); }
  updateReason(event: Event): void { this.reason.set((event.target as HTMLTextAreaElement).value); }
  updateConfirmation(event: Event): void { this.confirmation.set((event.target as HTMLInputElement).value); }

  reasonRequired(): boolean {
    const proposal = this.control.proposal();
    return this.decision() === 'reject' && Boolean(proposal && proposal.risk_level !== 'low');
  }

  confirmationWord(): string | null {
    return this.decision() === 'approve' && this.control.proposal()?.risk_level === 'high' ? 'APPROVE' : null;
  }

  canConfirm(): boolean {
    if (this.reasonRequired() && !this.reason().trim()) return false;
    const word = this.confirmationWord();
    return !word || this.confirmation().trim() === word;
  }

  confirm(): void {
    const decision = this.decision();
    if (!decision || !this.canConfirm() || this.control.busy()) return;
    const reason = this.reason().trim() || null;
    const request = decision === 'approve'
      ? this.control.approve(reason, this.confirmation().trim() || null)
      : this.control.reject(reason);
    request.subscribe({ next: () => this.decision.set(null), error: () => undefined });
  }
}
