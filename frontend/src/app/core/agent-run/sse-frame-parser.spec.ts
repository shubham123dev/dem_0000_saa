import { describe, expect, it } from 'vitest';
import { SseFrameParser } from './sse-frame-parser';

describe('SseFrameParser', () => {
  it('parses split chunks and multiline data', () => {
    const parser = new SseFrameParser();
    expect(parser.push('id: 4\nevent: activity.updated\ndata: {"a":')).toEqual([]);
    const frames = parser.push('1}\ndata: tail\n\n');
    expect(frames).toEqual([{ id: '4', event: 'activity.updated', data: '{"a":1}\ntail', retry: null }]);
  });

  it('preserves a CRLF delimiter split across chunks', () => {
    const parser = new SseFrameParser();
    expect(parser.push('id: 2\r')).toEqual([]);
    expect(parser.push('\nevent: answer.completed\r\ndata: {"ok":true}\r')).toEqual([]);
    expect(parser.push('\n\r\n')).toEqual([
      { id: '2', event: 'answer.completed', data: '{"ok":true}', retry: null }
    ]);
  });

  it('ignores heartbeat comments and accepts a final unterminated frame', () => {
    const parser = new SseFrameParser();
    expect(parser.push(': heartbeat\n\n')).toEqual([]);
    expect(parser.push('data: final')).toEqual([]);
    expect(parser.finish()).toEqual([{ id: null, event: 'message', data: 'final', retry: null }]);
  });
});
