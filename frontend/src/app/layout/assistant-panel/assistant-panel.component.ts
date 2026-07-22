import { A11yModule } from '@angular/cdk/a11y';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output, ViewChild, computed, effect, inject, type ElementRef } from '@angular/core';
import { ActionNavigationStore } from '../../core/action-control/action-navigation.store';
import type { AgentActivityStatus } from '../../features/assistant-conversation/agent-activity.model';
import { AgentConversationStore } from '../../features/assistant-conversation/agent-conversation.store';
import { AssistantActivityComponent } from '../../features/assistant-conversation/assistant-activity/assistant-activity.component';
import { AssistantComposerComponent } from '../../features/assistant-conversation/assistant-composer/assistant-composer.component';
import { AssistantMessageComponent } from '../../features/assistant-conversation/assistant-message/assistant-message.component';
import { UiBadgeComponent, UiButtonComponent, UiCalloutComponent } from '../../shared/ui';
import type { ShellSectionId } from '../shell/shell-navigation.model';

interface StarterPrompt { readonly label: string; readonly query: string; }
const DEFAULT_PROMPTS: readonly StarterPrompt[] = [
  { label:'Summarize this workspace', query:'Give me a concise overview of this organization and its current workspace status.' },
  { label:'Show pending approvals', query:'List the governed action proposals that are currently waiting for approval.' },
  { label:'Explain available capabilities', query:'Summarize the workplace read tools and governed actions available to me.' }
];
const SECTION_PROMPTS: Partial<Record<ShellSectionId, readonly StarterPrompt[]>> = {
  users:[{label:'List active users',query:'List active organization users with their roles and membership status.'},{label:'Explain seat coverage',query:'Summarize assigned and available organization seats.'}],
  reports:[{label:'Summarize report access',query:'Summarize the reports this organization can currently access.'},{label:'Find restricted reports',query:'Identify reports that do not currently have active organization access.'}],
  approvals:[{label:'Review waiting proposals',query:'List proposals that are waiting for approval and summarize their risk.'},{label:'Explain approval policy',query:'Explain the approval requirements for the currently available governed actions.'}],
  audit:[{label:'Summarize recent audit activity',query:'Summarize the most recent organization audit activity and outcomes.'}],
  settings:[{label:'List settings resources',query:'List available workplace setting resources and their current state.'}]
};

import { CurrentUserStore } from '../../core/auth/current-user.store';

@Component({
  selector:'app-assistant-panel', standalone:true,
  imports:[A11yModule,AssistantActivityComponent,AssistantComposerComponent,AssistantMessageComponent,UiBadgeComponent,UiButtonComponent,UiCalloutComponent],
  changeDetection:ChangeDetectionStrategy.OnPush,
  templateUrl:'./assistant-panel.component.html', styleUrl:'./assistant-panel.component.scss'
})
export class AssistantPanelComponent {
  @ViewChild('transcript') private transcript?: ElementRef<HTMLElement>;
  @ViewChild(AssistantComposerComponent) private composer?: AssistantComposerComponent;
  @Input() overlay=false;
  @Input() currentSection:ShellSectionId='home';
  @Output() readonly closePressed=new EventEmitter<void>();
  @Output() readonly sectionSelected=new EventEmitter<ShellSectionId>();
  @Output() readonly loginRequested=new EventEmitter<void>();
  readonly conversation=inject(AgentConversationStore);
  readonly userStore=inject(CurrentUserStore);
  private readonly actionNavigation=inject(ActionNavigationStore);
  readonly greeting=this.createGreeting();
  readonly activityStatus = computed<AgentActivityStatus>(() => {
    if (this.conversation.cancellationRequested()) return 'cancellation_requested';
    const connection = this.conversation.connection();
    if (this.conversation.pending()) {
      if (connection === 'connecting') return 'connecting';
      if (connection === 'open') return 'live';
      if (connection === 'reconnecting') return 'reconnecting';
      return 'working';
    }
    const lastMessage = this.conversation.messages().at(-1);
    if (lastMessage?.title === 'Run cancelled') return 'cancelled';
    if (lastMessage?.title === 'Run failed') return 'failed';
    if (this.conversation.canResume()) return lastMessage?.role === 'error' ? 'interrupted' : 'stopped';
    if (lastMessage?.role === 'error') return 'interrupted';
    if (lastMessage?.mode === 'clarification_required') return 'clarification_required';
    if (lastMessage?.mode === 'action_proposal') return 'proposal_ready';
    if (this.conversation.activities().length > 0 && this.conversation.activities().every((item) => item.state === 'completed')) return 'completed';
    return 'idle';
  });
  constructor(){effect(()=>{this.conversation.messages();this.conversation.activities();this.conversation.pending();queueMicrotask(()=>this.scrollToLatest());});}
  prompts():readonly StarterPrompt[]{return SECTION_PROMPTS[this.currentSection]??DEFAULT_PROMPTS;}
  submit(text:string):void{this.conversation.submit(text);}
  submitPrompt(prompt:StarterPrompt):void{this.conversation.submit(prompt.query);}
  startNewConversation():void{this.conversation.clearConversation();queueMicrotask(()=>this.composer?.focus());}
  reviewProposal(proposalId:string|null):void{this.actionNavigation.open(proposalId);this.sectionSelected.emit('approvals');}
  private scrollToLatest():void{const element=this.transcript?.nativeElement;if(element)element.scrollTop=element.scrollHeight;}
  private createGreeting():string{const hour=new Date().getHours();return hour<12?'Good morning.':hour<18?'Good afternoon.':'Good evening.';}
}
