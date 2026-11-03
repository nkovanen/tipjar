import type { PluginClientContext, PluginScreenProps, PluginSidebarItemProps } from '@getpaseo/plugin/client';
import { copyText, SidebarRow } from '@getpaseo/plugin/client/ui';
import { Review } from './client/review';

function Screen(props:PluginScreenProps) {
  return <Review key={props.host.id} theme={props.theme} layout={props.layout} copy={copyText}/>;
}
function Sidebar({openScreen,currentScreen}:PluginSidebarItemProps) {
  return <SidebarRow icon="Scan" active={currentScreen?.screenId==='review'}
    onPress={()=>openScreen({screenId:'review'})}/>;
}
export default function contribute(client:PluginClientContext) {
  const screen=client.addScreen({id:'review',title:'Tipjar request review',Component:Screen});
  const sidebar=client.addSidebarHeaderItem({id:'review',title:'Tipjar request review',Component:Sidebar});
  return ()=>{sidebar();screen();};
}
