#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
const root=path.resolve(process.cwd(),'app/frontend/src');
const entry=path.join(root,'index.js');
const deny=['framer-motion','recharts'];
const denyOnLogin=['react-day-picker','date-fns'];
const seen=new Set();const q=[entry];const problems=[];
const importRe=/import\s+(?:[^"']+from\s+)?["']([^"']+)["']/g;
while(q.length){const f=q.pop();if(seen.has(f)||!fs.existsSync(f))continue;seen.add(f);const txt=fs.readFileSync(f,'utf8');let m;while((m=importRe.exec(txt))){const imp=m[1];if(deny.includes(imp)||denyOnLogin.includes(imp)||denyOnLogin.some(d=>imp.startsWith(d+'/'))){problems.push({file:path.relative(root,f),imp});}if(imp.startsWith('.')){let p=path.resolve(path.dirname(f),imp);for(const ext of ['','.js','.jsx']){const c=p+ext;if(fs.existsSync(c)&&fs.statSync(c).isFile()){q.push(c);break;} } for(const ext of ['/index.js','/index.jsx']){const c=p+ext;if(fs.existsSync(c)){q.push(c);break;}}}}}
if(problems.length){console.error('Denied imports reachable from initial app entry (/ and /login):');for(const p of problems){console.error(` - ${p.imp} via ${p.file}`);}process.exit(1);}
console.log('OK: deny-list modules are not reachable from initial entry graph.');
