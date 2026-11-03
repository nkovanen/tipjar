import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import fixture from './unsigned-request.json';
import { Review } from '../client/review';

afterEach(cleanup);
const colors = {foreground:'#eeeeee', foregroundMuted:'#bbbbbb', surface0:'#111111',
  surface1:'#222222', accent:'#dddddd', accentForeground:'#111111'};
function mount(copy: (text:string)=>Promise<void> = async()=>{}, compact = false) {
  return render(<Review theme={{colors} as never} layout={{compact,platform:'web'}} copy={copy}/>);
}
function upload(value: unknown = fixture) {
  const bytes = JSON.stringify(value, null, 2);
  fireEvent.change(screen.getByLabelText('Unsigned request JSON'), {target:{value:bytes}});
  fireEvent.click(screen.getByRole('button', {name:'Inspect request'}));
  return bytes;
}

describe('unsigned native review flow through real React Native Web primitives', () => {
  it.each([false,true])('shows complete inert data, omissions and only review/copy actions (compact=%s)', compact => {
    mount(undefined,compact);
    upload({...fixture, errors:['<script>evil()</script>\u001b\u202e'], notice:'WORKER SAYS APPROVED'});
    expect(screen.getByText(/Uploaded snapshot; potentially stale/)).toBeTruthy();
    expect(screen.getByText(/Fresh CLI verification/)).toBeTruthy();
    expect(screen.getByText(/No complete contract, evidence or payload/)).toBeTruthy();
    expect(screen.getByText(/Observation times missing/)).toBeTruthy();
    expect(screen.getByText(/Full unsigned request JSON/)).toBeTruthy();
    const data = screen.getByTestId('request-details').textContent!;
    expect(JSON.parse(data).policy_inventories).toEqual(fixture.policy_inventories);
    expect(data).toContain('evil()');
    expect(data).not.toContain('\u001b');
    expect(data).not.toContain('\u202e');
    expect(screen.getByTestId('request-details').querySelector('script')).toBeNull();
    expect(screen.queryByRole('button',{name:/authorize|approve|dispatch|publish/i})).toBeNull();
    expect(screen.getByText(/No declared agent invitation/)).toBeTruthy();
  });
  it('displays supplied timestamps without treating old observations as current', () => {
    mount();
    const changed = structuredClone(fixture);
    changed.policy_inventories[0].inventory.observed_at = '2000-01-01T00:00:00Z';
    // Unknown schema fields must be refused, not presented as verified observations.
    upload(changed);
    expect(screen.getByRole('alert').textContent).toMatch(/schema/i);
    expect(screen.queryByRole('button',{name:'Copy unsigned request'})).toBeNull();
  });
  it('invalidates old view and copy immediately on replacement, including invalid replacement', () => {
    mount(); upload();
    expect(screen.getByRole('button',{name:'Copy unsigned request'})).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Unsigned request JSON'), {target:{value:'broken'}});
    expect(screen.queryByTestId('request-details')).toBeNull();
    expect(screen.queryByRole('button',{name:'Copy unsigned request'})).toBeNull();
    fireEvent.click(screen.getByRole('button',{name:'Inspect request'}));
    expect(screen.getByRole('alert')).toBeTruthy();
    upload({...fixture, bindings:{...fixture.bindings, head_ref:'replacement'}});
    expect(screen.getByTestId('request-details').textContent).toContain('replacement');
  });
  it('keeps an inspected snapshot unchanged when the source object changes without replacement', () => {
    mount();
    const source=structuredClone(fixture);
    upload(source);
    const before=screen.getByTestId('request-details').textContent;
    source.bindings.head_ref='changed-without-upload';
    expect(screen.getByTestId('request-details').textContent).toBe(before);
    expect(screen.getByText(/potentially stale/)).toBeTruthy();
  });
  it('escapes format controls in repository summaries as well as full JSON', () => {
    mount(); upload({...fixture, bindings:{...fixture.bindings,source_repository:'acme/\u202ephotos'}});
    expect(screen.getByText(/Source:/).textContent).not.toContain('\u202e');
    expect(screen.getByText(/Source:/).textContent).toContain('\\u202e');
  });
  it('keeps proposal budgets separate from authority and rejects unbounded values', () => {
    mount(); upload();
    expect(screen.getByText(/Proposal only/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Proposed minutes'), {target:{value:'481'}});
    expect(screen.getByText(/Budget proposal invalid/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Proposed minutes'), {target:{value:'60'}});
    expect(screen.queryByText(/Budget proposal invalid/)).toBeNull();
    expect(JSON.parse(screen.getByTestId('request-details').textContent!).issued).toBe(false);
  });
  it('copies exact original unsigned bytes and reports success only after completion', async () => {
    let finish!:()=>void;
    let copied = '';
    mount(text => {copied=text; return new Promise<void>(resolve=>{finish=resolve;});});
    const original = upload();
    fireEvent.click(screen.getByRole('button',{name:'Copy unsigned request'}));
    expect(screen.queryByText('Copied unsigned request.')).toBeNull();
    expect(copied).toBe(original);
    finish();
    await waitFor(()=>expect(screen.getByText('Copied unsigned request.')).toBeTruthy());
  });
  it('reports clipboard failure without a false success', async () => {
    mount(async()=>{throw new Error('clipboard denied');}); upload();
    fireEvent.click(screen.getByRole('button',{name:'Copy unsigned request'}));
    await waitFor(()=>expect(screen.getByText(/Copy failed/)).toBeTruthy());
    expect(screen.queryByText('Copied unsigned request.')).toBeNull();
  });
  it('does not attach an old asynchronous copy result to a replacement view', async () => {
    let finish!:()=>void;
    mount(()=>new Promise<void>(resolve=>{finish=resolve;})); upload();
    fireEvent.click(screen.getByRole('button',{name:'Copy unsigned request'}));
    upload({...fixture,bindings:{...fixture.bindings,head_ref:'new-input'}});
    finish();
    await waitFor(()=>expect(screen.getByTestId('request-details').textContent).toContain('new-input'));
    expect(screen.queryByText('Copied unsigned request.')).toBeNull();
  });
});
