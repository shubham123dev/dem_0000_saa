import { DatePipe, JsonPipe } from '@angular/common';
import { A11yModule } from '@angular/cdk/a11y';
import { ChangeDetectionStrategy, Component, HostListener, inject, signal } from '@angular/core';
import { ApprovalCenterStore } from './approval-center.store';

@Component({
  selector:'app-approval-center',standalone:true,imports:[A11yModule,DatePipe,JsonPipe],
  providers:[ApprovalCenterStore],changeDetection:ChangeDetectionStrategy.OnPush,
  templateUrl:'./approval-center.component.html',styleUrl:'./approval-center.component.scss'
})
export class ApprovalCenterComponent {
  readonly dialog=signal<'approve'|'reject'|'cancel'|'execute'|'rollback'|null>(null);
  readonly reason=signal('');
  readonly confirmation=signal('');
  readonly store=inject(ApprovalCenterStore);

  updateSearch(event:Event):void{this.store.setSearch((event.target as HTMLInputElement).value);}
  updateStatus(event:Event):void{this.store.setStatus((event.target as HTMLSelectElement).value);}
  updateReason(event:Event):void{this.reason.set((event.target as HTMLTextAreaElement).value);}
  updateConfirmation(event:Event):void{this.confirmation.set((event.target as HTMLInputElement).value);}
  open(kind:'approve'|'reject'|'cancel'|'execute'|'rollback'):void{this.reason.set('');this.confirmation.set('');this.dialog.set(kind);}
  close():void{if(!this.store.busy())this.dialog.set(null);}
  @HostListener('document:keydown.escape') closeOnEscape():void{if(this.dialog())this.close();}

  reasonRequired():boolean{
    const proposal=this.store.selected();
    return this.dialog()==='reject'&&Boolean(proposal&&proposal.risk_level!=='low');
  }

  confirmationWord():string|null{
    const proposal=this.store.selected();
    if(!proposal||proposal.risk_level!=='high')return null;
    return this.dialog()==='execute'?'EXECUTE':this.dialog()==='approve'?'APPROVE':null;
  }

  canConfirm():boolean{
    if(this.reasonRequired()&&!this.reason().trim())return false;
    const word=this.confirmationWord();
    return !word||this.confirmation().trim()===word;
  }

  confirm():void{
    const kind=this.dialog();
    if(!kind||!this.canConfirm()||this.store.busy())return;
    const reason=this.reason().trim()||null;
    const typed=this.confirmation().trim()||null;
    const succeeded=()=>this.dialog.set(null);
    if(kind==='approve')this.store.approve(reason,typed,succeeded);
    else if(kind==='reject')this.store.reject(reason,succeeded);
    else if(kind==='cancel')this.store.cancel(reason,succeeded);
    else if(kind==='execute')this.store.execute(typed,succeeded);
    else if(kind==='rollback')this.store.rollback(reason,succeeded);
  }

  statusLabel(value:string):string{return value.replaceAll('_',' ').replace(/^./,(letter)=>letter.toUpperCase());}
}
