const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const model=require('../../web/model.js');
const source=fs.readFileSync(require.resolve('../../web/landing.js'),'utf8');
function page(search) {
  const target={hidden:true,children:[],textContent:'',append(...nodes){this.children.push(...nodes);}};
  vm.runInNewContext(source,{
    TipjarModel:model,URLSearchParams,
    location:{search,href:'https://example.com/tipjar/'+search},
    fetch(){throw new Error('Root must not fetch data');},
    document:{getElementById:id=>{assert.equal(id,'repository-invitation');return target;},
      createElement:tag=>({tag,textContent:'',href:''}),createTextNode:text=>({tag:'#text',textContent:text})}
  });
  return target;
}
assert.equal(page('').hidden,true);
const valid=page('?repo=Acme%2FProject');
assert.equal(valid.hidden,false);
const links=valid.children.filter(node=>node.tag==='a');
assert.equal(links.length,2);
assert.equal(links[0].href,'directory.html?repo=acme%2Fproject#maintainers');
assert.match(links[0].textContent,/acme\/project/);
assert.equal(links[1].href,'https://example.com/tipjar/leaderboard.html?repo=acme%2Fproject&period=month');
assert.match(links[1].textContent,/Look for this project/);
assert.match(valid.children[0].textContent,/not a verified invitation/);
for(const query of ['?repo='+encodeURIComponent('<img src=x onerror=alert(1)>'),'?repo='+encodeURIComponent('https://evil.invalid/a'),'?repo='+encodeURIComponent('a/b?x=y'),'?repo='+encodeURIComponent('a/b#c'),'?repo=a/b&repo=a/b','?repo=a/b&repository_id=101','?repo=a/b&author_id=301']) {
  const invalid=page(query);
  assert.equal(invalid.hidden,false);
  assert.equal(invalid.children.length,0);
  assert.match(invalid.textContent,/not recognized/);
  assert.ok(!invalid.textContent.includes(query));
  assert.doesNotMatch(invalid.textContent,/<img|evil\.invalid|a\/b/);
}
console.log('Landing repo handoff regressions passed');
