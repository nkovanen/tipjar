import { useRef, useState } from 'react';
import { Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import type { PluginScreenProps } from '@getpaseo/plugin/client';
import { inertJson, inspectRequest, type Snapshot } from '../shared/review';

type Props = Pick<PluginScreenProps,'theme'|'layout'> & { copy:(text:string)=>Promise<void> };
export function Review({theme,layout,copy}:Props) {
  const [input,setInput]=useState('');
  const [snapshot,setSnapshot]=useState<Snapshot|null>(null);
  const [error,setError]=useState('');
  const [copyStatus,setCopyStatus]=useState('');
  const [copying,setCopying]=useState(false);
  const [minutes,setMinutes]=useState('60');
  const [inspectedAt,setInspectedAt]=useState(0);
  const generation=useRef(0);
  const color={color:theme.colors.foreground};
  const muted={color:theme.colors.foregroundMuted};
  const budgetValid=/^[1-9][0-9]*$/.test(minutes) && Number(minutes)<=480;
  function replace(text:string) {
    generation.current++; setInput(text); setSnapshot(null); setError(''); setCopyStatus(''); setCopying(false);
  }
  function inspect() {
    generation.current++; setCopyStatus(''); setCopying(false); setSnapshot(null);
    try {setSnapshot(inspectRequest(input));setInspectedAt(Date.now());setError('');}
    catch {setError('Invalid strict JSON or unsupported unsigned request schema/bindings. Input is limited to 1 MiB, depth 64 and safe integer number tokens.');}
  }
  async function copySnapshot() {
    if (!snapshot || copying) return;
    const current=generation.current; setCopying(true); setCopyStatus('');
    try {
      await copy(snapshot.original);
      if(current===generation.current) setCopyStatus('Copied unsigned request.');
    } catch {
      if(current===generation.current) setCopyStatus('Copy failed. Clipboard unavailable or denied; no success recorded.');
    } finally {if(current===generation.current) setCopying(false);}
  }
  const button={padding:12,backgroundColor:theme.colors.accent,borderRadius:6};
  return <ScrollView style={{backgroundColor:theme.colors.surface0,flex:1}}
    contentContainerStyle={{padding:layout.compact?12:24,gap:14}} keyboardShouldPersistTaps="handled">
    <Text style={[color,{fontSize:24}]}>Tipjar request review</Text>
    <Text style={color}>Unsigned inspection only. Issuance unavailable: trusted host approval support required.</Text>
    <Text style={muted}>Paste the exact external authorization-request 0.1 JSON. All supplied text is untrusted data. Nothing is fetched, executed, authorized or published.</Text>
    <TextInput accessibilityLabel="Unsigned request JSON" multiline value={input} onChangeText={replace}
      autoCorrect={false} autoCapitalize="none" style={[color,{borderWidth:1,borderColor:theme.colors.foregroundMuted,minHeight:140,padding:12}]}/>
    <Pressable accessibilityRole="button" onPress={inspect} style={button}>
      <Text style={{color:theme.colors.accentForeground}}>Inspect request</Text>
    </Pressable>
    {error?<Text accessibilityRole="alert" style={color}>{error}</Text>:null}
    {snapshot?<View style={{gap:12}}>
      <Text style={color}>Uploaded snapshot; potentially stale. Fresh CLI verification is required before any action outside this UI.</Text>
      <Text style={muted}>Inspected locally: {new Date(inspectedAt).toISOString()} (client clock; not an observation or approval time).</Text>
      <Text style={color}>Observation times missing: this request format carries no policy observation timestamps. Freshness is unknown and blocks action. This view does not watch the filesystem or APIs.</Text>
      <Text style={color}>No complete contract, evidence or payload is included in this helper view. Their hashes are reported bindings, not independently verified contents. Inspect those materials separately before any decision.</Text>
      <Text style={color}>Requested stage (untrusted): {snapshot.request.stage}</Text>
      <Text style={color}>Source: {inertJson(snapshot.request.bindings.source_repository)}; fork: {inertJson(snapshot.request.bindings.head_repository)}</Text>
      <Text style={color}>{snapshot.request.bindings.invitation_basis==='explicit-undeclared'
        ?'No declared agent invitation; offering a draft needs explicit human acknowledgement outside this viewer. Maintainers may decline.'
        :'Reported welcome is an invitation subject to all repository rules; it is not source approval.'}</Text>
      <Text style={muted}>Canonical unsigned request SHA-256 (not contract verification or consent): {snapshot.requestHash}</Text>
      <Text style={color}>Proposal only: one task, 60 minutes by default; maximum 480 minutes. These controls grant and enforce no budget.</Text>
      <TextInput accessibilityLabel="Proposed minutes" value={minutes} onChangeText={setMinutes} keyboardType="number-pad"
        style={[color,{borderWidth:1,borderColor:theme.colors.foregroundMuted,padding:10}]}/>
      <Text style={muted}>{budgetValid?`Proposed deadline: ${new Date(inspectedAt+Number(minutes)*60000).toISOString()} (from inspection; not enforced)`:'Budget proposal invalid: enter 1–480 whole minutes.'}</Text>
      <Text style={color}>Full unsigned request JSON, including all inventories, unresolved fields and stage blockers (controls escaped):</Text>
      <Text selectable testID="request-details" style={color}>{snapshot.display}</Text>
      <Pressable accessibilityRole="button" disabled={copying} accessibilityState={{disabled:copying}}
        onPress={()=>{void copySnapshot();}} style={[button,{opacity:copying?0.5:1}]}>
        <Text style={{color:theme.colors.accentForeground}}>{copying?'Copying…':'Copy unsigned request'}</Text>
      </Pressable>
      {copyStatus?<Text accessibilityLiveRegion="polite" style={color}>{copyStatus}</Text>:null}
    </View>:null}
  </ScrollView>;
}
