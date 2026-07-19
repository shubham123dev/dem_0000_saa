import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, OnChanges, Output, signal } from '@angular/core';
import { ProposalControlFacade } from '../../../core/action-control/proposal-control.facade';
import { UiBadgeComponent, UiButtonComponent } from '../../../shared/ui';
import type { ConversationProposal } from '../agent-conversation.model';

@Component({selector:'app-assistant-proposal-card',standalone:true,imports:[DatePipe,UiBadgeComponent,UiButtonComponent],providers:[ProposalControlFacade],changeDetection:ChangeDetectionStrategy.OnPush,templateUrl:'./assistant-proposal-card.component.html',styleUrl:'./assistant-proposal-card.component.scss'})
export class AssistantProposalCardComponent implements OnChanges {
  @Input({required:true}) proposal!:ConversationProposal;
  @Input({required:true}) messageId!:string;
  @Output() readonly reviewRequested=new EventEmitter<string|null>();
  readonly decision=signal<'approve'|'reject'|'execute'|'cancel'|null>(null);
  readonly reason=signal('');
  readonly confirmation=signal('');
  constructor(readonly control:ProposalControlFacade){}
  ngOnChanges():void{if(this.messageId)this.control.load(this.proposal.id??null,this.messageId);}
  riskTone():'info'|'warning'|'danger'{const risk=this.control.proposal()?.risk_level??this.proposal.riskLevel;return risk==='high'?'danger':risk==='medium'?'warning':'info';}
  openDecision(value:'approve'|'reject'|'execute'|'cancel'):void{this.reason.set('');this.confirmation.set('');this.decision.set(value);}
  closeDecision():void{if(!this.control.busy())this.decision.set(null);}
  updateReason(event:Event):void{this.reason.set((event.target as HTMLTextAreaElement).value);}
  updateConfirmation(event:Event):void{this.confirmation.set((event.target as HTMLInputElement).value);}
  reasonRequired():boolean{const current=this.control.proposal();return this.decision()==='reject'&&Boolean(current&&current.risk_level!=='low');}
  confirmationWord():string|null{const current=this.control.proposal();if(!current||current.risk_level!=='high')return null;return this.decision()==='execute'?'EXECUTE':this.decision()==='approve'?'APPROVE':null;}
  canConfirm():boolean{if(this.reasonRequired()&&!this.reason().trim())return false;const word=this.confirmationWord();return !word||this.confirmation().trim()===word;}
  decisionTitle():string{const value=this.decision();return value==='approve'?'Approve this proposal?':value==='reject'?'Reject this proposal?':value==='execute'?'Execute the approved change?':'Cancel this proposal?';}
  decisionText():string{const value=this.decision();if(value==='approve')return 'This records approval only. Execution remains a separate explicit step.';if(value==='reject')return 'Rejecting closes this proposal without applying the change.';if(value==='execute')return 'This applies only the previously reviewed and approved change.';return 'Cancelling closes the proposal without applying the change.';}
  confirm():void{
    const value=this.decision();if(!value||!this.canConfirm()||this.control.busy())return;
    const reason=this.reason().trim()||null;const confirmation=this.confirmation().trim()||null;
    const request=value==='approve'?this.control.approve(reason,confirmation):value==='reject'?this.control.reject(reason):value==='execute'?this.control.execute(confirmation):this.control.cancel(reason);
    request.subscribe({next:()=>this.decision.set(null),error:()=>undefined});
  }
}
