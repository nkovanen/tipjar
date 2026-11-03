const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const model=require('../../web/model.js');
const source=fs.readFileSync(require.resolve('../../web/landing.js'),'utf8');
function page(search) {
  const target={hidden:true,children:[],textContent:'',append(...nodes){this.children.push(...nodes);}};
  vm.runInNewContext(source,{TipjarModel:model,URLSearchParams,location:{search},document:{getElementById:id=>{assert.equal(id,'repository-invitation');return target;},createElement:tag=>({tag,textContent:'',href:''})}});
  return target;
}
assert.equal(page('').hidden,true);
const valid=page('?repo=Acme%2FProject');
assert.equal(valid.hidden,false);
assert.equal(valid.children[0].href,'directory.html?repo=acme%2Fproject#maintainers');
assert.match(valid.children[0].textContent,/acme\/project/);
for(const value of ['<img src=x onerror=alert(1)>','https://evil.invalid/a','a/b?x=y','a/b#c']) {
  const invalid=page('?repo='+encodeURIComponent(value));
  assert.equal(invalid.hidden,false);
  assert.equal(invalid.children.length,0);
  assert.ok(invalid.textContent.includes(value));
}
console.log('Landing repo handoff regressions passed');
