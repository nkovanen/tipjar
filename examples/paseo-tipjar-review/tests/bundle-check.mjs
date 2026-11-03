import { build } from 'esbuild';
const result=await build({
  entryPoints:['index.client.tsx'],bundle:true,write:false,platform:'browser',target:'es2022',
  format:'esm',metafile:true,
  external:['react','react/jsx-runtime','react-native','@getpaseo/plugin/client','@getpaseo/plugin/client/ui'],
});
const imports=Object.values(result.metafile.outputs).flatMap(output=>output.imports.map(item=>item.path));
if(imports.some(name=>name.startsWith('node:'))) throw Error('Node runtime in client bundle');
console.log('Browser-target bundle passed:',result.outputFiles[0].contents.length,'bytes');
console.log('External host imports:',imports.join(', '));
