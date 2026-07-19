import { inject, Injectable, signal } from '@angular/core';
import { catchError, finalize, tap, throwError, type Observable, type Subscription } from 'rxjs';
import { APP_RUNTIME_CONFIG } from '../config/app-config.token';
import { normalizeWorkplaceError } from '../errors/error-normalizer';
import { ActionControlApiService } from './action-control-api.service';
import type { ActionProposalControl } from './action-control.models';

@Injectable()
export class ProposalControlFacade {
  private readonly config=inject(APP_RUNTIME_CONFIG);
  private readonly api=inject(ActionControlApiService);
  private readonly organizationId=this.config.defaultOrganizationId;
  private readonly proposalState=signal<ActionProposalControl|null>(null);
  private readonly loadingState=signal(false);
  private readonly busyState=signal(false);
  private readonly errorState=signal<string|null>(null);
  private loadRequest?:Subscription;
  private messageId:string|null=null;
  private executionKey:string|null=null;

  readonly proposal=this.proposalState.asReadonly();
  readonly loading=this.loadingState.asReadonly();
  readonly busy=this.busyState.asReadonly();
  readonly error=this.errorState.asReadonly();

  load(proposalId:string|null,messageId:string):void{
    if(!this.organizationId)return;
    this.messageId=messageId;
    const request=proposalId?this.api.detail(this.organizationId,proposalId):this.api.forMessage(this.organizationId,messageId);
    this.loadingState.set(true);this.errorState.set(null);this.loadRequest?.unsubscribe();
    this.loadRequest=request.pipe(finalize(()=>this.loadingState.set(false))).subscribe({next:(proposal)=>this.proposalState.set(proposal),error:(error:unknown)=>this.setError(error)});
  }

  approve(reason:string|null,confirmation:string|null):Observable<ActionProposalControl>{return this.command((organizationId,proposalId)=>this.api.approve(organizationId,proposalId,reason,confirmation));}
  reject(reason:string|null):Observable<ActionProposalControl>{return this.command((organizationId,proposalId)=>this.api.reject(organizationId,proposalId,reason));}
  cancel(reason:string|null):Observable<ActionProposalControl>{return this.command((organizationId,proposalId)=>this.api.cancel(organizationId,proposalId,reason));}
  execute(confirmation:string|null):Observable<ActionProposalControl>{
    this.executionKey??=globalThis.crypto?.randomUUID?.()??`execution-${Date.now()}`;
    return this.command((organizationId,proposalId)=>this.api.execute(organizationId,proposalId,this.executionKey!,confirmation));
  }
  refresh():void{const proposal=this.proposal();if(proposal)this.load(proposal.id,this.messageId??'');else if(this.messageId)this.load(null,this.messageId);}

  private command(factory:(organizationId:string,proposalId:string)=>Observable<ActionProposalControl>):Observable<ActionProposalControl>{
    const proposalId=this.proposal()?.id;
    if(!this.organizationId||!proposalId)return throwError(()=>new Error('No authoritative proposal is available.'));
    this.busyState.set(true);this.errorState.set(null);
    return factory(this.organizationId,proposalId).pipe(
      tap((proposal)=>{this.proposalState.set(proposal);if(proposal.execution&&proposal.execution.outcome!=='reconciliation_required')this.executionKey=null;}),
      catchError((error:unknown)=>{this.setError(error);this.refresh();return throwError(()=>error);}),
      finalize(()=>this.busyState.set(false))
    );
  }
  private setError(error:unknown):void{const normalized=normalizeWorkplaceError(error);this.errorState.set(`${normalized.title}: ${normalized.message}`);}
}
