import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output, inject, signal } from '@angular/core';
import type { OnChanges } from '@angular/core';
import { ProposalControlFacade } from '../../../core/action-control/proposal-control.facade';
import { UiBadgeComponent, Ui