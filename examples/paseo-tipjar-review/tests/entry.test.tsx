import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import type { ComponentType } from 'react';
import fixture from './unsigned-request.json';

// Only the host-owned clipboard/sidebar boundary is unavailable in jsdom.
vi.mock('@getpaseo/plugin/client/ui',()=>({copyText:async()=>{},SidebarRow:()=>null}));
import contribute from '../index.client';
afterEach(cleanup);

it('registers only local review surfaces and clears pasted data on host change',()=>{
  let Screen!:ComponentType<any>;
  let removed=0;
  const client=new Proxy({
    addScreen:({Component}:{Component:ComponentType<any>})=>{Screen=Component;return()=>{removed++;};},
    addSidebarHeaderItem:()=>()=>{removed++;},
  },{get(target,key){if(!(key in target)) throw Error('Unexpected host capability: '+String(key));return Reflect.get(target,key);}});
  const dispose=contribute(client as never);
  const props={theme:{colors:{foreground:'#eee',foregroundMuted:'#bbb',surface0:'#111',accent:'#ddd',accentForeground:'#111'}},
    layout:{compact:true,platform:'web'},params:{},host:{id:'host-a',label:'A'}};
  const rendered=render(<Screen {...props}/>);
  fireEvent.change(screen.getByLabelText('Unsigned request JSON'),{target:{value:JSON.stringify(fixture)}});
  fireEvent.click(screen.getByRole('button',{name:'Inspect request'}));
  expect(screen.getByTestId('request-details')).toBeTruthy();
  rendered.rerender(<Screen {...props} host={{id:'host-b',label:'B'}}/>);
  expect(screen.queryByTestId('request-details')).toBeNull();
  expect((screen.getByLabelText('Unsigned request JSON') as HTMLTextAreaElement).value).toBe('');
  dispose(); expect(removed).toBe(2);
});
