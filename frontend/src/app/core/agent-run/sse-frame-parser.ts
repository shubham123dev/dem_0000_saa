export interface SseFrame {
  readonly id: string | null;
  readonly event: string;
  readonly data: string;
  readonly retry: number | null;
}

export class SseFrameParser {
  private buffer = '';
  private pendingCarriageReturn = false;

  push(chunk: string): readonly SseFrame[] {
    this.buffer += this.normalize(chunk);
    return this.drainCompleteFrames();
  }

  finish(): readonly SseFrame[] {
    if (this.pendingCarriageReturn) {
      this.buffer += '\n';
      this.pendingCarriageReturn = false;
    }
    const complete = this.drainCompleteFrames();
    if (!this.buffer.trim()) {
      this.buffer = '';
      return complete;
    }
    const finalFrame = this.parseFrame(this.buffer);
    this.buffer = '';
    return finalFrame ? [...complete, finalFrame] : complete;
  }

  private normalize(chunk: string): string {
    let value = this.pendingCarriageReturn ? `\r${chunk}` : chunk;
    this.pendingCarriageReturn = false;
    if (value.endsWith('\r')) {
      this.pendingCarriageReturn = true;
      value = value.slice(0, -1);
    }
    return value.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  }

  private drainCompleteFrames(): SseFrame[] {
    const frames: SseFrame[] = [];
    let boundary = this.buffer.indexOf('\n\n');
    while (boundary >= 0) {
      const raw = this.buffer.slice(0, boundary);
      this.buffer = this.buffer.slice(boundary + 2);
      const frame = this.parseFrame(raw);
      if (frame) frames.push(frame);
      boundary = this.buffer.indexOf('\n\n');
    }
    return frames;
  }

  private parseFrame(raw: string): SseFrame | null {
    let id: string | null = null;
    let event = 'message';
    let retry: number | null = null;
    const data: string[] = [];
    for (const line of raw.split('\n')) {
      if (!line || line.startsWith(':')) continue;
      const delimiter = line.indexOf(':');
      const field = delimiter < 0 ? line : line.slice(0, delimiter);
      let value = delimiter < 0 ? '' : line.slice(delimiter + 1);
      if (value.startsWith(' ')) value = value.slice(1);
      if (field === 'id' && !value.includes('\0')) id = value;
      else if (field === 'event') event = value || 'message';
      else if (field === 'data') data.push(value);
      else if (field === 'retry' && /^\d+$/.test(value)) retry = Number(value);
    }
    if (data.length === 0) return null;
    return { id, event, data: data.join('\n'), retry };
  }
}
